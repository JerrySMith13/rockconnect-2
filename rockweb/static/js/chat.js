(function () {
    "use strict";

    const API = "/api/conversations/";
    const POLL_INTERVAL = 5000;
    const CSRF = document.querySelector("[name=csrfmiddlewaretoken]").value;

    // ── State ───────────────────────────────────────────────
    let conversations = [];
    let activeConvId = null;
    let messages = [];
    let currentUserId = null;
    let pollTimer = null;

    // ── DOM refs ────────────────────────────────────────────
    const convListEl = document.getElementById("conversation-list");
    const chatMain = document.getElementById("chat-main");
    const chatApp = document.getElementById("chat-app");
    const searchInput = document.getElementById("sidebar-search");

    // ── Fetch helpers ───────────────────────────────────────

    async function api(url, opts = {}) {
        const headers = { "X-CSRFToken": CSRF, ...opts.headers };
        if (opts.body && typeof opts.body === "object") {
            headers["Content-Type"] = "application/json";
            opts.body = JSON.stringify(opts.body);
        }
        const resp = await fetch(url, { ...opts, headers });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.error || `HTTP ${resp.status}`);
        }
        return resp.json();
    }

    // ── Init ────────────────────────────────────────────────

    async function init() {
        const me = await api("/api/users/me/");
        currentUserId = me.id;
        await loadConversations();
        startPolling();
    }

    // ── Conversations ───────────────────────────────────────

    async function loadConversations() {
        conversations = await api(API);
        renderConversationList();
    }

    function getConvDisplayName(conv) {
        if (conv.title) return conv.title;
        const others = conv.members.filter((m) => m.id !== currentUserId);
        if (others.length === 0) return "You";
        return others.map((m) => m.username).join(", ");
    }

    function getConvInitial(conv) {
        const name = getConvDisplayName(conv);
        return name.charAt(0).toUpperCase();
    }

    function formatTime(iso) {
        const d = new Date(iso);
        const now = new Date();
        const diff = now - d;
        if (diff < 86400000 && d.getDate() === now.getDate()) {
            return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        }
        if (diff < 604800000) {
            return d.toLocaleDateString([], { weekday: "short" });
        }
        return d.toLocaleDateString([], { month: "short", day: "numeric" });
    }

    function formatDateDivider(iso) {
        const d = new Date(iso);
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const msgDay = new Date(d.getFullYear(), d.getMonth(), d.getDate());
        const diff = today - msgDay;
        if (diff === 0) return "Today";
        if (diff === 86400000) return "Yesterday";
        return d.toLocaleDateString([], { weekday: "long", month: "long", day: "numeric" });
    }

    function renderConversationList(filter = "") {
        const q = filter.toLowerCase();
        const filtered = q
            ? conversations.filter((c) => getConvDisplayName(c).toLowerCase().includes(q))
            : conversations;

        if (filtered.length === 0) {
            convListEl.innerHTML = `<li class="sidebar-empty">${q ? "No matching conversations" : "No conversations yet"}</li>`;
            return;
        }

        convListEl.innerHTML = filtered
            .map((c) => {
                const name = getConvDisplayName(c);
                const preview = c.last_message
                    ? `${c.last_message.sender}: ${c.last_message.body}`
                    : "No messages yet";
                const time = c.last_message ? formatTime(c.last_message.created_at) : "";
                const active = c.id === activeConvId ? " active" : "";
                const unread = c.unread_count > 0
                    ? `<span class="conv-unread">${c.unread_count}</span>`
                    : "";
                return `
                <li class="conversation-item${active}" data-id="${c.id}">
                    <div class="conv-avatar">${getConvInitial(c)}</div>
                    <div class="conv-info">
                        <div class="conv-name">${esc(name)}</div>
                        <div class="conv-preview">${esc(preview)}</div>
                    </div>
                    <div class="conv-meta">
                        <div class="conv-time">${esc(time)}</div>
                        ${unread}
                    </div>
                </li>`;
            })
            .join("");

        convListEl.querySelectorAll(".conversation-item").forEach((el) => {
            el.addEventListener("click", () => openConversation(parseInt(el.dataset.id)));
        });
    }

    // ── Open conversation ───────────────────────────────────

    async function openConversation(convId) {
        activeConvId = convId;
        chatApp.classList.add("conv-open");
        renderConversationList(searchInput.value);

        const conv = conversations.find((c) => c.id === convId);
        if (!conv) return;

        const membersText = conv.members.map((m) => m.username).join(", ");

        chatMain.innerHTML = `
            <div class="chat-header">
                <button class="back-btn" id="back-btn">&larr;</button>
                <div class="conv-avatar">${getConvInitial(conv)}</div>
                <div class="chat-header-info">
                    <div class="chat-header-name">${esc(getConvDisplayName(conv))}</div>
                    <div class="chat-header-members">${esc(membersText)}</div>
                </div>
            </div>
            <div class="message-list" id="message-list"></div>
            <div class="chat-compose">
                <textarea class="compose-input" id="compose-input" rows="1" placeholder="Type a message..."></textarea>
                <button class="compose-send" id="compose-send" disabled>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
                </button>
            </div>`;

        document.getElementById("back-btn").addEventListener("click", closeConversation);
        setupCompose();
        await loadMessages();
        markRead(convId);
    }

    function closeConversation() {
        activeConvId = null;
        chatApp.classList.remove("conv-open");
        chatMain.innerHTML = `<div class="chat-placeholder">Select a conversation to start messaging</div>`;
        renderConversationList(searchInput.value);
    }

    // ── Messages ────────────────────────────────────────────

    async function loadMessages() {
        messages = await api(`${API}${activeConvId}/messages/?limit=50`);
        renderMessages();
        scrollToBottom();
    }

    function renderMessages() {
        const listEl = document.getElementById("message-list");
        if (!listEl) return;

        if (messages.length === 0) {
            listEl.innerHTML = `<div class="chat-placeholder" style="flex:1">No messages yet. Say hello!</div>`;
            return;
        }

        let html = "";
        let lastDate = "";

        // Load-more button
        if (messages.length >= 50) {
            html += `<div class="load-more"><button class="load-more-btn" id="load-more-btn">Load older messages</button></div>`;
        }

        for (const msg of messages) {
            const msgDate = formatDateDivider(msg.created_at);
            if (msgDate !== lastDate) {
                html += `<div class="msg-date-divider">${msgDate}</div>`;
                lastDate = msgDate;
            }

            if (msg.is_system) {
                html += `<div class="msg-system">${esc(msg.body)}</div>`;
                continue;
            }

            const isOwn = msg.sender && msg.sender.id === currentUserId;
            const initial = msg.sender ? msg.sender.username.charAt(0).toUpperCase() : "?";
            const senderName = msg.sender ? msg.sender.username : "Deleted user";
            const time = new Date(msg.created_at).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
            });
            const edited = msg.edited_at ? ` <span class="msg-edited">(edited)</span>` : "";

            html += `
            <div class="msg-group${isOwn ? " own" : ""}" data-msg-id="${msg.id}">
                <div class="msg-avatar">${initial}</div>
                <div class="msg-content">
                    <div class="msg-sender">${esc(senderName)}</div>
                    <div class="msg-bubble">${esc(msg.body)}${edited}</div>
                    <div class="msg-time">${time}</div>
                </div>
            </div>`;
        }

        listEl.innerHTML = html;

        const loadMoreBtn = document.getElementById("load-more-btn");
        if (loadMoreBtn) {
            loadMoreBtn.addEventListener("click", loadOlderMessages);
        }
    }

    async function loadOlderMessages() {
        if (messages.length === 0) return;
        const oldestId = messages[0].id;
        const older = await api(`${API}${activeConvId}/messages/?before=${oldestId}&limit=50`);
        if (older.length === 0) {
            const btn = document.getElementById("load-more-btn");
            if (btn) btn.remove();
            return;
        }
        messages = [...older, ...messages];
        renderMessages();
    }

    function scrollToBottom() {
        const listEl = document.getElementById("message-list");
        if (listEl) {
            listEl.scrollTop = listEl.scrollHeight;
        }
    }

    // ── Compose ─────────────────────────────────────────────

    function setupCompose() {
        const input = document.getElementById("compose-input");
        const sendBtn = document.getElementById("compose-send");

        input.addEventListener("input", () => {
            sendBtn.disabled = !input.value.trim();
            // Auto-resize
            input.style.height = "auto";
            input.style.height = Math.min(input.scrollHeight, 120) + "px";
        });

        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (input.value.trim()) sendMessage();
            }
        });

        sendBtn.addEventListener("click", sendMessage);
    }

    async function sendMessage() {
        const input = document.getElementById("compose-input");
        const body = input.value.trim();
        if (!body || !activeConvId) return;

        input.value = "";
        input.style.height = "auto";
        document.getElementById("compose-send").disabled = true;

        try {
            const msg = await api(`${API}${activeConvId}/messages/`, {
                method: "POST",
                body: { body },
            });
            messages.push(msg);
            renderMessages();
            scrollToBottom();
            // Refresh sidebar to update preview / ordering
            loadConversations();
        } catch (err) {
            input.value = body;
            document.getElementById("compose-send").disabled = false;
        }
    }

    // ── Mark read ───────────────────────────────────────────

    async function markRead(convId) {
        try {
            await api(`${API}${convId}/read/`, { method: "POST" });
            const conv = conversations.find((c) => c.id === convId);
            if (conv) conv.unread_count = 0;
            renderConversationList(searchInput.value);
        } catch { /* ignore */ }
    }

    // ── Polling ─────────────────────────────────────────────

    function startPolling() {
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(async () => {
            await loadConversations();
            if (activeConvId) {
                const lastId = messages.length ? messages[messages.length - 1].id : 0;
                // Fetch only new messages since last known
                try {
                    const all = await api(`${API}${activeConvId}/messages/?limit=50`);
                    const newMsgs = all.filter((m) => m.id > lastId);
                    if (newMsgs.length > 0) {
                        messages.push(...newMsgs);
                        renderMessages();
                        scrollToBottom();
                        markRead(activeConvId);
                    }
                } catch { /* ignore */ }
            }
        }, POLL_INTERVAL);
    }

    // ── New conversation modal ──────────────────────────────

    document.getElementById("new-conv-btn").addEventListener("click", () => {
        document.getElementById("new-conv-modal").classList.add("visible");
        document.getElementById("new-conv-username").value = "";
        document.getElementById("new-conv-title").value = "";
        document.getElementById("new-conv-error").style.display = "none";
        document.getElementById("new-conv-username").focus();
    });

    document.getElementById("new-conv-cancel").addEventListener("click", () => {
        document.getElementById("new-conv-modal").classList.remove("visible");
    });

    document.getElementById("new-conv-modal").addEventListener("click", (e) => {
        if (e.target === e.currentTarget) {
            e.currentTarget.classList.remove("visible");
        }
    });

    document.getElementById("new-conv-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const errorEl = document.getElementById("new-conv-error");
        errorEl.style.display = "none";

        const usernames = document.getElementById("new-conv-username").value
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean);

        if (usernames.length === 0) {
            errorEl.textContent = "Enter at least one username.";
            errorEl.style.display = "block";
            return;
        }

        try {
            // Look up user IDs
            const memberIds = [];
            for (const username of usernames) {
                const user = await api(`/api/users/${encodeURIComponent(username)}/`);
                memberIds.push(user.id);
            }

            const title = document.getElementById("new-conv-title").value.trim();
            const payload = { member_ids: memberIds };
            if (title) payload.title = title;
            if (memberIds.length > 1) payload.is_group = true;

            const conv = await api(API, { method: "POST", body: payload });
            document.getElementById("new-conv-modal").classList.remove("visible");
            await loadConversations();
            openConversation(conv.id);
        } catch (err) {
            errorEl.textContent = err.message;
            errorEl.style.display = "block";
        }
    });

    // ── Sidebar search ──────────────────────────────────────

    searchInput.addEventListener("input", () => {
        renderConversationList(searchInput.value);
    });

    // ── Utility ─────────────────────────────────────────────

    function esc(str) {
        const d = document.createElement("div");
        d.textContent = str;
        return d.innerHTML;
    }

    // ── Boot ────────────────────────────────────────────────
    init();
})();
