import re
import xml.etree.ElementTree as ET
from sqlite3 import Row
from typing import Dict, List, Union

from defusedxml import ElementTree as SafeET
from defusedxml.common import DefusedXmlException
from loguru import logger

# '&' not already part of an XML entity or character reference
_BARE_AMPERSAND = re.compile(r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)")


def generate_opml(feeds: List[Union[Dict, Row]]) -> str:
    root = ET.Element("opml", version="2.0")
    head = ET.SubElement(root, "head")
    ET.SubElement(head, "title").text = "RSS Aggregator Feeds"
    body = ET.SubElement(root, "body")
    for feed in feeds:
        url = feed["url"]
        feed_title = feed["title"] or url
        ET.SubElement(body, "outline", type="rss", text=feed_title, title=feed_title, xmlUrl=url)
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def parse_opml(content: bytes) -> List[str]:
    """Extract feed URLs from an OPML document. Raises ValueError if it can't be parsed."""
    try:
        text = content.decode("utf-8-sig")  # also strips a UTF-8 BOM
    except UnicodeDecodeError as e:
        raise ValueError("OPML file must be UTF-8 encoded") from e
    # Many exporters emit bare '&' in URLs; escape them so the XML parses.
    text = _BARE_AMPERSAND.sub("&amp;", text)
    try:
        # defusedxml blocks entity-expansion ("billion laughs") and external entity attacks.
        root = SafeET.fromstring(text)
    except (ET.ParseError, DefusedXmlException) as e:
        logger.error("OPML parsing failed: {}", e)
        raise ValueError("Invalid OPML file") from e
    urls = [o.get("xmlUrl").strip() for o in root.iter("outline") if o.get("xmlUrl")]
    if not urls:
        logger.warning("No outline elements with xmlUrl found in OPML")
    return urls
