import socket
import threading
import sys
import time

# indirizzo e porta del server
HOST = "127.0.0.1"
PORT = 5555


def ricevi_messaggi(sock):
    """Riceve i messaggi dal server e li stampa. Gira in un thread separato."""
    while True:
        try:
            messaggio = sock.recv(4096).decode("utf-8")
            if not messaggio:
                print("\nConnessione chiusa dal server.")
                break
            print(messaggio, end="")
        except:
            print("\nConnessione persa.")
            break


def avvia_client():
    """Avvia il client della chat."""
    # chiedo il nome utente
    username = input("Inserisci il tuo username: ").strip()
    if not username:
        print("Username non valido.")
        return

    # chiedo il nome della stanza
    nome_stanza = input("Inserisci il nome della stanza: ").strip()
    if not nome_stanza:
        print("Nome stanza non valido.")
        return

    # creo il socket e mi connetto al server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, PORT))
        print(f"Connesso al server su {HOST}:{PORT}\n")
    except:
        print("Impossibile connettersi al server. E' avviato?")
        return

    # invio il nome utente al server
    sock.send(username.encode("utf-8"))

    # piccola pausa per evitare che i messaggi si mescolino
    time.sleep(0.1)

    # invio il nome della stanza al server
    sock.send(nome_stanza.encode("utf-8"))

    # avvio il thread che ascolta i messaggi in arrivo dal server
    thread = threading.Thread(target=ricevi_messaggi, args=(sock,))
    thread.daemon = True
    thread.start()

    # spiego i comandi disponibili
    print("--- Comandi ---")
    print("/msg utente testo  → messaggio privato")
    print("/list              → lista utenti nella stanza")
    print("/game              → avvia una partita di Tris nella stanza")
    print("/mossa N           → gioca nella cella N (1-9) durante una partita")
    print("/quit              → esci dalla chat")
    print("---------------\n")

    # ciclo principale: leggo l'input e lo invio al server
    while True:
        try:
            comando = input()
            if not comando:
                continue

            sock.send(comando.encode("utf-8"))

            if comando.strip() == "/quit":
                print("Uscita...")
                sock.close()
                sys.exit(0)

        except KeyboardInterrupt:
            print("\nUscita...")
            try:
                sock.send("/quit".encode("utf-8"))
            except:
                pass
            sock.close()
            sys.exit(0)
        except:
            print("Connessione persa.")
            sock.close()
            sys.exit(1)


# --- avvio del client ---
if __name__ == "__main__":
    avvia_client()
