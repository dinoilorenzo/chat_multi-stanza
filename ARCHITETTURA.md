# Architettura del Sistema Chat Multi-Stanza

Questo documento descrive in dettaglio la struttura, i componenti e il flusso di funzionamento del sistema di chat Client-Server multi-stanza.

---

## 1. Struttura del Progetto

Il sistema è composto da tre file principali:

1. **`server.py`**: Il gestore centrale (broker) della chat. Rimane in ascolto di nuove connessioni, traccia gli utenti e le stanze, e smista i messaggi.
2. **`client.py`**: L'interfaccia a riga di comando per l'utente. Permette di connettersi, inviare messaggi e ricevere aggiornamenti.
3. **`README.txt`**: Guida rapida all'installazione e all'esecuzione.

---

## 2. Architettura Logica (Client-Server & Pub-Sub/Multicast)

Il sistema adotta un'architettura **Client-Server**. Tutti i client comunicano esclusivamente tramite il server centrale; non c'è comunicazione diretta (peer-to-peer) tra i client.

```
                  +------------------+
                  |    server.py     |
                  +--------+---------+
                           |
       +-------------------+-------------------+
       | (Stanza: "Sport") | (Stanza: "Sport") | (Stanza: "Tech")
       v                   v                   v
+--------------+    +--------------+    +--------------+
|   Client A   |    |   Client B   |    |   Client C   |
+--------------+    +--------------+    +--------------+
```

### Modelli di Comunicazione Utilizzati
* **Multicast Applicativo (Stanze):** Quando un utente invia un messaggio normale, il server lo distribuisce solo ai membri di quella specifica stanza.
* **Point-to-Point / Unicast (Messaggi Privati):** Con il comando `/msg`, il messaggio viene recapitato dal server solo al socket del destinatario designato.
* **Publish-Subscribe (Pub-Sub):** Le stanze agiscono come "topic" a cui i client si iscrivono all'accesso.

---

## 3. Dettaglio dei Componenti

### A. Il Server (`server.py`)

Il server gestisce lo stato dell'applicazione in memoria attraverso tre strutture dati principali (dizionari globali):
* `rooms = {}` $\rightarrow$ Mappa il nome di una stanza alla lista dei socket dei client attualmente connessi ad essa (`{ nome_stanza: [socket1, socket2, ...] }`).
* `clients = {}` $\rightarrow$ Associa ogni socket attivo al rispettivo nome utente (`{ socket: username }`).
* `client_rooms = {}` $\rightarrow$ Tiene traccia di quale stanza stia occupando ciascun socket (`{ socket: nome_stanza }`).

#### Flusso del Thread Principale
1. Crea un socket TCP su `127.0.0.1:5555` e si mette in ascolto (`listen()`).
2. Entra in un ciclo infinito dove accetta nuove connessioni (`accept()`).
3. Per ogni client connesso, avvia un thread dedicato chiamato `handle_client`.

#### Il Thread del Client (`handle_client`)
* **Fase di Handshake:** Riceve prima l'username e poi il nome della stanza. Registra le informazioni nei dizionari e notifica la stanza del nuovo ingresso.
* **Ciclo di Ricezione:** Rimane in attesa di dati dal socket del client. All'arrivo di un messaggio:
  * Controlla se è un comando (`/quit`, `/list`, `/msg`).
  * Esegue l'azione corrispondente o esegue il broadcast del testo agli altri membri della stanza.
* **Gestione Disconnessione:** Se il client si scollega o invia `/quit`, rimuove il socket dai dizionari, notifica la stanza e chiude in sicurezza la connessione.

---

## 4. Il Client (`client.py`)

Per evitare che l'interfaccia si blocchi in attesa dell'input dell'utente (impedendo la ricezione di nuovi messaggi), il client utilizza **due thread concorrenti**:

```
+-------------------------------------------------------+
|                       CLIENT                          |
|                                                       |
|  +-----------------------+   Input    +------------+  |
|  | Thread Principale     | ---------> |   Server   |  |
|  | (Ciclo input utente)  |            +-----+------+  |
|  +-----------------------+                  |         |
|                                             | Socket  |
|  +-----------------------+   Stampa         v         |
|  | Thread in Background  | <----------------+         |
|  | (Ricezione messaggi)  |                            |
|  +-----------------------+                            |
+-------------------------------------------------------+
```

1. **Thread Principale (Invio):**
   * Richiede username e stanza all'avvio.
   * Si connette al server ed esegue l'handshake.
   * Entra in un ciclo infinito bloccato su `input()`. Ogni testo digitato viene codificato in UTF-8 e inviato immediatamente al server.
   * Se viene inserito `/quit`, chiude la connessione ed esce.

2. **Thread in Background (Ricezione):**
   * Esegue la funzione `receive_messages`.
   * Rimane in attesa di messaggi in arrivo dal server (`recv()`).
   * Appena riceve una stringa, la decodifica e la stampa direttamente sul terminale dell'utente.
   * Se il server chiude la connessione, avvisa l'utente e termina il ciclo.
