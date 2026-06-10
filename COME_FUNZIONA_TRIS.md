# Come Funziona il Gioco Tris Multi-Stanza

Il Tris è integrato direttamente nella chat multi-stanza. Non è un'applicazione separata: gli utenti entrano in una stanza, chattano, e quando vogliono avviano una partita con il comando `/game` — tutto nello stesso posto.

---

## Struttura dei File Coinvolti

| File | Ruolo |
|---|---|
| `server.py` | Gestisce sia la chat che la logica del Tris |
| `client.py` | Client da terminale per chat + Tris |
| `web_gateway.py` | Gateway che fa da ponte tra browser e server.py |
| `static/js/app.js` | Mostra la scacchiera nel browser e invia le mosse |

> `server_tris.py` e `client_tris.py` sono versioni standalone del solo Tris, utili per testare il gioco in isolamento su porta 5556.

---

## Come Funziona: Passo per Passo

### 1. Entrata in stanza
Gli utenti entrano in una stanza (via terminale o browser). Possono chattare liberamente.

### 2. Avvio della partita (`/game`)

Quando un utente digita `/game`:
- Il server verifica che non ci sia già una partita in corso nella stanza
- Il server verifica che ci siano almeno 2 utenti nella stanza
- Prende i **primi 2 utenti** come giocatori: il primo diventa X, il secondo O
- Inizializza la scacchiera (9 celle vuote) e la manda a **tutti** nella stanza
- Manda "Tocca a te per primo!" solo al giocatore X (Point-to-Point)
- Manda "Aspetta il tuo turno" solo al giocatore O (Point-to-Point)

Gli altri utenti nella stanza (spettatori) ricevono la scacchiera e gli aggiornamenti ma non possono giocare.

### 3. Fare una mossa (`/mossa N`)

Il giocatore di turno invia `/mossa N` (con N da 1 a 9, che corrisponde alle celle della scacchiera):

```
 1 | 2 | 3
---+---+---
 4 | 5 | 6
---+---+---
 7 | 8 | 9
```

Il server controlla:
- È il turno di questo giocatore?
- Il numero è valido (1-9)?
- La cella è libera?

Se tutto è ok: aggiorna la scacchiera e la manda a **tutti nella stanza**. Poi controlla vincitore e pareggio.

### 4. Fine partita

Se c'è un vincitore o pareggio:

| Messaggio | Destinatario | Modello |
|---|---|---|
| "🏆 HAI VINTO! Complimenti..." | Solo al vincitore | **Point-to-Point** |
| "😞 HAI PERSO! ..." | Solo al perdente | **Point-to-Point** |
| "=== X ha vinto la partita ===" | Tutta la stanza | **Multicast** |
| "Potete continuare a chattare..." | Tutta la stanza | **Multicast** |

Dopo la partita:
- Il dizionario `partite` viene svuotato per quella stanza
- Gli utenti possono chattare normalmente
- È possibile usare `/game` per una nuova partita

---

## I Modelli di Comunicazione nel Tris

### Point-to-Point (Unicast)
Messaggi che vanno **solo a un giocatore**:
- "Tocca a te!" → solo al giocatore di turno
- "Non è il tuo turno!" → solo a chi ha sbagliato
- "Cella già occupata!" → solo a chi ha sbagliato
- "HAI VINTO!" → solo al vincitore
- "HAI PERSO!" → solo al perdente

```
server.py ───────────────────→ Giocatore A (solo lui)
               "HAI VINTO!"
```

### Multicast Applicativo
Messaggi che vanno **a tutti nella stanza** (giocatori e spettatori):
- Scacchiera aggiornata dopo ogni mossa
- Annuncio inizio partita
- Annuncio vincitore o pareggio
- Notifica se un giocatore si disconnette durante la partita

```
server.py ───────────────────→ Giocatore A
          (scacchiera)  ├────→ Giocatore B
                        └────→ Spettatore C
```

### Publish-Subscribe (Pub-Sub)
Le stanze sono "topic": ogni utente riceve solo gli aggiornamenti della stanza in cui si trova.

```
Stanza "sala-1" (topic) → Mario, Luigi, Peach
Stanza "sala-2" (topic) → Carlo, Daisy

Mario non riceve le partite di "sala-2".
```

---

## Struttura del Dizionario `partite` nel Server

```python
partite = {
    "sala-1": {
        "board":    [" ", "X", " ", "O", " ", " ", " ", " ", " "],
        "turno":    <socket_di_Mario>,
        "giocatori":[<socket_di_Mario>, <socket_di_Luigi>],
        "simboli":  {<socket_di_Mario>: "X", <socket_di_Luigi>: "O"}
    }
}
```

---

## Come Avviare il Tris

### Da terminale

```bash
# Terminale 1 - avvia il server unificato
python3 server.py

# Terminale 2 - primo giocatore
python3 client.py
# → username: Mario
# → stanza: sala-1

# Terminale 3 - secondo giocatore
python3 client.py
# → username: Luigi
# → stanza: sala-1

# Da uno dei due terminali:
/game       ← avvia la partita
/mossa 5    ← gioca nella cella centrale
```

### Con interfaccia web

```bash
python3 server.py
./venv/bin/python3 web_gateway.py
# apri http://127.0.0.1:8000 in due schede, stessa stanza
# clicca 🎮 o digita /game per avviare
# clicca direttamente sulle celle per giocare
```
