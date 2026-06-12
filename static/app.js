// ----- Mobile navigation -----
const topbar = document.querySelector("#topbar");
const navToggle = document.querySelector("#navToggle");
const mainNav = document.querySelector("#mainNav");

function closeMobileNav() {
  if (!topbar || !navToggle) return;
  topbar.classList.remove("nav-open");
  navToggle.setAttribute("aria-expanded", "false");
  navToggle.setAttribute("aria-label", "Open menu");
  document.body.classList.remove("nav-open");
}

function toggleMobileNav() {
  if (!topbar || !navToggle) return;
  const isOpen = topbar.classList.toggle("nav-open");
  navToggle.setAttribute("aria-expanded", String(isOpen));
  navToggle.setAttribute("aria-label", isOpen ? "Close menu" : "Open menu");
  document.body.classList.toggle("nav-open", isOpen);
  if (isOpen) closeAlertsPanel?.();
}

if (navToggle && mainNav && topbar) {
  navToggle.addEventListener("click", (event) => {
    event.stopPropagation();
    toggleMobileNav();
  });
  mainNav.querySelectorAll("a, button").forEach((el) => {
    el.addEventListener("click", () => {
      if (window.matchMedia("(max-width: 900px)").matches) closeMobileNav();
    });
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && topbar.classList.contains("nav-open")) {
      closeMobileNav();
    }
  });
  window.addEventListener("resize", () => {
    if (window.innerWidth > 900) closeMobileNav();
  });
}

// ----- Confirm modal (replaces browser confirm) -----
const confirmModal = document.querySelector("#confirmModal");
const confirmModalMessage = document.querySelector("#confirmModalMessage");
const confirmModalOk = document.querySelector("#confirmModalOk");
const confirmModalCancel = document.querySelector("#confirmModalCancel");
let pendingForm = null;

function openConfirmModal(message, form) {
  if (!confirmModal || !confirmModalMessage) return false;
  pendingForm = form;
  confirmModalMessage.textContent = message;
  confirmModal.hidden = false;
  confirmModalOk.focus();
  return true;
}

function closeConfirmModal() {
  if (!confirmModal) return;
  confirmModal.hidden = true;
  pendingForm = null;
}

if (confirmModal) {
  document.querySelectorAll(".confirm-form").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const message = form.getAttribute("data-confirm");
      if (!message) return;
      event.preventDefault();
      openConfirmModal(message, form);
    });
  });

  confirmModalOk?.addEventListener("click", () => {
    if (pendingForm) pendingForm.submit();
    closeConfirmModal();
  });

  confirmModalCancel?.addEventListener("click", closeConfirmModal);
  confirmModal.querySelectorAll("[data-modal-close]").forEach((el) => {
    el.addEventListener("click", closeConfirmModal);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && confirmModal && !confirmModal.hidden) {
      closeConfirmModal();
    }
  });
}

// ----- Alerts dropdown (top-right popup) -----
const alertsTrigger = document.querySelector("#alertsTrigger");
const alertsPanel = document.querySelector("#alertsPanel");
const alertsClose = document.querySelector("#alertsClose");
const alertsClearAll = document.querySelector("#alertsClearAll");
const alertsBadge = document.querySelector("#alertsBadge");

function closeAlertsPanel() {
  if (!alertsPanel || !alertsTrigger) return;
  alertsPanel.hidden = true;
  alertsTrigger.setAttribute("aria-expanded", "false");
}

function showAlertsEmpty() {
  if (!alertsPanel) return;
  const body = alertsPanel.querySelector(".alerts-panel-body");
  if (!body || body.querySelector(".alert-item")) return;
  body.innerHTML = '<p class="muted alerts-empty">No notifications yet.</p>';
  alertsClearAll?.remove();
}

async function dismissNotification(id, itemEl) {
  try {
    const response = await fetch(`/api/notifications/${id}`, { method: "DELETE" });
    if (!response.ok) return;
    itemEl.remove();
    showAlertsEmpty();
  } catch (error) {
    /* non-fatal */
  }
}

async function clearAllNotifications() {
  try {
    const response = await fetch("/api/notifications/clear", { method: "POST" });
    if (!response.ok) return;
    alertsPanel.querySelectorAll(".alert-item").forEach((item) => item.remove());
    showAlertsEmpty();
  } catch (error) {
    /* non-fatal */
  }
}

async function openAlertsPanel() {
  if (!alertsPanel || !alertsTrigger) return;
  const isOpen = !alertsPanel.hidden;
  if (isOpen) {
    closeAlertsPanel();
    return;
  }
  alertsPanel.hidden = false;
  alertsTrigger.setAttribute("aria-expanded", "true");
  try {
    await fetch("/api/notifications/mark-read", { method: "POST" });
    if (alertsBadge) alertsBadge.remove();
    alertsPanel.querySelectorAll(".alert-item.unread").forEach((item) => {
      item.classList.remove("unread");
    });
  } catch (error) {
    /* non-fatal */
  }
}

if (alertsTrigger && alertsPanel) {
  alertsTrigger.addEventListener("click", (event) => {
    event.stopPropagation();
    openAlertsPanel();
  });
  alertsClose?.addEventListener("click", closeAlertsPanel);
  alertsClearAll?.addEventListener("click", clearAllNotifications);
  alertsPanel.addEventListener("click", (event) => {
    const dismissBtn = event.target.closest(".alert-dismiss");
    if (!dismissBtn) return;
    event.stopPropagation();
    const item = dismissBtn.closest(".alert-item");
    const id = item?.dataset.notificationId;
    if (id && item) dismissNotification(id, item);
  });
  document.addEventListener("click", (event) => {
    if (!alertsPanel.hidden && !alertsPanel.contains(event.target) && event.target !== alertsTrigger) {
      closeAlertsPanel();
    }
  });
}

// ----- Faculty notes: edit on hover only -----
document.querySelectorAll(".note-editable").forEach((row) => {
  const display = row.querySelector(".note-display");
  const editForm = row.querySelector(".note-edit-form");
  const editToggle = row.querySelector(".note-edit-toggle");
  const editCancel = row.querySelector(".note-edit-cancel");
  const noteText = row.querySelector(".note-text");

  if (!display || !editForm || !editToggle) return;

  function showEdit() {
    display.hidden = true;
    editForm.hidden = false;
  }

  function hideEdit() {
    editForm.hidden = true;
    display.hidden = false;
  }

  editToggle.addEventListener("click", showEdit);
  editCancel?.addEventListener("click", hideEdit);
  editForm.addEventListener("submit", () => {
    if (noteText) noteText.textContent = editForm.querySelector("textarea")?.value || noteText.textContent;
  });
});

// ----- Auto-dismiss flash toasts -----
document.querySelectorAll(".toast").forEach((toast) => {
  setTimeout(() => {
    toast.classList.add("toast-hide");
    setTimeout(() => toast.remove(), 320);
  }, 4200);
});

// ----- AI admissions assistant -----
const launcher = document.querySelector("#chatLauncher");
const panel = document.querySelector("#chatPanel");
const closeButton = document.querySelector("#chatClose");
const form = document.querySelector("#chatForm");
const input = document.querySelector("#chatInput");
const messages = document.querySelector("#chatMessages");

if (launcher && panel && form && input && messages) {
  function escapeHtml(text) {
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function renderMarkdown(text) {
    let safe = escapeHtml(text);
    safe = safe.replace(
      /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener">$1</a>'
    );
    safe = safe.replace(
      /(^|[\s(])(https?:\/\/[^\s<)]+)/g,
      '$1<a href="$2" target="_blank" rel="noopener">$2</a>'
    );
    safe = safe.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

    const lines = safe.split(/\n/);
    let html = "";
    let inList = false;
    for (const line of lines) {
      const item = line.match(/^\s*[-*]\s+(.*)/);
      if (item) {
        if (!inList) {
          html += "<ul>";
          inList = true;
        }
        html += "<li>" + item[1] + "</li>";
      } else {
        if (inList) {
          html += "</ul>";
          inList = false;
        }
        if (line.trim() !== "") {
          html += "<p>" + line + "</p>";
        }
      }
    }
    if (inList) html += "</ul>";
    return html;
  }

  function appendMessage(text, role) {
    const bubble = document.createElement("div");
    bubble.className = role === "user" ? "user-msg" : "assistant-msg";
    if (role === "user") {
      bubble.textContent = text;
    } else {
      bubble.innerHTML = renderMarkdown(text);
    }
    messages.appendChild(bubble);
    messages.scrollTop = messages.scrollHeight;
  }

  launcher.addEventListener("click", () => {
    panel.classList.add("open");
    input.focus();
  });

  closeButton.addEventListener("click", () => {
    panel.classList.remove("open");
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = input.value.trim();
    if (!text) return;

    appendMessage(text, "user");
    input.value = "";
    input.disabled = true;

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const data = await response.json();
      appendMessage(data.reply || data.error || "I could not answer that.", "assistant");
    } catch (error) {
      appendMessage("The AI assistant is unavailable right now.", "assistant");
    } finally {
      input.disabled = false;
      input.focus();
    }
  });
}
