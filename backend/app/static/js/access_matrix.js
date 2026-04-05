function getCookie(name) {
  const cookie = document.cookie
    .split(";")
    .map((v) => v.trim())
    .find((v) => v.startsWith(name + "="));
  if (!cookie) return "";
  return decodeURIComponent(cookie.slice(name.length + 1));
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const method = (options.method || "GET").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
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

const state = {
  apps: [],
  users: [],
  directoryOptions: [],
};

const adminUser = document.getElementById("matrix-admin-user");
const head = document.getElementById("matrix-head");
const body = document.getElementById("matrix-body");
const foot = document.getElementById("matrix-foot");
const userFilter = document.getElementById("matrix-user-filter");
const appFilter = document.getElementById("matrix-app-filter");
const message = document.getElementById("matrix-message");

let directoryTimer = null;

function withBase(path) {
  const marker = "/admin/access-matrix";
  const pathname = window.location.pathname;
  const prefix = pathname.includes(marker) ? pathname.slice(0, pathname.indexOf(marker)) : "";
  if (path.startsWith("/")) return `${prefix}${path}`;
  return `${prefix}/${path}`;
}

function setMessage(text, tone = "neutral") {
  message.textContent = text;
  message.style.color = tone === "error" ? "#b42318" : tone === "success" ? "#157347" : "#5d708f";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function filteredApps() {
  const q = String(appFilter?.value || "").trim().toLowerCase();
  return state.apps.filter((app) => !q || app.app_key.toLowerCase().includes(q));
}

function filteredUsers() {
  const q = String(userFilter?.value || "").trim().toLowerCase();
  return state.users.filter((user) => {
    if (!q) return true;
    return (
      String(user.employee_id).includes(q) ||
      String(user.name || "").toLowerCase().includes(q) ||
      String(user.email || "").toLowerCase().includes(q)
    );
  });
}

function levelOptions(selected) {
  const current = Number(selected || 0);
  return [0, 1, 2, 3, 4, 5]
    .map((level) => {
      const label = level === 0 ? "No access" : `Level ${level}`;
      return `<option value="${level}" ${current === level ? "selected" : ""}>${label}</option>`;
    })
    .join("");
}

function renderMatrix() {
  const apps = filteredApps();
  const users = filteredUsers();
  document.getElementById("matrix-user-count").textContent = String(users.length);
  document.getElementById("matrix-app-count").textContent = String(apps.length);

  head.innerHTML = `
    <tr>
      <th class="sticky-col matrix-user-col">User</th>
      ${apps.map((app) => `<th>${escapeHtml(app.app_key)}<small>${app.user_count} users</small></th>`).join("")}
    </tr>
  `;

  body.innerHTML = users
    .map(
      (user) => `
        <tr>
          <th class="sticky-col matrix-user-cell">
            <div>${escapeHtml(user.name || `Employee ${user.employee_id}`)}</div>
            <small>#${escapeHtml(user.employee_id)}${user.email ? ` · ${escapeHtml(user.email)}` : ""}</small>
          </th>
          ${apps
            .map(
              (app) => `
                <td>
                  <select data-employee-id="${escapeHtml(user.employee_id)}" data-app-key="${escapeHtml(app.app_key)}" class="matrix-level-select level-${Number(user.app_levels?.[app.app_key] || 0)}">
                    ${levelOptions(user.app_levels?.[app.app_key] || 0)}
                  </select>
                </td>
              `
            )
            .join("")}
        </tr>
      `
    )
    .join("");

  foot.innerHTML = `
    <tr class="matrix-add-row">
      <th class="sticky-col matrix-user-cell">
        <label class="matrix-add-user">
          <span>Add user</span>
          <input type="search" id="matrix-add-user-input" list="matrix-user-suggestions" placeholder="Search employee name or ID" autocomplete="off" />
          <datalist id="matrix-user-suggestions"></datalist>
        </label>
      </th>
      ${apps
        .map(
          (app) => `
            <td>
              <select data-add-app-key="${escapeHtml(app.app_key)}" class="matrix-level-select level-0">
                ${levelOptions(0)}
              </select>
            </td>
          `
        )
        .join("")}
    </tr>
    <tr>
      <td class="sticky-col matrix-user-cell">
        <button id="matrix-add-user-btn" type="button">Add user</button>
      </td>
      <td colspan="${Math.max(1, apps.length)}" class="matrix-foot-note">Choose one or more non-zero app levels before adding the new user.</td>
    </tr>
  `;
}

async function loadSession() {
  try {
    const me = await api(withBase("/api/auth/me?appKey=atlas_user_auth_admin"));
    if (!me.is_admin) {
      sessionStorage.setItem("atlas_auth_notice", "You are signed in, but this account does not have Atlas admin access.");
      window.location.href = withBase("/login");
      return false;
    }
    adminUser.textContent = `Admin: ${me.name || me.employee_id}`;
    return true;
  } catch {
    window.location.href = withBase("/login");
    return false;
  }
}

async function loadMatrix() {
  const data = await api(withBase("/api/auth/users/matrix"));
  state.apps = Array.isArray(data.apps) ? data.apps : [];
  state.users = Array.isArray(data.users) ? data.users : [];
  renderMatrix();
}

async function lookupDirectory(query) {
  const q = String(query || "").trim();
  const datalist = document.getElementById("matrix-user-suggestions");
  if (!datalist) return;
  if (!q) {
    state.directoryOptions = [];
    datalist.innerHTML = "";
    return;
  }
  const data = await api(withBase(`/api/auth/employees/search?q=${encodeURIComponent(q)}`));
  state.directoryOptions = Array.isArray(data.items) ? data.items : [];
  datalist.innerHTML = state.directoryOptions
    .map((item) => `<option value="${escapeHtml(item.name)} (${escapeHtml(item.employee_id)})"></option>`)
    .join("");
}

function resolveAddUserSelection() {
  const input = document.getElementById("matrix-add-user-input");
  const raw = String(input?.value || "").trim();
  const exact = state.directoryOptions.find((item) => `${item.name} (${item.employee_id})` === raw);
  if (exact) return exact;
  const digits = raw.replace(/\D+/g, "");
  if (!digits) return null;
  return state.directoryOptions.find((item) => String(item.employee_id) === String(Number(digits))) || { employee_id: Number(digits), name: raw };
}

async function updateCell(employeeId, appKey, accessLevel, selectEl) {
  setMessage(`Saving ${appKey} for ${employeeId}...`);
  try {
    await api(withBase(`/api/auth/users/matrix/${employeeId}/apps/${encodeURIComponent(appKey)}`), {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ access_level: Number(accessLevel) }),
    });
    selectEl.className = `matrix-level-select level-${Number(accessLevel)}`;
    const user = state.users.find((row) => Number(row.employee_id) === Number(employeeId));
    if (user) user.app_levels[appKey] = Number(accessLevel);
    setMessage(`Saved ${appKey} for ${employeeId}.`, "success");
  } catch (error) {
    setMessage(error.message, "error");
    await loadMatrix();
  }
}

async function addUserFromRow() {
  const selected = resolveAddUserSelection();
  if (!selected?.employee_id) {
    setMessage("Choose a user from employee search first.", "error");
    return;
  }
  const levels = {};
  document.querySelectorAll("[data-add-app-key]").forEach((select) => {
    const level = Number(select.value || 0);
    if (level > 0) levels[select.dataset.addAppKey] = level;
  });
  if (!Object.keys(levels).length) {
    setMessage("Choose at least one non-zero access level before adding the user.", "error");
    return;
  }
  setMessage(`Adding ${selected.name || selected.employee_id}...`);
  await api(withBase("/api/auth/users/matrix/add-user"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      employee_id: String(selected.employee_id),
      app_levels: levels,
    }),
  });
  setMessage(`Added ${selected.name || selected.employee_id} to the matrix.`, "success");
  await loadMatrix();
}

document.getElementById("matrix-logout-btn")?.addEventListener("click", async () => {
  try {
    await api(withBase("/api/auth/logout"), { method: "POST" });
  } finally {
    window.location.href = withBase("/login");
  }
});

document.addEventListener("change", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLSelectElement)) return;
  if (target.dataset.employeeId && target.dataset.appKey) {
    void updateCell(target.dataset.employeeId, target.dataset.appKey, target.value, target);
    return;
  }
  if (target.dataset.addAppKey) {
    target.className = `matrix-level-select level-${Number(target.value || 0)}`;
  }
});

document.addEventListener("input", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLInputElement)) return;
  if (target.id === "matrix-user-filter" || target.id === "matrix-app-filter") {
    renderMatrix();
    return;
  }
  if (target.id === "matrix-add-user-input") {
    clearTimeout(directoryTimer);
    directoryTimer = setTimeout(() => {
      void lookupDirectory(target.value).catch(() => {});
    }, 180);
  }
});

document.addEventListener("click", (event) => {
  const target = event.target;
  if (target instanceof HTMLElement && target.id === "matrix-add-user-btn") {
    void addUserFromRow().catch((error) => setMessage(error.message, "error"));
  }
});

async function bootstrap() {
  const ok = await loadSession();
  if (!ok) return;
  await loadMatrix();
}

bootstrap().catch(() => {
  window.location.href = withBase("/login");
});
