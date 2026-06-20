const chatLog = document.querySelector("#chatLog");
const chatForm = document.querySelector("#chatForm");
const messageInput = document.querySelector("#messageInput");
const sendButton = document.querySelector("#sendButton");
const messageTemplate = document.querySelector("#messageTemplate");
const connectionPill = document.querySelector("#connectionPill");
const chatList = document.querySelector("#chatList");
const addChatButton = document.querySelector("#addChatButton");
const chatSearchInput = document.querySelector("#chatSearchInput");
const rateLimitPanel = document.querySelector("#rateLimitPanel");
const rateLimitRemaining = document.querySelector("#rateLimitRemaining");
const rateLimitFill = document.querySelector("#rateLimitFill");
const rateLimitWindow = document.querySelector("#rateLimitWindow");
const rateLimitModal = document.querySelector("#rateLimitModal");
const rateLimitBackdrop = document.querySelector("#rateLimitBackdrop");
const rateLimitClose = document.querySelector("#rateLimitClose");
const rateLimitOk = document.querySelector("#rateLimitOk");
const rateLimitPopupSeconds = document.querySelector("#rateLimitPopupSeconds");
const rateLimitPopupUnit = document.querySelector("#rateLimitPopupUnit");
const rateLimitPopupFill = document.querySelector("#rateLimitPopupFill");
const rateLimitDescription = document.querySelector("#rateLimitDescription");
const emptyState = document.querySelector("#emptyState");
const starField = document.querySelector("#starField");
const appShell = document.querySelector(".app-shell");
const sidebarToggle = document.querySelector(".sidebar-toggle");
const mobileSidebarButton = document.querySelector("#mobileSidebarButton");
const sidebarScrim = document.querySelector("#sidebarScrim");
const messageSearchInput = document.querySelector("#messageSearchInput");
const messageSearchCount = document.querySelector("#messageSearchCount");
const welcomeHeading = document.querySelector("#welcomeHeading");
const accountButton = document.querySelector("#accountButton");
const accountStatusText = document.querySelector("#accountStatusText");
const accountOrbImage = document.querySelector("#accountOrbImage");
const accountModal = document.querySelector("#accountModal");
const accountModalBackdrop = document.querySelector("#accountModalBackdrop");
const accountModalClose = document.querySelector("#accountModalClose");
const accountModalTitle = document.querySelector("#accountModalTitle");
const accountModalSubtitle = document.querySelector("#accountModalSubtitle");
const accountModalViews = document.querySelectorAll("[data-account-view]");
const signInForm = document.querySelector("#signInForm");
const createAccountForm = document.querySelector("#createAccountForm");
const signInMessage = document.querySelector("#signInMessage");
const createAccountMessage = document.querySelector("#createAccountMessage");
const accountAvatarImage = document.querySelector("#accountAvatarImage");
const accountModalUsername = document.querySelector("#accountModalUsername");
const accountModalCreated = document.querySelector("#accountModalCreated");
const accountChatCount = document.querySelector("#accountChatCount");
const accountMessageCount = document.querySelector("#accountMessageCount");
const accountSessionCount = document.querySelector("#accountSessionCount");
const accountProfilePictureInput = document.querySelector("#accountProfilePictureInput");
const accountProfilePictureButton = document.querySelector("#accountProfilePictureButton");
const accountRateLimitResetButton = document.querySelector("#accountRateLimitResetButton");
const accountRateLimitResetMessage = document.querySelector("#accountRateLimitResetMessage");
const accountSignOutButton = document.querySelector("#accountSignOutButton");
const accountDeleteButton = document.querySelector("#accountDeleteButton");
const accountDeleteConfirm = document.querySelector("#accountDeleteConfirm");
const accountDeleteCancel = document.querySelector("#accountDeleteCancel");
const accountDeleteConfirmButton = document.querySelector("#accountDeleteConfirmButton");

const CHATS_KEY = "learny-chats";
const ACTIVE_CHAT_KEY = "learny-active-chat-id";
const SESSION_KEY = "learny-session-id";
const RATE_LIMIT_SESSION_KEY = "learny-rate-limit-session-id";
const COPY_ICON_PATH = "./icon_library/copy.png";
const CHECK_ICON_PATH = "./icon_library/check.png";
const X_ICON_PATH = "./icon_library/X.png";
const PROFILE_ICON_PATH = "./icon_library/profile.png";
const PROFILE_PICTURE_MAX_BYTES = 512 * 1024;
const PROFILE_PICTURE_TYPES = new Set(["image/png", "image/jpeg", "image/webp", "image/gif"]);
const COPY_RESET_DELAY_MS = 1400;
const WORD_REVEAL_STEP_MS = 52;
const WORD_REVEAL_DURATION_MS = 300;
const WORD_REVEAL_FOOTER_DELAY_MS = 850;
const WELCOME_TEXTS = ["Hey! I'm Learny!", "What's on your mind?"];
const WELCOME_LOCK_DELAY_MS = 2200;
const WELCOME_SWAP_FADE_MS = 1000;
const MOBILE_SIDEBAR_QUERY = "(max-width: 860px)";
const DIRECT_FILE_MODE = window.location.protocol === "file:";
const STATUS_CHECK_INTERVAL_MS = 15000;
const STATUS_FETCH_TIMEOUT_MS = 8000;
const ASK_RETRY_BASE_DELAY_MS = 1200;
const ASK_RETRY_MAX_DELAY_MS = 3500;
const ASK_REQUEST_TIMEOUT_MS = 10000;
const DEFAULT_RATE_LIMIT = {
  limit: 30,
  remaining: 30,
  windowMs: 86400000,
  resetAt: 0,
  limited: false,
};
const GENERIC_ERROR_MESSAGE = "Something went wrong. Try again later.";
const UNKNOWN_ANSWER_MESSAGE = "I do not know that yet.";
const WASMER_API_BASE = "https://learny-ai-adamsrealm1.wasmer.app";
const WASMER_API_FALLBACK_BASE = "https://learny-ai.wasmer.app";
const API_BASE_CANDIDATES = buildApiBaseCandidates();
const DESKTOP_STAR_COUNT = 360;
const MOBILE_STAR_COUNT = 230;
const PROMPT_META_MARKERS = [
  "current user question",
  "previous conversation",
  "recent conversation",
  "chat context",
  "system prompt",
  "hidden instructions",
];

let chats = loadStoredChats();
let activeChatId = localStorage.getItem(ACTIVE_CHAT_KEY) || "";
let sessionId = "";
let rateLimitSessionId = localStorage.getItem(RATE_LIMIT_SESSION_KEY) || "";
let isSending = false;
let chatSearchQuery = "";
let messageSearchQuery = "";
let messageSearchIndex = 0;
let activeApiBase = "";
let welcomeTextIndex = 0;
let welcomeTimeoutId = null;
let welcomeSequenceStarted = false;
let currentAccount = null;
let currentAccountStats = null;
let currentRateLimit = { ...DEFAULT_RATE_LIMIT };
let rateLimitRefreshTimerId = null;
let rateLimitPopupTimerId = null;
let serverChatsLoaded = false;
let serverSyncTimerId = null;
let activeAccountView = "";
const mobileSidebarMedia = window.matchMedia
  ? window.matchMedia(MOBILE_SIDEBAR_QUERY)
  : null;

function buildApiBaseCandidates() {
  if (DIRECT_FILE_MODE) {
    return [WASMER_API_BASE];
  }

  const host = window.location.hostname.toLowerCase();
  const wasmerHost = new URL(WASMER_API_BASE).hostname;
  const wasmerFallbackHost = new URL(WASMER_API_FALLBACK_BASE).hostname;
  if (host === "learny.env.pm" || host.endsWith(".github.io")) {
    return [WASMER_API_BASE, WASMER_API_FALLBACK_BASE];
  }
  if (host === wasmerHost || host === wasmerFallbackHost) {
    const fallback = host === wasmerHost ? WASMER_API_FALLBACK_BASE : WASMER_API_BASE;
    return ["", fallback];
  }
  if (host === "localhost" || host === "127.0.0.1" || host === "") {
    return ["", WASMER_API_BASE, WASMER_API_FALLBACK_BASE];
  }
  return ["", WASMER_API_BASE, WASMER_API_FALLBACK_BASE];
}

function createId(prefix) {
  const randomPart = Math.random().toString(36).slice(2, 10);
  return `${prefix}-${Date.now().toString(36)}-${randomPart}`;
}

function createStarField() {
  if (!starField) {
    return;
  }

  const starCount = window.innerWidth < 700 ? MOBILE_STAR_COUNT : DESKTOP_STAR_COUNT;
  const fragment = document.createDocumentFragment();
  starField.replaceChildren();

  for (let index = 0; index < starCount; index += 1) {
    const star = document.createElement("span");
    const angle = Math.random() * Math.PI * 2;
    const travel = 8 + Math.random() * 22;
    const duration = 260 + Math.random() * 460;
    const smallStar = Math.random() < 0.88;
    const size = smallStar ? 0.7 + Math.random() * 0.75 : 1.45 + Math.random() * 0.85;
    const opacity = 0.24 + Math.random() * 0.56;
    const glow = smallStar ? 2 + Math.random() * 4 : 4 + Math.random() * 7;

    star.className = "star";
    star.style.setProperty("--x", `${Math.random() * 100}vw`);
    star.style.setProperty("--y", `${Math.random() * 100}vh`);
    star.style.setProperty("--travel-x", `${Math.cos(angle) * travel}vw`);
    star.style.setProperty("--travel-y", `${Math.sin(angle) * travel}vh`);
    star.style.setProperty("--size", `${size.toFixed(2)}px`);
    star.style.setProperty("--opacity", opacity.toFixed(2));
    star.style.setProperty("--glow", `${glow.toFixed(2)}px`);
    star.style.setProperty("--glow-opacity", (opacity * 0.42).toFixed(2));
    star.style.setProperty("--duration", `${duration.toFixed(1)}s`);
    star.style.setProperty("--delay", `${(-Math.random() * duration).toFixed(1)}s`);
    fragment.append(star);
  }

  starField.append(fragment);
}

function escapePlainText(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;")
    .replace(/\n/g, "<br>");
}

function renderMessageHtml(text) {
  return window.LearnyMarkdown && typeof window.LearnyMarkdown.renderMarkdown === "function"
    ? window.LearnyMarkdown.renderMarkdown(text)
    : escapePlainText(text);
}

function animateWords(container) {
  if (!container || !("NodeFilter" in window)) {
    return 0;
  }

  const textNodes = [];
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      if (!node.nodeValue || !node.nodeValue.trim()) {
        return NodeFilter.FILTER_REJECT;
      }
      if (node.parentElement && node.parentElement.closest("pre, code, script, style")) {
        return NodeFilter.FILTER_REJECT;
      }
      return NodeFilter.FILTER_ACCEPT;
    },
  });

  while (walker.nextNode()) {
    textNodes.push(walker.currentNode);
  }

  let wordIndex = 0;
  textNodes.forEach((node) => {
    const fragment = document.createDocumentFragment();
    let pendingWhitespace = "";
    node.nodeValue.split(/(\s+)/).forEach((part) => {
      if (!part) {
        return;
      }
      if (/^\s+$/.test(part)) {
        pendingWhitespace += part;
        return;
      }

      const word = document.createElement("span");
      word.className = "word-fade";
      word.style.animationDuration = `${WORD_REVEAL_DURATION_MS}ms`;
      word.textContent = `${pendingWhitespace}${part}`;
      fragment.append(word);
      window.setTimeout(() => {
        word.classList.add("word-visible");
      }, wordIndex * WORD_REVEAL_STEP_MS);
      pendingWhitespace = "";
      wordIndex += 1;
    });
    if (pendingWhitespace) {
      fragment.append(document.createTextNode(pendingWhitespace));
    }
    node.replaceWith(fragment);
  });

  return wordIndex;
}

function wordRevealDuration(wordCount) {
  if (!Number.isFinite(wordCount) || wordCount <= 0) {
    return 0;
  }
  return (wordCount - 1) * WORD_REVEAL_STEP_MS + WORD_REVEAL_DURATION_MS;
}

function scrollChatToBottom({ smooth = true } = {}) {
  if (!chatLog) {
    return;
  }

  const top = chatLog.scrollHeight;
  if (typeof chatLog.scrollTo === "function") {
    chatLog.scrollTo({ top, behavior: smooth ? "smooth" : "auto" });
    return;
  }

  chatLog.scrollTop = top;
}

function keepChatPinnedToBottom(milliseconds) {
  if (!chatLog || !Number.isFinite(milliseconds) || milliseconds <= 0) {
    scrollChatToBottom({ smooth: true });
    return;
  }

  const deadline = performance.now() + milliseconds;

  function tick() {
    chatLog.scrollTop = chatLog.scrollHeight;
    if (performance.now() < deadline) {
      window.requestAnimationFrame(tick);
      return;
    }
    scrollChatToBottom({ smooth: true });
  }

  window.requestAnimationFrame(tick);
}

async function copyTextToClipboard(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  textarea.style.top = "0";
  document.body.append(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

function setCopyButtonState(button, copied) {
  const icon = button.querySelector("img");
  if (!icon) {
    return;
  }
  icon.src = copied ? CHECK_ICON_PATH : COPY_ICON_PATH;
  button.classList.toggle("copied", copied);
  button.title = copied ? "Copied" : "Copy message";
  button.setAttribute("aria-label", copied ? "Copied" : "Copy message");
}

async function handleCopyMessage(button, text) {
  button.disabled = true;
  try {
    await copyTextToClipboard(text);
    setCopyButtonState(button, true);
    window.setTimeout(() => {
      setCopyButtonState(button, false);
      button.disabled = false;
    }, COPY_RESET_DELAY_MS);
  } catch (error) {
    setCopyButtonState(button, false);
    button.disabled = false;
  }
}

function clearMessageSearch() {
  messageSearchQuery = "";
  messageSearchIndex = 0;
  if (messageSearchInput) {
    messageSearchInput.value = "";
  }
  updateMessageSearch();
}

function messageMatchesCurrentSearch(node, query) {
  const text = node.dataset.searchText || "";
  return text.includes(query);
}

function updateMessageSearch({ scrollToCurrent = false } = {}) {
  if (!chatLog || !messageSearchCount) {
    return;
  }

  const query = messageSearchQuery.trim().toLowerCase();
  const messages = [...chatLog.querySelectorAll(".message:not(.typing)")];
  const matches = [];

  messages.forEach((node) => {
    node.classList.remove("message-search-match", "message-search-dim", "message-search-current");
    if (!query) {
      return;
    }

    if (messageMatchesCurrentSearch(node, query)) {
      node.classList.add("message-search-match");
      matches.push(node);
    } else {
      node.classList.add("message-search-dim");
    }
  });

  if (!query) {
    messageSearchCount.textContent = "";
    return;
  }

  if (matches.length === 0) {
    messageSearchCount.textContent = "0";
    messageSearchIndex = 0;
    return;
  }

  messageSearchIndex = Math.min(Math.max(messageSearchIndex, 0), matches.length - 1);
  const current = matches[messageSearchIndex];
  current.classList.add("message-search-current");
  messageSearchCount.textContent = `${messageSearchIndex + 1}/${matches.length}`;

  if (scrollToCurrent) {
    current.scrollIntoView({ block: "center", behavior: "smooth" });
  }
}

function cycleMessageSearch(direction) {
  const query = messageSearchQuery.trim().toLowerCase();
  if (!query) {
    return;
  }

  const matches = [...chatLog.querySelectorAll(".message:not(.typing)")].filter((node) =>
    messageMatchesCurrentSearch(node, query),
  );
  if (matches.length === 0) {
    updateMessageSearch();
    return;
  }

  messageSearchIndex = (messageSearchIndex + direction + matches.length) % matches.length;
  updateMessageSearch({ scrollToCurrent: true });
}

function renderWelcomeHeadingText(text) {
  if (!welcomeHeading) {
    return;
  }

  const fragment = document.createDocumentFragment();
  text.split(/(\s+)/).forEach((part, index) => {
    if (!part) {
      return;
    }
    if (/^\s+$/.test(part)) {
      fragment.append(document.createTextNode(part));
      return;
    }
    const word = document.createElement("span");
    word.className = "welcome-word";
    word.style.animationDelay = `${index * 38}ms`;
    word.textContent = part;
    fragment.append(word);
  });
  welcomeHeading.replaceChildren(fragment);
}

function startWelcomeHeadingCycle() {
  if (!welcomeHeading || welcomeSequenceStarted) {
    return;
  }

  welcomeSequenceStarted = true;
  welcomeTextIndex = 0;
  renderWelcomeHeadingText(WELCOME_TEXTS[0]);
  if (WELCOME_TEXTS.length < 2) {
    return;
  }

  welcomeTimeoutId = window.setTimeout(() => {
    welcomeHeading.classList.add("is-changing");
    window.setTimeout(() => {
      welcomeTextIndex = 1;
      renderWelcomeHeadingText(WELCOME_TEXTS[welcomeTextIndex]);
      welcomeHeading.classList.remove("is-changing");
      welcomeTimeoutId = null;
    }, WELCOME_SWAP_FADE_MS);
  }, WELCOME_LOCK_DELAY_MS);
}

function isMobileSidebarLayout() {
  return Boolean(mobileSidebarMedia && mobileSidebarMedia.matches);
}

function setSidebarOpen(open) {
  if (!appShell) {
    return;
  }

  const shouldOpen = Boolean(open && isMobileSidebarLayout());
  appShell.classList.toggle("sidebar-open", shouldOpen);
  document.body.classList.toggle("sidebar-lock", shouldOpen);
  if (mobileSidebarButton) {
    mobileSidebarButton.setAttribute("aria-expanded", String(shouldOpen));
    mobileSidebarButton.title = shouldOpen ? "Close sidebar" : "Open sidebar";
  }
}

function setDesktopSidebarCollapsed(collapsed) {
  if (!appShell) {
    return;
  }

  const shouldCollapse = Boolean(collapsed && !isMobileSidebarLayout());
  appShell.classList.toggle("sidebar-collapsed", shouldCollapse);
  document.body.classList.toggle("sidebar-lock", false);
  if (sidebarToggle) {
    sidebarToggle.setAttribute("aria-expanded", String(!shouldCollapse));
    sidebarToggle.title = shouldCollapse ? "Expand sidebar" : "Collapse sidebar";
    const label = sidebarToggle.querySelector(".sr-only");
    if (label) {
      label.textContent = shouldCollapse ? "Expand sidebar" : "Collapse sidebar";
    }
  }
}

function toggleSidebarControl() {
  if (isMobileSidebarLayout()) {
    setSidebarOpen(false);
    return;
  }

  setDesktopSidebarCollapsed(!appShell.classList.contains("sidebar-collapsed"));
}

function closeSidebarOnMobile() {
  if (isMobileSidebarLayout()) {
    setSidebarOpen(false);
  }
}

function syncSidebarForViewport() {
  if (isMobileSidebarLayout()) {
    setDesktopSidebarCollapsed(false);
  } else {
    setSidebarOpen(false);
  }
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
        createdAt: Number.isFinite(chat.createdAt) ? chat.createdAt : Date.now(),
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
                text: sanitizeStoredMessageText(message),
                source: sanitizeStoredMessageSource(message),
                thoughtSeconds: normalizeThoughtSeconds(message.thoughtSeconds),
                createdAt: Number.isFinite(message.createdAt) ? message.createdAt : Date.now(),
              }))
          : [],
      }));
  } catch (error) {
    return [];
  }
}

function saveChats() {
  localStorage.setItem(CHATS_KEY, JSON.stringify(chats));
  if (currentAccount && serverChatsLoaded) {
    queueServerChatSync();
  }
}

function normalizeRateLimit(rateLimit) {
  if (!rateLimit || typeof rateLimit !== "object") {
    return { ...DEFAULT_RATE_LIMIT };
  }

  const limit = Number.isFinite(rateLimit.limit) && rateLimit.limit > 0
    ? Math.floor(rateLimit.limit)
    : DEFAULT_RATE_LIMIT.limit;
  const remaining = Number.isFinite(rateLimit.remaining)
    ? Math.max(0, Math.min(limit, Math.floor(rateLimit.remaining)))
    : limit;
  const windowMs = Number.isFinite(rateLimit.windowMs) && rateLimit.windowMs > 0
    ? Math.floor(rateLimit.windowMs)
    : DEFAULT_RATE_LIMIT.windowMs;
  const resetAt = Number.isFinite(rateLimit.resetAt) && rateLimit.resetAt > 0
    ? Math.floor(rateLimit.resetAt)
    : Date.now() + windowMs;

  return {
    limit,
    remaining,
    windowMs,
    resetAt,
    limited: Boolean(rateLimit.limited) && Date.now() < resetAt,
  };
}

function isRateLimited() {
  return Boolean(
    currentRateLimit &&
      currentRateLimit.limited &&
      currentRateLimit.remaining <= 0 &&
      Date.now() < currentRateLimit.resetAt,
  );
}

function rateLimitWindowSeconds(rateLimit = currentRateLimit || DEFAULT_RATE_LIMIT) {
  return Math.max(1, Math.ceil(rateLimit.windowMs / 1000));
}

function rateLimitSecondsLeft(rateLimit = currentRateLimit || DEFAULT_RATE_LIMIT) {
  const secondsLeft = Math.max(0, Math.ceil((rateLimit.resetAt - Date.now()) / 1000));
  return Math.min(secondsLeft, rateLimitWindowSeconds(rateLimit));
}

function pluralize(value, singular, plural = `${singular}s`) {
  return value === 1 ? singular : plural;
}

function rateLimitPercent(rateLimit = currentRateLimit || DEFAULT_RATE_LIMIT) {
  if (!rateLimit || rateLimit.limit <= 0 || rateLimit.remaining <= 0) {
    return 0;
  }
  return Math.max(1, Math.min(100, Math.round((rateLimit.remaining / rateLimit.limit) * 100)));
}

function rateLimitResetParts(rateLimit = currentRateLimit || DEFAULT_RATE_LIMIT) {
  const secondsLeft = rateLimitSecondsLeft(rateLimit);
  const hoursLeft = Math.floor(secondsLeft / 3600);
  if (hoursLeft > 0) {
    const displayHours = Math.ceil(secondsLeft / 3600);
    return {
      value: displayHours,
      unit: pluralize(displayHours, "hour"),
      label: `${displayHours} ${pluralize(displayHours, "hour")} until reset`,
    };
  }

  const minutesLeft = Math.max(1, Math.ceil(secondsLeft / 60));
  return {
    value: minutesLeft,
    unit: pluralize(minutesLeft, "minute"),
    label: `${minutesLeft} ${pluralize(minutesLeft, "minute")} until reset`,
  };
}

function rateLimitRemainingLabel(rateLimit = currentRateLimit || DEFAULT_RATE_LIMIT) {
  return `${rateLimit.remaining} ${pluralize(rateLimit.remaining, "message")} left`;
}

function syncComposerAvailability() {
  if (DIRECT_FILE_MODE) {
    sendButton.disabled = true;
    messageInput.disabled = true;
    return;
  }

  if (!isSending) {
    sendButton.disabled = false;
    messageInput.disabled = false;
  }
}

function renderRateLimit() {
  const rateLimit = currentRateLimit || DEFAULT_RATE_LIMIT;
  const limited = isRateLimited();
  const fillRatio = rateLimit.limit > 0 ? rateLimit.remaining / rateLimit.limit : 1;
  const percent = rateLimitPercent(rateLimit);
  const resetParts = rateLimitResetParts(rateLimit);
  const remainingLabel = rateLimitRemainingLabel(rateLimit);

  if (rateLimitPanel) {
    rateLimitPanel.classList.toggle("limited", limited);
    rateLimitPanel.setAttribute("title", remainingLabel);
    rateLimitPanel.setAttribute(
      "aria-label",
      `Message rate limit: ${percent} percent, ${remainingLabel}, ${resetParts.label}`,
    );
  }
  if (rateLimitRemaining) {
    rateLimitRemaining.textContent = `${percent}%`;
  }
  if (rateLimitFill) {
    rateLimitFill.style.setProperty("--rate-fill", String(Math.max(0, Math.min(1, fillRatio))));
  }
  if (rateLimitWindow) {
    rateLimitWindow.textContent = resetParts.label;
  }

  if (rateLimitRefreshTimerId !== null) {
    window.clearTimeout(rateLimitRefreshTimerId);
    rateLimitRefreshTimerId = null;
  }
  if (Date.now() < rateLimit.resetAt) {
    const nextTickMs = limited || rateLimitSecondsLeft(rateLimit) < 3600 ? 1000 : 60000;
    rateLimitRefreshTimerId = window.setTimeout(() => {
      rateLimitRefreshTimerId = null;
      if (Date.now() >= rateLimit.resetAt) {
        loadRateLimit();
        return;
      }
      renderRateLimit();
    }, nextTickMs);
  }

  syncComposerAvailability();
}

function renderRateLimitPopup() {
  if (!rateLimitModal || rateLimitModal.hidden) {
    return;
  }

  const windowSeconds = rateLimitWindowSeconds();
  const secondsLeft = rateLimitSecondsLeft();
  const elapsed = Math.max(0, windowSeconds - secondsLeft);
  const progress = windowSeconds > 0 ? elapsed / windowSeconds : 1;
  const resetParts = rateLimitResetParts();
  if (rateLimitDescription) {
    rateLimitDescription.textContent = currentAccount
      ? "You've hit your rate limit for Learny AI.\nYour rate limit will reset when the timer below finishes."
      : "You've hit your rate limit for Learny AI. Create a free account to get 200 messages a day.\nYour rate limit will reset when the timer below finishes.";
  }
  if (rateLimitPopupSeconds) {
    rateLimitPopupSeconds.textContent = String(resetParts.value);
  }
  if (rateLimitPopupUnit) {
    rateLimitPopupUnit.textContent = `${resetParts.unit} left`;
  }
  if (rateLimitPopupFill) {
    rateLimitPopupFill.style.setProperty("--rate-popup-fill", String(Math.max(0, Math.min(1, progress))));
  }

  if (rateLimitPopupTimerId !== null) {
    window.clearTimeout(rateLimitPopupTimerId);
    rateLimitPopupTimerId = null;
  }
  if (isRateLimited()) {
    rateLimitPopupTimerId = window.setTimeout(() => {
      rateLimitPopupTimerId = null;
      if (Date.now() >= currentRateLimit.resetAt) {
        closeRateLimitPopup();
        loadRateLimit();
        return;
      }
      renderRateLimitPopup();
    }, 1000);
  }
}

function openRateLimitPopup({ force = false } = {}) {
  if (!rateLimitModal || (!force && !isRateLimited())) {
    return;
  }

  rateLimitModal.hidden = false;
  document.body.classList.add("rate-limit-open");
  renderRateLimitPopup();
  window.setTimeout(() => {
    if (rateLimitOk) {
      rateLimitOk.focus();
    }
  }, 70);
}

function closeRateLimitPopup() {
  if (!rateLimitModal || rateLimitModal.hidden) {
    return;
  }

  rateLimitModal.hidden = true;
  document.body.classList.remove("rate-limit-open");
  if (rateLimitPopupTimerId !== null) {
    window.clearTimeout(rateLimitPopupTimerId);
    rateLimitPopupTimerId = null;
  }
  if (!isRateLimited()) {
    syncComposerAvailability();
  }
}

function updateRateLimit(rateLimit) {
  currentRateLimit = normalizeRateLimit(rateLimit);
  renderRateLimit();
  renderRateLimitPopup();
}

function accountProfilePicture() {
  if (!currentAccount || typeof currentAccount.profilePicture !== "string") {
    return "";
  }
  return currentAccount.profilePicture.trim();
}

function renderAccountProfilePicture() {
  const customPicture = accountProfilePicture();
  const imageSource = customPicture || PROFILE_ICON_PATH;
  [accountOrbImage, accountAvatarImage].forEach((image) => {
    if (image) {
      image.src = imageSource;
    }
  });

  if (accountProfilePictureButton) {
    accountProfilePictureButton.textContent = customPicture
      ? "Remove profile picture"
      : "Add profile picture";
  }
}

function updateAccountButton() {
  renderAccountProfilePicture();

  if (!accountButton || !accountStatusText) {
    return;
  }

  if (currentAccount) {
    accountButton.classList.add("signed-in");
    accountStatusText.textContent = `@${currentAccount.username}`;
    return;
  }

  accountButton.classList.remove("signed-in");
  accountStatusText.textContent = "Sign in to sync";
}

function formatAccountDate(timestamp) {
  const date = new Date(Number(timestamp));
  if (Number.isNaN(date.getTime())) {
    return "Account ready";
  }
  return `Created ${date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  })}`;
}

function setAccountFormMessage(node, text = "", isError = false) {
  if (!node) {
    return;
  }
  node.textContent = text;
  node.classList.toggle("error", isError);
}

function setAuthFormBusy(form, busy) {
  if (!form) {
    return;
  }

  form.querySelectorAll("input, button").forEach((field) => {
    field.disabled = busy;
  });

  const button = form.querySelector("button[type='submit']");
  if (!button) {
    return;
  }
  if (!button.dataset.originalText) {
    button.dataset.originalText = button.textContent;
  }
  button.textContent = busy ? "Working..." : button.dataset.originalText;
}

function resetDeleteConfirmation() {
  if (accountDeleteConfirm) {
    accountDeleteConfirm.hidden = true;
  }
}

function renderAccountModalDetails() {
  renderAccountProfilePicture();

  if (!currentAccount) {
    if (accountRateLimitResetButton) {
      accountRateLimitResetButton.hidden = true;
    }
    setAccountFormMessage(accountRateLimitResetMessage);
    return;
  }

  if (accountModalUsername) {
    accountModalUsername.textContent = currentAccount.username;
  }
  if (accountModalCreated) {
    accountModalCreated.textContent = formatAccountDate(currentAccount.createdAt);
  }
  if (accountChatCount) {
    accountChatCount.textContent = String((currentAccountStats && currentAccountStats.chats) || 0);
  }
  if (accountMessageCount) {
    accountMessageCount.textContent = String((currentAccountStats && currentAccountStats.messages) || 0);
  }
  if (accountSessionCount) {
    accountSessionCount.textContent = String((currentAccountStats && currentAccountStats.sessions) || 0);
  }
  if (accountRateLimitResetButton) {
    accountRateLimitResetButton.hidden = !currentAccount.canResetRateLimits;
  }
  if (!currentAccount.canResetRateLimits) {
    setAccountFormMessage(accountRateLimitResetMessage);
  }
}

function setAccountModalCopy(view) {
  if (!accountModalTitle || !accountModalSubtitle) {
    return;
  }

  if (view === "create-account") {
    accountModalTitle.textContent = "Create account";
    accountModalSubtitle.textContent = "Start syncing Learny chats with the account database.";
    return;
  }
  if (view === "myaccount" && currentAccount) {
    accountModalTitle.textContent = "My account";
    accountModalSubtitle.textContent = "Settings, sessions, and synced chat memory.";
    return;
  }

  accountModalTitle.textContent = "Sign in";
  accountModalSubtitle.textContent = "Connect Learny to your saved chats and settings.";
}

function showAccountView(view) {
  let nextView = view;
  if (nextView === "myaccount" && !currentAccount) {
    nextView = "sign-in";
  }
  if (!["sign-in", "create-account", "myaccount"].includes(nextView)) {
    nextView = currentAccount ? "myaccount" : "sign-in";
  }

  activeAccountView = nextView;
  resetDeleteConfirmation();
  setAccountFormMessage(signInMessage);
  setAccountFormMessage(createAccountMessage);

  accountModalViews.forEach((node) => {
    node.hidden = node.dataset.accountView !== nextView;
  });
  setAccountModalCopy(nextView);
  if (nextView === "myaccount") {
    renderAccountModalDetails();
  }
}

async function refreshAccountModalDetails() {
  if (!currentAccount || DIRECT_FILE_MODE) {
    renderAccountModalDetails();
    return;
  }

  try {
    const data = await apiFetch(
      "/api/account",
      { timeoutMs: STATUS_FETCH_TIMEOUT_MS },
      activeApiBase ? [activeApiBase, ...API_BASE_CANDIDATES] : API_BASE_CANDIDATES,
    );
    if (data.authenticated && data.account) {
      currentAccount = data.account;
      currentAccountStats = data.stats || null;
      updateAccountButton();
    }
  } catch (error) {
    setConnection("offline", "Servers offline");
  }
  renderAccountModalDetails();
}

function openAccountModal(view = currentAccount ? "myaccount" : "sign-in") {
  if (!accountModal) {
    return;
  }

  closeSidebarOnMobile();
  accountModal.hidden = false;
  document.body.classList.add("account-modal-open");
  showAccountView(view);
  window.setTimeout(() => {
    const firstInput = accountModal.querySelector("[data-account-view]:not([hidden]) input:not([hidden])");
    const closeButton = accountModalClose;
    if (firstInput instanceof HTMLElement) {
      firstInput.focus();
    } else if (closeButton) {
      closeButton.focus();
    }
  }, 80);
  if (activeAccountView === "myaccount") {
    refreshAccountModalDetails();
  }
}

function closeAccountModal() {
  if (!accountModal || accountModal.hidden) {
    return;
  }

  accountModal.hidden = true;
  document.body.classList.remove("account-modal-open");
  activeAccountView = "";
  resetDeleteConfirmation();
  if (messageInput && !DIRECT_FILE_MODE) {
    messageInput.focus();
  }
}

function clearSignedInLocalState() {
  currentAccount = null;
  currentAccountStats = null;
  serverChatsLoaded = false;
  chats = [];
  activeChatId = "";
  sessionId = "";
  localStorage.removeItem(ACTIVE_CHAT_KEY);
  localStorage.removeItem(SESSION_KEY);
  localStorage.setItem(CHATS_KEY, JSON.stringify(chats));
  updateAccountButton();
  renderChatList();
  renderActiveChat();
}

function normalizeServerChats(serverChats) {
  if (!Array.isArray(serverChats)) {
    return [];
  }

  return serverChats
    .filter((chat) => chat && typeof chat === "object" && typeof chat.id === "string")
    .map((chat) => ({
      id: chat.id,
      title: typeof chat.title === "string" && chat.title.trim() ? chat.title.trim() : "New chat",
      sessionId:
        typeof chat.sessionId === "string" && chat.sessionId.trim()
          ? chat.sessionId.trim()
          : createId("session"),
      createdAt: Number.isFinite(chat.createdAt) ? chat.createdAt : Date.now(),
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
              text: sanitizeStoredMessageText(message),
              source: sanitizeStoredMessageSource(message),
              thoughtSeconds: normalizeThoughtSeconds(message.thoughtSeconds),
              createdAt: Number.isFinite(message.createdAt) ? message.createdAt : Date.now(),
            }))
        : [],
    }));
}

function queueServerChatSync() {
  if (!currentAccount || !serverChatsLoaded || DIRECT_FILE_MODE) {
    return;
  }

  if (serverSyncTimerId !== null) {
    window.clearTimeout(serverSyncTimerId);
  }
  serverSyncTimerId = window.setTimeout(() => {
    serverSyncTimerId = null;
    syncChatsToServer();
  }, 260);
}

async function syncChatsToServer() {
  if (!currentAccount || DIRECT_FILE_MODE) {
    return;
  }

  try {
    await apiFetch(
      "/api/chats/sync",
      {
        method: "POST",
        body: JSON.stringify({ chats }),
        timeoutMs: STATUS_FETCH_TIMEOUT_MS,
      },
      activeApiBase ? [activeApiBase, ...API_BASE_CANDIDATES] : API_BASE_CANDIDATES,
    );
  } catch (error) {
    setConnection("offline", "Servers offline");
  }
}

async function loadAccountAndChats() {
  updateAccountButton();
  if (DIRECT_FILE_MODE) {
    return null;
  }

  try {
    const accountData = await apiFetch(
      "/api/account",
      { timeoutMs: STATUS_FETCH_TIMEOUT_MS },
      activeApiBase ? [activeApiBase, ...API_BASE_CANDIDATES] : API_BASE_CANDIDATES,
    );
    if (!accountData.authenticated || !accountData.account) {
      currentAccount = null;
      currentAccountStats = null;
      serverChatsLoaded = false;
      updateAccountButton();
      return accountData;
    }

    currentAccount = accountData.account;
    currentAccountStats = accountData.stats || null;
    updateAccountButton();

    const chatData = await apiFetch(
      "/api/chats",
      { timeoutMs: STATUS_FETCH_TIMEOUT_MS },
      activeApiBase ? [activeApiBase, ...API_BASE_CANDIDATES] : API_BASE_CANDIDATES,
    );
    const remoteChats = normalizeServerChats(chatData.chats);
    serverChatsLoaded = true;

    if (remoteChats.length > 0) {
      chats = remoteChats;
      if (!getActiveChat()) {
        activeChatId = sortedChats()[0].id;
      }
      const activeChat = getActiveChat();
      sessionId = activeChat ? activeChat.sessionId : "";
      localStorage.setItem(CHATS_KEY, JSON.stringify(chats));
      if (activeChat) {
        localStorage.setItem(ACTIVE_CHAT_KEY, activeChat.id);
        localStorage.setItem(SESSION_KEY, activeChat.sessionId);
      }
      renderChatList();
      renderActiveChat();
      return accountData;
    }

    if (chats.length > 0) {
      queueServerChatSync();
    }
    return accountData;
  } catch (error) {
    currentAccount = null;
    currentAccountStats = null;
    serverChatsLoaded = false;
    updateAccountButton();
    return null;
  }
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

function chatMatchesSearch(chat, query) {
  if (!query) {
    return true;
  }

  const searchableText = [
    chat.title,
    ...chat.messages.map((message) => message.text),
  ]
    .join(" ")
    .toLowerCase();

  return searchableText.includes(query);
}

function visibleChats() {
  const query = chatSearchQuery.trim().toLowerCase();
  return sortedChats().filter((chat) => chatMatchesSearch(chat, query));
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

function isStoredErrorMessage(message) {
  return message.source === "error";
}

function isPromptMetaText(text) {
  const normalized = text.toLowerCase();
  return PROMPT_META_MARKERS.some((marker) => normalized.includes(marker));
}

function sanitizeStoredMessageText(message) {
  if (message.speaker === "Learny" && isPromptMetaText(message.text)) {
    return GENERIC_ERROR_MESSAGE;
  }
  return isStoredErrorMessage(message) ? GENERIC_ERROR_MESSAGE : message.text;
}

function sanitizeStoredMessageSource(message) {
  if (isStoredErrorMessage(message)) {
    return "";
  }
  if (message.speaker === "Learny") {
    return "";
  }
  return typeof message.source === "string" ? message.source : "";
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

function sourceLabel() {
  return "";
}

function clearChatSearch() {
  chatSearchQuery = "";
  if (chatSearchInput) {
    chatSearchInput.value = "";
  }
}

function createChat() {
  clearChatSearch();
  clearMessageSearch();
  const chat = {
    id: createId("chat"),
    title: "New chat",
    sessionId: createId("session"),
    createdAt: Date.now(),
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
  closeSidebarOnMobile();
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
  clearMessageSearch();
  renderChatList();
  renderActiveChat();
  closeSidebarOnMobile();
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
  if (deletingActiveChat) {
    clearMessageSearch();
  }
}

function clearMessages() {
  chatLog.querySelectorAll(".message").forEach((message) => message.remove());
}

function displayMessage(
  { speaker, text, source = "", thoughtSeconds = null },
  { animateWords: shouldAnimateWords = false } = {},
) {
  setEmptyState(false);
  const node = messageTemplate.content.firstElementChild.cloneNode(true);
  node.classList.add(speaker === "You" ? "user" : "learny");
  node.dataset.searchText = `${speaker} ${source} ${text}`.toLowerCase();
  node.querySelector(".speaker").textContent = speaker;
  node.querySelector(".source").textContent = source === "error" ? "" : source;
  const bubble = node.querySelector(".bubble");
  const textNode = document.createElement("div");
  textNode.className = "bubble-text markdown-body";
  textNode.innerHTML = renderMessageHtml(text);
  let revealDuration = 0;
  let pinnedScrollDuration = 0;
  if (shouldAnimateWords && speaker === "Learny") {
    const wordCount = animateWords(textNode);
    revealDuration = wordRevealDuration(wordCount);
    pinnedScrollDuration = revealDuration + WORD_REVEAL_FOOTER_DELAY_MS + 520;
    node.classList.add("word-revealing");
    window.setTimeout(() => {
      node.classList.add("reveal-complete");
    }, revealDuration + WORD_REVEAL_FOOTER_DELAY_MS);
  }
  bubble.replaceChildren(textNode);

  if (speaker === "Learny") {
    const footer = document.createElement("div");
    footer.className = "message-footer";

    const thought = document.createElement("span");
    thought.className = "thought-time";
    thought.textContent = `Thought for ${formatThoughtSeconds(thoughtSeconds)} seconds`;

    const copyButton = document.createElement("button");
    copyButton.className = "message-copy-button";
    copyButton.type = "button";
    copyButton.title = "Copy message";
    copyButton.setAttribute("aria-label", "Copy message");

    const copyIcon = document.createElement("img");
    copyIcon.className = "ui-icon message-copy-icon";
    copyIcon.src = COPY_ICON_PATH;
    copyIcon.alt = "";
    copyIcon.setAttribute("aria-hidden", "true");

    copyButton.append(copyIcon);
    copyButton.addEventListener("click", () => handleCopyMessage(copyButton, text));
    footer.append(thought, copyButton);
    bubble.append(footer);
  }

  chatLog.append(node);
  updateMessageSearch();
  scrollChatToBottom({ smooth: true });
  if (pinnedScrollDuration > 0) {
    keepChatPinnedToBottom(pinnedScrollDuration);
  }
  return node;
}

function saveMessage(message) {
  const chat = ensureActiveChat();
  chat.messages.push({
    ...message,
    createdAt: Number.isFinite(message.createdAt) ? message.createdAt : Date.now(),
  });
  chat.updatedAt = Date.now();

  if (message.speaker === "You" && chat.title === "New chat") {
    chat.title = titleFromMessage(message.text);
  }

  saveChats();
  renderChatList();
}

function addMessage(message, { persist = true, animateWords = false } = {}) {
  const node = displayMessage(message, { animateWords });
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
    updateMessageSearch();
    return;
  }
  chat.messages.forEach((message) => displayMessage(message));
  updateMessageSearch();
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

  const matchingChats = visibleChats();
  if (matchingChats.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty-chat-list";
    empty.textContent = "No matching chats";
    chatList.append(empty);
    return;
  }

  matchingChats.forEach((chat) => {
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

    const deleteIcon = document.createElement("img");
    deleteIcon.className = "ui-icon x-icon";
    deleteIcon.src = X_ICON_PATH;
    deleteIcon.alt = "";
    deleteIcon.setAttribute("aria-hidden", "true");
    deleteButton.append(deleteIcon);

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
        text: GENERIC_ERROR_MESSAGE,
        source: "",
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
  scrollChatToBottom({ smooth: true });
  return node;
}

function apiUrl(apiBase, path) {
  return `${apiBase}${path}`;
}

function isApiResponseData(data) {
  if (!data || typeof data !== "object") {
    return false;
  }
  return (
    "app" in data ||
    "answer" in data ||
    "questions" in data ||
    "error" in data ||
    "authenticated" in data ||
    "account" in data ||
    "chats" in data ||
    "rateLimit" in data
  );
}

function sleep(milliseconds) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });
}

function askRetryDelay(attempt) {
  const exponentialDelay = ASK_RETRY_BASE_DELAY_MS * 2 ** Math.min(attempt, 4);
  return Math.min(exponentialDelay, ASK_RETRY_MAX_DELAY_MS);
}

function isUsableAskResponse(data) {
  if (!data || typeof data !== "object" || data.error) {
    return false;
  }
  if (data.source === "unknown") {
    return false;
  }
  return (
    typeof data.answer === "string" &&
    data.answer.trim() &&
    data.answer.trim() !== GENERIC_ERROR_MESSAGE &&
    data.answer.trim() !== UNKNOWN_ANSWER_MESSAGE
  );
}

async function apiFetch(path, options = {}, apiBases = [activeApiBase]) {
  if (DIRECT_FILE_MODE) {
    throw new Error(GENERIC_ERROR_MESSAGE);
  }

  const { timeoutMs = 0, headers = {}, ...fetchOptions } = options;
  const basesToTry = [...new Set(apiBases.filter((base) => typeof base === "string"))];
  if (basesToTry.length === 0) {
    basesToTry.push("");
  }

  let lastError = null;
  const startedAt = performance.now();
  for (const apiBase of basesToTry) {
    const remainingTimeout =
      timeoutMs > 0 ? Math.max(0, timeoutMs - (performance.now() - startedAt)) : 0;
    if (timeoutMs > 0 && remainingTimeout <= 0) {
      break;
    }

    const controller =
      timeoutMs > 0 && "AbortController" in window ? new AbortController() : null;
    const timeoutId = controller
      ? window.setTimeout(() => controller.abort(), remainingTimeout)
      : null;

    try {
      const requestHeaders = { ...headers };
      if (fetchOptions.body !== undefined && !("Content-Type" in requestHeaders)) {
        requestHeaders["Content-Type"] = "application/json";
      }
      if (sessionId && !("X-Learny-Session" in requestHeaders)) {
        requestHeaders["X-Learny-Session"] = sessionId;
      }
      if (rateLimitSessionId && !("X-Learny-Rate-Session" in requestHeaders)) {
        requestHeaders["X-Learny-Rate-Session"] = rateLimitSessionId;
      }

      const response = await fetch(apiUrl(apiBase, path), {
        credentials: "include",
        headers: requestHeaders,
        ...fetchOptions,
        ...(controller ? { signal: controller.signal } : {}),
      });

      let data = {};
      try {
        data = await response.json();
      } catch {
        data = {};
      }

      if (!response.ok) {
        const responseError = new Error(GENERIC_ERROR_MESSAGE);
        responseError.status = response.status;
        responseError.data = data;
        responseError.retryable = data && typeof data === "object" ? data.retryable : undefined;
        responseError.stopFallback = response.status === 429;
        throw responseError;
      }
      if (!isApiResponseData(data)) {
        throw new Error(GENERIC_ERROR_MESSAGE);
      }

      activeApiBase = apiBase;
      return data;
    } catch (error) {
      lastError = error;
      if (error && error.stopFallback) {
        throw error;
      }
    } finally {
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId);
      }
    }
  }

  throw lastError || new Error(GENERIC_ERROR_MESSAGE);
}

async function loadStatus() {
  setConnection("checking", "Checking server status...");

  if (DIRECT_FILE_MODE) {
    setConnection("offline", "Servers offline");
    return;
  }

  try {
    const status = await apiFetch(
      "/api/status",
      { timeoutMs: STATUS_FETCH_TIMEOUT_MS },
      API_BASE_CANDIDATES,
    );
    setConnection(status.ok ? "online" : "offline", status.ok ? "Servers online" : "Servers offline");
  } catch (error) {
    if (isSending) {
      setConnection("checking", "Checking server status...");
      return;
    }
    setConnection("offline", "Servers offline");
  }
}

async function loadRateLimit() {
  if (DIRECT_FILE_MODE) {
    updateRateLimit(DEFAULT_RATE_LIMIT);
    return;
  }

  try {
    const data = await apiFetch(
      "/api/rate-limit",
      { timeoutMs: STATUS_FETCH_TIMEOUT_MS },
      activeApiBase ? [activeApiBase, ...API_BASE_CANDIDATES] : API_BASE_CANDIDATES,
    );
    if (data.rateSessionId) {
      rateLimitSessionId = data.rateSessionId;
      localStorage.setItem(RATE_LIMIT_SESSION_KEY, rateLimitSessionId);
    }
    updateRateLimit(data.rateLimit);
  } catch (error) {
    updateRateLimit(DEFAULT_RATE_LIMIT);
  }
}

async function askLearny(message) {
  if (DIRECT_FILE_MODE) {
    return;
  }

  if (isRateLimited()) {
    renderRateLimit();
    openRateLimitPopup({ force: true });
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

  let attempt = 0;
  let completed = false;
  try {
    while (!completed) {
      try {
        const data = await apiFetch(
          "/api/ask",
          {
            method: "POST",
            body: JSON.stringify({ message, sessionId, chatId: chat.id }),
            timeoutMs: ASK_REQUEST_TIMEOUT_MS,
          },
          activeApiBase ? [activeApiBase, ...API_BASE_CANDIDATES] : API_BASE_CANDIDATES,
        );
        if (!isUsableAskResponse(data)) {
          const error = new Error(GENERIC_ERROR_MESSAGE);
          if (data && typeof data === "object") {
            error.data = data;
          }
          throw error;
        }

        sessionId = data.sessionId;
        chat.sessionId = data.sessionId;
        localStorage.setItem(SESSION_KEY, sessionId);
        if (data.rateSessionId) {
          rateLimitSessionId = data.rateSessionId;
          localStorage.setItem(RATE_LIMIT_SESSION_KEY, rateLimitSessionId);
        }
        updateRateLimit(data.rateLimit);
        if (isRateLimited()) {
          openRateLimitPopup({ force: true });
        }
        saveChats();
        typing.remove();
        const thoughtSeconds = (performance.now() - thoughtStartedAt) / 1000;
        addMessage({
          speaker: "Learny",
          text: data.answer,
          source: sourceLabel(),
          thoughtSeconds,
        }, { animateWords: true });
        await loadStatus();
        completed = true;
      } catch (error) {
        if (error && error.status === 429 && error.data && error.data.rateLimit) {
          typing.remove();
          if (error.data.rateSessionId) {
            rateLimitSessionId = error.data.rateSessionId;
            localStorage.setItem(RATE_LIMIT_SESSION_KEY, rateLimitSessionId);
          }
          updateRateLimit(error.data.rateLimit);
          openRateLimitPopup({ force: true });
          completed = true;
          continue;
        }

        attempt += 1;
        setConnection("checking", "Checking server status...");
        await sleep(askRetryDelay(attempt));
      }
    }
  } finally {
    isSending = false;
    syncComposerAvailability();
    if (!isRateLimited()) {
      messageInput.focus();
    }
  }
}

async function handleAccountAuthSubmit(form, messageNode, endpoint) {
  if (!form) {
    return;
  }

  const formData = new FormData(form);
  const username = String(formData.get("username") || "").trim();
  const password = String(formData.get("password") || "");
  if (!username || !password) {
    setAccountFormMessage(messageNode, GENERIC_ERROR_MESSAGE, true);
    return;
  }

  setAuthFormBusy(form, true);
  setAccountFormMessage(messageNode);
  try {
    const data = await apiFetch(
      endpoint,
      {
        method: "POST",
        body: JSON.stringify({ username, password }),
        timeoutMs: STATUS_FETCH_TIMEOUT_MS,
      },
      activeApiBase ? [activeApiBase, ...API_BASE_CANDIDATES] : API_BASE_CANDIDATES,
    );
    if (!data.authenticated || !data.account) {
      throw new Error(GENERIC_ERROR_MESSAGE);
    }
    currentAccount = data.account;
    currentAccountStats = data.stats || null;
    form.reset();
    await loadAccountAndChats();
    await loadRateLimit();
    openAccountModal("myaccount");
  } catch (error) {
    setAccountFormMessage(messageNode, GENERIC_ERROR_MESSAGE, true);
  } finally {
    setAuthFormBusy(form, false);
  }
}

function setProfilePictureButtonBusy(busy) {
  if (!accountProfilePictureButton) {
    return;
  }
  accountProfilePictureButton.disabled = busy;
  if (busy) {
    accountProfilePictureButton.textContent = "Working...";
  } else {
    renderAccountProfilePicture();
  }
}

function readProfilePictureFile(file) {
  return new Promise((resolve, reject) => {
    if (!file || !PROFILE_PICTURE_TYPES.has(file.type) || file.size > PROFILE_PICTURE_MAX_BYTES) {
      reject(new Error(GENERIC_ERROR_MESSAGE));
      return;
    }

    const reader = new FileReader();
    reader.addEventListener("load", () => {
      const result = typeof reader.result === "string" ? reader.result : "";
      if (!result.startsWith("data:image/")) {
        reject(new Error(GENERIC_ERROR_MESSAGE));
        return;
      }
      resolve(result);
    });
    reader.addEventListener("error", () => reject(new Error(GENERIC_ERROR_MESSAGE)));
    reader.readAsDataURL(file);
  });
}

async function saveAccountProfilePicture(profilePicture) {
  const data = await apiFetch(
    "/api/account/profile-picture",
    {
      method: "POST",
      body: JSON.stringify({ profilePicture }),
      timeoutMs: STATUS_FETCH_TIMEOUT_MS,
    },
    activeApiBase ? [activeApiBase, ...API_BASE_CANDIDATES] : API_BASE_CANDIDATES,
  );
  if (!data.authenticated || !data.account) {
    throw new Error(GENERIC_ERROR_MESSAGE);
  }

  currentAccount = data.account;
  currentAccountStats = data.stats || currentAccountStats;
  updateAccountButton();
  renderAccountModalDetails();
}

async function handleAccountProfilePictureButton() {
  if (!currentAccount || !accountProfilePictureInput) {
    return;
  }

  if (!accountProfilePicture()) {
    accountProfilePictureInput.click();
    return;
  }

  setProfilePictureButtonBusy(true);
  try {
    await saveAccountProfilePicture(null);
    accountProfilePictureInput.value = "";
  } catch (error) {
    setConnection("offline", "Servers offline");
  } finally {
    setProfilePictureButtonBusy(false);
  }
}

async function handleAccountProfilePictureInputChange(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) {
    return;
  }

  setProfilePictureButtonBusy(true);
  try {
    const profilePicture = await readProfilePictureFile(file);
    await saveAccountProfilePicture(profilePicture);
  } catch (error) {
    setConnection("offline", "Servers offline");
  } finally {
    event.target.value = "";
    setProfilePictureButtonBusy(false);
  }
}

async function handleRateLimitReset() {
  if (!accountRateLimitResetButton || !currentAccount || !currentAccount.canResetRateLimits) {
    return;
  }

  accountRateLimitResetButton.disabled = true;
  accountRateLimitResetButton.textContent = "Resetting...";
  setAccountFormMessage(accountRateLimitResetMessage);
  try {
    const data = await apiFetch(
      "/api/rate-limits/reset",
      {
        method: "POST",
        body: JSON.stringify({}),
        timeoutMs: STATUS_FETCH_TIMEOUT_MS,
      },
      activeApiBase ? [activeApiBase, ...API_BASE_CANDIDATES] : API_BASE_CANDIDATES,
    );
    if (!data.ok || !data.rateLimit) {
      throw new Error(GENERIC_ERROR_MESSAGE);
    }
    if (data.rateSessionId) {
      rateLimitSessionId = data.rateSessionId;
      localStorage.setItem(RATE_LIMIT_SESSION_KEY, rateLimitSessionId);
    }
    updateRateLimit(data.rateLimit);
    closeRateLimitPopup();
    setAccountFormMessage(accountRateLimitResetMessage, "All rate limits were reset.");
  } catch (error) {
    setAccountFormMessage(accountRateLimitResetMessage, GENERIC_ERROR_MESSAGE, true);
  } finally {
    accountRateLimitResetButton.disabled = false;
    accountRateLimitResetButton.textContent = "Reset all rate limits";
  }
}

async function handleAccountSignOut() {
  if (!accountSignOutButton) {
    return;
  }

  accountSignOutButton.disabled = true;
  accountSignOutButton.textContent = "Signing out...";
  try {
    await apiFetch(
      "/api/accounts/sign-out",
      {
        method: "POST",
        body: JSON.stringify({}),
        timeoutMs: STATUS_FETCH_TIMEOUT_MS,
      },
      activeApiBase ? [activeApiBase, ...API_BASE_CANDIDATES] : API_BASE_CANDIDATES,
    );
  } catch (error) {
    setConnection("offline", "Servers offline");
  } finally {
    clearSignedInLocalState();
    await loadRateLimit();
    accountSignOutButton.disabled = false;
    accountSignOutButton.textContent = "Sign out";
    openAccountModal("sign-in");
  }
}

async function handleAccountDelete() {
  if (!accountDeleteConfirmButton) {
    return;
  }

  accountDeleteConfirmButton.disabled = true;
  accountDeleteConfirmButton.textContent = "Deleting...";
  try {
    const data = await apiFetch(
      "/api/accounts/delete",
      {
        method: "POST",
        body: JSON.stringify({}),
        timeoutMs: STATUS_FETCH_TIMEOUT_MS,
      },
      activeApiBase ? [activeApiBase, ...API_BASE_CANDIDATES] : API_BASE_CANDIDATES,
    );
    if (!data.deleted) {
      throw new Error(GENERIC_ERROR_MESSAGE);
    }
    clearSignedInLocalState();
    await loadRateLimit();
    openAccountModal("sign-in");
  } catch (error) {
    setConnection("offline", "Servers offline");
  } finally {
    accountDeleteConfirmButton.disabled = false;
    accountDeleteConfirmButton.textContent = "Delete forever";
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
  if (isRateLimited()) {
    renderRateLimit();
    openRateLimitPopup();
    return;
  }
  messageInput.value = "";
  askLearny(message);
});

if (addChatButton) {
  addChatButton.addEventListener("click", resetChat);
}

if (accountButton) {
  accountButton.addEventListener("click", (event) => {
    event.preventDefault();
    openAccountModal(currentAccount ? "myaccount" : "sign-in");
  });
}

document.querySelectorAll("[data-open-account-view]").forEach((button) => {
  button.addEventListener("click", () => {
    openAccountModal(button.dataset.openAccountView || "sign-in");
  });
});

if (accountModalBackdrop) {
  accountModalBackdrop.addEventListener("click", () => closeAccountModal());
}

if (accountModalClose) {
  accountModalClose.addEventListener("click", () => closeAccountModal());
}

if (rateLimitBackdrop) {
  rateLimitBackdrop.addEventListener("click", closeRateLimitPopup);
}

if (rateLimitClose) {
  rateLimitClose.addEventListener("click", closeRateLimitPopup);
}

if (rateLimitOk) {
  rateLimitOk.addEventListener("click", closeRateLimitPopup);
}

if (signInForm) {
  signInForm.addEventListener("submit", (event) => {
    event.preventDefault();
    handleAccountAuthSubmit(signInForm, signInMessage, "/api/accounts/sign-in");
  });
}

if (createAccountForm) {
  createAccountForm.addEventListener("submit", (event) => {
    event.preventDefault();
    handleAccountAuthSubmit(createAccountForm, createAccountMessage, "/api/accounts/create");
  });
}

if (accountProfilePictureButton) {
  accountProfilePictureButton.addEventListener("click", handleAccountProfilePictureButton);
}

if (accountProfilePictureInput) {
  accountProfilePictureInput.addEventListener("change", handleAccountProfilePictureInputChange);
}

if (accountRateLimitResetButton) {
  accountRateLimitResetButton.addEventListener("click", handleRateLimitReset);
}

if (accountSignOutButton) {
  accountSignOutButton.addEventListener("click", handleAccountSignOut);
}

if (accountDeleteButton) {
  accountDeleteButton.addEventListener("click", () => {
    if (accountDeleteConfirm) {
      accountDeleteConfirm.hidden = false;
    }
  });
}

if (accountDeleteCancel) {
  accountDeleteCancel.addEventListener("click", resetDeleteConfirmation);
}

if (accountDeleteConfirmButton) {
  accountDeleteConfirmButton.addEventListener("click", handleAccountDelete);
}

if (chatSearchInput) {
  chatSearchInput.addEventListener("input", () => {
    chatSearchQuery = chatSearchInput.value;
    renderChatList();
  });
}

if (messageSearchInput) {
  messageSearchInput.addEventListener("input", () => {
    messageSearchQuery = messageSearchInput.value;
    messageSearchIndex = 0;
    updateMessageSearch({ scrollToCurrent: Boolean(messageSearchQuery.trim()) });
  });

  messageSearchInput.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") {
      return;
    }
    event.preventDefault();
    cycleMessageSearch(event.shiftKey ? -1 : 1);
  });
}

if (mobileSidebarButton) {
  mobileSidebarButton.setAttribute("aria-controls", "sidebar");
  mobileSidebarButton.setAttribute("aria-expanded", "false");
  mobileSidebarButton.addEventListener("click", () => {
    setSidebarOpen(!appShell.classList.contains("sidebar-open"));
  });
}

if (sidebarScrim) {
  sidebarScrim.addEventListener("click", () => setSidebarOpen(false));
}

if (sidebarToggle) {
  sidebarToggle.setAttribute("aria-controls", "sidebar");
  sidebarToggle.setAttribute("aria-expanded", "true");
  sidebarToggle.addEventListener("click", toggleSidebarControl);
}

if (mobileSidebarMedia) {
  if (typeof mobileSidebarMedia.addEventListener === "function") {
    mobileSidebarMedia.addEventListener("change", syncSidebarForViewport);
  } else if (typeof mobileSidebarMedia.addListener === "function") {
    mobileSidebarMedia.addListener(syncSidebarForViewport);
  }
}

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    if (rateLimitModal && !rateLimitModal.hidden) {
      closeRateLimitPopup();
      return;
    }
    if (accountModal && !accountModal.hidden) {
      closeAccountModal();
      return;
    }
    setSidebarOpen(false);
  }
});

startWelcomeHeadingCycle();
createStarField();

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
renderRateLimit();

if (DIRECT_FILE_MODE) {
  addMessage(
    {
      speaker: "Learny",
      text: GENERIC_ERROR_MESSAGE,
      source: "",
    },
    { persist: false },
  );
  messageInput.disabled = true;
  sendButton.disabled = true;
} else {
  renderActiveChat();
}

loadAccountAndChats();
loadStatus();
loadRateLimit();
if (!DIRECT_FILE_MODE) {
  window.setInterval(loadStatus, STATUS_CHECK_INTERVAL_MS);
}
