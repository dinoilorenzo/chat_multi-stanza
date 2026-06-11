// Client web della Chat Multi-Stanza con Tris integrato.
// Comunica col gateway (web_gateway.py) via Socket.IO.
// Il gateway fa da ponte verso server.py (TCP 5555).

const socket = io();

// --- Stato dell'app ---
let myName = "";
let myRoom = "";
let roomUsers = [];
let wantListEcho = false;
let gameActive = false;   // true quando c'è una partita di tris in corso
let isMyTurn = false;     // true quando tocca a me muovere nel tris

// --- Riferimenti DOM ---
const loginScreen   = document.getElementById("login-screen");
const chatScreen    = document.getElementById("chat-screen");
const loginForm     = document.getElementById("login-form");
const usernameInput = document.getElementById("username-input");
const roomInput     = document.getElementById("room-input");
const loginError    = document.getElementById("login-error");

const roomNameEl    = document.getElementById("room-name");
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
const cmdGameBtn    = document.getElementById("cmd-game");
const refreshUsersBtn = document.getElementById("refresh-users");
const leaveBtn      = document.getElementById("leave-btn");

// scacchiera tris
const trisBoard  = document.getElementById("tris-board");
const trisStatus = document.getElementById("tris-status");
const trisCells  = document.querySelectorAll(".tris-cell");

// comandi disponibili per l'autocompletamento
const COMMANDS = [
    { name: "/msg",   args: " ", desc: "Messaggio privato a un utente", template: "/msg " },
    { name: "/list",  args: "",  desc: "Mostra gli utenti nella stanza", template: "/list" },
    { name: "/game",  args: "",  desc: "Avvia una partita di Tris nella stanza", template: "/game" },
    { name: "/mossa", args: " ", desc: "Gioca nella cella N (1-9)", template: "/mossa " },
    { name: "/quit",  args: "",  desc: "Esci dalla chat", template: "/quit" },
];

// ===================== INVIO HANDSHAKE =====================
loginForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const username = usernameInput.value.trim();
    const room = roomInput.value.trim();
    if (!username || !room) return;

    myName = username;
    myRoom = room;
    socket.emit("join", { username, room });
});

// ===================== EVENTI DAL GATEWAY =====================
socket.on("joined", ({ username, room }) => {
    myName = username;
    myRoom = room;

    roomNameEl.textContent = room;
    topbarRoomEl.textContent = "#" + room;
    myNameEl.textContent = username;
    myAvatarEl.textContent = initials(username);
    myAvatarEl.style.background = colorFor(username);

    loginScreen.hidden = true;
    chatScreen.hidden = false;
    messageInput.focus();

    // chiedo subito la lista utenti
    socket.emit("send_message", { text: "/list" });
});

socket.on("error_msg", ({ text }) => {
    loginError.textContent = text;
    loginError.hidden = false;
});

socket.on("server_closed", () => {
    addSystemMessage("Connessione chiusa dal server.", true);
});

socket.on("message", ({ text }) => {
    handleIncoming(text);
});

// ===================== PARSING DEI MESSAGGI =====================
function handleIncoming(text) {

    // 1) Riga della scacchiera tris (es. " X | O |   ") → aggiorno la UI grafica
    if (/^\s*[XO ]\s*\|\s*[XO ]\s*\|\s*[XO ]\s*$/.test(text)) {
        if (gameActive) {
            parseBoardLine(text);
        }
        // non mostro le righe ASCII in chat quando la board è visibile
        return;
    }

    // 2) Separatori della scacchiera: ignoro
    if (/^---\+---\+---$/.test(text)) {
        return;
    }

    // 3) Inizio partita → mostro la scacchiera e messaggio di sistema
    if (/=== PARTITA DI TRIS/.test(text)) {
        showBoard();
        addSystemMessage(text);
        return;
    }

    // 4) "Tocca a te" → abilito le celle
    if (/^(Tu sei X\.\s+)?Tocca a te/i.test(text)) {
        isMyTurn = true;
        trisStatus.textContent = "🟢 Tocca a te! Clicca una cella.";
        enableEmptyCells();
        addSystemMessage(text);
        return;
    }

    // 5) "Aspetta il tuo turno" → disabilito le celle
    if (/^Tu sei O\.\s*Aspetta il tuo turno/i.test(text)) {
        isMyTurn = false;
        trisStatus.textContent = "⏳ Aspetta il turno dell'avversario…";
        disableAllCells();
        addSystemMessage(text);
        return;
    }

    // 6) HAI VINTO → messaggio speciale di vittoria
    if (/^🏆\s*HAI VINTO/i.test(text)) {
        isMyTurn = false;
        disableAllCells();
        addWinMessage(text);
        return;
    }

    // 7) HAI PERSO → messaggio speciale di sconfitta
    if (/^😞\s*HAI PERSO/i.test(text)) {
        isMyTurn = false;
        disableAllCells();
        addLoseMessage(text);
        return;
    }

    // 8) Fine partita → nascondo la scacchiera dopo qualche secondo
    if (/^Potete continuare a chattare|^Potete usare \/game|^===\s+.*\s+Partita annullata\./i.test(text)) {
        addSystemMessage(text);
        setTimeout(hideBoard, 3000);
        return;
    }

    // 9) Lista utenti → aggiorno la sidebar
    const listMatch = text.match(/^Utenti nella stanza '.*?':\s*(.*)$/);
    if (listMatch) {
        updateUsersList(listMatch[1]);
        if (wantListEcho) {
            addSystemMessage(text);
            wantListEcho = false;
        }
        return;
    }

    // 10) Messaggio privato: "[Privato da X]: testo"
    const privMatch = text.match(/^\[Privato da (.+?)\]:\s?([\s\S]*)$/);
    if (privMatch) {
        addChatMessage(privMatch[1], privMatch[2], { mine: false, priv: true });
        return;
    }

    // 11) Messaggi di sistema (entrate/uscite/benvenuto/avvisi/tris)
    if (
        /^Benvenuto nella stanza/.test(text) ||
        /^[^:]+ è entrato nella stanza\./.test(text) ||
        /^[^:]+ ha lasciato la stanza\./.test(text) ||
        /^Utente '.*' non trovato/.test(text) ||
        /^Uso:/.test(text) ||
        /^Comandi:/.test(text) ||
        /^===/.test(text) ||
        /^Servono almeno/.test(text) ||
        /^[^:]*non c'è nessuna partita/i.test(text) ||
        /^Non sei uno dei giocatori/.test(text) ||
        /^[^:]*c'è già una partita/i.test(text) ||
        /^Pareggio/.test(text)
    ) {
        addSystemMessage(text);
        if (/ è entrato nella stanza\.| ha lasciato la stanza\./.test(text)) {
            socket.emit("send_message", { text: "/list" });
        }
        return;
    }

    // 12) Messaggio normale: "username: testo"
    const normalMatch = text.match(/^(.+?):\s([\s\S]*)$/);
    if (normalMatch) {
        addChatMessage(normalMatch[1], normalMatch[2], { mine: false, priv: false });
        return;
    }

    // 13) Qualsiasi altra cosa → sistema
    if (text.trim()) {
        addSystemMessage(text);
    }
}

// ===================== LOGICA SCACCHIERA TRIS =====================

// buffer per raccogliere le 3 righe della scacchiera prima di aggiornarla
let boardLineBuffer = [];

function parseBoardLine(line) {
    // una riga della scacchiera ha questo formato: " X | O |   "
    boardLineBuffer.push(line);
    if (boardLineBuffer.length === 3) {
        // ho tutte e 3 le righe: aggiorno la scacchiera grafica
        const symbols = [];
        boardLineBuffer.forEach(row => {
            row.split("|").forEach(part => {
                const s = part.trim();
                symbols.push(s === "" ? " " : s);
            });
        });
        updateBoardUI(symbols);
        boardLineBuffer = [];
    }
}

function updateBoardUI(symbols) {
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
            cell.textContent = "";
            cell.className = "tris-cell";
            cell.disabled = !isMyTurn;
        }
    });
}

function showBoard() {
    gameActive = true;
    isMyTurn = false;
    boardLineBuffer = [];
    trisBoard.hidden = false;
    trisStatus.textContent = "Partita in corso…";
    resetBoard();
}

function hideBoard() {
    gameActive = false;
    isMyTurn = false;
    boardLineBuffer = [];
    trisBoard.hidden = true;
}

function resetBoard() {
    trisCells.forEach(cell => {
        cell.textContent = "";
        cell.className = "tris-cell";
        cell.disabled = true;
    });
}

function enableEmptyCells() {
    trisCells.forEach(cell => {
        if (!cell.textContent) {
            cell.disabled = false;
        }
    });
}

function disableAllCells() {
    trisCells.forEach(cell => { cell.disabled = true; });
}

// clic su una cella della scacchiera → invia /mossa N
trisCells.forEach(cell => {
    cell.addEventListener("click", () => {
        if (!isMyTurn || cell.disabled || cell.textContent !== "") return;

        const numero = cell.dataset.cell;
        // invia il comando /mossa N come messaggio normale al server
        socket.emit("send_message", { text: `/mossa ${numero}` });

        isMyTurn = false;
        trisStatus.textContent = "⏳ Aspetta il turno dell'avversario…";
        disableAllCells();
    });
});

// ===================== RENDERING MESSAGGI =====================
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

function addWinMessage(text) {
    // messaggio speciale stile banner per la vittoria
    const el = document.createElement("div");
    el.className = "msg-system msg-win";
    el.textContent = text;
    messagesEl.appendChild(el);
    scrollToBottom();
}

function addLoseMessage(text) {
    // messaggio speciale stile banner per la sconfitta
    const el = document.createElement("div");
    el.className = "msg-system msg-lose";
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

// ===================== AUTOCOMPLETAMENTO COMANDI =====================
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
    pickerItems[activeIndex].classList.add("is-active");
    pickerItems[activeIndex].scrollIntoView({ block: "nearest" });
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

// ===================== INVIO MESSAGGI =====================
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

    // /game — avvia partita, lo mostro anche in chat come mia azione
    if (text === "/game") {
        addSystemMessage("Stai avviando una partita di Tris…");
        socket.emit("send_message", { text });
        messageInput.value = "";
        hideAllPickers();
        return;
    }

    // /mossa N — mossa nel tris
    if (text.startsWith("/mossa ")) {
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

    // messaggio normale: eco locale + invio
    addChatMessage(myName, text, { mine: true, priv: false });
    socket.emit("send_message", { text });
    messageInput.value = "";
    hideAllPickers();
});

cmdListBtn.addEventListener("click", () => {
    wantListEcho = true;
    socket.emit("send_message", { text: "/list" });
});

cmdGameBtn.addEventListener("click", () => {
    addSystemMessage("Stai avviando una partita di Tris…");
    socket.emit("send_message", { text: "/game" });
});

refreshUsersBtn.addEventListener("click", () => {
    socket.emit("send_message", { text: "/list" });
});

leaveBtn.addEventListener("click", () => {
    socket.emit("send_message", { text: "/quit" });
    location.reload();
});
