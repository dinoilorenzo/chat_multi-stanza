===================================
  CHAT MULTI-STANZA - Istruzioni
===================================

Questo progetto è una semplice chat multi-stanza scritta in Python.
I client possono entrare in stanze diverse e parlare tra loro.


--- REQUISITI ---

- Python 3.x installato sul computer
- Nessuna libreria esterna necessaria


--- COME AVVIARE ---

1. Apri un terminale e avvia il server:

   python server.py

   Dovresti vedere: "Server avviato su 127.0.0.1:5555"


2. Apri un ALTRO terminale (o più terminali) e avvia il client:

   python client.py

   Ti verrà chiesto:
   - Il tuo username (es. Mario)
   - Il nome della stanza (es. generale)


3. Ripeti il passo 2 per ogni utente che vuole connettersi.
   Utenti nella stessa stanza possono parlare tra loro.


--- COMANDI DISPONIBILI ---

  /msg username messaggio   → Invia un messaggio privato a un utente
  /list                     → Mostra la lista degli utenti nella stanza
  /quit                     → Esci dalla chat


--- ESEMPIO ---

  Terminale 1 (server):
    $ python server.py

  Terminale 2 (client 1):
    $ python client.py
    Inserisci il tuo username: Mario
    Inserisci il nome della stanza: generale

  Terminale 3 (client 2):
    $ python client.py
    Inserisci il tuo username: Luigi
    Inserisci il nome della stanza: generale

  Ora Mario e Luigi possono scambiarsi messaggi nella stanza "generale"!

  Per un messaggio privato:
    /msg Luigi Ciao, come stai?


--- NOTE ---

- Il server deve essere avviato PRIMA dei client
- Tutti i client si connettono a 127.0.0.1 (localhost) sulla porta 5555
- Se la stanza non esiste, viene creata automaticamente
- Se tutti escono da una stanza, la stanza viene eliminata
