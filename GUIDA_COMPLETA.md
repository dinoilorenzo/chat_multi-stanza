# Guida Completa del Progetto: Chat & Tris Multi-Stanza

Questo file spiega **tutto il sistema**: come è strutturato, come ogni pezzo si collega agli altri, e come avviare tutto.

---

## 1. Cos'è questo progetto?

Il progetto è composto da **due applicazioni distinte** che condividono la stessa interfaccia web:

| Applicazione | Descrizione |
|---|---|
| **Chat Multi-Stanza** | Gli utenti entrano in stanze e chattano in tempo reale |
| **Tris Multiplayer** | Due giocatori si sfidano a Tris in un "tavolo" virtuale |

Entrambe usano la stessa architettura di base: **Client-Server con socket TCP**.

---

## 2. I File del Progetto e a Cosa Servono

```
chat_multi-stanza/
│
├── server.py            ← Server TCP della chat (porta 5555)
├── client.py            ← Client da terminale per la chat
│
├── server_tris.py       ← Server TCP del gioco Tris (porta 5556)
├── client_tris.py       ← Client da terminale per il Tris
│
├── web_gateway.py       ← Gateway web: fa da ponte tra browser e server TCP
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
├── ARCHITETTURA.md      ← Architettura della chat multi-stanza
└── COME_FUNZIONA_TRIS.md ← Architettura del gioco Tris
```

---

## 3. Architettura Generale: Come Tutto è Collegato

Il sistema ha **tre strati**:

```
┌─────────────────────────────────────────────────────────┐
│                   STRATO 1 — BROWSER                    │
│              (index.html + app.js + style.css)          │
│                                                         │
│  [Selettore Chat/Tris]  [Scacchiera Tris]  [Chat box]  │
└──────────────────────────┬──────────────────────────────┘
                           │  WebSocket (Socket.IO)
                           ▼
┌─────────────────────────────────────────────────────────┐
│                STRATO 2 — GATEWAY WEB                   │
│                   (web_gateway.py)                      │
│                     porta 8000                          │
│                                                         │
│   bridges = {}        tris_bridges = {}                 │
│   (bridge chat)       (bridge tris)                     │
└────────────┬────────────────────────┬───────────────────┘
             │ TCP socket             │ TCP socket
             ▼                        ▼
┌────────────────────┐   ┌────────────────────────────┐
│  STRATO 3 — SERVER │   │   STRATO 3 — SERVER TRIS   │
│    (server.py)     │   │      (server_tris.py)      │
│     porta 5555     │   │        porta 5556          │
└────────────────────┘   └────────────────────────────┘
```

### Come funziona il flusso (esempio con il Tris):

1. L'utente apre il browser su `http://127.0.0.1:8000`
2. Seleziona la modalità **Tris**, inserisce username e nome tavolo e clicca "Entra"
3. `app.js` invia un evento WebSocket `join_tris` al gateway
4. `web_gateway.py` apre una connessione TCP verso `server_tris.py` e fa l'handshake (manda username + nome tavolo)
5. Quando arrivano 2 giocatori, `server_tris.py` avvia la partita e invia la scacchiera a entrambi via TCP
6. Il gateway riceve il testo ASCII e lo rispedisce al browser via WebSocket come evento `message`
7. `app.js` interpreta il testo e aggiorna graficamente la scacchiera nel browser
8. Quando il giocatore clicca una cella, `app.js` invia `tris_move` al gateway
9. Il gateway converte il clic in `/mossa N` e lo manda via TCP al server
10. Il ciclo ricomincia dal punto 5

---

## 4. I Modelli di Comunicazione Usati

Il sistema non usa un solo modo per comunicare: usa **tre modelli diversi** a seconda della situazione.

### 4.1 — Point-to-Point (Unicast)
Un messaggio va **solo a un destinatario specifico**.

**Esempi:**
- Il server del Tris manda "Tocca a te!" solo al giocatore di turno
- Il server manda "Cella già occupata" solo a chi ha sbagliato mossa
- Il server della chat manda un messaggio privato `/msg` solo al destinatario

```
server_tris.py ───────────────────→ Giocatore A (solo lui)
                  "Tocca a te!"
```

### 4.2 — Multicast Applicativo (Broadcast sul gruppo)
Un messaggio va **a tutti i membri di un gruppo** (stanza o tavolo), ma non agli altri.

**Esempi:**
- Il server del Tris manda la scacchiera aggiornata a entrambi i giocatori del tavolo
- Il server della chat distribuisce i messaggi normali a tutti gli utenti nella stessa stanza
- Il server del Tris annuncia il vincitore a entrambi i giocatori

```
server_tris.py ───────────────────→ Giocatore A (tavolo "Tavolo-1")
               (scacchiera)  └────→ Giocatore B (tavolo "Tavolo-1")

                          ✗ Giocatore C (tavolo "Tavolo-2" → non riceve)
```

> È detto "Applicativo" perché è il codice Python del server a fare un ciclo `for` sui socket del gruppo, non il protocollo di rete.

### 4.3 — Publish-Subscribe (Pub-Sub)
Gli utenti si **iscrivono a un topic** (stanza o tavolo) e ricevono solo i messaggi di quel topic.

**Esempi:**
- Entrare in una stanza chat = iscriversi al topic "generale"
- Entrare in un tavolo Tris = iscriversi al topic "Tavolo-1"
- Il gateway `web_gateway.py` agisce da **broker**: riceve gli eventi e li smista agli iscritti giusti

```
Topic "Tavolo-1"    →  Giocatore A, Giocatore B
Topic "Tavolo-2"    →  Giocatore C, Giocatore D
Topic "generale"    →  Mario, Luigi, Peach
```

### Riepilogo

| Situazione | Modello | Destinatari |
|---|---|---|
| "Tocca a te!" nel Tris | Point-to-Point | 1 giocatore |
| "Cella occupata" nel Tris | Point-to-Point | 1 giocatore |
| Messaggio privato `/msg` in chat | Point-to-Point | 1 utente |
| Scacchiera aggiornata nel Tris | Multicast sul tavolo | 2 giocatori |
| Messaggio di testo in chat | Multicast sulla stanza | Tutti nella stanza |
| Vincitore/pareggio nel Tris | Multicast sul tavolo | 2 giocatori |
| Iscrizione a stanza/tavolo | Publish-Subscribe | Iscritti al topic |

---

## 5. Come Funziona la Chat (`server.py`)

Il server mantiene in memoria tre dizionari:

```python
rooms        = {}  # nome_stanza → lista di socket connessi
clients      = {}  # socket      → username
client_rooms = {}  # socket      → nome della stanza
```

**Flusso di un messaggio normale:**
1. Client invia testo al server via TCP
2. Server prende la stanza del mittente da `client_rooms`
3. Server fa un ciclo su `rooms[stanza]` e manda il testo a tutti tranne il mittente

**Comandi supportati:**
| Comando | Cosa fa |
|---|---|
| `/msg utente testo` | Messaggio privato (Point-to-Point) |
| `/list` | Lista utenti nella stanza |
| `/quit` | Disconnessione pulita |

---

## 6. Come Funziona il Tris (`server_tris.py`)

Il server mantiene in memoria cinque dizionari:

```python
tavoli           = {}  # nome_tavolo → lista di 2 socket
giocatori        = {}  # socket      → username
giocatore_tavolo = {}  # socket      → nome del tavolo
scacchiere       = {}  # nome_tavolo → lista di 9 celle (" ", "X", "O")
turno_di         = {}  # nome_tavolo → socket del giocatore di turno
```

**Flusso di una mossa:**
1. Client invia `/mossa N` (con N da 1 a 9)
2. Server verifica: è il suo turno? La cella è libera?
3. Server aggiorna `scacchiere[tavolo][N-1]`
4. Server invia la scacchiera aggiornata a entrambi i giocatori
5. Server controlla righe, colonne, diagonali per trovare un vincitore
6. Se la partita finisce, resetta la scacchiera per la prossima

---

## 7. Come Funziona il Gateway (`web_gateway.py`)

Il gateway usa **Flask** per servire la pagina web e **Flask-SocketIO** per la comunicazione in tempo reale col browser.

Per ogni browser connesso, apre una connessione TCP verso il server giusto e la mantiene viva in un thread separato.

```python
bridges      = {}  # session_id → bridge TCP verso server.py (chat, porta 5555)
tris_bridges = {}  # session_id → bridge TCP verso server_tris.py (tris, porta 5556)
```

**Eventi WebSocket gestiti:**

| Evento in arrivo dal browser | Cosa fa il gateway |
|---|---|
| `join` | Apre un bridge TCP verso `server.py` e fa l'handshake |
| `join_tris` | Apre un bridge TCP verso `server_tris.py` e fa l'handshake |
| `send_message` | Manda il testo via TCP a `server.py` |
| `tris_move` | Converte il numero cella in `/mossa N` e lo manda a `server_tris.py` |
| `disconnect` | Chiude entrambi i bridge se esistono |

---

## 8. Come Avviare il Sistema

### Requisiti
- Python 3.x installato
- Un terminale per ogni processo (oppure eseguire in background)

### Installazione delle dipendenze (una volta sola)

```bash
# dalla cartella del progetto
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

---

### Opzione A — Solo Chat da Terminale

```bash
# Terminale 1: avvia il server
python3 server.py

# Terminale 2: primo utente
python3 client.py

# Terminale 3: secondo utente
python3 client.py
```

---

### Opzione B — Solo Tris da Terminale

```bash
# Terminale 1: avvia il server
python3 server_tris.py

# Terminale 2: primo giocatore
python3 client_tris.py

# Terminale 3: secondo giocatore
python3 client_tris.py
```

---

### Opzione C — Tutto con l'Interfaccia Web (raccomandato)

```bash
# Terminale 1: server della chat
python3 server.py

# Terminale 2: server del Tris
python3 server_tris.py

# Terminale 3: gateway web
./venv/bin/python3 web_gateway.py
```

Poi apri il browser su:

```
http://127.0.0.1:8000
```

- Per la **chat**: seleziona 💬 Chat, inserisci username e stanza, clicca "Entra nella chat"
- Per il **Tris**: seleziona ❌ Tris, inserisci username e nome tavolo (es. `Tavolo-1`), clicca "Entra nella partita"
- Apri una **seconda scheda** con lo stesso tavolo per far partire la partita

---

## 9. Porte Usate

| Porta | Processo | Protocollo |
|---|---|---|
| `5555` | `server.py` (chat) | TCP |
| `5556` | `server_tris.py` (tris) | TCP |
| `8000` | `web_gateway.py` (interfaccia web) | HTTP + WebSocket |

---

## 10. Glossario Veloce

| Termine | Significato nel progetto |
|---|---|
| **Socket TCP** | Canale di comunicazione bidirezionale tra client e server |
| **Thread** | Processo leggero: ogni client ha il suo thread sul server |
| **Bridge** | Oggetto nel gateway che tiene aperta la connessione TCP per conto del browser |
| **WebSocket** | Protocollo che permette al server di mandare messaggi al browser senza che il browser li chieda |
| **Socket.IO** | Libreria che gestisce i WebSocket sia sul browser (JS) che sul server (Python) |
| **Stanza/Tavolo** | Gruppo logico di utenti/giocatori che ricevono gli stessi messaggi |
