# Guida Completa del Progetto: Chat & Tris Multi-Stanza

Questo file spiega **tutto il sistema**: come è strutturato, come ogni pezzo si collega agli altri, e come avviare tutto.

---

## 1. Cos'è questo progetto?

Una piattaforma di comunicazione in tempo reale dove gli utenti entrano in **stanze virtuali**, possono **chattare** tra loro e, quando vogliono, avviare una partita di **Tris** (tic-tac-toe) direttamente nella stessa stanza — senza mai cambiare applicazione o connessione.

Al termine di una partita, il vincitore riceve un messaggio di vittoria e il perdente un messaggio di sconfitta, entrambi visibili solo ai diretti interessati. Dopo la partita, la chat nella stanza riprende normalmente.

---

## 2. I File del Progetto e a Cosa Servono

```
chat_multi-stanza/
│
├── server.py            ← Server TCP unificato: gestisce chat + tris (porta 5555)
├── client.py            ← Client da terminale (chat + tris via terminale)
│
├── server_tris.py       ← Server Tris standalone (porta 5556, uso indipendente)
├── client_tris.py       ← Client Tris da terminale (per server_tris.py)
│
├── web_gateway.py       ← Gateway web: fa da ponte tra browser e server.py
│
├── templates/
│   └── index.html       ← Pagina HTML dell'interfaccia web
│
├── static/
│   ├── css/style.css    ← Stili grafici dell'interfaccia
│   └── js/app.js        ← Logica JavaScript del client web
│
├── requirements.txt     ← Librerie Python necessarie (Flask, Flask-SocketIO)
├── venv/                ← Ambiente virtuale Python (non va su Git)
│
├── README.txt           ← Istruzioni rapide di avvio
├── ARCHITETTURA.md      ← Dettaglio dell'architettura della chat
├── COME_FUNZIONA_TRIS.md ← Dettaglio del gioco Tris
└── GUIDA_COMPLETA.md    ← Questo file
```

---

## 3. Architettura: Come Tutto è Collegato

Il sistema ha **tre strati**. Tutto passa per un unico server TCP (`server.py`):

```
┌─────────────────────────────────────────────────────────┐
│                   STRATO 1 — BROWSER                    │
│              (index.html + app.js + style.css)          │
│                                                         │
│   [Chat box]  [Scacchiera Tris]  [Barra dei comandi]   │
└──────────────────────────┬──────────────────────────────┘
                           │  WebSocket (Socket.IO)
                           ▼
┌─────────────────────────────────────────────────────────┐
│                STRATO 2 — GATEWAY WEB                   │
│                   (web_gateway.py)                      │
│                     porta 8000                          │
│              bridges = { sid → Bridge }                 │
└──────────────────────────┬──────────────────────────────┘
                           │  TCP socket
                           ▼
┌─────────────────────────────────────────────────────────┐
│             STRATO 3 — SERVER UNIFICATO                 │
│                    (server.py)                          │
│                    porta 5555                           │
│                                                         │
│   rooms + clients + client_rooms + partite             │
└─────────────────────────────────────────────────────────┘
```

### Come funziona il flusso (esempio con il Tris):

1. L'utente apre il browser su `http://127.0.0.1:8000`
2. Inserisce username e nome stanza e clicca "Entra nella stanza"
3. `app.js` invia un evento WebSocket `join` al gateway
4. `web_gateway.py` apre una connessione TCP verso `server.py` e fa l'handshake
5. L'utente clicca 🎮 o digita `/game`
6. Il gateway manda il testo `/game` via TCP a `server.py`
7. `server.py` avvia la partita, manda la scacchiera e i turni via TCP
8. Il gateway riceve il testo e lo manda al browser via WebSocket
9. `app.js` interpreta il testo, aggiorna graficamente la scacchiera
10. Quando il giocatore clicca una cella, `app.js` invia `/mossa N` come messaggio normale
11. Il server valida la mossa, aggiorna la scacchiera e manda il risultato

---

## 4. I Modelli di Comunicazione Usati

Il sistema usa **tre modelli diversi** a seconda della situazione.

### 4.1 — Point-to-Point (Unicast)
Un messaggio va **solo a un destinatario specifico**.

**Esempi:**
- Il server manda "🏆 HAI VINTO!" solo al vincitore
- Il server manda "😞 HAI PERSO!" solo al perdente
- Il server manda "Non è il tuo turno!" solo a chi ha sbagliato
- Il server manda un messaggio privato `/msg` solo al destinatario

```
server.py ───────────────────→ Giocatore A (solo lui)
               "HAI VINTO!"
```

### 4.2 — Multicast Applicativo (Broadcast sulla stanza)
Un messaggio va **a tutti i membri della stanza**, ma non a chi è in altre stanze.

**Esempi:**
- Ogni messaggio di chat normale viene inviato a tutti nella stanza
- La scacchiera aggiornata viene inviata a tutti (anche agli spettatori)
- L'annuncio "=== X ha vinto! ===" va a tutti nella stanza

```
server.py ───────────────────→ Mario (stanza "sala-1")
          (scacchiera)  ├────→ Luigi (stanza "sala-1")
                        └────→ Peach (stanza "sala-1")

                  ✗ Carlo (stanza "sala-2" → non riceve)
```

> È detto "Applicativo" perché il codice Python del server fa un ciclo `for` sui socket della stanza, non il protocollo di rete.

### 4.3 — Publish-Subscribe (Pub-Sub)
Gli utenti si **iscrivono a una stanza** (topic) e ricevono solo i messaggi di quella stanza.

**Esempi:**
- Entrare nella stanza "generale" = iscriversi al topic "generale"
- Il gateway `web_gateway.py` fa da **broker**: riceve gli eventi e li smista agli iscritti giusti

```
Topic "sala-1"    →  Mario, Luigi, Peach
Topic "sala-2"    →  Carlo, Daisy
```

### Riepilogo

| Situazione | Modello | Destinatari |
|---|---|---|
| "HAI VINTO!" al vincitore | Point-to-Point | 1 utente |
| "HAI PERSO!" al perdente | Point-to-Point | 1 utente |
| "Non è il tuo turno" | Point-to-Point | 1 utente |
| Messaggio privato `/msg` | Point-to-Point | 1 utente |
| Messaggio di chat normale | Multicast sulla stanza | Tutti nella stanza |
| Scacchiera aggiornata nel Tris | Multicast sulla stanza | Tutti nella stanza |
| Annuncio vincitore pubblico | Multicast sulla stanza | Tutti nella stanza |
| Ingresso in una stanza | Publish-Subscribe | Iscritti a quel topic |

---

## 5. Come Funziona il Server Unificato (`server.py`)

Il server mantiene in memoria quattro dizionari:

```python
rooms        = {}  # nome_stanza → lista di socket connessi
clients      = {}  # socket      → username
client_rooms = {}  # socket      → nome della stanza
partite      = {}  # nome_stanza → { board, turno, giocatori, simboli }
```

**Comandi supportati:**

| Comando | Cosa fa |
|---|---|
| `/msg utente testo` | Messaggio privato (Point-to-Point) |
| `/list` | Lista utenti nella stanza |
| `/game` | Avvia una partita di Tris nella stanza corrente |
| `/mossa N` | Gioca nella cella N (1-9) durante una partita |
| `/quit` | Disconnessione pulita |

**Flusso di `/game`:**
1. Il server verifica che non ci sia già una partita in corso
2. Il server verifica che ci siano almeno 2 utenti nella stanza
3. Prende i primi 2 utenti come giocatori (X e O)
4. Inizializza la scacchiera e la manda a tutti nella stanza
5. Manda "Tocca a te!" solo al giocatore X (Point-to-Point)

**Fine partita:**
- Manda "HAI VINTO!" solo al vincitore (Point-to-Point)
- Manda "HAI PERSO!" solo al perdente (Point-to-Point)
- Manda l'annuncio pubblico a tutti nella stanza (Multicast)
- Elimina la partita dal dizionario — la chat riprende normalmente

---

## 6. Come Funziona il Gateway (`web_gateway.py`)

Il gateway usa **Flask** per servire la pagina web e **Flask-SocketIO** per la comunicazione in tempo reale col browser.

```python
bridges = {}  # session_id → Bridge (connessione TCP verso server.py)
```

**Eventi WebSocket gestiti:**

| Evento in arrivo dal browser | Cosa fa il gateway |
|---|---|
| `join` | Apre un Bridge TCP verso `server.py` e fa l'handshake |
| `send_message` | Manda il testo (chat, /game, /mossa N, ecc.) via TCP |
| `disconnect` | Chiude il Bridge |

> **Nota:** Non esiste più un bridge separato per il tris. Tutto — chat e tris — passa per lo stesso bridge verso `server.py`.

---

## 7. Come Avviare il Sistema

### Requisiti
- Python 3.x installato
- Librerie Python installate (una volta sola)

### Installazione delle dipendenze (una volta sola)

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

---

### Opzione A — Da Terminale (senza interfaccia web)

```bash
# Terminale 1: avvia il server
python3 server.py

# Terminale 2: primo utente
python3 client.py

# Terminale 3: secondo utente
python3 client.py
```

Il primo utente può digitare `/game` per avviare il tris.

---

### Opzione B — Con l'Interfaccia Web (raccomandato)

```bash
# Terminale 1: server unificato
python3 server.py

# Terminale 2: gateway web
./venv/bin/python3 web_gateway.py
```

Poi apri il browser su:

```
http://127.0.0.1:8000
```

- Inserisci username e nome stanza, clicca "Entra nella stanza"
- Per avviare il Tris: clicca 🎮 oppure digita `/game` e premi Invio
- Apri una seconda scheda con lo stesso nome stanza per il secondo giocatore
- Quando ci sono 2 utenti, `/game` fa partire la partita

---

## 8. Porte Usate

| Porta | Processo | Protocollo | Uso |
|---|---|---|---|
| `5555` | `server.py` | TCP | Chat + Tris (tutto) |
| `8000` | `web_gateway.py` | HTTP + WebSocket | Interfaccia web |
| `5556` | `server_tris.py` | TCP | Tris standalone (opzionale) |

---

## 9. Glossario

| Termine | Significato nel progetto |
|---|---|
| **Socket TCP** | Canale di comunicazione bidirezionale tra client e server |
| **Thread** | Processo leggero: ogni client ha il suo thread sul server |
| **Bridge** | Oggetto nel gateway che mantiene aperta la connessione TCP verso il server per conto del browser |
| **WebSocket** | Protocollo che permette al server di mandare messaggi al browser senza che il browser li chieda prima |
| **Socket.IO** | Libreria che gestisce i WebSocket sia sul browser (JS) che sul server Python |
| **Stanza** | Gruppo logico di utenti che ricevono gli stessi messaggi — è anche il "topic" del sistema Pub-Sub |
| **Partita** | Sessione di gioco a Tris attiva in una stanza, con scacchiera e turni gestiti dal server |
