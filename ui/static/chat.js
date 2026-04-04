/**
 * AskVineet — Embeddable Chat Widget
 * Connects to FastAPI backend via REST (with WebSocket upgrade path).
 */

const API_BASE = window.location.origin;
const WS_BASE = window.location.origin.replace(/^http/, "ws");
let sessionId = crypto.randomUUID();
let ws = null;
let isWaiting = false;

// ── DOM helpers ─────────────────────────────────────────────────────────────

const $messages = () => document.getElementById("av-messages");
const $input = () => document.getElementById("av-input");
const $btn = () => document.getElementById("av-send-btn");
const $status = () => document.getElementById("av-status");
const $welcome = () => document.getElementById("av-welcome");
const $charCount = () => document.getElementById("av-char-count");

function setStatus(text) {
  $status().textContent = text;
}

function setWaiting(waiting) {
  isWaiting = waiting;
  $btn().disabled = waiting;
  $input().disabled = waiting;
}

// ── Welcome panel ────────────────────────────────────────────────────────────

function hideWelcome() {
  const w = $welcome();
  if (w) w.remove();
}

// ── Status pill ──────────────────────────────────────────────────────────────

async function checkApiStatus() {
  const dot = document.getElementById("av-status-dot");
  const text = document.getElementById("av-status-text");
  if (!dot || !text) return;

  try {
    const resp = await fetch(`${API_BASE}/health/`, { method: "GET" });
    if (resp.ok) {
      dot.className = "av-status-dot online";
      text.textContent = "API online";
    } else {
      dot.className = "av-status-dot degraded";
      text.textContent = `API ${resp.status}`;
    }
  } catch {
    dot.className = "av-status-dot offline";
    text.textContent = "API offline";
  }
}

// ── Session pill — copy to clipboard ─────────────────────────────────────────

function initSessionPill() {
  const label = document.getElementById("av-session-label");
  if (label) label.textContent = sessionId.slice(0, 8);

  const pill = document.getElementById("av-session-pill");
  if (!pill) return;
  pill.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(sessionId);
    } catch {
      // fallback: noop
    }
    const tooltip = document.getElementById("av-copied-tooltip");
    if (tooltip) {
      tooltip.classList.add("show");
      setTimeout(() => tooltip.classList.remove("show"), 1200);
    }
  });
}

// ── Sidebar collapse ─────────────────────────────────────────────────────────

function initSidebar() {
  const sidebar = document.getElementById("av-sidebar");
  const toggle = document.getElementById("av-sidebar-toggle");
  if (!sidebar || !toggle) return;

  // Restore persisted state
  if (localStorage.getItem("av-sidebar-collapsed") === "1") {
    sidebar.classList.add("collapsed");
  }

  toggle.addEventListener("click", () => {
    sidebar.classList.toggle("collapsed");
    localStorage.setItem(
      "av-sidebar-collapsed",
      sidebar.classList.contains("collapsed") ? "1" : "0",
    );
  });

  // New conversation button
  const newChat = document.getElementById("av-new-chat");
  if (newChat) {
    newChat.addEventListener("click", () => {
      sessionId = crypto.randomUUID();
      $messages().innerHTML = "";
      // Re-add welcome
      $messages().insertAdjacentHTML("afterbegin", welcomeHTML());
      initChips();
      const label = document.getElementById("av-session-label");
      if (label) label.textContent = sessionId.slice(0, 8);
      setStatus(`session: ${sessionId.slice(0, 8)} · ready`);
    });
  }
}

function welcomeHTML() {
  return `<div class="av-welcome" id="av-welcome">
    <div class="av-welcome-heading">&gt; Ask me anything</div>
    <div class="av-welcome-subtitle">Upload a doc or try one of these:</div>
    <div class="av-welcome-chips">
      <button class="av-chip" data-prompt="Summarize a PDF">Summarize a PDF</button>
      <button class="av-chip" data-prompt="Explain this document">Explain this document</button>
      <button class="av-chip" data-prompt="Find key insights">Find key insights</button>
      <button class="av-chip" data-prompt="Compare two files">Compare two files</button>
    </div>
  </div>`;
}

// ── Prompt chips ─────────────────────────────────────────────────────────────

function initChips() {
  document.querySelectorAll(".av-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const input = $input();
      input.value = chip.dataset.prompt;
      input.focus();
      autoResizeTextarea(input);
      updateCharCount();
    });
  });
}

// ── Mobile hamburger ─────────────────────────────────────────────────────────

function initMobileMenu() {
  const hamburger = document.getElementById("av-hamburger");
  const sidebar = document.getElementById("av-sidebar");
  const overlay = document.getElementById("av-overlay");
  if (!hamburger || !sidebar || !overlay) return;

  hamburger.addEventListener("click", () => {
    sidebar.classList.add("mobile-open");
    overlay.classList.add("active");
  });

  overlay.addEventListener("click", () => {
    sidebar.classList.remove("mobile-open");
    overlay.classList.remove("active");
  });
}

// ── File upload (paperclip) ──────────────────────────────────────────────────

function initFileUpload() {
  const attachBtn = document.getElementById("av-attach-btn");
  const fileInput = document.getElementById("av-file-input");
  if (!attachBtn || !fileInput) return;

  attachBtn.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", async () => {
    const file = fileInput.files[0];
    if (!file) return;
    setStatus(`Uploading ${file.name}…`);
    try {
      const form = new FormData();
      form.append("file", file);
      const resp = await fetch(`${API_BASE}/documents/upload`, {
        method: "POST",
        body: form,
      });
      if (resp.ok) {
        setStatus(`Uploaded: ${file.name}`);
      } else {
        setStatus(`Upload failed (${resp.status})`);
      }
    } catch {
      setStatus("Upload error — is the API running?");
    }
    fileInput.value = "";
  });
}

// ── Textarea auto-resize + char counter ──────────────────────────────────────

function autoResizeTextarea(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 144) + "px";
  el.style.overflowY = el.scrollHeight > 144 ? "auto" : "hidden";
}

function updateCharCount() {
  const counter = $charCount();
  if (!counter) return;
  const len = $input().value.length;
  counter.textContent = `${len} / 1000`;
  counter.classList.toggle("warn", len > 900);
}

// ── Message rendering ────────────────────────────────────────────────────────

function appendMessage(role, content, sources = [], route = "") {
  hideWelcome();

  const el = document.createElement("div");
  el.className = `av-msg av-msg--${role}`;

  if (role === "assistant") {
    el.innerHTML = `<span class="av-prefix">[AskVineet]</span>${escapeHtml(content)}`;

    if (sources && sources.length > 0) {
      const srcDiv = document.createElement("div");
      srcDiv.className = "av-sources";
      srcDiv.innerHTML = `📄 Sources (${sources.length}):`;
      sources.forEach((src) => {
        const item = document.createElement("div");
        item.className = "av-source-item";
        item.textContent = `${src.filename || src.source}${src.page ? " · p." + src.page : ""}: ${(src.excerpt || "").slice(0, 150)}…`;
        srcDiv.appendChild(item);
      });
      el.appendChild(srcDiv);
    }
  } else {
    el.innerHTML = `<span class="av-prefix">[You]</span>${escapeHtml(content)}`;
  }

  $messages().appendChild(el);
  $messages().scrollTop = $messages().scrollHeight;
  return el;
}

function appendTypingIndicator() {
  hideWelcome();

  const el = document.createElement("div");
  el.className = "av-typing-indicator";
  el.id = "av-typing";
  el.innerHTML =
    `<span class="av-prefix">[AskVineet]</span>` +
    `<span class="av-typing-block"></span>` +
    `<span class="av-typing-block"></span>` +
    `<span class="av-typing-block"></span>`;
  $messages().appendChild(el);
  $messages().scrollTop = $messages().scrollHeight;
  return el;
}

function removeTypingIndicator() {
  const el = document.getElementById("av-typing");
  if (el) el.remove();
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\n/g, "<br/>");
}

// ── Send message ─────────────────────────────────────────────────────────────

async function sendMessage() {
  const input = $input();
  const message = input.value.trim();
  if (!message || isWaiting) return;

  input.value = "";
  input.style.height = "auto";
  updateCharCount();
  appendMessage("user", message);
  setWaiting(true);
  setStatus("thinking...");

  const typing = appendTypingIndicator();

  try {
    const resp = await fetch(`${API_BASE}/chat/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: sessionId }),
    });

    removeTypingIndicator();

    if (!resp.ok) {
      const err = await resp.text();
      appendMessage("assistant", `⚠️ API error (${resp.status}): ${err}`);
      setStatus("error");
    } else {
      const data = await resp.json();
      appendMessage(
        "assistant",
        data.answer,
        data.sources || [],
        data.route_used,
      );
      setStatus(
        `route: ${data.route_used} · session: ${sessionId.slice(0, 8)}`,
      );
    }
  } catch (err) {
    removeTypingIndicator();
    appendMessage(
      "assistant",
      "❌ Cannot reach AskVineet API. Is the backend running?\n" +
        "Start it with: uvicorn app.main:app --reload",
    );
    setStatus("disconnected");
    console.error("AskVineet API error:", err);
  } finally {
    setWaiting(false);
    input.focus();
  }
}

// ── Keyboard shortcuts ───────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  const input = $input();

  // Send button click
  $btn().addEventListener("click", () => sendMessage());

  // Enter / Cmd+Enter to send
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.metaKey || !e.shiftKey)) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Auto-resize + char count
  input.addEventListener("input", () => {
    autoResizeTextarea(input);
    updateCharCount();
  });

  // Init all UI features
  initSessionPill();
  initSidebar();
  initChips();
  initMobileMenu();
  initFileUpload();
  checkApiStatus();
  updateCharCount();

  input.focus();
  setStatus(`session: ${sessionId.slice(0, 8)} · ready`);

  // Poll API status every 30s
  setInterval(checkApiStatus, 30000);
});
