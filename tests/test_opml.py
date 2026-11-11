import pytest

from app.services.opml_service import generate_opml, parse_opml


def test_round_trip():
    feeds = [{"url": "https://a.example/rss?x=1&y=2", "title": "A & B"}, {"url": "https://b.example/rss", "title": None}]
    assert parse_opml(generate_opml(feeds).encode()) == [f["url"] for f in feeds]


def test_tolerates_bom_and_bare_ampersands():
    doc = b'\xef\xbb\xbf<opml><body><outline xmlUrl="https://a.example/?a=1&b=2"/></body></opml>'
    assert parse_opml(doc) == ["https://a.example/?a=1&b=2"]


def test_rejects_entity_expansion():
    doc = b"""<?xml version="1.0"?>
<!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;&lol;&lol;">]>
<opml><body><outline xmlUrl="&lol2;"/></body></opml>"""
    with pytest.raises(ValueError):
        parse_opml(doc)


def test_rejects_garbage():
    with pytest.raises(ValueError):
        parse_opml(b"not xml")
