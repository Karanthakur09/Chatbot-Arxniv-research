import time
import requests
import xml.etree.ElementTree as ET

from shared.config import settings
from shared.logging import get_logger

logger = get_logger(__name__)


class ArxivClient:

    def __init__(self, query=None, batch_size=None):
        self.base_url = settings.ARXIV_BASE_URL
        self.query = query or settings.ARXIV_QUERY
        self.batch_size = batch_size or settings.ARXIV_BATCH_SIZE

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "legal-ai-pipeline/1.0",
        })

    def fetch_batch(self, start=0):

        params = {
            "search_query": self.query,
            "start": start,
            "max_results": self.batch_size,
        }

        try:
            response = self.session.get(
                self.base_url,
                params=params,
                timeout=settings.REQUEST_TIMEOUT
            )

            response.raise_for_status()  # ✅ better error handling

            return self.parse_response(response.text)

        except requests.exceptions.RequestException as e:
            logger.error(f"Arxiv API error: {e}")
            return []

        finally:
            # ✅ Config-driven rate limiting
            time.sleep(settings.ARXIV_RATE_LIMIT_SECONDS)

    def parse_response(self, xml_data):

        try:
            root = ET.fromstring(xml_data)
        except Exception as e:
            logger.error(f"XML Parse failed: {e}")
            return []

        ns = {"atom": "http://www.w3.org/2005/Atom"}

        entries = []

        for entry in root.findall("atom:entry", ns):

            try:
                raw_id = entry.find("atom:id", ns).text
                arxiv_id = raw_id.split("/")[-1].split("v")[0]

                title = entry.find("atom:title", ns).text.strip()

                published = entry.find("atom:published", ns).text

                authors = [
                    author.find("atom:name", ns).text
                    for author in entry.findall("atom:author", ns)
                ]

                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

                category_elem = entry.find("atom:category", ns)
                category = category_elem.attrib.get("term") if category_elem is not None else None

                entries.append({
                    "doc_id": arxiv_id,
                    "download_url": pdf_url,
                    "title": title,
                    "authors": authors,
                    "category": category,
                    "published": published
                })

            except Exception as e:
                logger.warning(f"Parse error: {e}")
                continue

        return entries