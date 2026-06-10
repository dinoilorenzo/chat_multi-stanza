# Architettura del Sistema Chat Multi-Stanza

Questo documento descrive la struttura, i componenti e il flusso di funzionamento del sistema.

---

## 1. Struttura del Progetto

Il sistema è composto da tre file principali per l'uso via terminale, più un gateway web e i file dell'interfaccia grafica:

| File | Ruolo |
|---|---|
| `server.py` | Server TCP unificato: gestisce chat, stanze e gioco Tris (porta 5555) |
| `client.py` | Client da terminale per chat e Tris |
| `web_gateway.py` | Gateway Flask/WebSocket che fa da ponte verso `server.py` |
| `templates/index.html` | Pagina HTML con chat, scacchiera e comandi |
| `static/js/app.js` | Logica JavaScript del client web |
| `static/css/style.css` | Stili dell'interfaccia |

---

## 2. Architettura Logica (Client-Server & Pub-Sub)

Il sistema adotta un'architettura **Client-Server**. Tutti i client comunicano esclusivamente tramite il server centrale; non c'è comunicazione diretta tra client.

```
Client A (terminale)              Client B (browser)
(client.py)                       (index.html + app.js)
     |                                     |
     |─── TCP 5555 ───┐      ┌─── WS ────→ web_gateway.py
     |                 ▼      ▼               |
     |              SERVER UNIFICATO ─────────┘
     |               (server.py)
     |               porta 5555
     └─────────────────────────────────────────
```

Il server gestisce sia la **chat** che il **gioco Tris** nello stesso processo, usando un unico dizionario per le stanze e uno separato per le partite in corso.

---

## 3. Le Strutture Dati del Server

Il server tiene tutto in memoria con semplici dizionari Python:

```python
rooms        = {}  # nome_stanza → lista dei socket connessi
clients      = {}  # socket      → username del client
client_rooms = {}  # socket      → nome della stanza in cui si trova
partite      = {}  # nome_stanza → { 'board': [...], 'turno': sock,
                   #                'giocatori': [s1, s2], 'simboli': {...} }
```

---

## 4. I Thread nel Server

Per ogni client connesso, il server crea un thread dedicato con `threading.Thread`. Ogni thread:
- Riceve i dati del client in un ciclo `while True`
- Chiama la funzione giusta in base al comando ricevuto
- Termina quando il client si disconnette o manda `/quit`

```
Thread principale (main) → accetta nuove connessioni (accept)
Thread client A          → gestisce A per tutta la sessione
Thread client B          → gestisce B per tutta la sessione
Thread client C          → gestisce C per tutta la sessione
```

---

## 5. I Modelli di Comunicazione

### Point-to-Point (Unicast)
Un messaggio viene inviato **solo a un destinatario specifico**.

**Quando viene usato:**
- Messaggio privato `/msg`
- "HAI VINTO!" → solo al vincitore
- "HAI PERSO!" → solo al perdente
- "Non è il tuo turno!" → solo a chi ha sbagliato

```
server.py ───────────────────→ Client A (solo lui)
```

### Multicast Applicativo
Un messaggio viene inviato **a tutti i client della stessa stanza**.

**Quando viene usato:**
- Messaggi normali di chat
- Scacchiera aggiornata dopo ogni mossa
- Annunci pubblici (inizio partita, vincitore, pareggio)
- Notifiche di ingresso/uscita dalla stanza

```
server.py ───────────────────→ Client A (stanza "generale")
          (messaggio)   ├────→ Client B (stanza "generale")
                        └────→ Client C (stanza "generale")
```

### Publish-Subscribe (Pub-Sub)
Le stanze si comportano come "topic". I client si **iscrivono** a una stanza e ricevono solo i messaggi di quella stanza.

```
Topic "generale"  →  Mario, Luigi
Topic "gaming"    →  Yoshi, Peach

Mario non riceve i messaggi del topic "gaming" e viceversa.
```

---

## 6. Flusso di una Sessione Completa

### Connessione

1. Il client si connette al server via socket TCP
2. Invia il proprio **username** (primo messaggio)
3. Invia il nome della **stanza** (secondo messaggio)
4. Il server lo aggiunge ai dizionari e alla stanza
5. Il server manda un messaggio di benvenuto e notifica gli altri

### Chat Normale

Il client invia testo libero → il server lo fa precedere da `username: ` e lo manda a tutti nella stanza (escludendo il mittente).

### Partita di Tris con `/game`

1. Un utente digita `/game`
2. Il server verifica: nessuna partita in corso + almeno 2 utenti nella stanza
3. Il server crea la partita, assegna X al primo e O al secondo utente
4. Manda la scacchiera a tutti e "Tocca a te" solo al giocatore X
5. I giocatori mandano `/mossa N` per giocare
6. Il server valida ogni mossa, aggiorna la scacchiera e la manda a tutti
7. Al termine: manda "HAI VINTO/PERSO" in modo privato + annuncio pubblico
8. Elimina la partita → la chat riprende normalmente

### Disconnessione

Il server rimuove il client da stanza e dizionari. Se era in una partita, la partita viene annullata e gli altri vengono avvisati.

---

## 7. Come Avviare

### Da terminale

```bash
# Terminale 1
python3 server.py

# Terminale 2 (utente 1)
python3 client.py

# Terminale 3 (utente 2)
python3 client.py
```

### Con interfaccia web

```bash
python3 server.py
./venv/bin/python3 web_gateway.py
# poi apri http://127.0.0.1:8000
```
