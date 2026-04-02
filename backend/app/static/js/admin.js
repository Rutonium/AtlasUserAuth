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
  selectedUser: null,
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
const userList = document.getElementById("user-list");
const userListMeta = document.getElementById("user-list-meta");
const userFilterInput = document.getElementById("user-filter-input");
const directorySearchInput = document.getElementById("directory-search-input");
const directoryResults = document.getElementById("directory-results");
const selectedUserEmpty = document.getElementById("selected-user-empty");
const selectedUserPanel = document.getElementById("selected-user-panel");
const selectedUserName = document.getElementById("selected-user-name");
const selectedUserMeta = document.getElementById("selected-user-meta");
const selectedUserAdmin = document.getElementById("selected-user-admin");
const selectedUserStatus = document.getElementById("selected-user-status");
const selectedUserApps = document.getElementById("selected-user-apps");
const accessCards = document.getElementById("access-cards");
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

function rightsCount(entry) {
  const rights = entry?.rights;
  return rights && typeof rights === "object" ? Object.keys(rights).length : 0;
}

function scoreUser(user, query) {
  const q = String(query || "").trim().toLowerCase();
  if (!q) return 9999;
  const employeeId = String(user.employee_id || "");
  const name = String(user.name || "").toLowerCase();
  const email = String(user.email || "").toLowerCase();
  const apps = Array.isArray(user.app_keys) ? user.app_keys.join(" ").toLowerCase() : "";
  if (employeeId === q) return 0;
  if (employeeId.startsWith(q)) return 1;
  if (name.startsWith(q)) return 2;
  if (email.startsWith(q)) return 3;
  if (apps.includes(q)) return 4;
  if (name.includes(q) || email.includes(q) || employeeId.includes(q)) return 5;
  return 10;
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

function renderUserList() {
  const filter = String(userFilterInput?.value || "");
  const users = [...state.users]
    .filter((user) => !filter.trim() || scoreUser(user, filter) < 10)
    .sort((a, b) => {
      const delta = scoreUser(a, filter) - scoreUser(b, filter);
      if (delta !== 0) return delta;
      return String(a.name || a.employee_id).localeCompare(String(b.name || b.employee_id));
    });

  userListMeta.textContent = `${users.length} of ${state.users.length} users shown`;
  if (!users.length) {
    userList.innerHTML = `<div class="empty-state">No users match the current filter.</div>`;
    return;
  }

  userList.innerHTML = users
    .map((user) => {
      const isSelected = Number(state.selectedUser?.employee_id) === Number(user.employee_id);
      const appChips = (user.app_keys || []).slice(0, 4).map((appKey) => `<span class="tiny-chip">${escapeHtml(appKey)}</span>`).join("");
      const extra = Array.isArray(user.app_keys) && user.app_keys.length > 4
        ? `<span class="tiny-chip">+${user.app_keys.length - 4} more</span>`
        : "";
      return `
        <button class="user-row ${isSelected ? "is-selected" : ""}" type="button" data-employee-id="${escapeHtml(user.employee_id)}">
          <div class="user-row-top">
            <strong>${escapeHtml(user.name || `Employee ${user.employee_id}`)}</strong>
            <span class="tiny-status ${user.is_active ? "active" : "inactive"}">${user.is_active ? "Active" : "Inactive"}</span>
          </div>
          <div class="user-row-meta">#${escapeHtml(user.employee_id)} · ${escapeHtml(user.email || "No email on file")}</div>
          <div class="user-row-foot">
            <span>${user.app_access_count || 0} grants</span>
            <span>${user.is_admin ? "Atlas admin" : "Standard user"}</span>
          </div>
          <div class="tiny-chip-row">${appChips}${extra}</div>
        </button>
      `;
    })
    .join("");
}

function fillAccessForm(entry) {
  const employeeId = Number(state.selectedUser?.employee_id || 0);
  document.getElementById("access-employee-id").value = employeeId ? String(employeeId) : "";
  document.getElementById("access-app-key").value = entry?.app_key || "";
  document.getElementById("access-role").value = entry?.role || "user";
  document.getElementById("access-level").value = String(entry?.access_level || 1);
  document.getElementById("access-label").value = entry?.access_label || ACCESS_LEVEL_LABELS[entry?.access_level || 1];
  document.getElementById("access-rights").value = JSON.stringify(entry?.rights || { can_view: true }, null, 2);
  document.getElementById("access-is-active").checked = entry ? Boolean(entry.is_active) : true;
}

function renderSelectedUser() {
  const user = state.selectedUser;
  if (!user) {
    selectedUserEmpty.classList.remove("hidden");
    selectedUserPanel.classList.add("hidden");
    accessCards.className = "access-cards empty-state";
    accessCards.textContent = "Select a user to view program access.";
    fillAccessForm(null);
    document.getElementById("reset-employee-id").value = "";
    return;
  }

  selectedUserEmpty.classList.add("hidden");
  selectedUserPanel.classList.remove("hidden");
  selectedUserName.textContent = user.name || `Employee ${user.employee_id}`;
  selectedUserMeta.textContent = `Employee ID ${user.employee_id}${user.email ? ` · ${user.email}` : ""}`;
  selectedUserAdmin.textContent = user.is_admin ? "Atlas admin enabled" : "No Atlas admin access";
  selectedUserStatus.textContent = user.is_active ? "Directory account active" : "Directory account inactive";
  selectedUserApps.innerHTML = (user.access_entries || []).length
    ? user.access_entries
        .map(
          (entry) =>
            `<span class="app-chip">${escapeHtml(entry.app_key)}<small>${escapeHtml(accessLabel(entry.access_level, entry.access_label))}</small></span>`
        )
        .join("")
    : `<span class="empty-state inline-empty">No program grants yet.</span>`;

  document.getElementById("reset-employee-id").value = String(user.employee_id);
  fillAccessForm(user.access_entries?.[0] || null);

  if (!(user.access_entries || []).length) {
    accessCards.className = "access-cards empty-state";
    accessCards.textContent = "This user has no program access yet. Use the editor to create the first grant.";
    return;
  }

  accessCards.className = "access-cards";
  accessCards.innerHTML = user.access_entries
    .map(
      (entry) => `
        <article class="access-card ${entry.is_active ? "" : "muted-card"}">
          <div class="access-card-head">
            <div>
              <div class="access-app">${escapeHtml(entry.app_key)}</div>
              <div class="access-role">${escapeHtml(entry.role)}</div>
            </div>
            <span class="level-badge level-${escapeHtml(entry.access_level)}">${escapeHtml(accessLabel(entry.access_level, entry.access_label))}</span>
          </div>
          <div class="access-card-body">
            <div class="access-stat">
              <span>Status</span>
              <strong>${entry.is_active ? "Active" : "Inactive"}</strong>
            </div>
            <div class="access-stat">
              <span>Rights</span>
              <strong>${rightsCount(entry)}</strong>
            </div>
          </div>
          <pre class="rights-preview">${escapeHtml(JSON.stringify(entry.rights || {}, null, 2))}</pre>
          <div class="access-card-actions">
            <button type="button" class="btn-secondary" data-action="edit-access" data-app-key="${escapeHtml(entry.app_key)}">Edit</button>
            <button type="button" data-action="toggle-access" data-app-key="${escapeHtml(entry.app_key)}">${entry.is_active ? "Deactivate" : "Reactivate"}</button>
          </div>
        </article>
      `
    )
    .join("");
}

function chooseDirectoryEmployee(item) {
  state.selectedDirectoryEmployee = item;
  provisionSelectedName.value = `${item.name} (${item.employee_id})`;
  provisionEmployeeId.value = String(item.employee_id);
  provisionSelection.textContent = `${item.name} selected from the employee directory. Provisioning will save Employee ID ${item.employee_id} into Atlas auth only when you create the user.`;
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
            ${existing ? `<button type="button" class="btn-secondary" data-action="open-user" data-employee-id="${escapeHtml(item.employee_id)}">Open existing user</button>` : ""}
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
      adminUser.textContent = "Not admin";
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

async function loadUsers(options = {}) {
  state.users = await api("api/auth/users");
  renderUserList();
  if (options.preserveSelection && state.selectedUser?.employee_id) {
    const stillExists = state.users.some((user) => Number(user.employee_id) === Number(state.selectedUser.employee_id));
    if (stillExists) {
      await selectUser(state.selectedUser.employee_id);
      return;
    }
  }
  if (!state.selectedUser && state.users.length) {
    await selectUser(state.users[0].employee_id);
  }
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

async function selectUser(employeeId) {
  const detail = await api(`api/auth/users/${encodeURIComponent(employeeId)}`);
  state.selectedUser = detail;
  renderUserList();
  renderSelectedUser();
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
      await Promise.all([loadUsers({ preserveSelection: false }), loadDashboardSummary()]);
      await selectUser(out.employee_id);
    } catch (error) {
      setMessage("provision-message", error.message, "error");
    }
  });
}

function setupAccessEditor() {
  const form = document.getElementById("rights-form");
  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fd = new FormData(form);
    const employeeId = Number(fd.get("employee_id"));
    if (!employeeId) {
      setMessage("rights-message", "Select a user before saving access.", "error");
      return;
    }
    const appKey = String(fd.get("app_key") || "").trim();
    let rights;
    try {
      rights = JSON.parse(String(fd.get("rights") || "{}"));
    } catch {
      setMessage("rights-message", "Rights JSON is invalid.", "error");
      return;
    }
    setMessage("rights-message", "Saving access grant...", "neutral");
    const payload = {
      role: String(fd.get("role") || "user").trim(),
      access_level: Number(fd.get("access_level") || 1),
      access_label: String(fd.get("access_label") || "").trim() || null,
      rights,
      is_active: fd.get("is_active") === "on",
    };
    try {
      await api(`api/auth/users/${employeeId}/apps/${encodeURIComponent(appKey)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setMessage("rights-message", `Saved ${appKey} access for ${employeeId}.`, "success");
      await Promise.all([loadUsers({ preserveSelection: true }), loadDashboardSummary()]);
    } catch (error) {
      setMessage("rights-message", error.message, "error");
    }
  });

  document.getElementById("format-rights-btn")?.addEventListener("click", () => {
    const rightsField = document.getElementById("access-rights");
    try {
      rightsField.value = JSON.stringify(JSON.parse(rightsField.value || "{}"), null, 2);
      setMessage("rights-message", "Rights JSON formatted.", "success");
    } catch {
      setMessage("rights-message", "Could not format invalid JSON.", "error");
    }
  });

  document.getElementById("reset-access-form-btn")?.addEventListener("click", () => {
    fillAccessForm(null);
    setMessage("rights-message", "Access editor cleared.", "neutral");
  });

  document.getElementById("new-access-btn")?.addEventListener("click", () => {
    fillAccessForm(null);
    setMessage("rights-message", "Ready to create a new access grant for the selected user.", "neutral");
  });
}

function setupInteractions() {
  document.getElementById("refresh-users")?.addEventListener("click", async () => {
    await Promise.all([loadUsers({ preserveSelection: true }), loadDashboardSummary(), loadHealth()]);
  });

  userFilterInput?.addEventListener("input", () => {
    renderUserList();
  });

  userList?.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-employee-id]");
    if (!button) return;
    const employeeId = Number(button.dataset.employeeId);
    if (employeeId) await selectUser(employeeId);
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
    if (action === "open-user") {
      await selectUser(employeeId);
      return;
    }
    if (action === "select-directory") {
      const resp = await api(`api/auth/employees/search?q=${encodeURIComponent(employeeId)}`);
      const item = (resp.items || []).find((entry) => Number(entry.employee_id) === employeeId);
      if (item) chooseDirectoryEmployee(item);
    }
  });

  accessCards?.addEventListener("click", async (event) => {
    const target = event.target.closest("[data-action]");
    const action = target?.dataset.action;
    const appKey = target?.dataset.appKey;
    if (!action || !appKey || !state.selectedUser) return;
    const entry = (state.selectedUser.access_entries || []).find((item) => item.app_key === appKey);
    if (!entry) return;
    if (action === "edit-access") {
      fillAccessForm(entry);
      setMessage("rights-message", `Editing ${appKey} for ${state.selectedUser.employee_id}.`, "neutral");
      return;
    }
    if (action === "toggle-access") {
      setMessage("rights-message", `${entry.is_active ? "Deactivating" : "Reactivating"} ${appKey}...`, "neutral");
      try {
        await api(`api/auth/users/${state.selectedUser.employee_id}/apps/${encodeURIComponent(appKey)}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            role: entry.role,
            access_level: entry.access_level,
            access_label: entry.access_label,
            rights: entry.rights,
            is_active: !entry.is_active,
          }),
        });
        await Promise.all([loadUsers({ preserveSelection: true }), loadDashboardSummary()]);
        setMessage("rights-message", `${appKey} updated.`, "success");
      } catch (error) {
        setMessage("rights-message", error.message, "error");
      }
    }
  });
}

async function bootstrap() {
  const ok = await loadSession();
  if (!ok) return;
  await Promise.all([loadDashboardSummary(), loadHealth(), loadUsers()]);
  renderSelectedUser();
}

setupProvision();
setupAccessEditor();
setupResetPassword();
setupLogout();
setupInteractions();
bootstrap().catch(() => {
  window.location.href = "login";
});
