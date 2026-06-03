import socket
import threading

# --- Variabili globali ---

# dizionario delle stanze: nome_stanza -> lista di socket dei client
rooms = {}

# dizionario dei client connessi: socket -> username
clients = {}

# dizionario che tiene traccia della stanza di ogni client: socket -> nome_stanza
client_rooms = {}

# indirizzo e porta del server
HOST = "127.0.0.1"
PORT = 5555


def broadcast(message, room_name, sender_socket=None):
    """Invia un messaggio a tutti i client nella stanza, tranne al mittente."""
    if room_name in rooms:
        for client in rooms[room_name]:
            if client != sender_socket:
                try:
                    client.send(message.encode("utf-8"))
                except:
                    # se non riesce a inviare, ignora
                    pass


def send_private_message(sender_socket, target_username, message):
    """Invia un messaggio privato a un utente specifico."""
    # cerco il socket dell'utente destinatario
    target_socket = None
    for sock, name in clients.items():
        if name == target_username:
            target_socket = sock
            break

    if target_socket is not None:
        sender_name = clients[sender_socket]
        private_msg = f"[Privato da {sender_name}]: {message}"
        try:
            target_socket.send(private_msg.encode("utf-8"))
        except:
            pass
    else:
        # avviso il mittente che l'utente non esiste
        try:
            sender_socket.send(f"Utente '{target_username}' non trovato.\n".encode("utf-8"))
        except:
            pass


def send_user_list(client_socket):
    """Invia la lista degli utenti nella stanza del client."""
    room_name = client_rooms[client_socket]
    if room_name in rooms:
        # creo la lista dei nomi
        user_list = []
        for sock in rooms[room_name]:
            user_list.append(clients[sock])
        lista = ", ".join(user_list)
        msg = f"Utenti nella stanza '{room_name}': {lista}\n"
    else:
        msg = "Stanza non trovata.\n"

    try:
        client_socket.send(msg.encode("utf-8"))
    except:
        pass


def remove_client(client_socket):
    """Rimuove un client dalla stanza e dal dizionario dei client."""
    if client_socket in client_rooms:
        room_name = client_rooms[client_socket]
        username = clients.get(client_socket, "sconosciuto")

        # rimuovo il client dalla stanza
        if room_name in rooms:
            if client_socket in rooms[room_name]:
                rooms[room_name].remove(client_socket)
            # se la stanza è vuota, la elimino
            if len(rooms[room_name]) == 0:
                del rooms[room_name]
                print(f"Stanza '{room_name}' eliminata (vuota)")

        # avviso gli altri nella stanza
        broadcast(f"{username} ha lasciato la stanza.\n", room_name)
        print(f"{username} disconnesso dalla stanza '{room_name}'")

        # rimuovo dai dizionari globali
        del client_rooms[client_socket]

    if client_socket in clients:
        del clients[client_socket]

    # chiudo il socket
    try:
        client_socket.close()
    except:
        pass


def handle_client(client_socket):
    """Gestisce la comunicazione con un singolo client."""
    try:
        # ricevo il nome utente (primo messaggio)
        username = client_socket.recv(1024).decode("utf-8").strip()
        if not username:
            client_socket.close()
            return

        # ricevo il nome della stanza (secondo messaggio)
        room_name = client_socket.recv(1024).decode("utf-8").strip()
        if not room_name:
            client_socket.close()
            return

        # salvo il client nei dizionari
        clients[client_socket] = username
        client_rooms[client_socket] = room_name

        # creo la stanza se non esiste
        if room_name not in rooms:
            rooms[room_name] = []
            print(f"Stanza '{room_name}' creata")

        # aggiungo il client alla stanza
        rooms[room_name].append(client_socket)
        print(f"{username} è entrato nella stanza '{room_name}'")

        # avviso il client che è entrato
        welcome = f"Benvenuto nella stanza '{room_name}', {username}!\n"
        client_socket.send(welcome.encode("utf-8"))

        # avviso gli altri nella stanza
        broadcast(f"{username} è entrato nella stanza.\n", room_name, client_socket)

    except:
        # se qualcosa va storto durante il setup, chiudo
        client_socket.close()
        return

    # ciclo principale: ricevo i messaggi dal client
    while True:
        try:
            data = client_socket.recv(4096).decode("utf-8").strip()
            if not data:
                # il client si è disconnesso
                break

            # controllo se è un comando
            if data == "/quit":
                break

            elif data == "/list":
                send_user_list(client_socket)

            elif data.startswith("/msg "):
                # formato: /msg username messaggio
                parts = data.split(" ", 2)
                if len(parts) >= 3:
                    target_username = parts[1]
                    message = parts[2]
                    send_private_message(client_socket, target_username, message)
                else:
                    client_socket.send("Uso: /msg username messaggio\n".encode("utf-8"))

            else:
                # messaggio normale: lo invio a tutta la stanza
                room_name = client_rooms[client_socket]
                full_message = f"{username}: {data}"
                broadcast(full_message, room_name, client_socket)

        except:
            # errore di connessione
            break

    # il client si è disconnesso
    remove_client(client_socket)


def start_server():
    """Avvia il server e accetta le connessioni."""
    # creo il socket del server
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # permette di riutilizzare l'indirizzo subito dopo la chiusura
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # associo il socket all'indirizzo e alla porta
    server_socket.bind((HOST, PORT))

    # metto il server in ascolto
    server_socket.listen()
    print(f"Server avviato su {HOST}:{PORT}")
    print("In attesa di connessioni...\n")

    while True:
        # accetto una nuova connessione
        client_socket, address = server_socket.accept()
        print(f"Nuova connessione da {address}")

        # creo un thread per gestire il client
        thread = threading.Thread(target=handle_client, args=(client_socket,))
        thread.daemon = True
        thread.start()


# --- Avvio del server ---
if __name__ == "__main__":
    start_server()
