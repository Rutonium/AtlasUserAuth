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
  appKey: "",
  apps: [],
  rows: [],
};

const adminUser = document.getElementById("rights-admin-user");
const appSelect = document.getElementById("rights-app-select");
const filterInput = document.getElementById("rights-filter");
const head = document.getElementById("rights-head");
const body = document.getElementById("rights-body");
const foot = document.getElementById("rights-foot");
const message = document.getElementById("rights-message");

function withBase(path) {
  const marker = "/admin/rights-matrix";
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

function filteredRows() {
  const q = String(filterInput?.value || "").trim().toLowerCase();
  return state.rows.filter((row) => !q || row.right_key.toLowerCase().includes(q));
}

function renderApps() {
  appSelect.innerHTML = state.apps
    .map((app) => `<option value="${escapeHtml(app)}" ${app === state.appKey ? "selected" : ""}>${escapeHtml(app)}</option>`)
    .join("");
  document.getElementById("rights-app-name").textContent = state.appKey || "-";
}

function renderMatrix() {
  const rows = filteredRows();
  document.getElementById("rights-row-count").textContent = String(rows.length);
  head.innerHTML = `
    <tr>
      <th class="sticky-col matrix-user-col">Right key</th>
      <th>Level 1</th>
      <th>Level 2</th>
      <th>Level 3</th>
      <th>Level 4</th>
      <th>Level 5</th>
      <th>Action</th>
    </tr>
  `;

  body.innerHTML = rows
    .map(
      (row) => `
        <tr>
          <th class="sticky-col matrix-user-cell">
            <div>${escapeHtml(row.right_key)}</div>
          </th>
          ${["1", "2", "3", "4", "5"]
            .map(
              (level) => `
                <td class="rights-cell">
                  <input
                    type="checkbox"
                    data-right-key="${escapeHtml(row.right_key)}"
                    data-level="${level}"
                    ${row.levels?.[level] ? "checked" : ""}
                  />
                </td>
              `
            )
            .join("")}
          <td>
            <button type="button" class="btn-secondary" data-delete-right="${escapeHtml(row.right_key)}">Delete</button>
          </td>
        </tr>
      `
    )
    .join("");

  foot.innerHTML = `
    <tr class="matrix-add-row">
      <th class="sticky-col matrix-user-cell">
        <label class="matrix-add-user">
          <span>Add right key</span>
          <input type="text" id="new-right-key" placeholder="can_view, can_edit, can_approve..." />
        </label>
      </th>
      <td colspan="6" class="matrix-foot-note">
        <button id="add-right-btn" type="button">Add right key</button>
      </td>
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

async function loadMatrix(selectedApp = "") {
  const data = await api(withBase(`/api/auth/apps/rights-matrix${selectedApp ? `?appKey=${encodeURIComponent(selectedApp)}` : ""}`));
  state.apps = Array.isArray(data.apps) ? data.apps : [];
  state.appKey = data.app_key || state.apps[0] || "";
  state.rows = Array.isArray(data.rows) ? data.rows : [];
  renderApps();
  renderMatrix();
}

async function saveRow(rightKey, levels) {
  await api(withBase(`/api/auth/apps/${encodeURIComponent(state.appKey)}/rights-matrix/${encodeURIComponent(rightKey)}`), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ levels }),
  });
}

document.getElementById("rights-logout-btn")?.addEventListener("click", async () => {
  try {
    await api(withBase("/api/auth/logout"), { method: "POST" });
  } finally {
    window.location.href = withBase("/login");
  }
});

appSelect?.addEventListener("change", () => {
  void loadMatrix(appSelect.value).catch((error) => setMessage(error.message, "error"));
});

filterInput?.addEventListener("input", () => {
  renderMatrix();
});

document.addEventListener("change", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLInputElement) || target.type !== "checkbox") return;
  const rightKey = target.dataset.rightKey;
  const level = target.dataset.level;
  if (!rightKey || !level) return;
  const row = state.rows.find((item) => item.right_key === rightKey);
  if (!row) return;
  row.levels[level] = target.checked;
  setMessage(`Saving ${rightKey}...`);
  void saveRow(rightKey, row.levels)
    .then(() => setMessage(`Saved ${rightKey}.`, "success"))
    .catch(async (error) => {
      setMessage(error.message, "error");
      await loadMatrix(state.appKey);
    });
});

document.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;

  if (target.id === "add-right-btn") {
    const input = document.getElementById("new-right-key");
    const rightKey = String(input?.value || "").trim();
    if (!state.appKey) {
      setMessage("Choose an app before adding rights.", "error");
      return;
    }
    if (!rightKey) {
      setMessage("Enter a right key first.", "error");
      return;
    }
    setMessage(`Adding ${rightKey}...`);
    void api(withBase(`/api/auth/apps/${encodeURIComponent(state.appKey)}/rights-matrix`), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ right_key: rightKey }),
    })
      .then(async () => {
        if (input) input.value = "";
        setMessage(`Added ${rightKey}.`, "success");
        await loadMatrix(state.appKey);
      })
      .catch((error) => setMessage(error.message, "error"));
    return;
  }

  if (target.dataset.deleteRight) {
    const rightKey = target.dataset.deleteRight;
    setMessage(`Deleting ${rightKey}...`);
    void api(withBase(`/api/auth/apps/${encodeURIComponent(state.appKey)}/rights-matrix/${encodeURIComponent(rightKey)}`), {
      method: "DELETE",
    })
      .then(async () => {
        setMessage(`Deleted ${rightKey}.`, "success");
        await loadMatrix(state.appKey);
      })
      .catch((error) => setMessage(error.message, "error"));
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
