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
const usersTable = document.getElementById("users-table");

async function loadSession() {
  try {
    const me = await api("/api/auth/me?appKey=atlas_user_auth_admin");
    if (Boolean(me.is_admin) === false) {
      adminUser.textContent = "Not admin";
      alert("Admin rights are required");
      window.location.href = "/";
      return;
    }
    adminUser.textContent = `Admin: ${me.name || me.employee_id}`;
  } catch {
    window.location.href = "/";
  }
}

async function loadUsers() {
  const data = await api("/api/auth/users");
  usersTable.innerHTML = data
    .map(
      (u) =>
        `<tr><td>${u.employee_id}</td><td>${u.name || ""}</td><td>${u.email || ""}</td><td>${u.is_admin}</td><td>${u.is_active}</td></tr>`
    )
    .join("");
}

function setupProvision() {
  const form = document.getElementById("provision-form");
  const msg = document.getElementById("provision-message");
  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    msg.textContent = "Provisioning...";
    msg.style.color = "#5d708f";
    const fd = new FormData(form);
    const payload = {
      employee_id: String(fd.get("employee_id") || ""),
      app_key: String(fd.get("app_key") || ""),
      initial_role: String(fd.get("initial_role") || "user"),
      make_admin: fd.get("make_admin") === "on",
    };

    try {
      const out = await api("/api/auth/users/provision-by-employee-id", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      msg.textContent = `Provisioned ${out.employee_id} for ${out.app_key}`;
      msg.style.color = "#0a5";
      await loadUsers();
    } catch (error) {
      msg.textContent = error.message;
      msg.style.color = "#c02";
    }
  });
}

function setupRights() {
  const form = document.getElementById("rights-form");
  const msg = document.getElementById("rights-message");
  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    msg.textContent = "Saving rights...";
    msg.style.color = "#5d708f";

    const fd = new FormData(form);
    const employeeId = Number(fd.get("employee_id"));
    const appKey = String(fd.get("app_key") || "");
    let rights;
    try {
      rights = JSON.parse(String(fd.get("rights") || "{}"));
    } catch {
      msg.textContent = "Rights JSON is invalid";
      msg.style.color = "#c02";
      return;
    }

    const payload = {
      role: String(fd.get("role") || "user"),
      rights,
      is_active: fd.get("is_active") === "on",
    };

    try {
      await api(`/api/auth/users/${employeeId}/apps/${encodeURIComponent(appKey)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      msg.textContent = "Rights updated";
      msg.style.color = "#0a5";
    } catch (error) {
      msg.textContent = error.message;
      msg.style.color = "#c02";
    }
  });
}

function setupLogout() {
  document.getElementById("logout-btn")?.addEventListener("click", async () => {
    try {
      await api("/api/auth/logout", { method: "POST" });
    } finally {
      window.location.href = "/";
    }
  });
}

document.getElementById("refresh-users")?.addEventListener("click", () => {
  loadUsers().catch((err) => alert(err.message));
});

loadSession().then(loadUsers).catch(() => {});
setupProvision();
setupRights();
setupLogout();
