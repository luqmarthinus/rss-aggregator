import re
import xml.etree.ElementTree as ET
from sqlite3 import Row
from typing import Dict, List, Union

from loguru import logger


def generate_opml(feeds: List[Union[Dict, Row]]) -> str:
    root = ET.Element("opml", version="1.0")
    head = ET.SubElement(root, "head")
    title = ET.SubElement(head, "title")
    title.text = "RSS Aggregator Feeds"
    body = ET.SubElement(root, "body")
    for feed in feeds:
        url = feed["url"]
        feed_title = feed["title"] if feed["title"] else url
        ET.SubElement(body, "outline", type="rss", xmlUrl=url, title=feed_title)
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def parse_opml(content: bytes) -> List[str]:
    try:
        # Remove UTF-8 BOM if present
        if content.startswith(b"\xef\xbb\xbf"):
            content = content[3:]
        # Decode to string
        text = content.decode("utf-8")

        # Escape unescaped ampersands that are not part of XML entities
        # Pattern: & not followed by any known entity name or numeric reference
        def replace_amp(match):
            return "&amp;"

        # Match & that is not part of &amp; &lt; &gt; &quot; &apos; &#...; &#x...;
        text = re.sub(r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", replace_amp, text)
        # Parse the fixed XML
        root = ET.fromstring(text)
        urls = []
        for outline in root.findall(".//outline"):
            url = outline.get("xmlUrl")
            if url:
                urls.append(url)
        if not urls:
            logger.warning("No outline elements with xmlUrl found in OPML")
        return urls
    except ET.ParseError as e:
        logger.error(f"OPML parsing failed: {e}")
        raise ValueError("Invalid OPML file") from e
