// Client web — Chat Multi-Stanza + Tris Multiplayer.
// Comunica col gateway (web_gateway.py) via Socket.IO.

const socket = io();

// --- Stato dell'app ---
let myName = "";
let myRoom = "";
let roomUsers = [];
let wantListEcho = false;
let currentMode = "chat";   // "chat" oppure "tris"
let mySymbol = "";           // "X" oppure "O" (solo in modalità tris)
let isMyTurn = false;        // true se tocca a me muovere

// --- Riferimenti DOM ---
const loginScreen    = document.getElementById("login-screen");
const chatScreen     = document.getElementById("chat-screen");
const loginForm      = document.getElementById("login-form");
const usernameInput  = document.getElementById("username-input");
const roomInput      = document.getElementById("room-input");
const loginError     = document.getElementById("login-error");
const enterBtn       = document.getElementById("enter-btn");
const roomLabelEl    = document.getElementById("room-label");

// selettore modalità
const modeChatBtn = document.getElementById("mode-chat");
const modeTrisBtn = document.getElementById("mode-tris");

// schermata chat
const roomNameEl    = document.getElementById("room-name");
const roomBadgeEl   = document.getElementById("room-badge");
const modeLabelEl   = document.getElementById("mode-label");
const topbarRoomEl  = document.getElementById("topbar-room");
const myNameEl      = document.getElementById("my-name");
const myAvatarEl    = document.getElementById("my-avatar");
const usersListEl   = document.getElementById("users-list");
const usersTitleEl  = document.getElementById("users-title");

const messagesEl    = document.getElementById("messages");
const messageForm   = document.getElementById("message-form");
const messageInput  = document.getElementById("message-input");
const msgUserPicker = document.getElementById("msg-user-picker");
const cmdPicker     = document.getElementById("cmd-picker");
const cmdListBtn    = document.getElementById("cmd-list");
const refreshUsersBtn = document.getElementById("refresh-users");
const leaveBtn      = document.getElementById("leave-btn");

// scacchiera tris
const trisBoard  = document.getElementById("tris-board");
const trisStatus = document.getElementById("tris-status");
const trisCells  = document.querySelectorAll(".tris-cell");

// ===================== SELETTORE MODALITÀ =====================
modeChatBtn.addEventListener("click", () => {
    currentMode = "chat";
    modeChatBtn.classList.add("is-active");
    modeTrisBtn.classList.remove("is-active");
    roomLabelEl.textContent = "Stanza";
    roomInput.placeholder = "es. generale";
    enterBtn.textContent = "Entra nella chat";
});

modeTrisBtn.addEventListener("click", () => {
    currentMode = "tris";
    modeTrisBtn.classList.add("is-active");
    modeChatBtn.classList.remove("is-active");
    roomLabelEl.textContent = "Tavolo";
    roomInput.placeholder = "es. Tavolo-1";
    enterBtn.textContent = "Entra nella partita";
});

// ===================== INVIO HANDSHAKE =====================
loginForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const username = usernameInput.value.trim();
    const room = roomInput.value.trim();
    if (!username || !room) return;

    myName = username;
    myRoom = room;

    // invio l'evento giusto in base alla modalità scelta
    if (currentMode === "tris") {
        socket.emit("join_tris", { username, room });
    } else {
        socket.emit("join", { username, room });
    }
});

// ===================== EVENTI DAL GATEWAY =====================
socket.on("joined", ({ username, room, mode }) => {
    myName = username;
    myRoom = room;

    roomNameEl.textContent = room;
    topbarRoomEl.textContent = "#" + room;
    myNameEl.textContent = username;
    myAvatarEl.textContent = initials(username);
    myAvatarEl.style.background = colorFor(username);

    loginScreen.hidden = true;
    chatScreen.hidden = false;

    // se la modalità è tris: mostro la scacchiera e nascondo il composer di chat
    if (mode === "tris") {
        currentMode = "tris";
        trisBoard.hidden = false;
        messageForm.hidden = true;
        cmdListBtn.hidden = true;
        roomBadgeEl.textContent = "❌";
        modeLabelEl.textContent = "Tavolo";
        trisStatus.textContent = "In attesa dell'avversario…";
        resetBoard();
    } else {
        currentMode = "chat";
        trisBoard.hidden = true;
        messageForm.hidden = false;
        roomBadgeEl.textContent = "#";
        modeLabelEl.textContent = "Stanza";
        messageInput.focus();
        socket.emit("send_message", { text: "/list" });
    }
});

socket.on("error_msg", ({ text }) => {
    loginError.textContent = text;
    loginError.hidden = false;
});

socket.on("server_closed", () => {
    addSystemMessage("Connessione chiusa dal server.", true);
});

socket.on("message", ({ text }) => {
    // il messaggio arriva sempre come stringa grezza dal server (chat o tris)
    if (currentMode === "tris") {
        handleTrisMessage(text);
    } else {
        handleIncoming(text);
    }
});

// ===================== LOGICA TRIS =====================
function resetBoard() {
    // svuoto tutte le celle della scacchiera
    trisCells.forEach((cell) => {
        cell.textContent = "";
        cell.className = "tris-cell";
        cell.disabled = true;   // le disabilito finché non tocca a me
    });
    isMyTurn = false;
}

function handleTrisMessage(text) {
    // il server tris manda messaggi di testo grezzo: li interpreto qui

    // riga della scacchiera come " X | O |   " → aggiorno la cella corrispondente
    // prima di tutto controllo se il testo contiene una scacchiera ASCII
    const lines = text.split("\n").map(l => l.trim()).filter(Boolean);

    // cerco le tre righe di gioco (contengono "|")
    const boardLines = lines.filter(l => l.match(/^\S+\s*\|\s*\S+\s*\|\s*\S+/));
    if (boardLines.length === 3) {
        // aggiorno la scacchiera grafica con i simboli estratti dalle righe
        const symbols = [];
        boardLines.forEach(line => {
            // splitta per "|", e per ogni parte prende il simbolo (es. "X", "O" o " ")
            line.split("|").forEach(part => {
                const s = part.trim();
                symbols.push(s === "" ? " " : s);
            });
        });
        updateBoardUI(symbols);
        return;
    }

    // "Tocca a te" → abilito i bottoni della scacchiera
    if (/Tocca a te/i.test(text)) {
        isMyTurn = true;
        trisStatus.textContent = "🟢 Tocca a te! Clicca una cella.";
        trisCells.forEach(cell => {
            // abilito solo le celle ancora vuote
            if (!cell.textContent) {
                cell.disabled = false;
            }
        });
        return;
    }

    // "Aspetta il tuo turno" o "Aspetta" → disabilito i bottoni
    if (/Aspetta/i.test(text)) {
        isMyTurn = false;
        trisStatus.textContent = "⏳ Aspetta il turno dell'avversario…";
        trisCells.forEach(cell => { cell.disabled = true; });
        return;
    }

    // simbolo assegnato al giocatore: "Tu sei X" o "Tu sei O"
    if (/Tu sei X/i.test(text)) {
        mySymbol = "X";
    } else if (/Tu sei O/i.test(text)) {
        mySymbol = "O";
    }

    // partita vinta, persa o pareggio → messaggio di sistema
    if (/ha vinto|Pareggio|Nuova partita|Partita iniziata|sei entrato/i.test(text)) {
        addSystemMessage(text);
        if (/Nuova partita/i.test(text)) {
            // resetto la scacchiera per la prossima partita
            resetBoard();
        }
        return;
    }

    // tutti gli altri messaggi (errori, avvisi) → log in chat
    if (text.trim()) {
        addSystemMessage(text);
    }
}

function updateBoardUI(symbols) {
    // symbols è un array di 9 elementi: " ", "X" o "O"
    trisCells.forEach((cell, i) => {
        const s = symbols[i];
        if (s === "X") {
            cell.textContent = "✕";
            cell.className = "tris-cell x";
            cell.disabled = true;
        } else if (s === "O") {
            cell.textContent = "○";
            cell.className = "tris-cell o";
            cell.disabled = true;
        } else {
            // cella vuota: abilitata solo se è il mio turno
            cell.textContent = "";
            cell.className = "tris-cell";
            cell.disabled = !isMyTurn;
        }
    });
}

// clic su una cella della scacchiera
trisCells.forEach((cell) => {
    cell.addEventListener("click", () => {
        if (!isMyTurn || cell.disabled || cell.textContent !== "") return;

        const numero = parseInt(cell.dataset.cell);
        socket.emit("tris_move", { cell: numero });

        // disabilito subito tutti i bottoni (aspetto la risposta del server)
        isMyTurn = false;
        trisStatus.textContent = "⏳ Aspetta il turno dell'avversario…";
        trisCells.forEach(c => { c.disabled = true; });
    });
});

// ===================== PARSING DEI MESSAGGI CHAT =====================
function handleIncoming(text) {
    // 1) Lista utenti -> aggiorno la sidebar
    const listMatch = text.match(/^Utenti nella stanza '.*?':\s*(.*)$/);
    if (listMatch) {
        updateUsersList(listMatch[1]);
        if (wantListEcho) {
            addSystemMessage(text);
            wantListEcho = false;
        }
        return;
    }

    // 2) Messaggio privato: "[Privato da X]: testo"
    const privMatch = text.match(/^\[Privato da (.+?)\]:\s?([\s\S]*)$/);
    if (privMatch) {
        addChatMessage(privMatch[1], privMatch[2], { mine: false, priv: true });
        return;
    }

    // 3) Messaggi di sistema
    if (
        /^Benvenuto nella stanza/.test(text) ||
        /è entrato nella stanza/.test(text) ||
        /ha lasciato la stanza/.test(text) ||
        /^Utente '.*' non trovato/.test(text) ||
        /^Uso: \/msg/.test(text) ||
        /^Stanza non trovata/.test(text)
    ) {
        addSystemMessage(text);
        if (/entrato nella stanza|ha lasciato la stanza/.test(text)) {
            socket.emit("send_message", { text: "/list" });
        }
        return;
    }

    // 4) Messaggio normale: "username: testo"
    const normalMatch = text.match(/^(.+?):\s([\s\S]*)$/);
    if (normalMatch) {
        addChatMessage(normalMatch[1], normalMatch[2], { mine: false, priv: false });
        return;
    }

    // 5) Qualsiasi altra cosa -> sistema
    addSystemMessage(text);
}

// ===================== RENDERING =====================
function addChatMessage(author, body, { mine, priv }) {
    const wrap = document.createElement("div");
    wrap.className = "msg";
    if (mine) wrap.classList.add("is-mine");
    if (priv) wrap.classList.add("is-private");

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = initials(author);
    avatar.style.background = colorFor(author);

    const bodyEl = document.createElement("div");
    bodyEl.className = "msg-body";

    const meta = document.createElement("div");
    meta.className = "msg-meta";
    meta.textContent = author;
    if (priv) {
        const tag = document.createElement("span");
        tag.className = "tag-private";
        tag.textContent = "privato";
        meta.appendChild(tag);
    }

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    bubble.textContent = body;

    bodyEl.appendChild(meta);
    bodyEl.appendChild(bubble);
    wrap.appendChild(avatar);
    wrap.appendChild(bodyEl);
    messagesEl.appendChild(wrap);
    scrollToBottom();
}

function addSystemMessage(text, isError = false) {
    const el = document.createElement("div");
    el.className = "msg-system";
    if (isError) el.classList.add("is-error");
    el.textContent = text;
    messagesEl.appendChild(el);
    scrollToBottom();
}

function updateUsersList(raw) {
    const names = raw.split(",").map((n) => n.trim()).filter(Boolean);
    roomUsers = names;
    usersListEl.innerHTML = "";
    usersTitleEl.textContent = `Utenti · ${names.length}`;

    names.forEach((name) => {
        const li = document.createElement("li");
        li.className = "user-item";
        if (name === myName) li.classList.add("is-me");

        const avatar = document.createElement("div");
        avatar.className = "avatar";
        avatar.textContent = initials(name);
        avatar.style.background = colorFor(name);

        const label = document.createElement("span");
        label.textContent = name === myName ? `${name} (tu)` : name;

        li.appendChild(avatar);
        li.appendChild(label);

        if (name !== myName) {
            li.addEventListener("click", () => {
                messageInput.value = `/msg ${name} `;
                messageInput.focus();
            });
        }

        usersListEl.appendChild(li);
    });

    updateMsgUserPicker();
}

// ===================== UTILITIES =====================
const AVATAR_COLORS = [
    "#6366f1", "#8b5cf6", "#ec4899", "#f59e0b",
    "#22c55e", "#06b6d4", "#ef4444", "#14b8a6",
];

function colorFor(name) {
    let hash = 0;
    for (let i = 0; i < name.length; i++) {
        hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }
    return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

function initials(name) {
    return (name.trim()[0] || "?").toUpperCase();
}

function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

// ===================== COMANDI CHAT =====================
const COMMANDS = [
    { name: "/msg", args: " ", desc: "Messaggio privato a un utente", template: "/msg " },
    { name: "/list", args: "", desc: "Mostra gli utenti nella stanza", template: "/list" },
    { name: "/quit", args: "", desc: "Esci dalla chat", template: "/quit" },
];

function getMsgPickerFilter(text) {
    if (!text.startsWith("/msg")) return null;
    const rest = text.slice(4);
    if (rest === "" || rest === " ") return "";
    if (!rest.startsWith(" ")) return null;
    const partial = rest.slice(1);
    if (partial.includes(" ")) return null;
    return partial.toLowerCase();
}

function hideMsgUserPicker() {
    msgUserPicker.hidden = true;
    msgUserPicker.innerHTML = "";
}

function selectMsgUser(name) {
    messageInput.value = `/msg ${name} `;
    hideMsgUserPicker();
    messageInput.focus();
}

function updateMsgUserPicker() {
    const filter = getMsgPickerFilter(messageInput.value);
    if (filter === null) { hideMsgUserPicker(); return; }

    const candidates = roomUsers.filter(
        (name) => name !== myName && name.toLowerCase().startsWith(filter)
    );

    msgUserPicker.innerHTML = "";
    if (candidates.length === 0) {
        const empty = document.createElement("li");
        empty.className = "msg-user-picker-empty";
        empty.textContent = filter ? "Nessun utente trovato" : "Nessun altro utente in stanza";
        msgUserPicker.appendChild(empty);
        msgUserPicker.hidden = false;
        return;
    }

    candidates.forEach((name) => {
        const li = document.createElement("li");
        li.className = "user-item";
        li.setAttribute("role", "option");
        const avatar = document.createElement("div");
        avatar.className = "avatar";
        avatar.textContent = initials(name);
        avatar.style.background = colorFor(name);
        const label = document.createElement("span");
        label.textContent = name;
        li.appendChild(avatar);
        li.appendChild(label);
        li.dataset.selectable = "1";
        li.__select = () => selectMsgUser(name);
        li.__complete = () => selectMsgUser(name);
        li.addEventListener("mousedown", (e) => { e.preventDefault(); selectMsgUser(name); });
        msgUserPicker.appendChild(li);
    });
    msgUserPicker.hidden = false;
}

function getCmdPickerFilter(text) {
    if (!text.startsWith("/")) return null;
    if (text.includes(" ")) return null;
    return text.slice(1).toLowerCase();
}

function hideCmdPicker() {
    cmdPicker.hidden = true;
    cmdPicker.innerHTML = "";
}

function selectCmd(cmd) {
    if (cmd.args === "") {
        messageInput.value = cmd.template;
        hideAllPickers();
        messageForm.requestSubmit();
        messageInput.focus();
        return;
    }
    completeCmd(cmd);
}

function completeCmd(cmd) {
    messageInput.value = cmd.template;
    hideCmdPicker();
    messageInput.focus();
    if (cmd.args !== "") { updateMsgUserPicker(); }
    syncPickerItems();
}

function updateCmdPicker() {
    const filter = getCmdPickerFilter(messageInput.value);
    if (filter === null) { hideCmdPicker(); return false; }

    const matches = COMMANDS.filter((c) => c.name.slice(1).startsWith(filter));
    cmdPicker.innerHTML = "";
    if (matches.length === 0) { hideCmdPicker(); return false; }

    matches.forEach((cmd) => {
        const li = document.createElement("li");
        li.className = "cmd-item";
        li.setAttribute("role", "option");
        const name = document.createElement("div");
        name.className = "cmd-name";
        const matched = filter.length;
        name.innerHTML = "/<b>" + cmd.name.slice(1, 1 + matched) + "</b>" + cmd.name.slice(1 + matched);
        const desc = document.createElement("div");
        desc.className = "cmd-desc";
        desc.textContent = cmd.desc;
        li.appendChild(name);
        li.appendChild(desc);
        li.dataset.selectable = "1";
        li.__select = () => selectCmd(cmd);
        li.__complete = () => completeCmd(cmd);
        li.addEventListener("mousedown", (e) => { e.preventDefault(); selectCmd(cmd); });
        cmdPicker.appendChild(li);
    });
    cmdPicker.hidden = false;
    return true;
}

let pickerItems = [];
let activeIndex = -1;

function activePicker() {
    if (!cmdPicker.hidden) return cmdPicker;
    if (!msgUserPicker.hidden) return msgUserPicker;
    return null;
}

function syncPickerItems() {
    const p = activePicker();
    pickerItems = p ? Array.from(p.querySelectorAll("[data-selectable]")) : [];
    activeIndex = -1;
}

function setActive(idx) {
    pickerItems.forEach((el) => el.classList.remove("is-active"));
    if (pickerItems.length === 0) { activeIndex = -1; return; }
    activeIndex = (idx + pickerItems.length) % pickerItems.length;
    const el = pickerItems[activeIndex];
    el.classList.add("is-active");
    el.scrollIntoView({ block: "nearest" });
}

function hideAllPickers() {
    hideMsgUserPicker();
    hideCmdPicker();
    pickerItems = [];
    activeIndex = -1;
}

function refreshPickers() {
    if (updateCmdPicker()) { hideMsgUserPicker(); } else { updateMsgUserPicker(); }
    syncPickerItems();
}

messageInput.addEventListener("input", refreshPickers);

messageInput.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { hideAllPickers(); return; }
    if (!activePicker() || pickerItems.length === 0) return;
    if (e.key === "ArrowDown") { e.preventDefault(); setActive(activeIndex + 1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive(activeIndex - 1); }
    else if (e.key === "Tab") { e.preventDefault(); const idx = activeIndex >= 0 ? activeIndex : 0; pickerItems[idx].__complete(); }
    else if (e.key === "Enter") { if (activeIndex >= 0) { e.preventDefault(); pickerItems[activeIndex].__select(); } }
});

messageInput.addEventListener("blur", () => { setTimeout(hideAllPickers, 150); });

// ===================== INVIO MESSAGGI CHAT =====================
messageForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = messageInput.value.trim();
    if (!text) return;

    if (text === "/quit") {
        socket.emit("send_message", { text });
        location.reload();
        return;
    }

    if (text === "/list") {
        wantListEcho = true;
        socket.emit("send_message", { text });
        messageInput.value = "";
        hideAllPickers();
        return;
    }

    const privCmd = text.match(/^\/msg\s+(\S+)\s+([\s\S]+)$/);
    if (privCmd) {
        addChatMessage(`Tu → ${privCmd[1]}`, privCmd[2], { mine: true, priv: true });
        socket.emit("send_message", { text });
        messageInput.value = "";
        hideAllPickers();
        return;
    }

    if (text.startsWith("/")) {
        socket.emit("send_message", { text });
        messageInput.value = "";
        hideAllPickers();
        return;
    }

    addChatMessage(myName, text, { mine: true, priv: false });
    socket.emit("send_message", { text });
    messageInput.value = "";
    hideAllPickers();
});

cmdListBtn.addEventListener("click", () => {
    wantListEcho = true;
    socket.emit("send_message", { text: "/list" });
});

refreshUsersBtn.addEventListener("click", () => {
    socket.emit("send_message", { text: "/list" });
});

leaveBtn.addEventListener("click", () => {
    if (currentMode === "tris") {
        location.reload();
    } else {
        socket.emit("send_message", { text: "/quit" });
        location.reload();
    }
});
