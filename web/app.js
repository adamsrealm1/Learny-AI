const chatLog = document.querySelector("#chatLog");
const chatForm = document.querySelector("#chatForm");
const messageInput = document.querySelector("#messageInput");
const sendButton = document.querySelector("#sendButton");
const messageTemplate = document.querySelector("#messageTemplate");
const connectionPill = document.querySelector("#connectionPill");
const chatList = document.querySelector("#chatList");
const addChatButton = document.querySelector("#addChatButton");
const emptyState = document.querySelector("#emptyState");
const newChatButton = document.querySelector("#newChatButton");

const CHATS_KEY = "learny-chats";
const ACTIVE_CHAT_KEY = "learny-active-chat-id";
const SESSION_KEY = "learny-session-id";
const DIRECT_FILE_MODE = window.location.protocol === "file:";
const STATUS_CHECK_INTERVAL_MS = 15000;
const SERVER_HINT = "Run wasmer run . --net --env PORT=8000, then open http://127.0.0.1:8000.";

let chats = loadStoredChats();
let activeChatId = localStorage.getItem(ACTIVE_CHAT_KEY) || "";
let sessionId = "";
let isSending = false;

function createId(prefix) {
  const randomPart = Math.random().toString(36).slice(2, 10);
  return `${prefix}-${Date.now().toString(36)}-${randomPart}`;
}

function loadStoredChats() {
  try {
    const parsed = JSON.parse(localStorage.getItem(CHATS_KEY) || "[]");
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed
      .filter((chat) => chat && typeof chat === "object" && typeof chat.id === "string")
      .map((chat) => ({
        id: chat.id,
        title: typeof chat.title === "string" && chat.title.trim() ? chat.title.trim() : "New chat",
        sessionId:
          typeof chat.sessionId === "string" && chat.sessionId.trim()
            ? chat.sessionId.trim()
            : createId("session"),
        updatedAt: Number.isFinite(chat.updatedAt) ? chat.updatedAt : Date.now(),
        messages: Array.isArray(chat.messages)
          ? chat.messages
              .filter(
                (message) =>
                  message &&
                  typeof message === "object" &&
                  typeof message.speaker === "string" &&
                  typeof message.text === "string",
              )
              .map((message) => ({
                speaker: message.speaker,
                text: message.text,
                source: typeof message.source === "string" ? message.source : "",
                thoughtSeconds: normalizeThoughtSeconds(message.thoughtSeconds),
              }))
          : [],
      }));
  } catch (error) {
    return [];
  }
}

function saveChats() {
  localStorage.setItem(CHATS_KEY, JSON.stringify(chats));
}

function getChatById(chatId) {
  return chats.find((chat) => chat.id === chatId) || null;
}

function getActiveChat() {
  return getChatById(activeChatId);
}

function sortedChats() {
  return [...chats].sort((left, right) => right.updatedAt - left.updatedAt);
}

function formatChatMeta(chat) {
  const count = chat.messages.filter((message) => message.speaker === "You").length;
  if (count === 0) {
    return "Empty chat";
  }
  return `${count} message${count === 1 ? "" : "s"}`;
}

function titleFromMessage(message) {
  const compact = message.replace(/\s+/g, " ").trim();
  if (!compact) {
    return "New chat";
  }
  return compact.length > 34 ? `${compact.slice(0, 34)}...` : compact;
}

function normalizeThoughtSeconds(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric < 0) {
    return null;
  }
  return Math.round(numeric * 10) / 10;
}

function formatThoughtSeconds(value) {
  const seconds = normalizeThoughtSeconds(value);
  if (seconds === null) {
    return "0";
  }
  return Number.isInteger(seconds) ? String(seconds) : seconds.toFixed(1);
}

function setEmptyState(visible) {
  if (emptyState) {
    emptyState.classList.toggle("hidden", !visible);
  }
}

function setConnection(state, label) {
  connectionPill.classList.remove("checking", "online", "offline");
  connectionPill.classList.add(state);
  connectionPill.querySelector("strong").textContent = label;
}

function sourceLabel(source, learned, model) {
  if (learned && model) {
    return `learned \u00b7 ${model}`;
  }
  if (source === "knowledge") {
    return "json";
  }
  if (source === "unknown") {
    return "unknown";
  }
  return source || "local";
}

function createChat() {
  const chat = {
    id: createId("chat"),
    title: "New chat",
    sessionId: createId("session"),
    updatedAt: Date.now(),
    messages: [],
  };
  chats.unshift(chat);
  activeChatId = chat.id;
  sessionId = chat.sessionId;
  localStorage.setItem(ACTIVE_CHAT_KEY, activeChatId);
  localStorage.setItem(SESSION_KEY, sessionId);
  saveChats();
  renderChatList();
  renderActiveChat();
  messageInput.focus();
  return chat;
}

function ensureActiveChat() {
  let chat = getActiveChat();
  if (!chat) {
    chat = createChat();
  }
  sessionId = chat.sessionId;
  localStorage.setItem(ACTIVE_CHAT_KEY, chat.id);
  localStorage.setItem(SESSION_KEY, sessionId);
  return chat;
}

function openChat(chatId) {
  const chat = getChatById(chatId);
  if (!chat) {
    return;
  }
  activeChatId = chat.id;
  sessionId = chat.sessionId;
  localStorage.setItem(ACTIVE_CHAT_KEY, activeChatId);
  localStorage.setItem(SESSION_KEY, sessionId);
  renderChatList();
  renderActiveChat();
  messageInput.focus();
}

function deleteChat(chatId) {
  const deletingActiveChat = chatId === activeChatId;
  chats = chats.filter((chat) => chat.id !== chatId);

  if (deletingActiveChat) {
    const nextChat = sortedChats()[0] || null;
    activeChatId = nextChat ? nextChat.id : "";
    sessionId = nextChat ? nextChat.sessionId : "";
  }

  if (activeChatId) {
    localStorage.setItem(ACTIVE_CHAT_KEY, activeChatId);
  } else {
    localStorage.removeItem(ACTIVE_CHAT_KEY);
  }

  if (sessionId) {
    localStorage.setItem(SESSION_KEY, sessionId);
  } else {
    localStorage.removeItem(SESSION_KEY);
  }

  saveChats();
  renderChatList();
  renderActiveChat();
}

function clearMessages() {
  chatLog.querySelectorAll(".message").forEach((message) => message.remove());
}

function displayMessage({ speaker, text, source = "", thoughtSeconds = null }) {
  setEmptyState(false);
  const node = messageTemplate.content.firstElementChild.cloneNode(true);
  node.classList.add(speaker === "You" ? "user" : "learny");
  node.querySelector(".speaker").textContent = speaker;
  node.querySelector(".source").textContent = source;
  const bubble = node.querySelector(".bubble");
  const textNode = document.createElement("span");
  textNode.className = "bubble-text";
  textNode.textContent = text;
  bubble.replaceChildren(textNode);

  if (speaker === "Learny") {
    const thought = document.createElement("span");
    thought.className = "thought-time";
    thought.textContent = `Thought for ${formatThoughtSeconds(thoughtSeconds)} seconds.`;
    bubble.append(thought);
  }

  chatLog.append(node);
  chatLog.scrollTop = chatLog.scrollHeight;
  return node;
}

function saveMessage(message) {
  const chat = ensureActiveChat();
  chat.messages.push(message);
  chat.updatedAt = Date.now();

  if (message.speaker === "You" && chat.title === "New chat") {
    chat.title = titleFromMessage(message.text);
  }

  saveChats();
  renderChatList();
}

function addMessage(message, { persist = true } = {}) {
  const node = displayMessage(message);
  if (persist) {
    saveMessage(message);
  }
  return node;
}

function renderActiveChat() {
  clearMessages();
  const chat = getActiveChat();
  if (!chat || chat.messages.length === 0) {
    setEmptyState(true);
    return;
  }
  chat.messages.forEach((message) => displayMessage(message));
}

function renderChatList() {
  chatList.replaceChildren();

  if (chats.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty-chat-list";
    empty.textContent = "No chats yet";
    chatList.append(empty);
    return;
  }

  sortedChats().forEach((chat) => {
    const item = document.createElement("article");
    item.className = "chat-item";
    if (chat.id === activeChatId) {
      item.classList.add("active");
    }

    const openButton = document.createElement("button");
    openButton.className = "chat-open-button";
    openButton.type = "button";
    openButton.title = chat.title;

    const title = document.createElement("strong");
    title.className = "chat-title";
    title.textContent = chat.title;

    const meta = document.createElement("span");
    meta.className = "chat-meta";
    meta.textContent = formatChatMeta(chat);

    const deleteButton = document.createElement("button");
    deleteButton.className = "delete-chat-button";
    deleteButton.type = "button";
    deleteButton.title = "Delete chat";
    deleteButton.setAttribute("aria-label", `Delete ${chat.title}`);
    deleteButton.textContent = "x";

    openButton.append(title, meta);
    item.append(openButton, deleteButton);
    chatList.append(item);

    openButton.addEventListener("click", () => openChat(chat.id));
    deleteButton.addEventListener("click", (event) => {
      event.stopPropagation();
      deleteChat(chat.id);
    });
  });
}

function resetChat() {
  if (DIRECT_FILE_MODE) {
    clearMessages();
    addMessage(
      {
        speaker: "Learny",
        text: `The interface is loaded, but the Wasmer-hosted API is not connected. ${SERVER_HINT}`,
        source: "servers offline",
      },
      { persist: false },
    );
    messageInput.disabled = true;
    sendButton.disabled = true;
    return;
  }

  createChat();
  messageInput.value = "";
  messageInput.disabled = false;
  sendButton.disabled = false;
}

function addTyping() {
  const node = messageTemplate.content.firstElementChild.cloneNode(true);
  node.classList.add("learny", "typing");
  node.querySelector(".speaker").textContent = "Learny";
  node.querySelector(".source").textContent = "thinking";
  const bubble = node.querySelector(".bubble");
  bubble.textContent = "";
  for (let index = 0; index < 3; index += 1) {
    const dot = document.createElement("span");
    dot.className = "typing-dot";
    bubble.append(dot);
  }
  chatLog.append(node);
  chatLog.scrollTop = chatLog.scrollHeight;
  return node;
}

async function apiFetch(path, options = {}) {
  if (DIRECT_FILE_MODE) {
    throw new Error(SERVER_HINT);
  }

  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      "X-Learny-Session": sessionId,
      ...(options.headers || {}),
    },
    ...options,
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Request failed.");
  }
  return data;
}

async function loadStatus() {
  setConnection("checking", "Checking server status...");

  if (DIRECT_FILE_MODE) {
    setConnection("offline", "Servers offline");
    return;
  }

  try {
    const status = await apiFetch("/api/status");
    setConnection(status.ok ? "online" : "offline", status.ok ? "Servers online" : "Servers offline");
  } catch (error) {
    setConnection("offline", "Servers offline");
  }
}

async function askLearny(message) {
  if (DIRECT_FILE_MODE) {
    return;
  }

  const chat = ensureActiveChat();
  sessionId = chat.sessionId;
  addMessage({ speaker: "You", text: message, source: "sent" });

  const typing = addTyping();
  const thoughtStartedAt = performance.now();
  isSending = true;
  sendButton.disabled = true;
  messageInput.disabled = true;

  try {
    const data = await apiFetch("/api/ask", {
      method: "POST",
      body: JSON.stringify({ message, sessionId }),
    });
    sessionId = data.sessionId;
    chat.sessionId = data.sessionId;
    localStorage.setItem(SESSION_KEY, sessionId);
    saveChats();
    typing.remove();
    const thoughtSeconds = (performance.now() - thoughtStartedAt) / 1000;
    addMessage({
      speaker: "Learny",
      text: data.answer,
      source: sourceLabel(data.source, data.learned, data.model),
      thoughtSeconds,
    });
    await loadStatus();
  } catch (error) {
    typing.remove();
    addMessage({
      speaker: "Learny",
      text: error.message,
      source: "error",
    });
    setConnection("offline", "Servers offline");
  } finally {
    isSending = false;
    sendButton.disabled = false;
    messageInput.disabled = false;
    messageInput.focus();
  }
}

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  if (isSending) {
    return;
  }

  const message = messageInput.value.trim();
  if (!message) {
    return;
  }
  messageInput.value = "";
  askLearny(message);
});

if (newChatButton) {
  newChatButton.addEventListener("click", resetChat);
}

if (addChatButton) {
  addChatButton.addEventListener("click", resetChat);
}

if (!getActiveChat() && chats.length > 0) {
  activeChatId = sortedChats()[0].id;
}

const activeChat = getActiveChat();
if (activeChat) {
  sessionId = activeChat.sessionId;
  localStorage.setItem(ACTIVE_CHAT_KEY, activeChat.id);
  localStorage.setItem(SESSION_KEY, activeChat.sessionId);
} else {
  localStorage.removeItem(ACTIVE_CHAT_KEY);
  localStorage.removeItem(SESSION_KEY);
}

renderChatList();

if (DIRECT_FILE_MODE) {
  addMessage(
    {
      speaker: "Learny",
      text: `The interface is loaded, but the Wasmer-hosted API is not connected. ${SERVER_HINT}`,
      source: "servers offline",
    },
    { persist: false },
  );
  messageInput.disabled = true;
  sendButton.disabled = true;
} else {
  renderActiveChat();
}

loadStatus();
if (!DIRECT_FILE_MODE) {
  window.setInterval(loadStatus, STATUS_CHECK_INTERVAL_MS);
}
