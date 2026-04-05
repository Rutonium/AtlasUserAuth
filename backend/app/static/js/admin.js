function getCookie(name) {
  const cookie = document.cookie
    .split(";")
    .map((v) => v.trim())
    .find((v) => v.startsWith(name + "="));
  if (cookie === undefined) return "";
  return decodeURIComponent(cookie.slice(name.length + 1));
}

async function api(path, options = {}) {
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
  if (response.ok === false) {
    const err = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || "Request failed");
  }
  return response.json().catch(() => ({}));
}

const adminUser = document.getElementById("admin-user");
const state = {
  me: null,
  users: [],
  summary: null,
  health: null,
  selectedDirectoryEmployee: null,
};

const ACCESS_LEVEL_LABELS = {
  1: "Viewer",
  2: "Contributor",
  3: "Specialist",
  4: "Manager",
  5: "Owner",
};

const healthPill = document.getElementById("health-pill");
const directorySearchInput = document.getElementById("directory-search-input");
const directoryResults = document.getElementById("directory-results");
const selectedUserName = document.getElementById("selected-user-name");
const selectedUserMeta = document.getElementById("selected-user-meta");
const selectedUserAdmin = document.getElementById("selected-user-admin");
const selectedUserStatus = document.getElementById("selected-user-status");
const selectedUserApps = document.getElementById("selected-user-apps");
const provisionSelection = document.getElementById("provision-selection");
const provisionSelectedName = document.getElementById("provision-selected-name");
const provisionEmployeeId = document.getElementById("provision-employee-id");
const topApps = document.getElementById("top-apps");
const healthSummary = document.getElementById("health-summary");

let directoryLookupTimer = null;

function setMessage(elementId, text, tone = "neutral") {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.textContent = text;
  el.dataset.tone = tone;
  el.style.color = tone === "error" ? "#b42318" : tone === "success" ? "#157347" : "#5d708f";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function accessLabel(level, label) {
  const normalizedLevel = Number(level || 1);
  const normalizedLabel = String(label || ACCESS_LEVEL_LABELS[normalizedLevel] || "Custom");
  return `L${normalizedLevel} · ${normalizedLabel}`;
}

function renderKpis() {
  const summary = state.summary || {};
  const health = state.health || {};
  document.getElementById("kpi-total-users").textContent = String(summary.total_users || 0);
  document.getElementById("kpi-admin-users").textContent = String(summary.admin_users || 0);
  document.getElementById("kpi-access-entries").textContent = String(summary.active_access_entries || 0);
  document.getElementById("kpi-unique-apps").textContent = String(summary.unique_apps || 0);
  document.getElementById("kpi-directory-status").textContent = health.employee_cache_ok
    ? `Employee directory ready · ${health.employee_cache_size || 0} records cached`
    : `Employee directory needs attention${health.employee_cache_last_error ? ` · ${health.employee_cache_last_error}` : ""}`;
}

function renderHealth() {
  const health = state.health || {};
  const healthOkay = Boolean(health.ok && health.db_ok);
  healthPill.textContent = healthOkay ? "Core systems healthy" : "Action needed in system health";
  healthPill.classList.toggle("pill-danger", !healthOkay);
  healthPill.classList.toggle("pill-success", healthOkay);

  const lines = [
    `<div><strong>API:</strong> ${health.ok ? "Healthy" : "Attention needed"}</div>`,
    `<div><strong>Database:</strong> ${health.db_ok ? "Connected" : "Unavailable"}</div>`,
    `<div><strong>Employee directory:</strong> ${health.employee_cache_ok ? `Ready (${health.employee_cache_size || 0} cached)` : "Cache unavailable"}</div>`,
  ];
  if (health.employee_cache_last_error) {
    lines.push(`<div><strong>Directory note:</strong> ${escapeHtml(health.employee_cache_last_error)}</div>`);
  }
  healthSummary.innerHTML = lines.join("");
}

function renderTopApps() {
  const items = Array.isArray(state.summary?.top_apps) ? state.summary.top_apps : [];
  if (!items.length) {
    topApps.className = "top-apps empty-state";
    topApps.textContent = "No program metrics yet.";
    return;
  }
  const max = Math.max(...items.map((item) => Number(item.user_count || 0)), 1);
  topApps.className = "top-apps";
  topApps.innerHTML = items
    .map((item) => {
      const width = Math.max(8, Math.round((Number(item.user_count || 0) / max) * 100));
      return `
        <div class="top-app-row">
          <div class="top-app-label">${escapeHtml(item.app_key)}</div>
          <div class="top-app-bar"><span style="width:${width}%"></span></div>
          <div class="top-app-count">${escapeHtml(item.user_count)}</div>
        </div>
      `;
    })
    .join("");
}

function renderSelectedEmployee() {
  const item = state.selectedDirectoryEmployee;
  if (!item) {
    selectedUserName.textContent = "No employee selected yet";
    selectedUserMeta.textContent = "Choose someone from the directory search below to provision or to prepare a password reset.";
    selectedUserAdmin.textContent = "Provisioning target not set";
    selectedUserStatus.textContent = "Awaiting directory selection";
    selectedUserApps.innerHTML = `<span class="empty-state inline-empty">Directory-driven provisioning keeps Employee IDs out of Atlas auth until the user is actually created.</span>`;
    return;
  }

  const existing = state.users.find((user) => Number(user.employee_id) === Number(item.employee_id));
  selectedUserName.textContent = item.name || `Employee ${item.employee_id}`;
  selectedUserMeta.textContent = `Employee ID ${item.employee_id}${item.email ? ` · ${item.email}` : ""}`;
  selectedUserAdmin.textContent = existing?.is_admin ? "Already an Atlas admin" : "Ready for provisioning";
  selectedUserStatus.textContent = existing
    ? `Already in Atlas auth${existing.is_active ? " · Active" : " · Inactive"}`
    : "Directory match only";
  selectedUserApps.innerHTML = existing && Array.isArray(existing.app_keys) && existing.app_keys.length
    ? existing.app_keys.map((appKey) => `<span class="app-chip">${escapeHtml(appKey)}</span>`).join("")
    : `<span class="empty-state inline-empty">${existing ? "No current app access recorded." : "This person has not been provisioned in Atlas auth yet."}</span>`;
}

function chooseDirectoryEmployee(item) {
  state.selectedDirectoryEmployee = item;
  provisionSelectedName.value = `${item.name} (${item.employee_id})`;
  provisionEmployeeId.value = String(item.employee_id);
  document.getElementById("reset-employee-id").value = String(item.employee_id);
  provisionSelection.textContent = `${item.name} selected from the employee directory. Provisioning will save Employee ID ${item.employee_id} into Atlas auth only when you create the user.`;
  renderSelectedEmployee();
}

function renderDirectoryResults(items) {
  if (!items.length) {
    directoryResults.className = "directory-results empty-state";
    directoryResults.textContent = "No matching employees found.";
    return;
  }
  directoryResults.className = "directory-results";
  directoryResults.innerHTML = items
    .map((item) => {
      const existing = state.users.find((user) => Number(user.employee_id) === Number(item.employee_id));
      return `
        <article class="directory-card">
          <div>
            <strong>${escapeHtml(item.name)}</strong>
            <div class="directory-meta">#${escapeHtml(item.employee_id)}${item.email ? ` · ${escapeHtml(item.email)}` : ""}</div>
          </div>
          <div class="directory-actions">
            <button type="button" data-action="select-directory" data-employee-id="${escapeHtml(item.employee_id)}">Use for provisioning</button>
            ${existing ? `<span class="directory-existing">Already in Atlas auth</span>` : ""}
          </div>
        </article>
      `;
    })
    .join("");
}

async function loadSession() {
  try {
    const me = await api("api/auth/me?appKey=atlas_user_auth_admin");
    if (Boolean(me.is_admin) === false) {
      adminUser.textContent = me.name || me.employee_id || "Signed in";
      sessionStorage.setItem(
        "atlas_auth_notice",
        "You are signed in, but this account does not have Atlas admin access."
      );
      window.location.href = "login";
      return false;
    }
    state.me = me;
    adminUser.textContent = `Admin: ${me.name || me.employee_id}`;
    return true;
  } catch {
    window.location.href = "login";
    return false;
  }
}

async function loadUsers() {
  state.users = await api("api/auth/users");
  renderSelectedEmployee();
}

async function loadDashboardSummary() {
  state.summary = await api("api/auth/users/summary");
  renderKpis();
  renderTopApps();
}

async function loadHealth() {
  state.health = await api("api/healthz");
  renderKpis();
  renderHealth();
}

async function lookupDirectory(query) {
  const q = String(query || "").trim();
  if (q.length < 1) {
    directoryResults.className = "directory-results empty-state";
    directoryResults.textContent = "Search results from the employee API will appear here.";
    return;
  }
  const out = await api(`api/auth/employees/search?q=${encodeURIComponent(q)}`);
  renderDirectoryResults(Array.isArray(out.items) ? out.items : []);
}

function generatePassword(length = 14) {
  const lower = "abcdefghjkmnpqrstuvwxyz";
  const upper = "ABCDEFGHJKMNPQRSTUVWXYZ";
  const digits = "23456789";
  const symbols = "!@#$%*+-_?";
  const all = lower + upper + digits + symbols;

  const randomIndex = (limit) => {
    const seed = new Uint32Array(1);
    window.crypto.getRandomValues(seed);
    return seed[0] % limit;
  };
  const pick = (chars) => chars[randomIndex(chars.length)];
  const out = [pick(lower), pick(upper), pick(digits), pick(symbols)];
  for (let i = out.length; i < length; i += 1) out.push(pick(all));
  for (let i = out.length - 1; i > 0; i -= 1) {
    const j = randomIndex(i + 1);
    const tmp = out[i];
    out[i] = out[j];
    out[j] = tmp;
  }
  return out.join("");
}

function setupResetPassword() {
  const form = document.getElementById("reset-password-form");
  const passwordInput = document.getElementById("generated-password");
  const generateBtn = document.getElementById("generate-password-btn");
  const copyBtn = document.getElementById("copy-password-btn");

  function setGeneratedPassword() {
    if (!passwordInput) return;
    passwordInput.value = generatePassword();
  }

  generateBtn?.addEventListener("click", () => {
    setGeneratedPassword();
    setMessage("reset-password-message", "New temporary password generated.", "success");
  });

  copyBtn?.addEventListener("click", async () => {
    if (!passwordInput) return;
    if (!passwordInput.value) setGeneratedPassword();
    try {
      await navigator.clipboard.writeText(passwordInput.value);
      setMessage("reset-password-message", "Password copied to clipboard.", "success");
    } catch {
      setMessage("reset-password-message", "Could not copy automatically. Please copy manually.", "error");
    }
  });

  setGeneratedPassword();

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const employeeId = Number(document.getElementById("reset-employee-id").value);
    if (!employeeId) {
      setMessage("reset-password-message", "Select a user before resetting credentials.", "error");
      return;
    }
    setMessage("reset-password-message", "Resetting password...", "neutral");

    const fd = new FormData(form);
    const newPassword = String(fd.get("new_password") || "");

    try {
      await api(`api/auth/users/${employeeId}/reset-credential`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ new_password: newPassword }),
      });
      setMessage("reset-password-message", `Password reset for ${employeeId}. Share the temporary password securely.`, "success");
    } catch (error) {
      setMessage("reset-password-message", error.message, "error");
    }
  });
}

function setupLogout() {
  document.getElementById("logout-btn")?.addEventListener("click", async () => {
    try {
      await api("api/auth/logout", { method: "POST" });
    } finally {
      window.location.href = "login";
    }
  });
}

function setupProvision() {
  const form = document.getElementById("provision-form");
  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!state.selectedDirectoryEmployee) {
      setMessage("provision-message", "Select a person from the directory search before provisioning.", "error");
      return;
    }
    setMessage("provision-message", "Provisioning user...", "neutral");
    const fd = new FormData(form);
    const payload = {
      employee_id: String(fd.get("employee_id") || ""),
      app_key: String(fd.get("app_key") || ""),
      initial_role: String(fd.get("initial_role") || "user"),
      initial_access_level: Number(fd.get("initial_access_level") || 1),
      initial_access_label: String(fd.get("initial_access_label") || "").trim() || null,
      make_admin: fd.get("make_admin") === "on",
    };

    try {
      const out = await api("api/auth/users/provision-by-employee-id", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setMessage(
        "provision-message",
        `Provisioned ${out.name || out.employee_id} for ${out.app_key} at ${accessLabel(out.access_level, out.access_label)}.`,
        "success"
      );
      await Promise.all([loadUsers(), loadDashboardSummary()]);
      document.getElementById("reset-employee-id").value = String(out.employee_id);
      selectedUserStatus.textContent = "Provisioned in Atlas auth";
      renderSelectedEmployee();
    } catch (error) {
      setMessage("provision-message", error.message, "error");
    }
  });
}

function setupInteractions() {
  document.getElementById("refresh-dashboard")?.addEventListener("click", async () => {
    await Promise.all([loadUsers(), loadDashboardSummary(), loadHealth()]);
  });

  directorySearchInput?.addEventListener("input", (event) => {
    clearTimeout(directoryLookupTimer);
    directoryLookupTimer = setTimeout(() => {
      void lookupDirectory(event.target.value);
    }, 200);
  });

  directoryResults?.addEventListener("click", async (event) => {
    const target = event.target.closest("[data-action]");
    const action = target?.dataset.action;
    const employeeId = Number(target?.dataset.employeeId);
    if (!action || !employeeId) return;
    if (action === "select-directory") {
      const resp = await api(`api/auth/employees/search?q=${encodeURIComponent(employeeId)}`);
      const item = (resp.items || []).find((entry) => Number(entry.employee_id) === employeeId);
      if (item) chooseDirectoryEmployee(item);
    }
  });
}

async function bootstrap() {
  const ok = await loadSession();
  if (!ok) return;
  await Promise.all([loadDashboardSummary(), loadHealth(), loadUsers()]);
  renderSelectedEmployee();
}

setupProvision();
setupResetPassword();
setupLogout();
setupInteractions();
bootstrap().catch(() => {
  window.location.href = "login";
});
