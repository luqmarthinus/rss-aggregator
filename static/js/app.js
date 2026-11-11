"use strict";

const PAGE_SIZE = 50;

const state = {
    apiKey: sessionStorage.getItem("apiKey") || "",
    feeds: [],
    currentFeedId: null, // null = all feeds
    offset: 0,
    hasMore: false,
};

const $ = (id) => document.getElementById(id);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str).replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
}

// Only allow http(s) links so a malicious feed can't inject javascript: URLs.
function safeUrl(url) {
    try {
        const u = new URL(url, window.location.href);
        return u.protocol === "http:" || u.protocol === "https:" ? u.href : "#";
    } catch {
        return "#";
    }
}

function timeAgo(iso) {
    if (!iso) return "";
    const date = new Date(iso);
    const seconds = Math.round((Date.now() - date.getTime()) / 1000);
    const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
    const units = [["year", 31536000], ["month", 2592000], ["week", 604800], ["day", 86400], ["hour", 3600], ["minute", 60]];
    for (const [unit, secs] of units) {
        if (Math.abs(seconds) >= secs) return rtf.format(-Math.round(seconds / secs), unit);
    }
    return "just now";
}

function debounce(fn, ms) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

function toast(message, variant = "success") {
    const el = document.createElement("div");
    el.className = `toast align-items-center text-bg-${variant} border-0`;
    el.setAttribute("role", "status");
    el.innerHTML = `<div class="d-flex"><div class="toast-body">${escapeHtml(message)}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button></div>`;
    $("toastContainer").appendChild(el);
    el.addEventListener("hidden.bs.toast", () => el.remove());
    new bootstrap.Toast(el, { delay: 4000 }).show();
}

class ApiError extends Error {
    constructor(status, detail) {
        super(detail || `HTTP ${status}`);
        this.status = status;
    }
}

async function apiCall(url, options = {}) {
    const headers = { ...(options.headers || {}) };
    if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
    if (state.apiKey) headers["X-API-Key"] = state.apiKey;
    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
        let detail = "";
        try { detail = (await res.json()).detail; } catch { /* non-JSON body */ }
        if (typeof detail !== "string") detail = "";
        if (res.status === 403 || res.status === 422 && !state.apiKey) detail = "Missing or invalid API key — click “API Key” to set it.";
        if (res.status === 429) detail = "Too many requests — please wait a moment.";
        throw new ApiError(res.status, detail);
    }
    return res.json();
}

function requireApiKey() {
    if (state.apiKey) return true;
    toast("Set your API key first (click “API Key”).", "warning");
    return false;
}

function updateApiKeyButton() {
    const btn = $("apiKeyBtn");
    btn.classList.toggle("btn-outline-warning", !state.apiKey);
    btn.classList.toggle("btn-outline-success", !!state.apiKey);
    btn.innerHTML = state.apiKey ? '<i class="bi-key-fill"></i> Key set' : '<i class="bi-key"></i> API Key';
}

// ---------------------------------------------------------------------------
// Feeds
// ---------------------------------------------------------------------------

function renderFeeds() {
    const totalUnread = state.feeds.reduce((n, f) => n + f.unread_count, 0);
    const item = (id, label, unread, extra = "") => `
        <div class="list-group-item list-group-item-action feed-item ${String(state.currentFeedId) === String(id) ? "active" : ""}"
             data-id="${escapeHtml(id)}" role="button" tabindex="0">
            <i class="bi-rss-fill"></i>
            <span class="feed-name" title="${escapeHtml(label)}">${escapeHtml(label)}</span>
            ${unread ? `<span class="badge rounded-pill text-bg-secondary">${unread}</span>` : ""}
            ${extra}
        </div>`;

    $("feedsList").innerHTML =
        item(null, "All feeds", totalUnread) +
        (state.feeds.length
            ? state.feeds.map((f) => item(f.id, f.title || f.url, f.unread_count,
                `<button class="btn btn-sm btn-danger delete-feed" data-id="${f.id}" aria-label="Delete feed"><i class="bi-trash"></i></button>`)).join("")
            : `<div class="empty-state small py-3">No feeds yet. Click <b>Add</b> to subscribe.</div>`);

    $("feedFilter").innerHTML = '<option value="all">All feeds</option>' +
        state.feeds.map((f) => `<option value="${f.id}">${escapeHtml(f.title || f.url)}</option>`).join("");
    $("feedFilter").value = state.currentFeedId ?? "all";
}

async function loadFeeds() {
    try {
        state.feeds = await apiCall("/feeds");
        if (state.currentFeedId !== null && !state.feeds.some((f) => String(f.id) === String(state.currentFeedId))) {
            state.currentFeedId = null;
        }
        renderFeeds();
    } catch (err) {
        console.error("Failed to load feeds:", err);
        toast(`Failed to load feeds: ${err.message}`, "danger");
    }
}

async function loadStats() {
    try {
        const s = await apiCall("/stats");
        $("statsBadge").textContent = `${s.unread} unread · ${s.articles} articles · ${s.feeds} feeds`;
    } catch { /* non-critical */ }
}

function selectFeed(id) {
    state.currentFeedId = id === "null" || id === "all" || id === null ? null : id;
    renderFeeds();
    loadArticles();
}

async function deleteFeed(id) {
    if (!requireApiKey()) return;
    if (!confirm("Delete this feed and all its articles?")) return;
    try {
        await apiCall(`/feeds/${id}`, { method: "DELETE" });
        if (String(state.currentFeedId) === String(id)) state.currentFeedId = null;
        toast("Feed deleted");
        await refreshAll();
    } catch (err) {
        toast(`Delete failed: ${err.message}`, "danger");
    }
}

async function addFeed() {
    const input = $("feedUrl");
    const url = input.value.trim();
    if (!url || !requireApiKey()) return;
    const btn = $("confirmAddFeed");
    btn.disabled = true;
    try {
        const feed = await apiCall("/feeds", { method: "POST", body: JSON.stringify({ url }) });
        bootstrap.Modal.getOrCreateInstance($("addFeedModal")).hide();
        input.value = "";
        toast("Feed added — fetching articles…");
        state.currentFeedId = feed.id;
        await loadFeeds();
        await loadArticles();
        // The server fetches the new feed in the background; pick up its articles shortly.
        setTimeout(refreshAll, 3000);
    } catch (err) {
        toast(`Failed to add feed: ${err.message}`, "danger");
    } finally {
        btn.disabled = false;
    }
}

// ---------------------------------------------------------------------------
// Articles
// ---------------------------------------------------------------------------

function articleQuery(offset) {
    const params = new URLSearchParams({ limit: PAGE_SIZE, offset });
    if (state.currentFeedId !== null) params.set("feed_id", state.currentFeedId);
    const readFilter = $("readFilter").value;
    if (readFilter !== "all") params.set("is_read", readFilter === "read");
    const search = $("searchInput").value.trim();
    if (search) params.set("search", search);
    return `/articles?${params}`;
}

function renderArticle(a) {
    const feed = state.feeds.find((f) => f.id === a.feed_id);
    const feedName = feed ? feed.title || feed.url : "";
    const published = a.published_at ? new Date(a.published_at) : null;
    return `
        <div class="card article-card ${a.is_read ? "article-read" : ""}" data-id="${a.id}">
            <div class="card-body">
                <h5 class="card-title">
                    <a href="${escapeHtml(safeUrl(a.link))}" target="_blank" rel="noopener noreferrer"
                       class="text-reset text-decoration-none open-article">${escapeHtml(a.title)}</a>
                </h5>
                <div class="article-meta">
                    ${feedName ? `<span><i class="bi-rss"></i> ${escapeHtml(feedName)}</span>` : ""}
                    ${published ? `<span class="ms-2" title="${escapeHtml(published.toLocaleString())}"><i class="bi-clock"></i> ${escapeHtml(timeAgo(a.published_at))}</span>` : ""}
                </div>
                <div class="card-text mb-2">${DOMPurify.sanitize(a.summary || "", { FORBID_TAGS: ["style", "form", "iframe"] })}</div>
                <a href="${escapeHtml(safeUrl(a.link))}" target="_blank" rel="noopener noreferrer" class="btn btn-sm btn-outline-primary open-article">Read original</a>
                <button class="btn btn-sm btn-outline-secondary mark-read" data-id="${a.id}" data-read="${a.is_read}">${a.is_read ? "Mark unread" : "Mark read"}</button>
            </div>
        </div>`;
}

async function loadArticles({ append = false } = {}) {
    const container = $("articlesContainer");
    const offset = append ? state.offset : 0;
    try {
        const articles = await apiCall(articleQuery(offset));
        // Make every link in sanitized summaries open safely in a new tab.
        DOMPurify.addHook("afterSanitizeAttributes", (node) => {
            if (node.tagName === "A") { node.setAttribute("target", "_blank"); node.setAttribute("rel", "noopener noreferrer"); }
        });
        const html = articles.map(renderArticle).join("");
        DOMPurify.removeHook("afterSanitizeAttributes");

        if (append) {
            container.insertAdjacentHTML("beforeend", html);
        } else if (!articles.length) {
            const unreadOnly = $("readFilter").value === "unread";
            container.innerHTML = `<div class="empty-state"><i class="bi-inbox d-block"></i>${
                unreadOnly ? "You're all caught up!" : state.feeds.length ? "No articles found." : "Add a feed to get started."}</div>`;
        } else {
            container.innerHTML = html;
        }
        state.offset = offset + articles.length;
        state.hasMore = articles.length === PAGE_SIZE;
        $("loadMoreBtn").classList.toggle("d-none", !state.hasMore);
    } catch (err) {
        console.error("Failed to load articles:", err);
        toast(`Failed to load articles: ${err.message}`, "danger");
    }
}

async function setRead(card, isRead, { silent = false } = {}) {
    if (!state.apiKey) { if (!silent) requireApiKey(); return; }
    const id = card.dataset.id;
    try {
        await apiCall(`/articles/${id}/read`, { method: "PUT", body: JSON.stringify({ is_read: isRead }) });
        card.classList.toggle("article-read", isRead);
        const btn = card.querySelector(".mark-read");
        btn.dataset.read = String(isRead);
        btn.textContent = isRead ? "Mark unread" : "Mark read";
        await Promise.all([loadFeeds(), loadStats()]);
    } catch (err) {
        if (!silent) toast(`Could not update article: ${err.message}`, "danger");
    }
}

async function markAllRead() {
    if (!requireApiKey()) return;
    const scope = state.currentFeedId === null ? "all feeds" : "this feed";
    if (!confirm(`Mark every unread article in ${scope} as read?`)) return;
    try {
        const params = state.currentFeedId === null ? "" : `?feed_id=${encodeURIComponent(state.currentFeedId)}`;
        const res = await apiCall(`/articles/mark-all-read${params}`, { method: "POST" });
        toast(`Marked ${res.updated} article${res.updated === 1 ? "" : "s"} as read`);
        await refreshAll();
    } catch (err) {
        toast(`Failed: ${err.message}`, "danger");
    }
}

// ---------------------------------------------------------------------------
// Refresh / OPML / API key
// ---------------------------------------------------------------------------

async function refreshAll() {
    await loadFeeds();
    await Promise.all([loadArticles(), loadStats()]);
}

async function manualRefresh() {
    if (!requireApiKey()) return;
    const btn = $("refreshBtn");
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Refreshing…';
    try {
        await apiCall("/refresh", { method: "POST" });
        // Poll until the background refresh finishes (max ~2 minutes).
        for (let i = 0; i < 60; i++) {
            await new Promise((r) => setTimeout(r, 2000));
            const { refreshing } = await apiCall("/refresh/status");
            if (!refreshing) break;
        }
        await refreshAll();
        toast("Feeds refreshed");
    } catch (err) {
        toast(`Refresh failed: ${err.message}`, "danger");
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi-arrow-repeat"></i> Refresh';
    }
}

function setApiKey() {
    const key = prompt("Enter your API key (for write operations). Leave empty to clear:", "");
    if (key === null) return;
    state.apiKey = key.trim();
    if (state.apiKey) sessionStorage.setItem("apiKey", state.apiKey);
    else sessionStorage.removeItem("apiKey");
    updateApiKeyButton();
    toast(state.apiKey ? "API key saved for this session" : "API key cleared", "info");
}

function exportOpml() {
    window.location.href = "/feeds/export.opml";
}

function importOpml() {
    if (!requireApiKey()) return;
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".opml,.xml,text/xml,text/x-opml";
    input.onchange = async () => {
        const file = input.files[0];
        if (!file) return;
        const formData = new FormData();
        formData.append("file", file);
        try {
            const res = await apiCall("/feeds/import.opml", { method: "POST", body: formData });
            let msg = `Imported ${res.added} feed${res.added === 1 ? "" : "s"}`;
            if (res.skipped) msg += `, ${res.skipped} already subscribed`;
            if (res.rejected.length) msg += `, ${res.rejected.length} rejected`;
            toast(msg);
            state.currentFeedId = null;
            await refreshAll();
            if (res.added) setTimeout(refreshAll, 5000);
        } catch (err) {
            toast(`Import failed: ${err.message}`, "danger");
        }
    };
    input.click();
}

// ---------------------------------------------------------------------------
// Wiring
// ---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
    updateApiKeyButton();
    $("apiKeyBtn").onclick = setApiKey;
    $("refreshBtn").onclick = manualRefresh;
    $("addFeedBtn").onclick = () => {
        if (!requireApiKey()) return;
        bootstrap.Modal.getOrCreateInstance($("addFeedModal")).show();
    };
    $("addFeedModal").addEventListener("shown.bs.modal", () => $("feedUrl").focus());
    $("confirmAddFeed").onclick = addFeed;
    $("feedUrl").addEventListener("keydown", (e) => { if (e.key === "Enter") addFeed(); });
    $("exportOpmlBtn").onclick = exportOpml;
    $("importOpmlBtn").onclick = importOpml;
    $("markAllReadBtn").onclick = markAllRead;
    $("loadMoreBtn").onclick = () => loadArticles({ append: true });
    $("searchInput").addEventListener("input", debounce(() => loadArticles(), 300));
    $("readFilter").onchange = () => loadArticles();
    $("feedFilter").onchange = (e) => selectFeed(e.target.value);

    // Event delegation: the lists are re-rendered, so bind once on the containers.
    $("feedsList").addEventListener("click", (e) => {
        const del = e.target.closest(".delete-feed");
        if (del) { e.stopPropagation(); deleteFeed(del.dataset.id); return; }
        const item = e.target.closest(".feed-item");
        if (item) selectFeed(item.dataset.id || null);
    });
    $("feedsList").addEventListener("keydown", (e) => {
        const item = e.target.closest(".feed-item");
        if (item && e.target === item && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); selectFeed(item.dataset.id || null); }
    });
    $("articlesContainer").addEventListener("click", (e) => {
        const card = e.target.closest(".article-card");
        if (!card) return;
        const toggle = e.target.closest(".mark-read");
        if (toggle) { setRead(card, toggle.dataset.read !== "true"); return; }
        // Opening an article marks it read (when an API key is set).
        if (e.target.closest(".open-article") && !card.classList.contains("article-read")) setRead(card, true, { silent: true });
    });

    refreshAll();
});
