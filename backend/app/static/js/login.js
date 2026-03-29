const form = document.getElementById("login-form");
const message = document.getElementById("login-message");
const employeeInput = document.getElementById("employee-id-input");
const employeeDatalist = document.getElementById("employee-suggestions");

let lookupTimer = null;

function resolvePostLoginTarget() {
  const params = new URLSearchParams(window.location.search);
  const requested =
    params.get("return_to") ||
    params.get("next") ||
    params.get("redirect") ||
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
    const resp = await fetch("api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(payload),
    });

    if (resp.ok === false) {
      const err = await resp.json().catch(() => ({ detail: "Login failed" }));
      throw new Error(err.detail || "Login failed");
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
