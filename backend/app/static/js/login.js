const form = document.getElementById("login-form");
const message = document.getElementById("login-message");

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
    const resp = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(payload),
    });

    if (resp.ok === false) {
      const err = await resp.json().catch(() => ({ detail: "Login failed" }));
      throw new Error(err.detail || "Login failed");
    }

    message.textContent = "Login successful. Redirecting to admin...";
    message.style.color = "#0a5";
    setTimeout(() => {
      window.location.href = "/admin";
    }, 400);
  } catch (error) {
    message.textContent = error.message || "Login failed";
    message.style.color = "#c02";
  }
});
