let apiKey = sessionStorage.getItem("apiKey") || "";
let currentFeedId = null;

function setApiKey() {
    const key = prompt("Enter your API key (for write operations):");
    if (key) {
        apiKey = key;
        sessionStorage.setItem("apiKey", key);
        alert("API key saved for this session");
        loadFeeds();
        loadArticles();
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
    try {
        const feeds = await apiCall("/feeds");
        const container = document.getElementById("feedsList");
        if (!container) return;
        container.innerHTML = feeds.map(f => `
            <a href="#" class="list-group-item list-group-item-action feed-item" data-id="${f.id}">
                <i class="bi-rss-fill"></i> ${escapeHtml(f.title || f.url)}
                <button class="btn btn-sm btn-danger float-end delete-feed" data-id="${f.id}"><i class="bi-trash"></i></button>
            </a>
        `).join("");
        // Update feed filter dropdown
        const filterSelect = document.getElementById("feedFilter");
        if (filterSelect) {
            filterSelect.innerHTML = '<option value="all">All feeds</option>' + feeds.map(f => `<option value="${f.id}">${escapeHtml(f.title || f.url)}</option>`).join("");
        }
        // If current selected feed no longer exists, reset selection
        if (currentFeedId && !feeds.some(f => f.id == currentFeedId)) {
            currentFeedId = null;
            document.getElementById("feedFilter").value = "all";
        }
        attachFeedEvents();
    } catch (err) {
        console.error("Failed to load feeds:", err);
    }
}

function attachFeedEvents() {
    document.querySelectorAll(".feed-item").forEach(el => {
        el.addEventListener("click", (e) => {
            if (e.target.classList.contains("delete-feed")) return;
            currentFeedId = el.dataset.id;
            document.querySelectorAll(".feed-item").forEach(i => i.classList.remove("active"));
            el.classList.add("active");
            loadArticles();
        });
    });
    document.querySelectorAll(".delete-feed").forEach(btn => {
        btn.addEventListener("click", async (e) => {
            e.stopPropagation();
            const id = btn.dataset.id;
            if (!confirm("Delete this feed and all its articles?")) return;
            try {
                await apiCall(`/feeds/${id}`, { method: "DELETE" });
                // Reset selection if deleted feed was selected
                if (currentFeedId == id) {
                    currentFeedId = null;
                    document.getElementById("feedFilter").value = "all";
                }
                // Reload everything
                await loadFeeds();
                await loadArticles();
            } catch (err) {
                console.error("Delete failed:", err);
                alert("Failed to delete feed. Check API key.");
            }
        });
    });
}

async function loadArticles() {
    try {
        let url = "/articles?limit=100";
        if (currentFeedId && currentFeedId !== "all") url += `&feed_id=${currentFeedId}`;
        const readFilter = document.getElementById("readFilter").value;
        if (readFilter === "unread") url += "&is_read=false";
        if (readFilter === "read") url += "&is_read=true";
        const search = document.getElementById("searchInput").value;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        const articles = await apiCall(url);
        const container = document.getElementById("articlesContainer");
        if (!container) return;
        if (!articles.length) {
            container.innerHTML = "<p class='text-muted'>No articles found.</p>";
            return;
        }
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
    } catch (err) {
        console.error("Failed to load articles:", err);
    }
}

async function addFeed() {
    const url = document.getElementById("feedUrl").value;
    if (!url) return;
    try {
        await apiCall("/feeds", { method: "POST", body: JSON.stringify({ url }) });
        bootstrap.Modal.getInstance(document.getElementById("addFeedModal")).hide();
        await loadFeeds();
        // Clear any selection and load articles from all feeds
        currentFeedId = null;
        document.getElementById("feedFilter").value = "all";
        await loadArticles();
    } catch (err) {
        alert("Failed to add feed. Check API key and URL.");
    }
}

async function manualRefresh() {
    try {
        await apiCall("/refresh", { method: "POST" });
        alert("Refresh started. New articles will appear in a few seconds.");
        // Reload feeds first (to update last fetch time) and then articles
        await loadFeeds();
        setTimeout(() => loadArticles(), 5000);
    } catch (err) {
        alert("Refresh failed. Check API key.");
    }
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
        try {
            const res = await fetch("/feeds/import.opml", {
                method: "POST",
                headers: { "X-API-Key": apiKey },
                body: formData
            });
            if (res.ok) {
                alert("Imported successfully");
                await loadFeeds();
                currentFeedId = null;
                document.getElementById("feedFilter").value = "all";
                await loadArticles();
            } else {
                alert("Import failed");
            }
        } catch (err) {
            alert("Import error");
        }
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

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("apiKeyBtn").onclick = setApiKey;
    document.getElementById("refreshBtn").onclick = manualRefresh;
    document.getElementById("addFeedBtn").onclick = () => new bootstrap.Modal(document.getElementById("addFeedModal")).show();
    document.getElementById("confirmAddFeed").onclick = addFeed;
    document.getElementById("exportOpmlBtn").onclick = exportOpml;
    document.getElementById("importOpmlBtn").onclick = importOpml;
    document.getElementById("searchBtn").onclick = () => loadArticles();
    document.getElementById("readFilter").onchange = () => loadArticles();
    document.getElementById("feedFilter").onchange = (e) => { 
        currentFeedId = e.target.value === "all" ? null : e.target.value;
        loadArticles();
    };
    loadFeeds();
    loadArticles();
});