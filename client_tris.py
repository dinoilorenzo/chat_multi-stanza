import socket
import threading
import sys

# indirizzo e porta del server
HOST = "127.0.0.1"
PORT = 5556


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
    """Avvia il client del tris."""
    # chiedo il nome utente
    username = input("Inserisci il tuo nome: ").strip()
    if not username:
        print("Nome non valido.")
        return

    # chiedo il tavolo a cui unirsi
    nome_tavolo = input("Inserisci il nome del tavolo (es. Tavolo-1): ").strip()
    if not nome_tavolo:
        print("Nome tavolo non valido.")
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
    import time
    time.sleep(0.1)

    # invio il nome del tavolo al server
    sock.send(nome_tavolo.encode("utf-8"))

    # avvio il thread che ascolta i messaggi in arrivo
    thread = threading.Thread(target=ricevi_messaggi, args=(sock,))
    thread.daemon = True
    thread.start()

    # spiego i comandi all'utente
    print("--- Comandi ---")
    print("/mossa N   → gioca nella cella N (da 1 a 9)")
    print("/quit      → esci dal gioco")
    print("---------------\n")

    # ciclo principale: leggo l'input e lo mando al server
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
