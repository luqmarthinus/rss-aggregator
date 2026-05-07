let apiKey = sessionStorage.getItem("apiKey") || "";
let currentFeedId = null;

function setApiKey() {
    const key = prompt("Enter your API key (for write operations):");
    if (key) {
        apiKey = key;
        sessionStorage.setItem("apiKey", key);
        alert("API key saved for this session");
    }
}

function apiHeaders() {
    const headers = { "Content-Type": "application/json" };
    if (apiKey) headers["X-API-Key"] = apiKey;
    return headers;
}

async function apiCall(url, options = {}) {
    const res = await fetch(url, { ...options, headers: apiHeaders() });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

async function loadFeeds() {
    const feeds = await apiCall("/feeds");
    const container = document.getElementById("feedsList");
    container.innerHTML = feeds.map(f => `
        <a href="#" class="list-group-item list-group-item-action feed-item" data-id="${f.id}">
            <i class="bi-rss-fill"></i> ${escapeHtml(f.title || f.url)}
            <button class="btn btn-sm btn-danger float-end delete-feed" data-id="${f.id}"><i class="bi-trash"></i></button>
        </a>
    `).join("");
    // Feed filter dropdown
    const filterSelect = document.getElementById("feedFilter");
    filterSelect.innerHTML = '<option value="all">All feeds</option>' + feeds.map(f => `<option value="${f.id}">${escapeHtml(f.title || f.url)}</option>`).join("");
    attachFeedEvents();
}

function attachFeedEvents() {
    document.querySelectorAll(".feed-item").forEach(el => {
        el.addEventListener("click", (e) => {
            if (e.target.classList.contains("delete-feed")) return;
            currentFeedId = el.dataset.id;
            loadArticles();
        });
    });
    document.querySelectorAll(".delete-feed").forEach(btn => {
        btn.addEventListener("click", async (e) => {
            e.stopPropagation();
            const id = btn.dataset.id;
            if (confirm("Delete feed?")) {
                await apiCall(`/feeds/${id}`, { method: "DELETE" });
                loadFeeds();
                loadArticles();
            }
        });
    });
}

async function loadArticles() {
    let url = "/articles?limit=100";
    if (currentFeedId && currentFeedId !== "all") url += `&feed_id=${currentFeedId}`;
    const readFilter = document.getElementById("readFilter").value;
    if (readFilter === "unread") url += "&is_read=false";
    if (readFilter === "read") url += "&is_read=true";
    const search = document.getElementById("searchInput").value;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    const articles = await apiCall(url);
    const container = document.getElementById("articlesContainer");
    if (!articles.length) { container.innerHTML = "<p class='text-muted'>No articles found.</p>"; return; }
    container.innerHTML = articles.map(a => `
        <div class="card article-card ${a.is_read ? 'article-read' : ''}">
            <div class="card-body">
                <h5 class="card-title">${escapeHtml(a.title)}</h5>
                <div class="card-text">${DOMPurify.sanitize(a.summary || "")}</div>
                <a href="${a.link}" target="_blank" class="btn btn-sm btn-outline-primary">Read original</a>
                <button class="btn btn-sm btn-outline-secondary mark-read" data-id="${a.id}" data-read="${a.is_read}">${a.is_read ? "Mark unread" : "Mark read"}</button>
                <small class="text-muted float-end">${a.published_at ? new Date(a.published_at).toLocaleString() : ""}</small>
            </div>
        </div>
    `).join("");
    document.querySelectorAll(".mark-read").forEach(btn => {
        btn.addEventListener("click", async () => {
            const id = btn.dataset.id;
            const newRead = btn.dataset.read === "true" ? false : true;
            await apiCall(`/articles/${id}/read`, { method: "PUT", body: JSON.stringify({ is_read: newRead }) });
            loadArticles();
        });
    });
}

async function addFeed() {
    const url = document.getElementById("feedUrl").value;
    await apiCall("/feeds", { method: "POST", body: JSON.stringify({ url }) });
    bootstrap.Modal.getInstance(document.getElementById("addFeedModal")).hide();
    loadFeeds();
}

async function manualRefresh() {
    await apiCall("/refresh", { method: "POST" });
    alert("Refresh started");
}

async function exportOpml() {
    window.open("/feeds/export.opml", "_blank");
}

function importOpml() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".opml,.xml";
    input.onchange = async (e) => {
        const file = e.target.files[0];
        const formData = new FormData();
        formData.append("file", file);
        const res = await fetch("/feeds/import.opml", { method: "POST", headers: { "X-API-Key": apiKey }, body: formData });
        if (res.ok) { alert("Imported"); loadFeeds(); }
        else alert("Import failed");
    };
    input.click();
}

function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/[&<>]/g, function(m) {
        if (m === "&") return "&amp;";
        if (m === "<") return "&lt;";
        if (m === ">") return "&gt;";
        return m;
    });
}

document.getElementById("apiKeyBtn").onclick = setApiKey;
document.getElementById("refreshBtn").onclick = manualRefresh;
document.getElementById("addFeedBtn").onclick = () => new bootstrap.Modal(document.getElementById("addFeedModal")).show();
document.getElementById("confirmAddFeed").onclick = addFeed;
document.getElementById("exportOpmlBtn").onclick = exportOpml;
document.getElementById("importOpmlBtn").onclick = importOpml;
document.getElementById("searchBtn").onclick = () => loadArticles();
document.getElementById("readFilter").onchange = () => loadArticles();
document.getElementById("feedFilter").onchange = (e) => { currentFeedId = e.target.value === "all" ? null : e.target.value; loadArticles(); };
loadFeeds();
loadArticles();
