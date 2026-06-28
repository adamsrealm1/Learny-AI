const chatLog = document.querySelector("#chatLog");
const chatForm = document.querySelector("#chatForm");
const messageInput = document.querySelector("#messageInput");
const sendButton = document.querySelector("#sendButton");
const attachButton = document.querySelector("#attachButton");
const fileInput = document.querySelector("#fileInput");
const attachmentTray = document.querySelector("#attachmentTray");
const messageTemplate = document.querySelector("#messageTemplate");
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
const attachmentAuthModal = document.querySelector("#attachmentAuthModal");
const attachmentAuthBackdrop = document.querySelector("#attachmentAuthBackdrop");
const attachmentAuthClose = document.querySelector("#attachmentAuthClose");
const attachmentAuthForm = document.querySelector("#attachmentAuthForm");
const attachmentAuthPassword = document.querySelector("#attachmentAuthPassword");
const attachmentAuthOk = document.querySelector("#attachmentAuthOk");
const attachmentAuthMessage = document.querySelector("#attachmentAuthMessage");
const emptyState = document.querySelector("#emptyState");
const starField = document.querySelector("#starField");
const appShell = document.querySelector(".app-shell");
const mainArea = document.querySelector(".main-area");
const chatPanel = document.querySelector(".chat-panel");
const sidebarToggle = document.querySelector(".sidebar-toggle");
const mobileSidebarButton = document.querySelector("#mobileSidebarButton");
const sidebarScrim = document.querySelector("#sidebarScrim");
const messageSearchInput = document.querySelector("#messageSearchInput");
const messageSearchCount = document.querySelector("#messageSearchCount");
const messageSearch = document.querySelector(".message-search");
const welcomeHeading = document.querySelector("#welcomeHeading");
const accountButton = document.querySelector("#accountButton");
const accountStatusText = document.querySelector("#accountStatusText");
const accountOrbImage = document.querySelector("#accountOrbImage");
const adminButton = document.querySelector("#adminButton");
const adminPortal = document.querySelector("#adminPortal");
const adminAvailabilityText = document.querySelector("#adminAvailabilityText");
const adminAvailabilityToggle = document.querySelector("#adminAvailabilityToggle");
const adminAvailabilityLabel = document.querySelector("#adminAvailabilityLabel");
const adminAccountsCount = document.querySelector("#adminAccountsCount");
const adminAdminsCount = document.querySelector("#adminAdminsCount");
const adminBansCount = document.querySelector("#adminBansCount");
const adminAccountsList = document.querySelector("#adminAccountsList");
const adminAdminsList = document.querySelector("#adminAdminsList");
const adminBansList = document.querySelector("#adminBansList");
const adminStatusMessage = document.querySelector("#adminStatusMessage");
const adminBanUsernameForm = document.querySelector("#adminBanUsernameForm");
const adminUnbanUsernameForm = document.querySelector("#adminUnbanUsernameForm");
const adminBanIpForm = document.querySelector("#adminBanIpForm");
const adminUnbanIpForm = document.querySelector("#adminUnbanIpForm");
const adminDeleteAccountForm = document.querySelector("#adminDeleteAccountForm");
const adminResetRateLimitForm = document.querySelector("#adminResetRateLimitForm");
const adminGrantForm = document.querySelector("#adminGrantForm");
const adminRevokeForm = document.querySelector("#adminRevokeForm");
const banLock = document.querySelector("#banLock");
const banLockAdminImage = document.querySelector("#banLockAdminImage");
const banLockAdminName = document.querySelector("#banLockAdminName");
const banLockTarget = document.querySelector("#banLockTarget");
const banLockDate = document.querySelector("#banLockDate");
const banLockReason = document.querySelector("#banLockReason");
const accountModal = document.querySelector("#accountInterface");
const accountBackButton = document.querySelector("#accountBackButton");
const accountModalTitle = document.querySelector("#accountModalTitle");
const accountModalSubtitle = document.querySelector("#accountModalSubtitle");
const accountModalViews = document.querySelectorAll("[data-account-view]");
const signInForm = document.querySelector("#signInForm");
const createAccountForm = document.querySelector("#createAccountForm");
const signInSubmitButton = document.querySelector("#signInSubmitButton");
const createAccountSubmitButton = document.querySelector("#createAccountSubmitButton");
const signInCaptcha = document.querySelector("#signInCaptcha");
const createAccountCaptcha = document.querySelector("#createAccountCaptcha");
const deleteAccountCaptcha = document.querySelector("#deleteAccountCaptcha");
const attachmentCaptcha = document.querySelector("#attachmentCaptcha");
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
const accountSignOutButton = document.querySelector("#accountSignOutButton");
const accountDeleteButton = document.querySelector("#accountDeleteButton");
const accountDeleteConfirm = document.querySelector("#accountDeleteConfirm");
const accountDeleteCancel = document.querySelector("#accountDeleteCancel");
const accountDeleteConfirmButton = document.querySelector("#accountDeleteConfirmButton");

const CHATS_KEY = "learny-chats";
const ACTIVE_CHAT_KEY = "learny-active-chat-id";
const SESSION_KEY = "learny-session-id";
const RATE_LIMIT_SESSION_KEY = "learny-rate-limit-session-id";
const APP_SCRIPT_SOURCE =
  document.currentScript?.getAttribute("src") ||
  document.querySelector('script[src*="app.js"]')?.getAttribute("src") ||
  "./web/app.js";
const APP_SCRIPT_URL = new URL(APP_SCRIPT_SOURCE, window.location.href);
const APP_ASSET_BASE_URL = new URL("../", APP_SCRIPT_URL);
const COPY_ICON_PATH = appAssetPath("icon_library/copy.png");
const CHECK_ICON_PATH = appAssetPath("icon_library/check.png");
const EDIT_ICON_PATH = appAssetPath("icon_library/edit.png");
const DELETE_ICON_PATH = appAssetPath("icon_library/delete.png");
const X_ICON_PATH = appAssetPath("icon_library/X.png");
const PROFILE_ICON_PATH = appAssetPath("icon_library/profile.png");
const PROFILE_PICTURE_MAX_BYTES = 512 * 1024;
const PROFILE_PICTURE_TYPES = new Set(["image/png", "image/jpeg", "image/webp", "image/gif"]);
const ATTACHMENT_MAX_BYTES = 4 * 1024 * 1024;
const ATTACHMENT_LIMIT = 10;
const ATTACHMENT_EXTENSIONS = new Set(["txt", "md", "log", "docx", "rtf", "pdf", "csv", "json", "xml"]);
const RECAPTCHA_SCRIPT_ID = "learny-recaptcha-script";
const COPY_RESET_DELAY_MS = 10000;
const MESSAGE_DELETE_DURATION_MS = 850;
const WORD_REVEAL_STEP_MS = 52;
const WORD_REVEAL_DURATION_MS = 300;
const WORD_REVEAL_FOOTER_DELAY_MS = 850;
const WELCOME_TEXT = "What's on your mind?";
const MOBILE_SIDEBAR_QUERY = "(max-width: 860px)";
const DIRECT_FILE_MODE = window.location.protocol === "file:";
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
const DEFAULT_PLATFORM = {
  available: true,
  updatedAt: 0,
};
const OWNER_ADMIN_USERNAME = "adamsrealm1";
const GENERIC_ERROR_MESSAGE = "Something went wrong. Try again later.";
const UNKNOWN_ANSWER_MESSAGE = "I do not know that yet.";
const WASMER_API_BASE = "https://learny-ai-adamsrealm1.wasmer.app";
const WASMER_API_FALLBACK_BASE = "https://learny-ai.wasmer.app";
const API_BASE_CANDIDATES = buildApiBaseCandidates();
const DESKTOP_STAR_COUNT = 360;
const MOBILE_STAR_COUNT = 230;
const DESKTOP_SIDEBAR_STAR_COUNT = 230;
const PROMPT_META_MARKERS = [
  "current user question",
  "previous conversation",
  "recent conversation",
  "chat context",
  "system prompt",
  "hidden instructions",
];

function appAssetPath(path) {
  return new URL(path.replace(/^\/+/, ""), APP_ASSET_BASE_URL).toString();
}

function clientTimeZone() {
  try {
    const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    return typeof timeZone === "string" ? timeZone : "";
  } catch {
    return "";
  }
}

function attachmentExtensionFromName(name) {
  const cleanName = String(name || "").trim();
  const dotIndex = cleanName.lastIndexOf(".");
  if (dotIndex < 0 || dotIndex === cleanName.length - 1) {
    return "";
  }
  return cleanName.slice(dotIndex + 1).toLowerCase();
}

function formatFileSize(bytes) {
  const size = Number(bytes);
  if (!Number.isFinite(size) || size <= 0) {
    return "0 KB";
  }
  if (size < 1024 * 1024) {
    return `${Math.max(1, Math.round(size / 1024))} KB`;
  }
  return `${(size / (1024 * 1024)).toFixed(size >= 10 * 1024 * 1024 ? 0 : 1)} MB`;
}

function normalizeAttachmentMeta(attachment) {
  if (!attachment || typeof attachment !== "object") {
    return null;
  }
  const name = typeof attachment.name === "string" ? attachment.name.trim() : "";
  if (!name) {
    return null;
  }
  const extension = attachmentExtensionFromName(name);
  if (!ATTACHMENT_EXTENSIONS.has(extension)) {
    return null;
  }
  const size = Number.isFinite(attachment.size) ? Math.max(0, Math.floor(attachment.size)) : 0;
  return {
    name,
    extension,
    size,
    type: typeof attachment.type === "string" ? attachment.type.trim() : "",
  };
}

function normalizeAttachmentMetas(message) {
  const rawAttachments = Array.isArray(message && message.attachments)
    ? message.attachments
    : message && message.attachment
      ? [message.attachment]
      : [];
  return rawAttachments
    .map((attachment) => normalizeAttachmentMeta(attachment))
    .filter(Boolean)
    .slice(0, ATTACHMENT_LIMIT);
}

function attachmentMetaFromFile(file) {
  if (!file) {
    return null;
  }
  return normalizeAttachmentMeta({
    name: file.name,
    size: file.size,
    type: file.type,
  });
}

function isAllowedAttachmentFile(file) {
  const meta = attachmentMetaFromFile(file);
  return Boolean(meta && file.size <= ATTACHMENT_MAX_BYTES);
}

let chats = loadStoredChats();
let activeChatId = localStorage.getItem(ACTIVE_CHAT_KEY) || "";
let sessionId = "";
let rateLimitSessionId = localStorage.getItem(RATE_LIMIT_SESSION_KEY) || "";
let isSending = false;
let chatSearchQuery = "";
let messageSearchQuery = "";
let messageSearchIndex = 0;
let activeApiBase = "";
let currentAccount = null;
let currentAccountStats = null;
let currentRateLimit = { ...DEFAULT_RATE_LIMIT };
let currentPlatform = { ...DEFAULT_PLATFORM };
let currentBan = null;
let activeView = "chat";
let adminPortalData = null;
let rateLimitRefreshTimerId = null;
let rateLimitPopupTimerId = null;
let platformRefreshTimerId = null;
let serverChatsLoaded = false;
let serverSyncTimerId = null;
let activeAccountView = "";
let selectedAttachments = [];
let captchaConfig = { enabled: false, siteKey: "" };
let recaptchaScriptPromise = null;
let attachmentVerificationToken = "";
let attachmentVerificationExpiresAt = 0;
const captchaControls = {
  signIn: {
    action: "sign-in",
    element: signInCaptcha,
    button: signInSubmitButton,
    token: "",
    widgetId: null,
    state: "idle",
  },
  createAccount: {
    action: "create-account",
    element: createAccountCaptcha,
    button: createAccountSubmitButton,
    token: "",
    widgetId: null,
    state: "idle",
  },
  deleteAccount: {
    action: "delete-account",
    element: deleteAccountCaptcha,
    button: accountDeleteConfirmButton,
    token: "",
    widgetId: null,
    state: "idle",
  },
  attachment: {
    action: "attachment",
    element: attachmentCaptcha,
    button: attachmentAuthOk,
    token: "",
    widgetId: null,
    state: "idle",
  },
};
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
  const sidebarStarCount = window.innerWidth <= 860 ? 0 : DESKTOP_SIDEBAR_STAR_COUNT;
  const rootStyles = getComputedStyle(document.documentElement);
  const cssSidebarWidth = Number.parseFloat(rootStyles.getPropertyValue("--sidebar-width"));
  const sidebarWidth = Number.isFinite(cssSidebarWidth) && cssSidebarWidth > 0 ? cssSidebarWidth : 292;
  const fragment = document.createDocumentFragment();
  starField.replaceChildren();

  function makeStar(sidebarOnly = false) {
    const star = document.createElement("span");
    const angle = Math.random() * Math.PI * 2;
    const travel = 14 + Math.random() * 26;
    const duration = 115 + Math.random() * 165;
    const smallStar = Math.random() < 0.88;
    const size = smallStar ? 0.7 + Math.random() * 0.75 : 1.45 + Math.random() * 0.85;
    const opacity = sidebarOnly ? 0.34 + Math.random() * 0.52 : 0.24 + Math.random() * 0.56;
    const glow = smallStar ? 2 + Math.random() * 4 : 4 + Math.random() * 7;
    const x = sidebarOnly ? `${4 + Math.random() * Math.max(sidebarWidth - 8, 1)}px` : `${Math.random() * 100}vw`;

    star.className = "star";
    star.style.setProperty("--x", x);
    star.style.setProperty("--y", `${Math.random() * 100}vh`);
    star.style.setProperty("--travel-x", `${Math.cos(angle) * travel}vw`);
    star.style.setProperty("--travel-y", `${Math.sin(angle) * travel}vh`);
    star.style.setProperty("--size", `${size.toFixed(2)}px`);
    star.style.setProperty("--opacity", opacity.toFixed(2));
    star.style.setProperty("--glow", `${glow.toFixed(2)}px`);
    star.style.setProperty("--glow-opacity", (opacity * 0.42).toFixed(2));
    star.style.setProperty("--duration", `${duration.toFixed(1)}s`);
    star.style.setProperty("--delay", `${(-Math.random() * duration).toFixed(1)}s`);
    return star;
  }

  for (let index = 0; index < starCount; index += 1) {
    fragment.append(makeStar());
  }

  for (let index = 0; index < sidebarStarCount; index += 1) {
    fragment.append(makeStar(true));
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
  if (!smooth) {
    chatLog.scrollTop = top;
    return;
  }

  if (typeof chatLog.scrollTo === "function") {
    chatLog.scrollTo({ top, behavior: "smooth" });
    [360, 760].forEach((delay) => {
      window.setTimeout(() => {
        if (chatLog) {
          chatLog.scrollTop = chatLog.scrollHeight;
        }
      }, delay);
    });
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
    scrollChatToBottom({ smooth: false });
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
  if (icon) {
    icon.src = copied ? CHECK_ICON_PATH : COPY_ICON_PATH;
  }
  const label = button.querySelector("[data-copy-label]");
  if (label) {
    label.textContent = copied ? "Copied" : "Copy";
  }
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

function createIconCopyButton(text) {
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
  return copyButton;
}

function createTextActionButton(label, className, onClick, iconPath = "") {
  const button = document.createElement("button");
  button.className = `message-text-action ${className}`;
  button.type = "button";
  button.title = label;
  button.setAttribute("aria-label", label);

  if (iconPath) {
    const icon = document.createElement("img");
    icon.className = "ui-icon message-action-icon";
    icon.src = iconPath;
    icon.alt = "";
    icon.setAttribute("aria-hidden", "true");
    button.append(icon);
  }

  const labelNode = document.createElement("span");
  labelNode.className = "sr-only";
  labelNode.textContent = label;
  button.append(labelNode);
  button.addEventListener("click", onClick);
  return button;
}

function createTextCopyButton(text) {
  const button = createTextActionButton("Copy", "message-copy-text-button", () =>
    handleCopyMessage(button, text),
    COPY_ICON_PATH,
  );
  const label = button.querySelector("span");
  if (label) {
    label.dataset.copyLabel = "";
  }
  button.title = "Copy message";
  button.setAttribute("aria-label", "Copy message");
  return button;
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

function showWelcomeHeading() {
  if (!welcomeHeading) {
    return;
  }

  renderWelcomeHeadingText(WELCOME_TEXT);
}

function clearSelectedAttachments() {
  selectedAttachments = [];
  if (fileInput) {
    fileInput.value = "";
  }
  renderAttachmentTray();
}

function addSelectedAttachments(files) {
  const nextAttachments = [...selectedAttachments];
  for (const file of files) {
    if (nextAttachments.length >= ATTACHMENT_LIMIT) {
      break;
    }
    if (!isAllowedAttachmentFile(file)) {
      continue;
    }
    nextAttachments.push({
      file,
      meta: attachmentMetaFromFile(file),
    });
  }
  selectedAttachments = nextAttachments;
  if (fileInput) {
    fileInput.value = "";
  }
  renderAttachmentTray();
}

function removeSelectedAttachment(index) {
  if (!Number.isInteger(index) || index < 0 || index >= selectedAttachments.length) {
    return;
  }
  selectedAttachments = selectedAttachments.filter((_, attachmentIndex) => attachmentIndex !== index);
  renderAttachmentTray();
}

function renderAttachmentTray() {
  if (!attachmentTray) {
    return;
  }

  const composer = chatForm;
  if (composer) {
    composer.classList.toggle("has-attachment", selectedAttachments.length > 0);
  }

  attachmentTray.replaceChildren();
  if (selectedAttachments.length === 0) {
    attachmentTray.hidden = true;
    return;
  }

  selectedAttachments.forEach((attachment, index) => {
    if (!attachment || !attachment.meta) {
      return;
    }

    const { name, extension, size } = attachment.meta;
    const card = document.createElement("div");
    card.className = "attachment-card";

    const icon = document.createElement("span");
    icon.className = "attachment-file-icon";
    icon.textContent = extension || "file";

    const info = document.createElement("span");
    info.className = "attachment-info";

    const filename = document.createElement("strong");
    filename.className = "attachment-name";
    filename.textContent = name;

    const meta = document.createElement("small");
    meta.className = "attachment-meta";
    meta.textContent = `${extension.toUpperCase()} document - ${formatFileSize(size)}`;

    info.append(filename, meta);

    const removeButton = document.createElement("button");
    removeButton.className = "attachment-remove";
    removeButton.type = "button";
    removeButton.title = "Remove attachment";
    removeButton.setAttribute("aria-label", `Remove ${name}`);

    const removeIcon = document.createElement("img");
    removeIcon.className = "ui-icon x-icon";
    removeIcon.src = X_ICON_PATH;
    removeIcon.alt = "";
    removeIcon.setAttribute("aria-hidden", "true");
    removeButton.append(removeIcon);
    removeButton.addEventListener("click", () => removeSelectedAttachment(index));

    card.append(icon, info, removeButton);
    attachmentTray.append(card);
  });
  attachmentTray.hidden = false;
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
                attachments: normalizeAttachmentMetas(message),
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
  let remaining = Number.isFinite(rateLimit.remaining)
    ? Math.max(0, Math.min(limit, Math.floor(rateLimit.remaining)))
    : limit;
  const windowMs = Number.isFinite(rateLimit.windowMs) && rateLimit.windowMs > 0
    ? Math.floor(rateLimit.windowMs)
    : DEFAULT_RATE_LIMIT.windowMs;
  let resetAt = Number.isFinite(rateLimit.resetAt) && rateLimit.resetAt > 0
    ? Math.floor(rateLimit.resetAt)
    : Date.now() + windowMs;
  const now = Date.now();
  if (resetAt <= now) {
    remaining = limit;
    resetAt = now + windowMs;
  }

  return {
    limit,
    remaining,
    windowMs,
    resetAt,
    limited: Boolean(rateLimit.limited) && now < resetAt,
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

function normalizePlatform(platform) {
  if (!platform || typeof platform !== "object") {
    return { ...DEFAULT_PLATFORM };
  }
  return {
    available: platform.available !== false,
    updatedAt: Number.isFinite(platform.updatedAt) ? Number(platform.updatedAt) : Date.now(),
  };
}

function isPlatformUnavailable() {
  return currentPlatform && currentPlatform.available === false;
}

function formatDateTime(timestamp) {
  const date = new Date(Number(timestamp));
  if (Number.isNaN(date.getTime())) {
    return "Unknown";
  }
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function renderBanLock() {
  if (!banLock) {
    return;
  }

  const banned = Boolean(currentBan);
  banLock.hidden = !banned;
  document.body.classList.toggle("ban-lock-active", banned);
  if (!banned) {
    return;
  }

  const createdByAccount = currentBan.createdByAccount || {};
  const createdByName = createdByAccount.username || currentBan.createdBy || "Unknown admin";
  if (banLockAdminImage) {
    banLockAdminImage.src = createdByAccount.profilePicture || PROFILE_ICON_PATH;
  }
  if (banLockAdminName) {
    banLockAdminName.textContent = createdByName;
  }
  if (banLockTarget) {
    const prefix = currentBan.kind === "username" ? "@" : "";
    banLockTarget.textContent = `${prefix}${currentBan.target || "Unknown"}`;
  }
  if (banLockDate) {
    banLockDate.textContent = formatDateTime(currentBan.createdAt);
  }
  if (banLockReason) {
    banLockReason.textContent = currentBan.reason || "Access was blocked by Learny moderation.";
  }
}

function updateBanState(ban) {
  currentBan = ban && typeof ban === "object" ? ban : null;
  renderBanLock();
}

function updatePlatform(platform) {
  currentPlatform = normalizePlatform(platform);
  renderPlatformState();
  syncComposerAvailability();
}

function isCurrentAdmin() {
  return Boolean(currentAccount && currentAccount.isAdmin);
}

function isCurrentOwnerAdmin() {
  return (
    isCurrentAdmin() &&
    String(currentAccount.username || "").toLowerCase() === OWNER_ADMIN_USERNAME
  );
}

function syncComposerAvailability() {
  const composer = chatForm;
  const unavailable = isPlatformUnavailable();
  if (composer) {
    composer.classList.toggle("unavailable", unavailable);
  }
  if (messageInput) {
    messageInput.placeholder = unavailable ? "Learny AI is currently unavailable." : "Ask anything";
  }

  if (DIRECT_FILE_MODE) {
    sendButton.disabled = true;
    messageInput.disabled = true;
    if (attachButton) {
      attachButton.disabled = true;
    }
    return;
  }

  if (unavailable) {
    sendButton.disabled = true;
    messageInput.disabled = true;
    if (attachButton) {
      attachButton.disabled = true;
    }
    return;
  }

  if (!isSending) {
    sendButton.disabled = false;
    messageInput.disabled = false;
    if (attachButton) {
      attachButton.disabled = false;
    }
  }
}

function renderRateLimit() {
  let rateLimit = currentRateLimit || DEFAULT_RATE_LIMIT;
  if (Date.now() >= rateLimit.resetAt) {
    currentRateLimit = {
      ...rateLimit,
      remaining: rateLimit.limit,
      resetAt: Date.now() + rateLimit.windowMs,
      limited: false,
    };
    rateLimit = currentRateLimit;
    window.setTimeout(loadRateLimit, 0);
  }
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

function normalizeCaptchaConfig(config) {
  if (!config || typeof config !== "object") {
    return { enabled: false, siteKey: "" };
  }
  return {
    enabled: Boolean(config.enabled && typeof config.siteKey === "string" && config.siteKey.trim()),
    siteKey: typeof config.siteKey === "string" ? config.siteKey.trim() : "",
  };
}

function isCaptchaEnabled() {
  return Boolean(captchaConfig.enabled && captchaConfig.siteKey);
}

function waitForRecaptchaReady(timeoutMs = 10000) {
  if (window.grecaptcha && typeof window.grecaptcha.render === "function") {
    return Promise.resolve();
  }
  return new Promise((resolve, reject) => {
    const startedAt = Date.now();
    const timerId = window.setInterval(() => {
      if (window.grecaptcha && typeof window.grecaptcha.render === "function") {
        window.clearInterval(timerId);
        resolve();
        return;
      }
      if (Date.now() - startedAt >= timeoutMs) {
        window.clearInterval(timerId);
        reject(new Error(GENERIC_ERROR_MESSAGE));
      }
    }, 120);
  });
}

function loadRecaptchaScript() {
  if (!isCaptchaEnabled()) {
    return Promise.resolve();
  }
  if (window.grecaptcha && typeof window.grecaptcha.render === "function") {
    return Promise.resolve();
  }
  if (recaptchaScriptPromise) {
    return recaptchaScriptPromise;
  }

  recaptchaScriptPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector(`#${RECAPTCHA_SCRIPT_ID}`);
    if (existing) {
      existing.addEventListener("load", () => waitForRecaptchaReady().then(resolve, reject), { once: true });
      existing.addEventListener("error", () => reject(new Error(GENERIC_ERROR_MESSAGE)), { once: true });
      waitForRecaptchaReady().then(resolve, reject);
      return;
    }

    const script = document.createElement("script");
    script.id = RECAPTCHA_SCRIPT_ID;
    script.src = "https://www.google.com/recaptcha/api.js?render=explicit";
    script.async = true;
    script.defer = true;
    script.addEventListener("load", () => waitForRecaptchaReady().then(resolve, reject), { once: true });
    script.addEventListener("error", () => reject(new Error(GENERIC_ERROR_MESSAGE)), { once: true });
    document.head.append(script);
  });
  return recaptchaScriptPromise;
}

function captchaControl(name) {
  return captchaControls[name] || null;
}

function setCaptchaToken(name, token) {
  const control = captchaControl(name);
  if (!control) {
    return;
  }
  control.token = String(token || "");
  syncCaptchaButtons();
}

function captchaToken(name) {
  const control = captchaControl(name);
  return control ? control.token : "";
}

function setCaptchaState(name, state, message = "") {
  const control = captchaControl(name);
  if (!control || !control.element) {
    return;
  }
  control.state = state;
  control.element.dataset.captchaState = state;
  control.element.dataset.captchaMessage = message;
  control.element.setAttribute("aria-busy", state === "loading" ? "true" : "false");
}

function syncCaptchaButtons() {
  Object.entries(captchaControls).forEach(([name, control]) => {
    if (!control.button) {
      return;
    }
    const requiresCaptcha = isCaptchaEnabled();
    const missingCaptcha = requiresCaptcha && !control.token;
    const missingAttachmentPassword =
      name === "attachment" &&
      attachmentAuthPassword &&
      !String(attachmentAuthPassword.value || "").trim();
    control.button.disabled = Boolean(missingCaptcha || missingAttachmentPassword);
  });
}

function captchaRenderTarget(control) {
  if (!control || !control.element) {
    return null;
  }
  if (control.renderTarget && control.renderTarget.isConnected) {
    return control.renderTarget;
  }
  const target = document.createElement("div");
  target.className = "captcha-widget-clip";
  control.element.append(target);
  control.renderTarget = target;
  return target;
}

async function renderCaptchaControl(name) {
  const control = captchaControl(name);
  if (!control || !control.element) {
    return;
  }
  control.element.classList.toggle("captcha-disabled", !isCaptchaEnabled());
  control.element.hidden = !isCaptchaEnabled();
  if (!isCaptchaEnabled()) {
    control.token = "";
    setCaptchaState(name, "idle");
    syncCaptchaButtons();
    return;
  }
  if (control.widgetId !== null) {
    setCaptchaState(name, "ready");
    return;
  }
  setCaptchaState(name, "loading", "Loading verification...");
  try {
    await loadRecaptchaScript();
    if (!window.grecaptcha || typeof window.grecaptcha.render !== "function") {
      throw new Error(GENERIC_ERROR_MESSAGE);
    }
    const renderTarget = captchaRenderTarget(control);
    if (!renderTarget) {
      throw new Error(GENERIC_ERROR_MESSAGE);
    }
    control.widgetId = window.grecaptcha.render(renderTarget, {
      sitekey: captchaConfig.siteKey,
      theme: "dark",
      callback: (token) => {
        setCaptchaState(name, "ready");
        setCaptchaToken(name, token);
      },
      "expired-callback": () => setCaptchaToken(name, ""),
      "error-callback": () => {
        setCaptchaState(name, "error", "Something went wrong. Try again later.");
        setCaptchaToken(name, "");
      },
    });
    setCaptchaState(name, "ready");
    syncCaptchaButtons();
  } catch (error) {
    setCaptchaState(name, "error", "Something went wrong. Try again later.");
    throw error;
  }
}

function queueCaptchaRender(name) {
  renderCaptchaControl(name).catch(() => {
    resetCaptchaControl(name);
    setCaptchaState(name, "error", "Something went wrong. Try again later.");
  });
}

async function renderCaptchaControls() {
  if (!isCaptchaEnabled()) {
    Object.entries(captchaControls).forEach(([name, control]) => {
      if (control.element) {
        control.element.hidden = true;
      }
      control.token = "";
      setCaptchaState(name, "idle");
    });
    syncCaptchaButtons();
    return;
  }
  Object.values(captchaControls).forEach((control) => {
    if (control.element) {
      control.element.hidden = false;
    }
  });
  syncCaptchaButtons();
  try {
    if (activeAccountView === "sign-in") {
      await renderCaptchaControl("signIn");
    } else if (activeAccountView === "create-account") {
      await renderCaptchaControl("createAccount");
    }
    if (accountDeleteConfirm && !accountDeleteConfirm.hidden) {
      await renderCaptchaControl("deleteAccount");
    }
    if (attachmentAuthModal && !attachmentAuthModal.hidden) {
      await renderCaptchaControl("attachment");
    }
  } catch (error) {}
}

function resetCaptchaControl(name) {
  const control = captchaControl(name);
  if (!control) {
    return;
  }
  control.token = "";
  if (control.widgetId === null && isCaptchaEnabled()) {
    setCaptchaState(name, "idle");
  }
  if (
    isCaptchaEnabled() &&
    control.widgetId !== null &&
    window.grecaptcha &&
    typeof window.grecaptcha.reset === "function"
  ) {
    window.grecaptcha.reset(control.widgetId);
  }
  syncCaptchaButtons();
}

function captchaPayload(name) {
  return isCaptchaEnabled() ? { captchaToken: captchaToken(name) } : {};
}

async function loadCaptchaConfig() {
  if (DIRECT_FILE_MODE) {
    captchaConfig = { enabled: false, siteKey: "" };
    syncCaptchaButtons();
    return captchaConfig;
  }
  try {
    const data = await apiFetch(
      "/api/captcha/config",
      { timeoutMs: STATUS_FETCH_TIMEOUT_MS },
      activeApiBase ? [activeApiBase, ...API_BASE_CANDIDATES] : API_BASE_CANDIDATES,
    );
    captchaConfig = normalizeCaptchaConfig(data.captcha);
  } catch (error) {
    captchaConfig = { enabled: false, siteKey: "" };
  }
  await renderCaptchaControls();
  return captchaConfig;
}

function openAttachmentAuthPopup() {
  if (!attachmentAuthModal) {
    return;
  }

  if (attachmentAuthForm) {
    attachmentAuthForm.reset();
  }
  if (attachmentAuthMessage) {
    attachmentAuthMessage.textContent = "";
    attachmentAuthMessage.classList.remove("error");
  }
  resetCaptchaControl("attachment");
  attachmentAuthModal.hidden = false;
  document.body.classList.add("attachment-auth-open");
  queueCaptchaRender("attachment");
  window.setTimeout(() => {
    if (attachmentAuthPassword) {
      attachmentAuthPassword.focus();
    }
  }, 70);
}

function closeAttachmentAuthPopup() {
  if (!attachmentAuthModal || attachmentAuthModal.hidden) {
    return;
  }

  attachmentAuthModal.hidden = true;
  document.body.classList.remove("attachment-auth-open");
  if (attachmentAuthForm) {
    attachmentAuthForm.reset();
  }
  resetCaptchaControl("attachment");
  if (attachButton && !DIRECT_FILE_MODE) {
    attachButton.focus();
  }
}

function attachmentVerificationIsValid() {
  return Boolean(
    (currentAccount && currentAccount.attachmentsVerified) ||
      (attachmentVerificationToken && Date.now() < attachmentVerificationExpiresAt),
  );
}

function clearAttachmentVerification() {
  attachmentVerificationToken = "";
  attachmentVerificationExpiresAt = 0;
}

function setAttachmentAuthMessage(text = "", isError = false) {
  if (!attachmentAuthMessage) {
    return;
  }
  attachmentAuthMessage.textContent = text;
  attachmentAuthMessage.classList.toggle("error", isError);
}

function setAttachmentAuthBusy(busy) {
  if (!attachmentAuthForm) {
    return;
  }
  attachmentAuthForm.querySelectorAll("input, button").forEach((field) => {
    field.disabled = busy;
  });
  if (attachmentAuthOk) {
    if (!attachmentAuthOk.dataset.originalText) {
      attachmentAuthOk.dataset.originalText = attachmentAuthOk.textContent;
    }
    attachmentAuthOk.textContent = busy ? "Checking..." : attachmentAuthOk.dataset.originalText;
  }
}

function openVerifiedFilePicker() {
  if (!currentAccount) {
    clearSelectedAttachments();
    openAccountModal("sign-in");
    return;
  }
  if (!attachmentVerificationIsValid()) {
    openAttachmentAuthPopup();
    return;
  }
  fileInput.click();
}

async function handleAttachmentAuthSubmit(event) {
  event.preventDefault();
  if (!currentAccount || !attachmentAuthForm) {
    closeAttachmentAuthPopup();
    openAccountModal("sign-in");
    return;
  }
  const formData = new FormData(attachmentAuthForm);
  const password = String(formData.get("password") || "");
  if (!password || (isCaptchaEnabled() && !captchaToken("attachment"))) {
    setAttachmentAuthMessage(GENERIC_ERROR_MESSAGE, true);
    syncCaptchaButtons();
    return;
  }

  setAttachmentAuthBusy(true);
  setAttachmentAuthMessage();
  try {
    const data = await apiFetch(
      "/api/attachments/verify",
      {
        method: "POST",
        body: JSON.stringify({ password, ...captchaPayload("attachment") }),
        timeoutMs: STATUS_FETCH_TIMEOUT_MS,
      },
      activeApiBase ? [activeApiBase, ...API_BASE_CANDIDATES] : API_BASE_CANDIDATES,
    );
    if (!data.attachmentVerification || !data.attachmentVerification.token) {
      throw new Error(GENERIC_ERROR_MESSAGE);
    }
    if (data.account) {
      currentAccount = data.account;
      currentAccountStats = data.stats || currentAccountStats;
      updateAccountButton();
      renderAccountModalDetails();
    } else if (currentAccount) {
      currentAccount = { ...currentAccount, attachmentsVerified: true };
    }
    attachmentVerificationToken = data.attachmentVerification.token;
    attachmentVerificationExpiresAt = Number(data.attachmentVerification.expiresAt) || 0;
    closeAttachmentAuthPopup();
    fileInput.click();
  } catch (error) {
    clearAttachmentVerification();
    setAttachmentAuthMessage(GENERIC_ERROR_MESSAGE, true);
    resetCaptchaControl("attachment");
  } finally {
    setAttachmentAuthBusy(false);
    syncCaptchaButtons();
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
    renderAdminAccess();
    return;
  }

  accountButton.classList.remove("signed-in");
  accountStatusText.textContent = "Sign in to sync";
  renderAdminAccess();
}

function renderAdminAccess() {
  const visible = isCurrentAdmin();
  if (adminButton) {
    adminButton.hidden = !visible;
    adminButton.classList.toggle("active", activeView === "admin");
  }
  renderAdminRoleAccess();
  if (!visible && activeView === "admin") {
    setMainView("chat");
  }
}

function renderAdminRoleAccess() {
  const canManageAdmins = isCurrentOwnerAdmin();
  if (adminGrantForm) {
    adminGrantForm.hidden = !canManageAdmins;
  }
  if (adminRevokeForm) {
    adminRevokeForm.hidden = !canManageAdmins;
  }
}

function renderPlatformState() {
  const available = !isPlatformUnavailable();
  if (adminAvailabilityText) {
    adminAvailabilityText.textContent = available
      ? "Learny is accepting messages."
      : "Learny is paused for everyone.";
  }
  if (adminAvailabilityToggle) {
    adminAvailabilityToggle.checked = available;
  }
  if (adminAvailabilityLabel) {
    adminAvailabilityLabel.textContent = available ? "Available" : "Unavailable";
  }
}

function setMainView(view) {
  const nextView =
    view === "account"
      ? "account"
      : view === "admin" && isCurrentAdmin()
        ? "admin"
        : "chat";
  activeView = nextView;
  if (appShell) {
    appShell.classList.toggle("account-mode", nextView === "account");
  }
  if (mainArea) {
    mainArea.classList.toggle("admin-mode", nextView === "admin");
    mainArea.classList.toggle("account-mode", nextView === "account");
  }
  if (chatPanel) {
    chatPanel.hidden = nextView !== "chat";
  }
  if (adminPortal) {
    adminPortal.hidden = nextView !== "admin";
  }
  if (accountModal) {
    accountModal.hidden = nextView !== "account";
  }
  if (messageSearch) {
    messageSearch.hidden = nextView !== "chat";
  }
  if (adminButton) {
    adminButton.classList.toggle("active", nextView === "admin");
  }
  closeSidebarOnMobile();
  if (nextView === "admin") {
    loadAdminPortal();
  } else if (nextView === "chat" && messageInput && !DIRECT_FILE_MODE && !isPlatformUnavailable()) {
    messageInput.focus();
  }
}

function setAdminStatus(text = "", isError = false) {
  if (!adminStatusMessage) {
    return;
  }
  adminStatusMessage.textContent = text;
  adminStatusMessage.classList.toggle("error", isError);
}

function accountImageSource(account) {
  return account && typeof account.profilePicture === "string" && account.profilePicture.trim()
    ? account.profilePicture.trim()
    : PROFILE_ICON_PATH;
}

function adminAccountRateLimitPercent(account) {
  const explicitPercent = Number(account && account.rateLimitPercent);
  if (Number.isFinite(explicitPercent)) {
    return Math.max(0, Math.min(100, Math.round(explicitPercent)));
  }
  const rateLimit = account && account.rateLimit;
  if (!rateLimit || !Number.isFinite(rateLimit.limit) || rateLimit.limit <= 0) {
    return 100;
  }
  const remaining = Number.isFinite(rateLimit.remaining) ? rateLimit.remaining : rateLimit.limit;
  return Math.max(0, Math.min(100, Math.round((remaining / rateLimit.limit) * 100)));
}

function renderAdminAccountRow(account, { compact = false } = {}) {
  const row = document.createElement("article");
  row.className = "admin-account-row";

  const image = document.createElement("img");
  image.className = "admin-avatar";
  image.src = accountImageSource(account);
  image.alt = "";

  const copy = document.createElement("div");
  copy.className = "admin-account-copy";
  const name = document.createElement("strong");
  name.textContent = account.username || "Unknown";
  const meta = document.createElement("span");
  meta.textContent = compact
    ? `Seen ${formatDateTime(account.lastSeenAt)}`
    : `${account.chatCount || 0} chats - ${account.messageCount || 0} messages`;
  const badges = document.createElement("div");
  badges.className = "admin-badges";
  if (!compact) {
    const rateBadge = document.createElement("span");
    rateBadge.className = "admin-badge rate-limit";
    rateBadge.textContent = `${adminAccountRateLimitPercent(account)}% rate limit`;
    badges.append(rateBadge);
  }
  if (account.isAdmin) {
    const badge = document.createElement("span");
    badge.className = "admin-badge admin";
    badge.textContent = "Admin";
    badges.append(badge);
  }
  if (account.ban) {
    const badge = document.createElement("span");
    badge.className = "admin-badge banned";
    badge.textContent = "Banned";
    badges.append(badge);
  }
  copy.append(name, meta, badges);
  row.append(image, copy);

  if (!compact) {
    const actions = document.createElement("div");
    actions.className = "admin-row-actions";
    const actionButtons = [];
    if (isCurrentOwnerAdmin()) {
      actionButtons.push(
        createAdminMiniAction(account.isAdmin ? "Remove admin" : "Give admin", () =>
          submitAdminJson("/api/admin/role", {
            username: account.username,
            admin: !account.isAdmin,
          }),
        ),
      );
    }
    actionButtons.push(
      createAdminMiniAction(account.ban ? "Unban" : "Ban", () =>
        submitAdminJson(
          account.ban ? "/api/admin/unban" : "/api/admin/ban",
          account.ban
            ? { kind: "username", target: account.username }
            : { kind: "username", target: account.username, reason: "No reason." },
        ),
      ),
      createAdminMiniAction("Delete", () =>
        submitAdminJson("/api/admin/delete-account", { username: account.username }),
        true,
      ),
    );
    actions.append(...actionButtons);
    row.append(actions);
  }

  return row;
}

function createAdminMiniAction(text, onClick, danger = false) {
  const button = document.createElement("button");
  button.className = `admin-mini-action${danger ? " danger" : ""}`;
  button.type = "button";
  button.textContent = text;
  button.addEventListener("click", onClick);
  return button;
}

function renderAdminList(container, items, emptyText, renderer) {
  if (!container) {
    return;
  }
  container.replaceChildren();
  if (!Array.isArray(items) || items.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty-admin-list";
    empty.textContent = emptyText;
    container.append(empty);
    return;
  }
  items.forEach((item) => container.append(renderer(item)));
}

function renderAdminBanRow(ban) {
  const row = document.createElement("article");
  row.className = "admin-ban-row";
  const title = document.createElement("strong");
  title.textContent = `${ban.kind === "username" ? "@" : ""}${ban.target || "Unknown"}`;
  const meta = document.createElement("span");
  meta.textContent = `${formatDateTime(ban.createdAt)} - ${ban.reason || "No reason supplied."}`;
  const actions = document.createElement("div");
  actions.className = "admin-row-actions";
  actions.append(
    createAdminMiniAction("Unban", () =>
      submitAdminJson("/api/admin/unban", { kind: ban.kind, target: ban.target }),
    ),
  );
  row.append(title, meta, actions);
  return row;
}

function renderAdminPortal(data = adminPortalData) {
  const portal = data && data.adminPortal ? data.adminPortal : data;
  if (!portal || typeof portal !== "object") {
    return;
  }
  adminPortalData = portal;
  renderAdminRoleAccess();
  updatePlatform(portal.platform || DEFAULT_PLATFORM);
  const accounts = Array.isArray(portal.accounts) ? portal.accounts : [];
  const admins = Array.isArray(portal.admins) ? portal.admins : [];
  const bans = Array.isArray(portal.bans) ? portal.bans : [];

  if (adminAccountsCount) {
    adminAccountsCount.textContent = String(accounts.length);
  }
  if (adminAdminsCount) {
    adminAdminsCount.textContent = String(admins.length);
  }
  if (adminBansCount) {
    adminBansCount.textContent = String(bans.length);
  }

  renderAdminList(adminAccountsList, accounts, "No accounts yet", (account) =>
    renderAdminAccountRow(account),
  );
  renderAdminList(adminAdminsList, admins, "No admins yet", (account) =>
    renderAdminAccountRow(account, { compact: true }),
  );
  renderAdminList(adminBansList, bans, "No active bans", renderAdminBanRow);
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
  resetCaptchaControl("deleteAccount");
}

function renderAccountModalDetails() {
  renderAccountProfilePicture();

  if (!currentAccount) {
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
  if (accountModal) {
    accountModal.dataset.activeAccountView = nextView;
  }
  resetDeleteConfirmation();
  setAccountFormMessage(signInMessage);
  setAccountFormMessage(createAccountMessage);

  accountModalViews.forEach((node) => {
    node.hidden = node.dataset.accountView !== nextView;
  });
  setAccountModalCopy(nextView);
  if (nextView === "sign-in") {
    resetCaptchaControl("createAccount");
    queueCaptchaRender("signIn");
  } else if (nextView === "create-account") {
    resetCaptchaControl("signIn");
    queueCaptchaRender("createAccount");
  } else {
    resetCaptchaControl("signIn");
    resetCaptchaControl("createAccount");
  }
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
  } catch (error) {}
  renderAccountModalDetails();
}

function openAccountModal(view = currentAccount ? "myaccount" : "sign-in") {
  if (!accountModal) {
    return;
  }

  setMainView("account");
  showAccountView(view);
  window.setTimeout(() => {
    const firstInput = accountModal.querySelector("[data-account-view]:not([hidden]) input:not([hidden])");
    if (firstInput instanceof HTMLElement) {
      firstInput.focus();
    } else if (accountBackButton) {
      accountBackButton.focus();
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

  setMainView("chat");
  activeAccountView = "";
  accountModal.dataset.activeAccountView = "";
  resetDeleteConfirmation();
  if (messageInput && !DIRECT_FILE_MODE) {
    messageInput.focus();
  }
}

function clearSignedInLocalState() {
  currentAccount = null;
  currentAccountStats = null;
  serverChatsLoaded = false;
  clearAttachmentVerification();
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
              attachments: normalizeAttachmentMetas(message),
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
  } catch (error) {}
}

async function loadPlatformState({ scheduleNext = true } = {}) {
  if (DIRECT_FILE_MODE || currentBan) {
    return null;
  }
  try {
    const data = await apiFetch(
      "/api/platform",
      { timeoutMs: STATUS_FETCH_TIMEOUT_MS },
      activeApiBase ? [activeApiBase, ...API_BASE_CANDIDATES] : API_BASE_CANDIDATES,
    );
    if (data.platform) {
      updatePlatform(data.platform);
    }
    if (data.account) {
      currentAccount = data.account;
      updateAccountButton();
    }
    if (data.ban) {
      updateBanState(data.ban);
    }
    return data;
  } catch (error) {
    return null;
  } finally {
    if (scheduleNext && platformRefreshTimerId === null && !currentBan) {
      platformRefreshTimerId = window.setTimeout(() => {
        platformRefreshTimerId = null;
        loadPlatformState();
      }, 10000);
    }
  }
}

async function loadAdminPortal() {
  if (!isCurrentAdmin() || DIRECT_FILE_MODE) {
    return null;
  }
  setAdminStatus("Loading portal...");
  try {
    const data = await apiFetch(
      "/api/admin/portal",
      { timeoutMs: STATUS_FETCH_TIMEOUT_MS },
      activeApiBase ? [activeApiBase, ...API_BASE_CANDIDATES] : API_BASE_CANDIDATES,
    );
    renderAdminPortal(data);
    setAdminStatus("Portal refreshed.");
    return data;
  } catch (error) {
    setAdminStatus(GENERIC_ERROR_MESSAGE, true);
    return null;
  }
}

async function submitAdminJson(endpoint, payload) {
  if (!isCurrentAdmin() || DIRECT_FILE_MODE) {
    return null;
  }
  setAdminStatus("Saving change...");
  try {
    const data = await apiFetch(
      endpoint,
      {
        method: "POST",
        body: JSON.stringify(payload),
        timeoutMs: STATUS_FETCH_TIMEOUT_MS,
      },
      activeApiBase ? [activeApiBase, ...API_BASE_CANDIDATES] : API_BASE_CANDIDATES,
    );
    renderAdminPortal(data);
    await refreshAccountModalDetails();
    updateAccountButton();
    setAdminStatus("Change saved.");
    return data;
  } catch (error) {
    setAdminStatus(GENERIC_ERROR_MESSAGE, true);
    return null;
  }
}

function bindAdminForm(form, handler) {
  if (!form) {
    return;
  }
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    await handler(formData);
    form.reset();
  });
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
      clearAttachmentVerification();
      updateAccountButton();
      return accountData;
    }

    const previousUsername = currentAccount ? currentAccount.username : "";
    currentAccount = accountData.account;
    if (previousUsername && previousUsername !== currentAccount.username) {
      clearAttachmentVerification();
    }
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
    clearAttachmentVerification();
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
    ...chat.messages
      .flatMap((message) => normalizeAttachmentMetas(message))
      .map((attachment) => attachment.name),
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

function releaseLoadingScreen() {
  if (window.LearnyLoading && typeof window.LearnyLoading.release === "function") {
    window.LearnyLoading.release();
    return;
  }

  const loader = document.getElementById("loadingScreen");
  document.body.classList.remove("site-loading");
  document.body.classList.add("site-loaded");
  if (loader) {
    loader.remove();
  }
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
  if (activeView !== "chat") {
    setMainView("chat");
  }
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
  if (activeView !== "chat") {
    setMainView("chat");
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

function refreshChatTitle(chat) {
  const firstUserMessage = chat.messages.find((message) => message.speaker === "You");
  chat.title = firstUserMessage ? titleFromMessage(firstUserMessage.text) : "New chat";
}

function messageIndicesForTurn(chat, messageIndex) {
  if (!chat || !Number.isInteger(messageIndex) || messageIndex < 0) {
    return [];
  }
  const message = chat.messages[messageIndex];
  if (!message || message.speaker !== "You") {
    return [];
  }

  const indices = [messageIndex];
  const nextMessage = chat.messages[messageIndex + 1];
  if (nextMessage && nextMessage.speaker === "Learny") {
    indices.push(messageIndex + 1);
  }
  return indices;
}

async function resendEditedUserMessage(messageIndex, text) {
  const chat = getActiveChat();
  if (DIRECT_FILE_MODE || !chat || !Number.isInteger(messageIndex) || messageIndex < 0 || isSending) {
    return false;
  }
  const message = chat.messages[messageIndex];
  if (!message || message.speaker !== "You") {
    return false;
  }
  if (isRateLimited()) {
    renderRateLimit();
    openRateLimitPopup({ force: true });
    return false;
  }

  chat.messages = chat.messages.slice(0, messageIndex);
  chat.sessionId = createId("session");
  sessionId = chat.sessionId;
  localStorage.setItem(SESSION_KEY, sessionId);

  chat.updatedAt = Date.now();
  refreshChatTitle(chat);
  saveChats();
  if (currentAccount && serverChatsLoaded) {
    await syncChatsToServer();
  }

  addMessage({ speaker: "You", text, source: "sent" });
  renderChatList();
  renderActiveChat();
  askLearny(text, { addUserMessage: false });
  return true;
}

function startUserMessageEdit(node, messageIndex, originalText) {
  if (!node || !Number.isInteger(messageIndex) || isSending) {
    return;
  }

  const bubble = node.querySelector(".bubble");
  const textNode = node.querySelector(".bubble-text");
  if (!bubble || !textNode || node.classList.contains("is-editing")) {
    return;
  }

  const existingEdit = chatLog.querySelector(".message.is-editing");
  if (existingEdit && existingEdit !== node) {
    renderActiveChat();
    const nextNode = chatLog.querySelector(`.message[data-message-index="${messageIndex}"]`);
    if (nextNode) {
      startUserMessageEdit(nextNode, messageIndex, originalText);
    }
    return;
  }

  node.classList.add("is-editing");

  const form = document.createElement("form");
  form.className = "message-edit-form";

  const textarea = document.createElement("textarea");
  textarea.className = "message-edit-input";
  textarea.name = "editedMessage";
  textarea.maxLength = 1200;
  textarea.rows = Math.min(8, Math.max(2, originalText.split(/\r?\n/).length));
  textarea.value = originalText;
  textarea.setAttribute("aria-label", "Edit message");

  const actions = document.createElement("div");
  actions.className = "message-edit-actions";

  const cancelButton = document.createElement("button");
  cancelButton.className = "message-edit-cancel";
  cancelButton.type = "button";
  cancelButton.title = "Cancel";
  cancelButton.setAttribute("aria-label", "Cancel edit");
  const cancelIcon = document.createElement("img");
  cancelIcon.className = "ui-icon message-edit-action-icon";
  cancelIcon.src = X_ICON_PATH;
  cancelIcon.alt = "";
  cancelIcon.setAttribute("aria-hidden", "true");
  cancelButton.append(cancelIcon);

  const saveButton = document.createElement("button");
  saveButton.className = "message-edit-save";
  saveButton.type = "submit";
  saveButton.title = "Save and resend";
  saveButton.setAttribute("aria-label", "Save and resend");
  const saveIcon = document.createElement("img");
  saveIcon.className = "ui-icon message-edit-action-icon";
  saveIcon.src = CHECK_ICON_PATH;
  saveIcon.alt = "";
  saveIcon.setAttribute("aria-hidden", "true");
  saveButton.append(saveIcon);

  actions.append(cancelButton, saveButton);
  form.append(textarea, actions);

  function closeEditor() {
    renderActiveChat();
  }

  cancelButton.addEventListener("click", closeEditor);
  textarea.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      closeEditor();
    }
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      form.requestSubmit();
    }
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const nextText = textarea.value.trim();
    if (!nextText) {
      textarea.focus();
      return;
    }
    saveButton.disabled = true;
    cancelButton.disabled = true;
    await resendEditedUserMessage(messageIndex, nextText);
  });

  textNode.replaceWith(form);
  window.setTimeout(() => {
    textarea.focus();
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);
  }, 40);
}

function deleteMessageTurn(messageIndex) {
  const chat = getActiveChat();
  const indices = messageIndicesForTurn(chat, messageIndex);
  if (indices.length === 0) {
    return;
  }

  const deletingLatestPendingMessage =
    isSending && indices.includes(chat.messages.length - 1) && indices.length === 1;
  if (deletingLatestPendingMessage) {
    return;
  }

  const nodes = [...chatLog.querySelectorAll(".message")].filter((node) =>
    indices.includes(Number(node.dataset.messageIndex)),
  );
  nodes.forEach((node) => node.classList.add("is-deleting"));

  window.setTimeout(() => {
    chat.messages = chat.messages.filter((_, index) => !indices.includes(index));
    chat.updatedAt = Date.now();
    refreshChatTitle(chat);
    saveChats();
    renderChatList();
    renderActiveChat();
  }, MESSAGE_DELETE_DURATION_MS);
}

function appendLearnyFooter(bubble, text, thoughtSeconds) {
  const footer = document.createElement("div");
  footer.className = "message-footer";

  const thought = document.createElement("span");
  thought.className = "thought-time";
  thought.textContent = `Thought for ${formatThoughtSeconds(thoughtSeconds)} seconds`;

  footer.append(thought, createIconCopyButton(text));
  bubble.append(footer);
}

function appendUserFooter(bubble, text, messageIndex, node) {
  if (!Number.isInteger(messageIndex)) {
    return;
  }

  const footer = document.createElement("div");
  footer.className = "message-footer user-message-footer";
  footer.append(
    createTextCopyButton(text),
    createTextActionButton("Edit", "message-edit-button", () =>
      startUserMessageEdit(node, messageIndex, text),
      EDIT_ICON_PATH,
    ),
    createTextActionButton(
      "Delete",
      "message-delete-button",
      () => deleteMessageTurn(messageIndex),
      DELETE_ICON_PATH,
    ),
  );
  bubble.append(footer);
}

function createMessageAttachment(attachment) {
  const meta = normalizeAttachmentMeta(attachment);
  if (!meta) {
    return null;
  }

  const wrapper = document.createElement("div");
  wrapper.className = "message-attachment";

  const icon = document.createElement("span");
  icon.className = "message-attachment-icon";
  icon.textContent = meta.extension || "file";

  const copy = document.createElement("span");
  copy.className = "message-attachment-copy";

  const name = document.createElement("strong");
  name.className = "message-attachment-name";
  name.textContent = meta.name;

  const detail = document.createElement("small");
  detail.className = "message-attachment-meta";
  detail.textContent = `${meta.extension.toUpperCase()} - ${formatFileSize(meta.size)}`;

  copy.append(name, detail);
  wrapper.append(icon, copy);
  return wrapper;
}

function displayMessage(
  { speaker, text, source = "", thoughtSeconds = null, attachments = [], attachment = null },
  {
    animateWords: shouldAnimateWords = false,
    messageIndex = null,
    autoScroll = true,
    smoothScroll = true,
  } = {},
) {
  setEmptyState(false);
  const node = messageTemplate.content.firstElementChild.cloneNode(true);
  node.classList.add(speaker === "You" ? "user" : "learny");
  if (Number.isInteger(messageIndex)) {
    node.dataset.messageIndex = String(messageIndex);
  }
  const attachmentMetas = normalizeAttachmentMetas({ attachments, attachment });
  node.dataset.searchText = `${speaker} ${source} ${text} ${attachmentMetas
    .map((meta) => meta.name)
    .join(" ")}`.toLowerCase();
  node.querySelector(".speaker").textContent = speaker;
  node.querySelector(".source").textContent = source === "error" ? "" : source;
  const bubble = node.querySelector(".bubble");
  bubble.dataset.glitch = text.replace(/\s+/g, " ").trim().slice(0, 240);
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
  if (speaker === "You") {
    attachmentMetas.forEach((attachmentMeta) => {
      const attachmentNode = createMessageAttachment(attachmentMeta);
      if (attachmentNode) {
        bubble.append(attachmentNode);
      }
    });
  }

  if (speaker === "Learny") {
    appendLearnyFooter(bubble, text, thoughtSeconds);
  } else {
    appendUserFooter(bubble, text, messageIndex, node);
  }

  chatLog.append(node);
  updateMessageSearch();
  if (autoScroll) {
    scrollChatToBottom({ smooth: smoothScroll });
  }
  if (pinnedScrollDuration > 0) {
    keepChatPinnedToBottom(pinnedScrollDuration);
  }
  return node;
}

function saveMessage(message) {
  const chat = ensureActiveChat();
  const savedMessage = {
    ...message,
    createdAt: Number.isFinite(message.createdAt) ? message.createdAt : Date.now(),
  };
  chat.messages.push(savedMessage);
  const messageIndex = chat.messages.length - 1;
  chat.updatedAt = Date.now();

  if (message.speaker === "You" && chat.title === "New chat") {
    chat.title = titleFromMessage(message.text);
  }

  saveChats();
  renderChatList();
  return messageIndex;
}

function addMessage(message, { persist = true, animateWords = false } = {}) {
  if (persist) {
    const messageIndex = saveMessage(message);
    return displayMessage(message, { animateWords, messageIndex });
  }
  return displayMessage(message, { animateWords });
}

function renderActiveChat() {
  clearMessages();
  const chat = getActiveChat();
  if (!chat || chat.messages.length === 0) {
    setEmptyState(true);
    updateMessageSearch();
    return;
  }
  chat.messages.forEach((message, index) =>
    displayMessage(message, { messageIndex: index, autoScroll: false }),
  );
  updateMessageSearch();
  keepChatPinnedToBottom(1400);
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
    if (attachButton) {
      attachButton.disabled = true;
    }
    return;
  }

  createChat();
  messageInput.value = "";
  messageInput.disabled = false;
  sendButton.disabled = false;
  if (attachButton) {
    attachButton.disabled = false;
  }
  clearSelectedAttachments();
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
    "rateLimit" in data ||
    "platform" in data ||
    "ban" in data ||
    "adminPortal" in data ||
    "captcha" in data ||
    "attachmentVerification" in data
  );
}

function consumeApiState(data) {
  if (!data || typeof data !== "object") {
    return;
  }
  if (data.platform) {
    updatePlatform(data.platform);
  }
  if (data.ban) {
    updateBanState(data.ban);
  }
  if (data.rateLimit) {
    updateRateLimit(data.rateLimit);
  }
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
      const hasFormDataBody =
        typeof FormData !== "undefined" && fetchOptions.body instanceof FormData;
      if (fetchOptions.body !== undefined && !hasFormDataBody && !("Content-Type" in requestHeaders)) {
        requestHeaders["Content-Type"] = "application/json";
      }
      if (sessionId && !("X-Learny-Session" in requestHeaders)) {
        requestHeaders["X-Learny-Session"] = sessionId;
      }
      if (rateLimitSessionId && !("X-Learny-Rate-Session" in requestHeaders)) {
        requestHeaders["X-Learny-Rate-Session"] = rateLimitSessionId;
      }
      const timeZone = clientTimeZone();
      if (timeZone && !("X-Learny-Time-Zone" in requestHeaders)) {
        requestHeaders["X-Learny-Time-Zone"] = timeZone;
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
        consumeApiState(data);
        const responseError = new Error(GENERIC_ERROR_MESSAGE);
        responseError.status = response.status;
        responseError.data = data;
        responseError.retryable = data && typeof data === "object" ? data.retryable : undefined;
        responseError.stopFallback = [401, 403, 429].includes(response.status) || Boolean(data && data.ban);
        throw responseError;
      }
      if (!isApiResponseData(data)) {
        throw new Error(GENERIC_ERROR_MESSAGE);
      }

      activeApiBase = apiBase;
      consumeApiState(data);
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

function createAskRequestBody(message, chat, attachments) {
  const selectedFiles = Array.isArray(attachments) ? attachments : [];
  if (selectedFiles.length > 0) {
    const formData = new FormData();
    formData.append("message", message);
    formData.append("sessionId", sessionId);
    formData.append("chatId", chat.id);
    if (attachmentVerificationToken) {
      formData.append("attachmentVerificationToken", attachmentVerificationToken);
    }
    selectedFiles.forEach((attachment) => {
      if (attachment && attachment.file) {
        formData.append("attachments", attachment.file, attachment.file.name);
      }
    });
    return formData;
  }

  return JSON.stringify({ message, sessionId, chatId: chat.id });
}

async function askLearny(message, { addUserMessage = true, attachments = [] } = {}) {
  if (DIRECT_FILE_MODE) {
    return;
  }

  if (isPlatformUnavailable()) {
    syncComposerAvailability();
    return;
  }

  if (isRateLimited()) {
    renderRateLimit();
    openRateLimitPopup({ force: true });
    return;
  }

  const chat = ensureActiveChat();
  sessionId = chat.sessionId;
  if (addUserMessage) {
    addMessage({
      speaker: "You",
      text: message,
      source: "sent",
      attachments: attachments.map((attachment) => attachment.meta).filter(Boolean),
    });
  }

  const typing = addTyping();
  const thoughtStartedAt = performance.now();
  isSending = true;
  sendButton.disabled = true;
  messageInput.disabled = true;
  if (attachButton) {
    attachButton.disabled = true;
  }

  let attempt = 0;
  let completed = false;
  try {
    while (!completed) {
      try {
        const data = await apiFetch(
          "/api/ask",
          {
            method: "POST",
            body: createAskRequestBody(message, chat, attachments),
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
        completed = true;
      } catch (error) {
        if (error && error.data && error.data.platform && error.data.platform.available === false) {
          typing.remove();
          updatePlatform(error.data.platform);
          completed = true;
          continue;
        }

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

        if (error && error.retryable === false) {
          typing.remove();
          addMessage({
            speaker: "Learny",
            text: GENERIC_ERROR_MESSAGE,
            source: "error",
            thoughtSeconds: (performance.now() - thoughtStartedAt) / 1000,
          });
          completed = true;
          continue;
        }

        attempt += 1;
        await sleep(askRetryDelay(attempt));
      }
    }
  } finally {
    isSending = false;
    syncComposerAvailability();
    if (!isRateLimited() && !isPlatformUnavailable()) {
      messageInput.focus();
    }
  }
}

async function handleAccountAuthSubmit(form, messageNode, endpoint, captchaName) {
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
  if (isCaptchaEnabled() && !captchaToken(captchaName)) {
    syncCaptchaButtons();
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
        body: JSON.stringify({ username, password, ...captchaPayload(captchaName) }),
        timeoutMs: STATUS_FETCH_TIMEOUT_MS,
      },
      activeApiBase ? [activeApiBase, ...API_BASE_CANDIDATES] : API_BASE_CANDIDATES,
    );
    if (!data.authenticated || !data.account) {
      throw new Error(GENERIC_ERROR_MESSAGE);
    }
    currentAccount = data.account;
    currentAccountStats = data.stats || null;
    clearAttachmentVerification();
    form.reset();
    await loadAccountAndChats();
    await loadRateLimit();
    openAccountModal("myaccount");
  } catch (error) {
    setAccountFormMessage(messageNode, GENERIC_ERROR_MESSAGE, true);
  } finally {
    setAuthFormBusy(form, false);
    resetCaptchaControl(captchaName);
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
  } catch (error) {} finally {
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
  } catch (error) {} finally {
    event.target.value = "";
    setProfilePictureButtonBusy(false);
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
  } catch (error) {} finally {
    clearSignedInLocalState();
    clearSelectedAttachments();
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
  if (isCaptchaEnabled() && !captchaToken("deleteAccount")) {
    syncCaptchaButtons();
    return;
  }

  accountDeleteConfirmButton.disabled = true;
  accountDeleteConfirmButton.textContent = "Deleting...";
  try {
    const data = await apiFetch(
      "/api/accounts/delete",
      {
        method: "POST",
        body: JSON.stringify({ ...captchaPayload("deleteAccount") }),
        timeoutMs: STATUS_FETCH_TIMEOUT_MS,
      },
      activeApiBase ? [activeApiBase, ...API_BASE_CANDIDATES] : API_BASE_CANDIDATES,
    );
    if (!data.deleted) {
      throw new Error(GENERIC_ERROR_MESSAGE);
    }
    clearSignedInLocalState();
    clearSelectedAttachments();
    await loadRateLimit();
    openAccountModal("sign-in");
  } catch (error) {} finally {
    accountDeleteConfirmButton.disabled = false;
    accountDeleteConfirmButton.textContent = "Delete forever";
    resetCaptchaControl("deleteAccount");
  }
}

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  if (isSending) {
    return;
  }
  if (isPlatformUnavailable()) {
    syncComposerAvailability();
    return;
  }

  const message = messageInput.value.trim();
  if (!message) {
    messageInput.focus();
    return;
  }
  if (isRateLimited()) {
    renderRateLimit();
    openRateLimitPopup();
    return;
  }
  if (!currentAccount && selectedAttachments.length > 0) {
    clearSelectedAttachments();
    openAccountModal("sign-in");
    return;
  }
  if (selectedAttachments.length > 0 && !attachmentVerificationIsValid()) {
    openAttachmentAuthPopup();
    return;
  }
  const attachments = [...selectedAttachments];
  messageInput.value = "";
  clearSelectedAttachments();
  askLearny(message, { attachments });
});

if (attachButton && fileInput) {
  attachButton.addEventListener("click", () => {
    if (isSending || DIRECT_FILE_MODE) {
      return;
    }
    if (!currentAccount) {
      clearSelectedAttachments();
      openAccountModal("sign-in");
      return;
    }
    openVerifiedFilePicker();
  });

  fileInput.addEventListener("change", (event) => {
    const files = event.target.files ? Array.from(event.target.files) : [];
    if (!currentAccount) {
      clearSelectedAttachments();
      openAccountModal("sign-in");
      return;
    }
    if (!attachmentVerificationIsValid()) {
      clearSelectedAttachments();
      openAttachmentAuthPopup();
      return;
    }
    if (files.length === 0) {
      return;
    }
    addSelectedAttachments(files);
    messageInput.focus();
  });
}

if (addChatButton) {
  addChatButton.addEventListener("click", resetChat);
}

if (accountButton) {
  accountButton.addEventListener("click", (event) => {
    event.preventDefault();
    openAccountModal(currentAccount ? "myaccount" : "sign-in");
  });
}

if (adminButton) {
  adminButton.addEventListener("click", () => setMainView("admin"));
}

if (adminAvailabilityToggle) {
  adminAvailabilityToggle.addEventListener("change", () => {
    submitAdminJson("/api/admin/platform", { available: adminAvailabilityToggle.checked });
  });
}

bindAdminForm(adminBanUsernameForm, (formData) =>
  submitAdminJson("/api/admin/ban", {
    kind: "username",
    target: String(formData.get("username") || "").trim(),
    reason: String(formData.get("reason") || "").trim(),
  }),
);

bindAdminForm(adminUnbanUsernameForm, (formData) =>
  submitAdminJson("/api/admin/unban", {
    kind: "username",
    target: String(formData.get("username") || "").trim(),
  }),
);

bindAdminForm(adminBanIpForm, (formData) =>
  submitAdminJson("/api/admin/ban", {
    kind: "ip",
    target: String(formData.get("ip") || "").trim(),
    reason: String(formData.get("reason") || "").trim(),
  }),
);

bindAdminForm(adminUnbanIpForm, (formData) =>
  submitAdminJson("/api/admin/unban", {
    kind: "ip",
    target: String(formData.get("ip") || "").trim(),
  }),
);

bindAdminForm(adminDeleteAccountForm, (formData) =>
  submitAdminJson("/api/admin/delete-account", {
    username: String(formData.get("username") || "").trim(),
  }),
);

bindAdminForm(adminResetRateLimitForm, (formData) =>
  submitAdminJson("/api/admin/rate-limit/reset", {
    username: String(formData.get("username") || "").trim(),
  }),
);

bindAdminForm(adminGrantForm, (formData) =>
  submitAdminJson("/api/admin/role", {
    username: String(formData.get("username") || "").trim(),
    admin: true,
  }),
);

bindAdminForm(adminRevokeForm, (formData) =>
  submitAdminJson("/api/admin/role", {
    username: String(formData.get("username") || "").trim(),
    admin: false,
  }),
);

document.querySelectorAll("[data-open-account-view]").forEach((button) => {
  button.addEventListener("click", () => {
    openAccountModal(button.dataset.openAccountView || "sign-in");
  });
});

if (accountBackButton) {
  accountBackButton.addEventListener("click", () => closeAccountModal());
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

if (attachmentAuthBackdrop) {
  attachmentAuthBackdrop.addEventListener("click", closeAttachmentAuthPopup);
}

if (attachmentAuthClose) {
  attachmentAuthClose.addEventListener("click", closeAttachmentAuthPopup);
}

if (attachmentAuthPassword) {
  attachmentAuthPassword.addEventListener("input", syncCaptchaButtons);
}

if (attachmentAuthForm) {
  attachmentAuthForm.addEventListener("submit", handleAttachmentAuthSubmit);
}

if (signInForm) {
  signInForm.addEventListener("submit", (event) => {
    event.preventDefault();
    handleAccountAuthSubmit(signInForm, signInMessage, "/api/accounts/sign-in", "signIn");
  });
}

if (createAccountForm) {
  createAccountForm.addEventListener("submit", (event) => {
    event.preventDefault();
    handleAccountAuthSubmit(createAccountForm, createAccountMessage, "/api/accounts/create", "createAccount");
  });
}

if (accountProfilePictureButton) {
  accountProfilePictureButton.addEventListener("click", handleAccountProfilePictureButton);
}

if (accountProfilePictureInput) {
  accountProfilePictureInput.addEventListener("change", handleAccountProfilePictureInputChange);
}

if (accountSignOutButton) {
  accountSignOutButton.addEventListener("click", handleAccountSignOut);
}

if (accountDeleteButton) {
  accountDeleteButton.addEventListener("click", () => {
    if (accountDeleteConfirm) {
      accountDeleteConfirm.hidden = false;
      queueCaptchaRender("deleteAccount");
      syncCaptchaButtons();
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
    if (attachmentAuthModal && !attachmentAuthModal.hidden) {
      closeAttachmentAuthPopup();
      return;
    }
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

showWelcomeHeading();
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
renderPlatformState();
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
loadPlatformState();
loadRateLimit();
loadCaptchaConfig();
releaseLoadingScreen();
