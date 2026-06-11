# Presentation Script for the Exam (Oral Presentation Speech)

This document is structured as a ready-to-use speech (complete with potential questions and answers) to present the project to the professor during the oral exam. It is written in the first person, using clear, technical, and fluent English.

---

## 1. Introduction and Project Goal
> **How to start the presentation:**

"Professor, the project I developed is a **Multi-Room Chat application with an integrated Tic-Tac-Toe game**. The main goal is to show how different models and paradigms of distributed communication can cooperate within a single infrastructure.

The application allows multiple users to connect, join specific rooms, chat with each other (both publicly and privately), and start Tic-Tac-Toe games directly inside the chat room, all updated in real time."

---

## 2. System Architecture
> **Explaining the network structure:**

"From an architectural perspective, the system follows a **classic Client-Server model**:
* At the center is the **Main Server (`server.py`)**, written in pure Python without external libraries to demonstrate the direct use of TCP sockets. It is a multi-threaded server that spawns a thread for each connected client to handle requests concurrently.
* For the clients, we have two modes: a **terminal-based** client (`client.py`) and a modern **web graphical user interface**.

To connect the web page without altering the TCP server's logic, I implemented a **Web Gateway (`web_gateway.py`)** in Flask that acts as a 'translator'. The browser communicates with the gateway using **WebSockets** (via *Socket.IO*), and the gateway in turn opens a standard TCP socket to the main server. This way, the entire system remains unified and driven by a single TCP server."

---

## 3. Communication Models Used (The Core of the Oral Exam)
> **This is the most important part to show theoretical knowledge applied to practice:**

"The key feature of the project is that it is not limited to a single type of communication, but rather implements three fundamental paradigms of distributed systems:

### 1. Publish-Subscribe (Application Pub-Sub)
We use it for managing the **chat rooms**:
* The rooms act exactly like **Topics**.
* When a user logs in and joins a room, they are essentially **subscribing** to that topic.
* From that moment on, they will only receive messages published to that room, while the server filters and discards messages from other rooms they are not subscribed to.

### 2. Application Multicast (Group Broadcast)
We use it for **group communications** within a single room:
* When a user sends a normal chat message, or when a system event occurs (such as a new user joining), the server multicasts that message to all clients associated with that specific room.
* In the Tic-Tac-Toe game, every move is validated by the server and sent via multicast to the entire room. This ensures that the board updates in real time for all users in the room, including any spectators.

### 3. Point-to-Point (Unicast)
We use it for **direct and private interactions**:
* For private messages between two users (`/msg username message`), the server forwards the data exclusively to the recipient's socket, without involving other users.
* In the Tic-Tac-Toe game, we use point-to-point communication to handle private game states: for example, turn prompts like *'It's your turn'* or *'Wait for your turn'*, and especially the final game outcome messages (*'🏆 YOU WON!'* sent only to the winner and *'😞 YOU LOST!'* sent only to the loser)."

---

## 4. State Management and Validation
> **How the game is managed:**

"I want to emphasize that **all game logic and state management are centralized on the server**. The board and turn states do not reside on the client side. When a user clicks on the grid or types `/mossa N`, they only send the intention to make a move.
The server receives the request in the thread dedicated to that client, validates whether it is actually their turn, if the cell is empty, and if the match is active. Only after this validation does it update the state in memory and notify the clients of the result. This prevents any anomalous behavior or attempts to submit invalid moves."

---

## 5. Potential Professor Questions (and how to answer them)

* **Q: Why did you choose TCP instead of UDP?**
  * *A: We chose TCP because both chat messages and game moves require maximum reliability. With UDP, we would risk losing text messages or moves, which would corrupt the game state. TCP guarantees reliable, ordered delivery of messages through acknowledgment (ACK) and retransmission mechanisms.*

* **Q: How is concurrency handled on the server?**
  * *A: The server uses a thread-per-client model. The main thread listens for new connections using `accept()`. As soon as a client connects, it spawns an independent daemon thread that runs an infinite loop for receiving data (`recv`). This ensures that one client's blocking read operation does not block the other clients.*

* **Q: What is the Web Gateway and why is it necessary?**
  * *A: Web browsers do not directly support raw TCP socket connections due to security constraints. Instead, they support WebSockets. The Flask gateway acts as an intermediary (bridge): it receives WebSocket messages from the browser client and forwards them over a standard TCP socket to the server, making the web application compatible with the pre-existing TCP server.*
