const pageName = document.body.dataset.accountPage || "";
const starField = document.querySelector("#starField");
const API_BASE_CANDIDATES = [
  "",
  "https://learny-ai-adamsrealm1.wasmer.app",
  "https://learny-ai.wasmer.app",
];
const STATUS_FETCH_TIMEOUT_MS = 8000;
const GENERIC_ERROR_MESSAGE = "Something went wrong. Try again later.";

let activeApiBase = "";

function createAccountStars() {
  if (!starField) {
    return;
  }

  const fragment = document.createDocumentFragment();
  const starCount = window.innerWidth < 700 ? 190 : 320;
  starField.replaceChildren();
  for (let index = 0; index < starCount; index += 1) {
    const star = document.createElement("span");
    const angle = Math.random() * Math.PI * 2;
    const travel = 6 + Math.random() * 18;
    const duration = 280 + Math.random() * 520;
    const size = 0.65 + Math.random() * 1.05;
    const opacity = 0.18 + Math.random() * 0.54;
    star.className = "star";
    star.style.setProperty("--x", `${Math.random() * 100}vw`);
    star.style.setProperty("--y", `${Math.random() * 100}vh`);
    star.style.setProperty("--travel-x", `${Math.cos(angle) * travel}vw`);
    star.style.setProperty("--travel-y", `${Math.sin(angle) * travel}vh`);
    star.style.setProperty("--size", `${size.toFixed(2)}px`);
    star.style.setProperty("--opacity", opacity.toFixed(2));
    star.style.setProperty("--glow", `${(3 + Math.random() * 7).toFixed(2)}px`);
    star.style.setProperty("--glow-opacity", (opacity * 0.42).toFixed(2));
    star.style.setProperty("--duration", `${duration.toFixed(1)}s`);
    star.style.setProperty("--delay", `${(-Math.random() * duration).toFixed(1)}s`);
    fragment.append(star);
  }
  starField.append(fragment);
}

function apiUrl(apiBase, path) {
  return `${apiBase}${path}`;
}

async function apiFetch(path, options = {}, apiBases = [activeApiBase]) {
  const { timeoutMs = STATUS_FETCH_TIMEOUT_MS, headers = {}, ...fetchOptions } = options;
  const basesToTry = [...new Set(apiBases.filter((base) => typeof base === "string"))];
  if (basesToTry.length === 0) {
    basesToTry.push("");
  }

  let lastError = null;
  for (const apiBase of basesToTry) {
    const controller =
      timeoutMs > 0 && "AbortController" in window ? new AbortController() : null;
    const timeoutId = controller ? window.setTimeout(() => controller.abort(), timeoutMs) : null;

    try {
      const response = await fetch(apiUrl(apiBase, path), {
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...headers,
        },
        ...fetchOptions,
        ...(controller ? { signal: controller.signal } : {}),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || data.error) {
        throw new Error(GENERIC_ERROR_MESSAGE);
      }
      activeApiBase = apiBase;
      return data;
    } catch (error) {
      lastError = error;
    } finally {
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId);
      }
    }
  }

  throw lastError || new Error(GENERIC_ERROR_MESSAGE);
}

function setFormMessage(text, isError = false) {
  const message = document.querySelector("#formMessage");
  if (!message) {
    return;
  }
  message.textContent = text;
  message.classList.toggle("error", isError);
}

function setFormBusy(form, busy) {
  const button = form.querySelector("button[type='submit']");
  form.querySelectorAll("input, button").forEach((field) => {
    field.disabled = busy;
  });
  if (button) {
    button.textContent = busy ? "Working..." : button.dataset.originalText || button.textContent;
  }
}

function accountInitial(username) {
  return String(username || "L").trim().slice(0, 1).toUpperCase() || "L";
}

function formatDate(timestamp) {
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

async function loadMyAccount() {
  const dashboard = document.querySelector("#accountDashboard");
  const signedOutPanel = document.querySelector("#signedOutPanel");
  const headline = document.querySelector("#accountHeadline");
  const subhead = document.querySelector("#accountSubhead");

  try {
    const data = await apiFetch("/api/account", {}, API_BASE_CANDIDATES);
    if (!data.authenticated || !data.account) {
      if (headline) headline.textContent = "Account sync is waiting.";
      if (subhead) subhead.textContent = "Sign in or create an account to store Learny chats.";
      if (signedOutPanel) signedOutPanel.hidden = false;
      return;
    }

    const { account, stats = {} } = data;
    if (headline) headline.textContent = "Your Learny account is ready.";
    if (subhead) subhead.textContent = "Chats and sessions are connected to the local database.";
    if (dashboard) dashboard.hidden = false;

    const avatar = document.querySelector("#accountAvatar");
    const username = document.querySelector("#accountUsername");
    const created = document.querySelector("#accountCreated");
    const chatCount = document.querySelector("#chatCount");
    const messageCount = document.querySelector("#messageCount");
    const sessionCount = document.querySelector("#sessionCount");

    if (avatar) avatar.textContent = accountInitial(account.username);
    if (username) username.textContent = account.username;
    if (created) created.textContent = formatDate(account.createdAt);
    if (chatCount) chatCount.textContent = String(stats.chats || 0);
    if (messageCount) messageCount.textContent = String(stats.messages || 0);
    if (sessionCount) sessionCount.textContent = String(stats.sessions || 0);
  } catch (error) {
    if (headline) headline.textContent = GENERIC_ERROR_MESSAGE;
    if (subhead) subhead.textContent = "";
  }
}

function wireAuthForm(form, endpoint) {
  if (!form) {
    return;
  }
  const button = form.querySelector("button[type='submit']");
  if (button) {
    button.dataset.originalText = button.textContent;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const username = String(formData.get("username") || "").trim();
    const password = String(formData.get("password") || "");
    if (!username || !password) {
      setFormMessage(GENERIC_ERROR_MESSAGE, true);
      return;
    }

    setFormBusy(form, true);
    setFormMessage("");
    try {
      await apiFetch(
        endpoint,
        {
          method: "POST",
          body: JSON.stringify({ username, password }),
        },
        API_BASE_CANDIDATES,
      );
      window.location.href = "/myaccount";
    } catch (error) {
      setFormMessage(GENERIC_ERROR_MESSAGE, true);
      setFormBusy(form, false);
    }
  });
}

function wireSignOut() {
  const button = document.querySelector("#signOutButton");
  if (!button) {
    return;
  }

  button.addEventListener("click", async () => {
    button.disabled = true;
    button.textContent = "Signing out...";
    try {
      await apiFetch(
        "/api/accounts/sign-out",
        { method: "POST", body: JSON.stringify({}) },
        API_BASE_CANDIDATES,
      );
    } catch (error) {
      // Keep navigation deterministic and avoid leaking raw error details.
    }
    window.location.href = "/sign-in";
  });
}

createAccountStars();

if (pageName === "myaccount") {
  loadMyAccount();
  wireSignOut();
} else if (pageName === "sign-in") {
  wireAuthForm(document.querySelector("#signInForm"), "/api/accounts/sign-in");
} else if (pageName === "create-account") {
  wireAuthForm(document.querySelector("#createAccountForm"), "/api/accounts/create");
}
