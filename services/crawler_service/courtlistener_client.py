# import requests
# import time

# from shared.config import settings
# from shared.logging import get_logger

# logger = get_logger(__name__)


# class CourtListenerClient:

#     def __init__(self):

#         self.base_url = settings.COURTLISTENER_API
#         self.session = requests.Session()

#     def fetch_page(self, url=None):

#         target = url or self.base_url

#         retries = 3

#         for attempt in range(retries):

#             try:

#                 response = self.session.get(target, timeout=30)

#                 if response.status_code == 200:
#                     return response.json()

#                 logger.warning(
#                     f"Bad response: {response.status_code}"
#                 )

#             except Exception as e:

#                 logger.error(f"API request failed: {e}")

#             time.sleep(2)

#         raise RuntimeError("CourtListener API unavailable")

import requests
import time

from shared.config import settings
from shared.logging import get_logger

logger = get_logger(__name__)


class CourtListenerClient:

    def __init__(self):
        self.base_url = settings.COURTLISTENER_API

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Token {settings.COURTLISTENER_API_KEY}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Connection": "keep-alive"
        })

    def fetch_page(self, url=None):

        target = url or self.base_url
        retries = 3

        for attempt in range(retries):
            try:
                response = self.session.get(target, timeout=30)

                if response.status_code == 200:
                    return response.json()

                elif response.status_code == 403:
                    logger.error("403 Forbidden - blocked. Sleeping before retry...")
                    time.sleep(5)

                else:
                    logger.warning(f"Bad response: {response.status_code}")

            except Exception as e:
                logger.error(f"API request failed: {e}")

            time.sleep(2)

        raise RuntimeError("CourtListener API unavailable")