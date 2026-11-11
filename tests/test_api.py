from tests.conftest import AUTH, run_db


def _seed_articles():
    async def go(db):
        await db.execute(
            "INSERT INTO feeds (id, url, title) VALUES "
            "(1, 'https://a.example/rss', 'A'), (2, 'https://b.example/rss', 'B')"
        )
        await db.executemany(
            "INSERT INTO articles (feed_id, guid, title, link, summary, published_at, is_read) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (1, "a1", "Alpha 100%", "https://a.example/1", "", "2025-01-01 10:00:00", 0),
                (1, "a2", "Beta", "https://a.example/2", "", "2025-01-02 10:00:00", 1),
                (2, "b1", "Gamma", "https://b.example/1", "", None, 0),
            ],
        )
        await db.commit()

    run_db(go)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_write_requires_api_key(client):
    assert client.post("/feeds", json={"url": "https://hnrss.org/newest"}).status_code == 422
    assert (
        client.post("/feeds", json={"url": "https://hnrss.org/newest"}, headers={"X-API-Key": "nope"}).status_code
        == 403
    )


def test_add_list_delete_feed(client):
    r = client.post("/v1/feeds", json={"url": "https://hnrss.org/newest"}, headers=AUTH)
    assert r.status_code == 201
    feed_id = r.json()["id"]
    assert client.post("/feeds", json={"url": "https://hnrss.org/newest"}, headers=AUTH).status_code == 409
    feeds = client.get("/feeds").json()
    assert [f["id"] for f in feeds] == [feed_id]
    assert feeds[0]["unread_count"] == 0
    assert client.delete(f"/feeds/{feed_id}", headers=AUTH).status_code == 200
    assert client.delete(f"/feeds/{feed_id}", headers=AUTH).status_code == 404


def test_add_feed_rejects_private_urls(client):
    r = client.post("/feeds", json={"url": "http://169.254.169.254/"}, headers=AUTH)
    assert r.status_code == 400


def test_list_articles_ordering_filters_and_utc(client):
    _seed_articles()
    articles = client.get("/articles").json()
    # Undated article falls back to created_at (now), so it sorts first.
    assert [a["title"] for a in articles] == ["Gamma", "Beta", "Alpha 100%"]
    assert articles[1]["published_at"].endswith("Z") or articles[1]["published_at"].endswith("+00:00")
    assert [a["title"] for a in client.get("/articles?is_read=false&feed_id=1").json()] == ["Alpha 100%"]
    # LIKE wildcards are matched literally.
    assert [a["title"] for a in client.get("/articles", params={"search": "100%"}).json()] == ["Alpha 100%"]
    assert len(client.get("/articles", params={"search": "%"}).json()) == 1


def test_feed_unread_counts(client):
    _seed_articles()
    counts = {f["title"]: f["unread_count"] for f in client.get("/feeds").json()}
    assert counts == {"A": 1, "B": 1}


def test_mark_read_and_mark_all(client):
    _seed_articles()
    assert client.put("/articles/9999/read", json={"is_read": True}, headers=AUTH).status_code == 404
    r = client.post("/articles/mark-all-read?feed_id=2", headers=AUTH)
    assert r.json() == {"updated": 1}
    assert client.get("/stats").json() == {"feeds": 2, "articles": 3, "unread": 1}
    assert client.post("/articles/mark-all-read", headers=AUTH).json() == {"updated": 1}
    assert client.get("/stats").json()["unread"] == 0


def test_opml_import_export(client):
    opml = b"""<opml><body>
        <outline xmlUrl="https://hnrss.org/newest"/>
        <outline xmlUrl="https://hnrss.org/newest"/>
        <outline xmlUrl="http://127.0.0.1/admin"/>
    </body></opml>"""
    r = client.post("/feeds/import.opml", files={"file": ("f.opml", opml)}, headers=AUTH)
    assert r.status_code == 200
    assert r.json() == {"added": 1, "skipped": 0, "rejected": ["http://127.0.0.1/admin"]}
    r = client.get("/feeds/export.opml")
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    assert "https://hnrss.org/newest" in r.text


def test_refresh_status(client):
    assert client.get("/refresh/status").json() == {"refreshing": False}
