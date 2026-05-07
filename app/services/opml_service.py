import xml.etree.ElementTree as ET
from typing import List, Dict

def generate_opml(feeds: List[Dict]) -> str:
    root = ET.Element("opml", version="1.0")
    head = ET.SubElement(root, "head")
    title = ET.SubElement(head, "title")
    title.text = "RSS Aggregator Feeds"
    body = ET.SubElement(root, "body")
    for feed in feeds:
        outline = ET.SubElement(body, "outline", type="rss", xmlUrl=feed["url"], title=feed.get("title") or feed["url"])
    return ET.tostring(root, encoding="unicode", xml_declaration=True)

def parse_opml(content: bytes) -> List[str]:
    root = ET.fromstring(content)
    urls = []
    for outline in root.findall(".//outline"):
        url = outline.get("xmlUrl")
        if url:
            urls.append(url)
    return urls
