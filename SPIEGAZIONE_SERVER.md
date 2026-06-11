# Script di Presentazione per l'Esame (Discorso per Interrogazione)

Questo documento è strutturato come un discorso pronto all'uso (con possibili domande e risposte) per presentare il progetto al professore durante l'esame orale. È scritto in prima persona, con un linguaggio chiaro, tecnico e scorrevole.

---

## 1. Introduzione e Obiettivo del Progetto
> **Come iniziare l'esposizione:**

"Professore, il progetto che ho realizzato consiste in un'applicazione di **Chat Multi-Stanza con un gioco Tris (Tic-Tac-Toe) integrato**. L'obiettivo principale è mostrare come far cooperare diversi modelli e paradigmi di comunicazione distribuita all'interno di un'unica infrastruttura.

L'applicazione permette a più utenti di connettersi, associarsi a delle stanze specifiche, chattare tra loro (sia pubblicamente che privatamente) e avviare partite a Tris direttamente all'interno della stanza di chat, il tutto visibile in tempo reale."

---

## 2. Architettura del Sistema
> **Spiegazione della struttura di rete:**

"Dal punto di vista architetturale, il sistema segue un modello **Client-Server classico**:
* Al centro c'è il **Server principale (`server.py`)**, scritto in Python standard senza librerie esterne per mostrare l'uso diretto delle socket TCP. È un server multithreading che assegna un thread a ogni client connesso per gestire le richieste in modo concorrente.
* Per i client, abbiamo due modalità: una da **terminale** (`client.py`) e una con **interfaccia web grafica** moderna.

Per collegare la pagina web senza stravolgere la logica del server TCP, ho inserito un **Gateway Web (`web_gateway.py`)** in Flask che fa da 'traduttore'. Il browser comunica con il gateway usando i **WebSocket** (tramite *Socket.IO*), e il gateway a sua volta apre una socket TCP standard verso il server principale. In questo modo, l'intero sistema rimane unificato e guidato da un unico server TCP."

---

## 3. Modelli di Comunicazione Utilizzati (Il Cuore dell'Interrogazione)
> **Questa è la parte più importante in cui mostrare la teoria applicata:**

"La particolarità del progetto è che non si limita a un solo tipo di comunicazione, ma implementa tre modelli fondamentali del calcolo distribuito:

### 1. Publish-Subscribe (Pub-Sub Applicativo)
Lo usiamo per la gestione delle **stanze di chat**:
* Le stanze si comportano esattamente come dei **Topic**. 
* Quando un utente fa il login ed entra in una stanza, si sta di fatto **iscrivendo** a quel topic.
* Da quel momento riceverà solo i messaggi pubblicati in quella stanza, mentre il server si occupa di filtrare e scartare i messaggi delle altre stanze a cui non è iscritto.

### 2. Multicast Applicativo (Group Broadcast)
Lo usiamo per le **comunicazioni di gruppo** all'interno della singola stanza:
* Quando un utente invia un messaggio normale in chat, o quando si verifica un evento di sistema (come l'ingresso di un nuovo utente), il server effettua un invio a tutti i client associati a quella specifica stanza.
* Nel gioco del Tris, ogni mossa viene validata dal server e inviata in multicast a tutta la stanza: questo garantisce che la scacchiera si aggiorni in tempo reale e contemporaneamente a tutti gli utenti presenti nella stanza, compresi eventuali spettatori.

### 3. Point-to-Point (Unicast)
Lo usiamo per le **interazioni dirette e private**:
* Per i messaggi privati tra due utenti (`/msg username messaggio`), il server inoltra il dato esclusivamente al socket del destinatario, senza coinvolgere gli altri.
* Nel gioco del Tris, usiamo la comunicazione point-to-point per gestire le informazioni riservate o gli stati del gioco: ad esempio, i messaggi di turno come *'Tocca a te'* o *'Aspetta il tuo turno'*, e soprattutto i messaggi finali di esito (*'🏆 HAI VINTO!'* inviato solo al vincitore e *'😞 HAI PERSO!'* inviato solo al perdente)."

---

## 4. Gestione dello Stato e Validazione
> **Come viene gestito il gioco:**

"Ci tengo a sottolineare che **tutta la logica e lo stato del gioco sono centralizzati sul server**. La scacchiera e i turni non risiedono sul client. Quando un utente clicca sulla griglia o digita `/mossa N`, invia solo l'intenzione di fare una mossa. 
Il server riceve la richiesta nel thread dedicato a quel client, verifica se è effettivamente il suo turno, se la cella è libera e se la partita è attiva. Solo dopo questa validazione aggiorna lo stato in memoria e ne notifica il risultato. Questo previene qualsiasi comportamento anomalo o tentativo di sottomissione di mosse non valide."

---

## 5. Possibili Domande del Professore (e come rispondere)

* **D: Perché avete usato TCP e non UDP?**
  * *R: Abbiamo scelto TCP perché la chat e le mosse di gioco richiedono massima affidabilità. Con UDP rischieremmo di perdere messaggi di testo o mosse, compromettendo lo stato del gioco. TCP garantisce la consegna ordinata e affidabile grazie ai meccanismi di riscontro (ACK) e ritrasmissione.*
  
* **D: Come viene gestita la concorrenza sul server?**
  * *R: Il server usa un thread per ogni client connesso. Il thread principale rimane in ascolto con `accept()` e, non appena si connette un client, genera un thread daemon indipendente che esegue un ciclo infinito di ricezione dati (`recv`). In questo modo, l'attesa bloccante di lettura di un client non blocca gli altri.*

* **D: Cos'è il Gateway Web e perché è necessario?**
  * *R: I browser non supportano direttamente le connessioni socket TCP 'crude' per motivi di sicurezza. Supportano invece i WebSocket. Il gateway Flask fa da intermediario (bridge): riceve i messaggi tramite WebSocket dal client browser e li inoltra su una socket TCP classica al server, rendendo la web app compatibile con il server preesistente.*
