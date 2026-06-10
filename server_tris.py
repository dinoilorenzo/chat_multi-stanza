import socket
import threading

# indirizzo e porta del server
HOST = "127.0.0.1"
PORT = 5556

# dizionario dei tavoli: nome_tavolo -> lista di socket (massimo 2 giocatori)
tavoli = {}

# dizionario: socket -> username del giocatore
giocatori = {}

# dizionario: socket -> nome del tavolo in cui si trova
giocatore_tavolo = {}

# dizionario: nome_tavolo -> lista di 9 celle (la scacchiera del tris)
# ogni cella puo' essere " ", "X" o "O"
scacchiere = {}

# dizionario: nome_tavolo -> socket del giocatore che deve muovere adesso
turno_di = {}


def mostra_scacchiera(nome_tavolo):
    """Restituisce la scacchiera come stringa da inviare ai client."""
    b = scacchiere[nome_tavolo]
    # disegno la griglia del tris
    riga = "\n"
    riga += f" {b[0]} | {b[1]} | {b[2]} \n"
    riga += "---+---+---\n"
    riga += f" {b[3]} | {b[4]} | {b[5]} \n"
    riga += "---+---+---\n"
    riga += f" {b[6]} | {b[7]} | {b[8]} \n"
    return riga


def controlla_vincitore(nome_tavolo):
    """Controlla se qualcuno ha vinto. Restituisce 'X', 'O' oppure None."""
    b = scacchiere[nome_tavolo]

    # tutte le combinazioni vincenti (righe, colonne, diagonali)
    combinazioni = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # righe
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # colonne
        [0, 4, 8], [2, 4, 6]              # diagonali
    ]

    for combo in combinazioni:
        a, c_mid, cc = combo
        if b[a] != " " and b[a] == b[c_mid] == b[cc]:
            return b[a]  # restituisco il simbolo vincente

    return None


def pareggio(nome_tavolo):
    """Controlla se la scacchiera e' piena (pareggio)."""
    b = scacchiere[nome_tavolo]
    # se non c'e' nessuna cella vuota e nessun vincitore, e' pareggio
    for cella in b:
        if cella == " ":
            return False
    return True


def invia_a_tutti(nome_tavolo, messaggio):
    """Invia un messaggio a entrambi i giocatori del tavolo (broadcast sul tavolo)."""
    if nome_tavolo in tavoli:
        for sock in tavoli[nome_tavolo]:
            try:
                sock.send(messaggio.encode("utf-8"))
            except:
                pass


def invia_a_uno(sock, messaggio):
    """Invia un messaggio a un solo giocatore (point-to-point)."""
    try:
        sock.send(messaggio.encode("utf-8"))
    except:
        pass


def rimuovi_giocatore(sock):
    """Rimuove il giocatore dal tavolo e dai dizionari."""
    if sock in giocatore_tavolo:
        nome_tavolo = giocatore_tavolo[sock]
        username = giocatori.get(sock, "sconosciuto")

        # avviso l'altro giocatore che questo se ne e' andato
        invia_a_tutti(nome_tavolo, f"\n{username} si e' disconnesso. Partita annullata.\n")
        print(f"{username} si e' disconnesso dal tavolo '{nome_tavolo}'")

        # rimuovo il giocatore dalla lista del tavolo
        if nome_tavolo in tavoli:
            if sock in tavoli[nome_tavolo]:
                tavoli[nome_tavolo].remove(sock)
            # se il tavolo e' rimasto vuoto, lo elimino tutto
            if len(tavoli[nome_tavolo]) == 0:
                del tavoli[nome_tavolo]
                if nome_tavolo in scacchiere:
                    del scacchiere[nome_tavolo]
                if nome_tavolo in turno_di:
                    del turno_di[nome_tavolo]
                print(f"Tavolo '{nome_tavolo}' eliminato")

        del giocatore_tavolo[sock]

    if sock in giocatori:
        del giocatori[sock]

    try:
        sock.close()
    except:
        pass


def avvia_partita(nome_tavolo):
    """Avvia una nuova partita: inizializza la scacchiera e decide chi inizia."""
    # creo una scacchiera vuota con 9 celle
    scacchiere[nome_tavolo] = [" "] * 9

    # il primo giocatore entrato nel tavolo gioca con X e inizia
    primo_giocatore = tavoli[nome_tavolo][0]
    secondo_giocatore = tavoli[nome_tavolo][1]
    turno_di[nome_tavolo] = primo_giocatore

    nome1 = giocatori[primo_giocatore]
    nome2 = giocatori[secondo_giocatore]

    print(f"Partita avviata sul tavolo '{nome_tavolo}': {nome1} (X) vs {nome2} (O)")

    # avviso entrambi i giocatori che la partita e' iniziata
    invia_a_uno(primo_giocatore, f"\nPartita iniziata! Tu sei X. Giochi tu per primo!\n")
    invia_a_uno(secondo_giocatore, f"\nPartita iniziata! Tu sei O. Aspetta il tuo turno.\n")

    # mando la scacchiera iniziale a entrambi
    scacchiera_str = mostra_scacchiera(nome_tavolo)
    invia_a_tutti(nome_tavolo, scacchiera_str)
    invia_a_tutti(nome_tavolo, f"Le celle sono numerate da 1 a 9. Usa /mossa N per giocare.\n")
    invia_a_uno(primo_giocatore, f"Tocca a te ({nome1})!\n")


def gestisci_mossa(sock, numero_cella):
    """Gestisce la mossa di un giocatore."""
    nome_tavolo = giocatore_tavolo[sock]
    username = giocatori[sock]

    # controllo che sia il turno di questo giocatore (point-to-point: rispondo solo a lui)
    if turno_di[nome_tavolo] != sock:
        invia_a_uno(sock, "Non e' il tuo turno! Aspetta.\n")
        return

    # controllo che il numero della cella sia valido (da 1 a 9)
    if numero_cella < 1 or numero_cella > 9:
        invia_a_uno(sock, "Numero non valido! Scegli una cella da 1 a 9.\n")
        return

    # le celle nel dizionario vanno da 0 a 8, quindi sottraggo 1
    indice = numero_cella - 1

    # controllo che la cella sia libera
    if scacchiere[nome_tavolo][indice] != " ":
        invia_a_uno(sock, "Cella gia' occupata! Scegli un'altra.\n")
        return

    # capisco quale simbolo usa questo giocatore
    # il primo giocatore del tavolo usa X, il secondo usa O
    if sock == tavoli[nome_tavolo][0]:
        simbolo = "X"
    else:
        simbolo = "O"

    # aggiorno la scacchiera
    scacchiere[nome_tavolo][indice] = simbolo
    print(f"{username} ha giocato in posizione {numero_cella} sul tavolo '{nome_tavolo}'")

    # mando la scacchiera aggiornata a tutti e due (broadcast sul tavolo)
    scacchiera_str = mostra_scacchiera(nome_tavolo)
    invia_a_tutti(nome_tavolo, scacchiera_str)

    # controllo se c'e' un vincitore
    vincitore = controlla_vincitore(nome_tavolo)
    if vincitore is not None:
        invia_a_tutti(nome_tavolo, f"\n{username} ha vinto con {vincitore}! Partita finita.\n")
        print(f"Partita finita sul tavolo '{nome_tavolo}': vince {username}")
        # resetto la scacchiera per una nuova partita
        scacchiere[nome_tavolo] = [" "] * 9
        turno_di[nome_tavolo] = tavoli[nome_tavolo][0]
        invia_a_tutti(nome_tavolo, "Nuova partita! Digita /mossa N per giocare.\n")
        invia_a_tutti(nome_tavolo, mostra_scacchiera(nome_tavolo))
        invia_a_uno(tavoli[nome_tavolo][0], f"Tocca a {giocatori[tavoli[nome_tavolo][0]]}!\n")
        return

    # controllo se e' pareggio
    if pareggio(nome_tavolo):
        invia_a_tutti(nome_tavolo, "\nPareggio! Nessuno ha vinto.\n")
        print(f"Pareggio sul tavolo '{nome_tavolo}'")
        # resetto la scacchiera per una nuova partita
        scacchiere[nome_tavolo] = [" "] * 9
        turno_di[nome_tavolo] = tavoli[nome_tavolo][0]
        invia_a_tutti(nome_tavolo, "Nuova partita! Digita /mossa N per giocare.\n")
        invia_a_tutti(nome_tavolo, mostra_scacchiera(nome_tavolo))
        invia_a_uno(tavoli[nome_tavolo][0], f"Tocca a {giocatori[tavoli[nome_tavolo][0]]}!\n")
        return

    # passo il turno all'altro giocatore
    if sock == tavoli[nome_tavolo][0]:
        prossimo = tavoli[nome_tavolo][1]
    else:
        prossimo = tavoli[nome_tavolo][0]

    turno_di[nome_tavolo] = prossimo
    invia_a_uno(prossimo, f"Tocca a te ({giocatori[prossimo]})!\n")


def gestisci_client(sock):
    """Gestisce la connessione di un singolo client."""
    try:
        # ricevo il nome utente
        username = sock.recv(1024).decode("utf-8").strip()
        if not username:
            sock.close()
            return

        # ricevo il nome del tavolo
        nome_tavolo = sock.recv(1024).decode("utf-8").strip()
        if not nome_tavolo:
            sock.close()
            return

        # salvo le informazioni del giocatore
        giocatori[sock] = username
        giocatore_tavolo[sock] = nome_tavolo

        # creo il tavolo se non esiste ancora
        if nome_tavolo not in tavoli:
            tavoli[nome_tavolo] = []
            print(f"Tavolo '{nome_tavolo}' creato")

        # controllo che il tavolo non sia gia' pieno (massimo 2 giocatori)
        if len(tavoli[nome_tavolo]) >= 2:
            invia_a_uno(sock, "Tavolo pieno! Scegli un altro tavolo.\n")
            del giocatori[sock]
            del giocatore_tavolo[sock]
            sock.close()
            return

        # aggiungo il giocatore al tavolo
        tavoli[nome_tavolo].append(sock)
        print(f"{username} si e' unito al tavolo '{nome_tavolo}'")
        invia_a_uno(sock, f"Sei entrato nel tavolo '{nome_tavolo}'. In attesa dell'avversario...\n")

        # se siamo in due, la partita puo' iniziare!
        if len(tavoli[nome_tavolo]) == 2:
            avvia_partita(nome_tavolo)

    except:
        sock.close()
        return

    # ciclo principale: ricevo i comandi del giocatore
    while True:
        try:
            dato = sock.recv(1024).decode("utf-8").strip()
            if not dato:
                break

            if dato == "/quit":
                break

            elif dato.startswith("/mossa "):
                # il giocatore vuole fare una mossa
                parti = dato.split(" ")
                if len(parti) == 2 and parti[1].isdigit():
                    numero = int(parti[1])
                    gestisci_mossa(sock, numero)
                else:
                    invia_a_uno(sock, "Uso: /mossa N (dove N e' un numero da 1 a 9)\n")

            else:
                invia_a_uno(sock, "Comando non riconosciuto. Usa /mossa N per giocare.\n")

        except:
            break

    # il giocatore si e' disconnesso
    rimuovi_giocatore(sock)


def avvia_server():
    """Avvia il server e aspetta le connessioni."""
    # creo il socket TCP
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen()

    print(f"Server Tris avviato su {HOST}:{PORT}")
    print("In attesa di giocatori...\n")

    while True:
        # aspetto una nuova connessione
        sock, indirizzo = server_socket.accept()
        print(f"Nuova connessione da {indirizzo}")

        # creo un thread separato per ogni giocatore
        thread = threading.Thread(target=gestisci_client, args=(sock,))
        thread.daemon = True
        thread.start()


# --- avvio del server ---
if __name__ == "__main__":
    avvia_server()
