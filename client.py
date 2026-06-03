import socket
import threading
import sys

# indirizzo e porta del server
HOST = "127.0.0.1"
PORT = 5555


def receive_messages(client_socket):
    """Riceve i messaggi dal server e li stampa a schermo."""
    while True:
        try:
            message = client_socket.recv(4096).decode("utf-8")
            if not message:
                # il server ha chiuso la connessione
                print("\nConnessione chiusa dal server.")
                break
            print(message)
        except:
            # errore di connessione
            print("\nConnessione persa con il server.")
            break


def start_client():
    """Avvia il client e gestisce l'invio dei messaggi."""
    # chiedo il nome utente
    username = input("Inserisci il tuo username: ").strip()
    if not username:
        print("Username non valido.")
        return

    # chiedo il nome della stanza
    room_name = input("Inserisci il nome della stanza: ").strip()
    if not room_name:
        print("Nome stanza non valido.")
        return

    # creo il socket del client
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # provo a connettermi al server
    try:
        client_socket.connect((HOST, PORT))
        print(f"Connesso al server {HOST}:{PORT}")
    except:
        print("Impossibile connettersi al server. È avviato?")
        return

    # invio il nome utente al server (primo messaggio)
    client_socket.send(username.encode("utf-8"))

    # piccola pausa per evitare che i messaggi si uniscano
    import time
    time.sleep(0.1)

    # invio il nome della stanza al server (secondo messaggio)
    client_socket.send(room_name.encode("utf-8"))

    # avvio il thread che riceve i messaggi in background
    thread = threading.Thread(target=receive_messages, args=(client_socket,))
    thread.daemon = True
    thread.start()

    # istruzioni per l'utente
    print("\n--- Comandi disponibili ---")
    print("/msg username messaggio  → messaggio privato")
    print("/list                    → lista utenti nella stanza")
    print("/quit                    → esci dalla chat")
    print("---------------------------\n")

    # ciclo principale: leggo l'input dell'utente e lo invio al server
    while True:
        try:
            message = input()
            if not message:
                continue

            # invio il messaggio al server
            client_socket.send(message.encode("utf-8"))

            # se il comando è /quit, esco
            if message.strip() == "/quit":
                print("Disconnessione in corso...")
                client_socket.close()
                sys.exit(0)

        except KeyboardInterrupt:
            # l'utente ha premuto Ctrl+C
            print("\nDisconnessione in corso...")
            try:
                client_socket.send("/quit".encode("utf-8"))
            except:
                pass
            client_socket.close()
            sys.exit(0)
        except:
            # errore generico (connessione persa)
            print("Errore di connessione.")
            client_socket.close()
            sys.exit(1)


# --- Avvio del client ---
if __name__ == "__main__":
    start_client()
