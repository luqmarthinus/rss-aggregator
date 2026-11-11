import pytest

from app.utils.security import UnsafeURLError, check_feed_url, is_public_ip


@pytest.mark.parametrize(
    "url",
    [
        "https://hnrss.org/newest",
        "http://feeds.bbci.co.uk/news/rss.xml",
        "https://172.217.0.1/feed",  # public 172.x address (previously blocked by mistake)
    ],
)
def test_allows_public_urls(url):
    assert check_feed_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/feed",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "http://localhost:8000/feeds",
        "http://foo.localhost/",
        "http://127.0.0.1/",
        "http://127.1.2.3/",
        "http://10.0.0.5/",
        "http://172.16.0.1/",
        "http://192.168.1.1/",
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata endpoint
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
        "http://[fd00::1]/",
        "http://0.0.0.0/",
    ],
)
def test_blocks_unsafe_urls(url):
    with pytest.raises(UnsafeURLError):
        check_feed_url(url)


def test_is_public_ip():
    assert is_public_ip("8.8.8.8")
    assert not is_public_ip("192.168.0.1")
    assert not is_public_ip("not-an-ip")
