import socket
import threading
import time

# indirizzo e porta del server
HOST = "127.0.0.1"
PORT = 5555

# dizionario delle stanze: nome_stanza -> lista di socket dei client
rooms = {}

# dizionario dei client connessi: socket -> username
clients = {}

# dizionario: socket -> nome della stanza in cui si trova
client_rooms = {}

# dizionario delle partite di tris in corso: nome_stanza -> info partita
# info partita: { 'board': [...], 'turno': socket, 'giocatori': [s1, s2], 'simboli': {s1: 'X', s2: 'O'} }
partite = {}


# ===================== FUNZIONI TRIS =====================

def mostra_scacchiera(board):
    """Restituisce la scacchiera come stringa da inviare ai client."""
    b = board
    riga = "\n"
    riga += f" {b[0]} | {b[1]} | {b[2]} \n"
    riga += "---+---+---\n"
    riga += f" {b[3]} | {b[4]} | {b[5]} \n"
    riga += "---+---+---\n"
    riga += f" {b[6]} | {b[7]} | {b[8]} \n"
    return riga


def controlla_vincitore(board):
    """Controlla se qualcuno ha vinto. Restituisce 'X', 'O' oppure None."""
    combinazioni = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # righe
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # colonne
        [0, 4, 8], [2, 4, 6]              # diagonali
    ]
    for combo in combinazioni:
        a, b, c = combo
        if board[a] != " " and board[a] == board[b] == board[c]:
            return board[a]
    return None


def pareggio(board):
    """Controlla se tutte le celle sono occupate (pareggio)."""
    return all(cella != " " for cella in board)


def avvia_partita(sock):
    """Avvia una partita di tris nella stanza del richiedente."""
    nome_stanza = client_rooms[sock]

    # controllo se c'è già una partita in corso in questa stanza
    if nome_stanza in partite:
        invia(sock, "C'e' gia' una partita in corso in questa stanza!\n")
        return

    # controllo che ci siano almeno 2 giocatori
    if len(rooms[nome_stanza]) < 2:
        invia(sock, "Servono almeno 2 giocatori nella stanza per iniziare!\n")
        return

    # prendo i primi due giocatori della stanza
    g1 = rooms[nome_stanza][0]
    g2 = rooms[nome_stanza][1]

    # creo la partita
    partite[nome_stanza] = {
        'board': [' '] * 9,
        'turno': g1,
        'giocatori': [g1, g2],
        'simboli': {g1: 'X', g2: 'O'}
    }

    nome1 = clients[g1]
    nome2 = clients[g2]

    # avviso tutti nella stanza
    broadcast(f"\n=== PARTITA DI TRIS: {nome1} (X) vs {nome2} (O) ===\n", nome_stanza)
    invia(g1, "Tu sei X. Tocca a te per primo!\n")
    invia(g2, "Tu sei O. Aspetta il tuo turno.\n")
    broadcast(mostra_scacchiera(partite[nome_stanza]['board']), nome_stanza)
    broadcast("Usa /mossa N (da 1 a 9) per giocare.\n", nome_stanza)

    print(f"Partita di Tris avviata nella stanza '{nome_stanza}': {nome1} vs {nome2}")


def gestisci_mossa(sock, numero_cella):
    """Gestisce la mossa di un giocatore."""
    nome_stanza = client_rooms[sock]
    username = clients[sock]

    # controllo se c'è una partita in questa stanza
    if nome_stanza not in partite:
        invia(sock, "Non c'e' nessuna partita in corso. Usa /game per iniziarne una.\n")
        return

    partita = partite[nome_stanza]

    # controllo che questo giocatore faccia parte della partita
    if sock not in partita['simboli']:
        invia(sock, "Non sei uno dei giocatori di questa partita.\n")
        return

    # controllo il turno
    if partita['turno'] != sock:
        invia(sock, "Non e' il tuo turno! Aspetta.\n")
        return

    # controllo validita' della cella
    if numero_cella < 1 or numero_cella > 9:
        invia(sock, "Numero non valido! Scegli una cella da 1 a 9.\n")
        return

    indice = numero_cella - 1
    if partita['board'][indice] != " ":
        invia(sock, "Cella gia' occupata! Scegline un'altra.\n")
        return

    # eseguo la mossa
    simbolo = partita['simboli'][sock]
    partita['board'][indice] = simbolo
    print(f"{username} gioca in posizione {numero_cella} nella stanza '{nome_stanza}'")

    # mando la scacchiera aggiornata a tutti nella stanza
    broadcast(mostra_scacchiera(partita['board']), nome_stanza)

    # controllo se c'e' un vincitore
    vincitore_simbolo = controlla_vincitore(partita['board'])
    if vincitore_simbolo is not None:
        g1, g2 = partita['giocatori']

        # capisco chi ha vinto e chi ha perso
        if simbolo == partita['simboli'][g1]:
            vincitore_sock = g1
            perdente_sock = g2
        else:
            vincitore_sock = g2
            perdente_sock = g1

        nome_vincitore = clients[vincitore_sock]
        nome_perdente = clients[perdente_sock]

        # messaggi point-to-point: solo al vincitore e solo al perdente
        invia(vincitore_sock, f"\n🏆 HAI VINTO! Complimenti {nome_vincitore}!\n")
        invia(perdente_sock, f"\n😞 HAI PERSO! {nome_vincitore} ha vinto questa volta.\n")

        # annuncio pubblico a tutta la stanza
        broadcast(f"\n=== {nome_vincitore} ha vinto la partita di Tris! ===\n", nome_stanza)
        broadcast("Potete continuare a chattare o usare /game per una nuova partita.\n", nome_stanza)

        del partite[nome_stanza]
        print(f"Vince {nome_vincitore} nella stanza '{nome_stanza}'")
        return

    # controllo pareggio
    if pareggio(partita['board']):
        broadcast("\n=== Pareggio! Nessuno ha vinto. ===\n", nome_stanza)
        broadcast("Potete continuare a chattare o usare /game per una nuova partita.\n", nome_stanza)
        del partite[nome_stanza]
        print(f"Pareggio nella stanza '{nome_stanza}'")
        return

    # passo il turno all'altro giocatore
    g1, g2 = partita['giocatori']
    prossimo = g2 if sock == g1 else g1
    partita['turno'] = prossimo
    invia(prossimo, f"Tocca a te ({clients[prossimo]})!\n")


# ===================== FUNZIONI CHAT =====================

def broadcast(messaggio, nome_stanza, escludi=None):
    """Invia un messaggio a tutti i client nella stanza (tranne escludi)."""
    if nome_stanza in rooms:
        for sock in rooms[nome_stanza]:
            if sock != escludi:
                try:
                    sock.send(messaggio.encode("utf-8"))
                except:
                    pass


def invia(sock, messaggio):
    """Invia un messaggio a un solo client (point-to-point)."""
    try:
        sock.send(messaggio.encode("utf-8"))
    except:
        pass


def rimuovi_client(sock):
    """Rimuove il client dalla stanza e dai dizionari globali."""
    if sock in client_rooms:
        nome_stanza = client_rooms[sock]
        username = clients.get(sock, "sconosciuto")

        # se c'era una partita con questo giocatore, la annullo
        if nome_stanza in partite:
            partita = partite[nome_stanza]
            if sock in partita['simboli']:
                broadcast(f"\n=== {username} si e' disconnesso. Partita annullata. ===\n", nome_stanza)
                broadcast("Potete usare /game per una nuova partita.\n", nome_stanza)
                del partite[nome_stanza]

        # rimuovo il client dalla stanza
        if nome_stanza in rooms and sock in rooms[nome_stanza]:
            rooms[nome_stanza].remove(sock)

        # se la stanza e' vuota la elimino
        if nome_stanza in rooms and len(rooms[nome_stanza]) == 0:
            del rooms[nome_stanza]
            print(f"Stanza '{nome_stanza}' eliminata (vuota)")

        broadcast(f"{username} ha lasciato la stanza.\n", nome_stanza)
        print(f"{username} disconnesso dalla stanza '{nome_stanza}'")
        del client_rooms[sock]

    if sock in clients:
        del clients[sock]

    try:
        sock.close()
    except:
        pass


def gestisci_client(sock):
    """Gestisce la connessione di un singolo client."""
    try:
        # ricevo il nome utente (primo messaggio)
        username = sock.recv(1024).decode("utf-8").strip()
        if not username:
            sock.close()
            return

        # ricevo il nome della stanza (secondo messaggio)
        nome_stanza = sock.recv(1024).decode("utf-8").strip()
        if not nome_stanza:
            sock.close()
            return

        # salvo il client nei dizionari
        clients[sock] = username
        client_rooms[sock] = nome_stanza

        # creo la stanza se non esiste
        if nome_stanza not in rooms:
            rooms[nome_stanza] = []
            print(f"Stanza '{nome_stanza}' creata")

        rooms[nome_stanza].append(sock)
        print(f"{username} e' entrato nella stanza '{nome_stanza}'")

        # messaggio di benvenuto
        invia(sock, f"Benvenuto nella stanza '{nome_stanza}', {username}!\n")
        invia(sock, "Comandi: /msg utente testo | /list | /game | /mossa N | /quit\n")
        broadcast(f"{username} e' entrato nella stanza.\n", nome_stanza, escludi=sock)

    except:
        sock.close()
        return

    # ciclo principale: ricevo i messaggi dal client
    while True:
        try:
            dato = sock.recv(4096).decode("utf-8").strip()
            if not dato:
                break

            if dato == "/quit":
                break

            elif dato == "/list":
                nome_stanza = client_rooms[sock]
                nomi = [clients[s] for s in rooms[nome_stanza]]
                invia(sock, f"Utenti nella stanza '{nome_stanza}': {', '.join(nomi)}\n")

            elif dato == "/game":
                # avvia una partita di tris nella stanza
                avvia_partita(sock)

            elif dato.startswith("/mossa "):
                # il giocatore vuole fare una mossa nel tris
                parti = dato.split(" ")
                if len(parti) == 2 and parti[1].isdigit():
                    gestisci_mossa(sock, int(parti[1]))
                else:
                    invia(sock, "Uso: /mossa N (dove N e' un numero da 1 a 9)\n")

            elif dato.startswith("/msg "):
                # messaggio privato (point-to-point)
                parti = dato.split(" ", 2)
                if len(parti) >= 3:
                    target_username = parti[1]
                    messaggio = parti[2]
                    target_sock = None
                    for s, n in clients.items():
                        if n == target_username:
                            target_sock = s
                            break
                    if target_sock:
                        invia(target_sock, f"[Privato da {clients[sock]}]: {messaggio}\n")
                    else:
                        invia(sock, f"Utente '{target_username}' non trovato.\n")
                else:
                    invia(sock, "Uso: /msg utente messaggio\n")

            else:
                # messaggio normale: broadcast a tutta la stanza
                nome_stanza = client_rooms[sock]
                broadcast(f"{username}: {dato}", nome_stanza, escludi=sock)

        except:
            break

    # il client si e' disconnesso
    rimuovi_client(sock)


def avvia_server():
    """Avvia il server e accetta le connessioni."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen()

    print(f"Server avviato su {HOST}:{PORT}")
    print("In attesa di connessioni...\n")

    while True:
        sock, indirizzo = server_socket.accept()
        print(f"Nuova connessione da {indirizzo}")
        thread = threading.Thread(target=gestisci_client, args=(sock,))
        thread.daemon = True
        thread.start()


# --- avvio del server ---
if __name__ == "__main__":
    avvia_server()
