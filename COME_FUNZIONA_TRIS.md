# Come Funziona il Gioco Tris Multiplayer

Questo documento spiega come è costruito e come funziona il sistema di gioco Tris multiplayer via socket TCP, e come si collega all'interfaccia web.

---

## Struttura del Progetto

| File                        | Ruolo                                                    |
|-----------------------------|----------------------------------------------------------|
| `server_tris.py`            | Il server TCP che gestisce tutta la logica di gioco      |
| `client_tris.py`            | Client da terminale (alternativo alla UI web)            |
| `server.py`                 | Il server TCP per la chat multi-stanza (porta 5555)      |
| `web_gateway.py`            | Gateway Flask/WebSocket che fa da ponte verso entrambi i server |
| `templates/index.html`      | Pagina HTML con selettore modalità e scacchiera grafica  |
| `static/js/app.js`          | Logica del client web (Chat e Tris)                      |
| `static/css/style.css`      | Stili dell'interfaccia web                               |

---

## Architettura Generale: Client-Server + Web UI

Il sistema usa una architettura **Client-Server** classica. I due giocatori **non comunicano mai direttamente tra loro**: tutto passa obbligatoriamente attraverso il server.

**Da terminale** (senza UI):
```
client_tris.py ──── TCP 5556 ────→ server_tris.py
client_tris.py ──── TCP 5556 ────→ server_tris.py
```

**Tramite interfaccia web** (con UI):
```
Browser A ──WebSocket──→ web_gateway.py ──TCP 5556──→ server_tris.py
Browser B ──WebSocket──→ web_gateway.py ──TCP 5556──→ server_tris.py
```

Il gateway (`web_gateway.py`) fa da **ponte (bridge)**: apre una connessione TCP verso `server_tris.py` per conto di ogni giocatore connesso dal browser, e usa WebSocket per comunicare con il browser in tempo reale.

Il server fa da **arbitro**: riceve la mossa da un giocatore, la valida, aggiorna la scacchiera e invia gli aggiornamenti a entrambi.

---

## Come Funziona: Passo per Passo

### 1. Connessione e accesso al tavolo
Quando un client si avvia, fa due cose:
1. Invia il proprio **username** al server.
2. Invia il nome del **tavolo** a cui vuole unirsi (es. "Tavolo-1").

Il server riceve queste informazioni e aggiunge il giocatore al tavolo scelto.

- Se il tavolo **non esiste**, il server lo crea automaticamente.
- Se il tavolo è già **pieno (2 giocatori)**, il server rifiuta la connessione.
- Se nel tavolo c'è già **1 giocatore**, il server aspetta il secondo.
- Quando arrivano **2 giocatori**, la partita inizia automaticamente.

### 2. Avvio della partita
Il server assegna i simboli:
- Il **primo** giocatore entrato nel tavolo → **X** (gioca per primo)
- Il **secondo** giocatore entrato → **O** (aspetta il suo turno)

Il server invia a entrambi la scacchiera iniziale (vuota) e il numero delle celle (da 1 a 9):
```
 1 | 2 | 3
---+---+---
 4 | 5 | 6
---+---+---
 7 | 8 | 9
```

### 3. Una mossa
Il giocatore il cui turno è attivo invia al server il comando:
```
/mossa N
```
dove N è un numero da 1 a 9.

Il server controlla:
- È il turno di questo giocatore?
- La cella N esiste? (da 1 a 9)
- La cella N è libera?

Se tutto è ok, il server aggiorna la scacchiera e la manda ad entrambi i giocatori. Se c'è un errore, risponde solo al giocatore che ha sbagliato.

### 4. Fine partita
Dopo ogni mossa il server controlla se:
- C'è un **vincitore** (tre X o tre O in riga, colonna o diagonale)
- È **pareggio** (tutte le 9 celle occupate senza vincitore)

Se la partita finisce, il server lo comunica a entrambi i giocatori e fa partire automaticamente una **nuova partita**.

---

## I Modelli di Comunicazione Usati

Questo sistema usa **tre diversi modelli di comunicazione** a seconda della situazione:

### 1. Point-to-Point (Unicast)
Un messaggio viene inviato **solo a uno specifico giocatore**.

**Quando viene usato:**
- Quando un giocatore prova a muovere ma **non è il suo turno** → il server avvisa solo lui.
- Quando un giocatore sceglie una **cella già occupata** → il server avvisa solo lui.
- Quando tocca a un giocatore → il server manda "Tocca a te!" solo a lui.

```
Server ──────────────────→ Giocatore 1 (solo lui)
              "Non è il tuo turno!"
```

### 2. Broadcast sul Tavolo (Multicast Applicativo)
Un messaggio viene inviato **a entrambi i giocatori del tavolo**.

**Quando viene usato:**
- Dopo ogni mossa valida: il server manda la **scacchiera aggiornata** a tutti e due.
- Quando la partita finisce: il server annuncia il **vincitore o il pareggio** a tutti e due.
- Quando un giocatore si disconnette: il server avvisa l'**altro giocatore**.

```
Server ──────────────────→ Giocatore 1
         (scacchiera)  └──→ Giocatore 2
```

> **Nota:** Questo è chiamato "Multicast Applicativo" perché la logica di invio a un gruppo è gestita dal codice Python del server (ciclo `for` sui socket del tavolo), non dal protocollo di rete.

### 3. Publish-Subscribe (Pub-Sub)
I **tavoli** si comportano come "topic" di un sistema Pub-Sub.

- I giocatori si **iscrivono** (`subscribe`) a un tavolo quando vi entrano.
- Il server fa da **broker**: riceve gli eventi (le mosse) e li distribuisce agli iscritti di quel topic.
- Un giocatore riceve solo i messaggi del **proprio tavolo**, non quelli degli altri tavoli.

```
Tavolo-1 (topic)         Tavolo-2 (topic)
   ├── Giocatore A           ├── Giocatore C
   └── Giocatore B           └── Giocatore D

A e B non ricevono i messaggi di Tavolo-2 e viceversa.
```

---

## Riepilogo: Quale modello per quale situazione

| Situazione                        | Modello usato          | Destinatario         |
|-----------------------------------|------------------------|----------------------|
| "Non è il tuo turno"              | Point-to-Point         | 1 giocatore          |
| "Cella già occupata"              | Point-to-Point         | 1 giocatore          |
| "Tocca a te!"                     | Point-to-Point         | 1 giocatore          |
| Scacchiera aggiornata dopo mossa  | Multicast sul tavolo   | 2 giocatori          |
| Annuncio vincitore / pareggio     | Multicast sul tavolo   | 2 giocatori          |
| Avversario disconnesso            | Multicast sul tavolo   | 2 giocatori          |
| Iscrizione a un tavolo            | Publish-Subscribe      | Iscritti al topic    |

---

## Strutture Dati usate nel Server

Il server tiene tutto in memoria usando semplici dizionari Python:

```python
tavoli          = {}  # nome_tavolo  → lista dei 2 socket dei giocatori
giocatori       = {}  # socket       → username del giocatore
giocatore_tavolo = {} # socket       → nome del tavolo in cui si trova
scacchiere      = {}  # nome_tavolo  → lista di 9 celle (" ", "X", "O")
turno_di        = {}  # nome_tavolo  → socket del giocatore che deve muovere
```

---

## Ruolo del Gateway Web

`web_gateway.py` fa da **intermediario** tra il browser e i server TCP. Ha due dizionari separati:

```python
bridges      = {}  # sid → bridge verso server.py      (chat, porta 5555)
tris_bridges = {}  # sid → bridge verso server_tris.py (tris, porta 5556)
```

Quando il browser clicca su una cella della scacchiera, invia un evento WebSocket `tris_move` con il numero della cella. Il gateway lo converte in `/mossa N` e lo manda via TCP a `server_tris.py`. La risposta del server (la scacchiera aggiornata come testo ASCII) viene ricevuta dal bridge e rimandata al browser via WebSocket come evento `message`. Il browser (in `app.js`) interpreta il testo e aggiorna graficamente la scacchiera.

---

## Come si Avvia

**Con terminale (senza UI):**
```bash
# Terminale 1 - avvia il server
python3 server_tris.py

# Terminale 2 - primo giocatore
python3 client_tris.py

# Terminale 3 - secondo giocatore
python3 client_tris.py
```

**Con interfaccia web:**
```bash
# Terminale 1 - server chat
python3 server.py

# Terminale 2 - server tris
python3 server_tris.py

# Terminale 3 - gateway web
./venv/bin/python3 web_gateway.py

# Poi apri due schede del browser su http://127.0.0.1:8000
# Seleziona "Tris", inserisci username e nome del tavolo
# Quando entrano 2 giocatori, la partita parte automaticamente!
```
