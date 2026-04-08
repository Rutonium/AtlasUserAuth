const form = document.getElementById("login-form");
const message = document.getElementById("login-message");
const employeeInput = document.getElementById("employee-id-input");
const employeeDatalist = document.getElementById("employee-suggestions");
const sessionPanel = document.getElementById("session-panel");
const sessionSummary = document.getElementById("session-summary");
const continueLink = document.getElementById("continue-link");
const adminLink = document.getElementById("admin-link");
const logoutExistingBtn = document.getElementById("logout-existing-btn");
const launcherPanel = document.getElementById("app-launcher-panel");
const launcherCopy = document.getElementById("app-launcher-copy");
const launcherBadge = document.getElementById("app-launcher-badge");
const launcherCards = Array.from(document.querySelectorAll("[data-app-target]"));

let lookupTimer = null;
let selectedLauncherTarget = "";
let selectedLauncherLabel = "";

function getCookie(name) {
  const cookie = document.cookie
    .split(";")
    .map((v) => v.trim())
    .find((v) => v.startsWith(name + "="));
  if (!cookie) return "";
  return decodeURIComponent(cookie.slice(name.length + 1));
}

function resolvePostLoginTarget() {
  const params = new URLSearchParams(window.location.search);
  const requested =
    params.get("return_to") ||
    params.get("next") ||
    params.get("redirect") ||
    selectedLauncherTarget ||
    "";
  if (!requested) return "admin";

  // Allow only same-origin redirects.
  if (requested.startsWith("/")) return requested;
  try {
    const parsed = new URL(requested, window.location.origin);
    if (parsed.origin !== window.location.origin) return "admin";
    return `${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch {
    return "admin";
  }
}

function hasExplicitReturnTarget() {
  const params = new URLSearchParams(window.location.search);
  return Boolean(params.get("return_to") || params.get("next") || params.get("redirect"));
}

function shouldShowLauncher() {
  return Boolean(launcherPanel) && hasExplicitReturnTarget() === false;
}

function updateLauncherSelection(target, label) {
  selectedLauncherTarget = target || "";
  selectedLauncherLabel = label || "";

  launcherCards.forEach((card) => {
    card.classList.toggle("is-selected", card.dataset.appTarget === selectedLauncherTarget);
  });

  if (launcherBadge) {
    launcherBadge.textContent = selectedLauncherLabel
      ? `Selected: ${selectedLauncherLabel}`
      : "No destination selected";
  }

  if (launcherCopy) {
    launcherCopy.textContent = selectedLauncherLabel
      ? `After sign-in, continue directly to ${selectedLauncherLabel}.`
      : "Pick an Atlas app to open after sign-in.";
  }
}

function setLauncherEnabled(enabled) {
  launcherCards.forEach((card) => {
    card.classList.toggle("is-live-link", enabled);
  });
}

function initializeLauncher() {
  if (!shouldShowLauncher()) return;
  launcherPanel?.classList.remove("hidden");
  setLauncherEnabled(false);

  launcherCards.forEach((card) => {
    card.addEventListener("click", () => {
      const target = card.dataset.appTarget || "";
      const label = card.dataset.appLabel || card.dataset.appKey || "the selected app";

      if (form?.classList.contains("hidden")) {
        if (target) window.location.href = target;
        return;
      }

      updateLauncherSelection(target, label);
      message.textContent = `After sign-in, you will be sent to ${label}.`;
      message.style.color = "#0a5f73";
    });
  });
}

async function loginApi(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const method = (options.method || "GET").toUpperCase();
  if (["GET", "HEAD", "OPTIONS"].includes(method) === false) {
    headers["X-CSRF-Token"] = getCookie("atlas_auth_csrf");
  }
  const response = await fetch(path, {
    ...options,
    headers,
    credentials: "include",
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || "Request failed");
  }
  return response.json().catch(() => ({}));
}

function showSessionState(me) {
  form?.classList.add("hidden");
  sessionPanel?.classList.remove("hidden");
  logoutExistingBtn?.classList.remove("hidden");
  if (shouldShowLauncher()) {
    launcherPanel?.classList.remove("hidden");
    setLauncherEnabled(true);
  }

  const target = resolvePostLoginTarget();
  const hasRequestedTarget = target !== "admin";
  if (sessionSummary) {
    const role = me.role ? `Role: ${me.role}` : "No app role selected";
    sessionSummary.textContent = `Signed in as ${me.name || me.employee_id}. ${role}.`;
  }
  if (continueLink) {
    continueLink.href = target;
    continueLink.textContent = hasRequestedTarget ? "Continue to app" : "Continue";
    continueLink.classList.toggle("hidden", false);
  }
  if (adminLink) {
    adminLink.textContent = me.is_admin ? "Open admin page" : "Admin access required";
    adminLink.classList.toggle("is-disabled", !me.is_admin);
    if (!me.is_admin) adminLink.setAttribute("aria-disabled", "true");
    else adminLink.removeAttribute("aria-disabled");
  }

  message.textContent = hasRequestedTarget
    ? "You are already signed in. Continue to the requested app when you are ready."
    : me.is_admin
      ? "You are already signed in. You can continue to the admin dashboard."
      : "You are already signed in. No return destination was provided, so stay here or continue into an app-specific link.";
  message.style.color = "#157347";
}

async function checkExistingSession() {
  const bouncedNotice = sessionStorage.getItem("atlas_auth_notice");
  if (bouncedNotice) {
    message.textContent = bouncedNotice;
    message.style.color = "#b42318";
    sessionStorage.removeItem("atlas_auth_notice");
  }
  try {
    const me = await loginApi("api/auth/me?appKey=atlas_user_auth_admin");
    if (me?.authenticated) {
      showSessionState(me);
    }
  } catch {
    // Not signed in yet. The normal login form should remain visible.
  }
}

function scoreEmployee(item, query) {
  const q = query.toLowerCase().trim();
  const id = String(item.employee_id || "");
  const name = String(item.name || "").toLowerCase();
  if (!q) return 9999;
  if (id === q) return 0;
  if (id.startsWith(q)) return 1;
  if (name.startsWith(q)) return 2;
  if (id.includes(q)) return 3;
  if (name.includes(q)) return 4;
  return 10;
}

async function lookupEmployees(query) {
  if (!employeeDatalist) return;
  const q = String(query || "").trim();
  if (q.length < 1) {
    employeeDatalist.innerHTML = "";
    return;
  }
  try {
    const resp = await fetch(`api/auth/employees/public-search?q=${encodeURIComponent(q)}`, {
      credentials: "include",
    });
    if (resp.ok === false) return;
    const data = await resp.json();
    const items = Array.isArray(data.items) ? data.items : [];
    items.sort((a, b) => scoreEmployee(a, q) - scoreEmployee(b, q));

    employeeDatalist.innerHTML = "";
    items.slice(0, 12).forEach((item) => {
      const id = String(item.employee_id || "");
      const name = String(item.name || "");
      const option = document.createElement("option");
      option.value = id;
      option.label = `${name} (${id})`;
      employeeDatalist.appendChild(option);
    });
  } catch {
    // silent: suggestions are best-effort helper only
  }
}

employeeInput?.addEventListener("input", (event) => {
  const value = event.target.value;
  clearTimeout(lookupTimer);
  lookupTimer = setTimeout(() => {
    void lookupEmployees(value);
  }, 180);
});

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  message.textContent = "Signing in...";
  message.style.color = "#5d708f";

  const fd = new FormData(form);
  const payload = {
    employee_id: String(fd.get("employee_id") || "").trim(),
    password: String(fd.get("password") || ""),
  };

  try {
    await loginApi("api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const me = await loginApi("api/auth/me?appKey=atlas_user_auth_admin");
    if (!hasExplicitReturnTarget()) {
      showSessionState(me);
      return;
    }

    const target = resolvePostLoginTarget();
    message.textContent = "Login successful. Redirecting...";
    message.style.color = "#0a5";
    setTimeout(() => {
      window.location.href = target;
    }, 400);
  } catch (error) {
    message.textContent = error.message || "Login failed";
    message.style.color = "#c02";
  }
});

logoutExistingBtn?.addEventListener("click", async () => {
  try {
    await loginApi("api/auth/logout", { method: "POST" });
  } finally {
    window.location.href = "login";
  }
});

adminLink?.addEventListener("click", (event) => {
  if (adminLink.getAttribute("aria-disabled") === "true") {
    event.preventDefault();
    message.textContent = "This account is signed in, but it does not currently have Atlas admin access.";
    message.style.color = "#b42318";
  }
});

checkExistingSession();
initializeLauncher();
