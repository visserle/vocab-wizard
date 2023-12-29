"""Get one image url for one query via bing."""

import logging
import re
import requests
from urllib.parse import quote_plus


logger = logging.getLogger(__name__.rsplit(".", maxsplit=1)[-1])


class BingImageSearch:
    """Class for fetching one image URL from Bing image search query."""

    def __init__(self, query, language=None, adult='off', img_filter=''):
        self.query = query.strip('"\'') # quotes change search results to literal
        self.adult = adult
        self.img_filter = img_filter
        self.headers = self._build_headers(language)
        self.url_count = 15
        self.timeout = 8


    def _build_headers(self, language):
        """See https://www.ibm.com/docs/en/rpa/21.0?topic=languages-supported-bing-engine for language codes."""
        DEFAULT_USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11'
        headers = {'User-Agent': DEFAULT_USER_AGENT}
        if language == "en":
            language = "en-US"
        elif language == "fr":
            language = "fr-FR"
        elif language == "de":
            language = "de-DE"
        elif language == "es":
            language = "es-ES" # and so on
        headers['Accept-Language'] = ', '.join([f'{language};q=1', 'en-US;q=0.5'])
        
        return headers

    @staticmethod
    def get_filter(shorthand):
        filter_map = {
            'line': "+filterui:photo-linedrawing",
            'linedrawing': "+filterui:photo-linedrawing",
            'photo': "+filterui:photo-photo",
            'clipart': "+filterui:photo-clipart",
            'transparent': "+filterui:photo-transparent"
        }
        return filter_map.get(shorthand, "")

    def fetch_image_urls(self):
        """Fetches image urls from Bing."""
        counter = 0
        urls = []
        while not urls and counter < 5: # sometimes Bing returns empty list
            request_url = f'https://www.bing.com/images/async?q={quote_plus(self.query)}' \
                        f'&first=0&count={self.url_count}&adlt={self.adult}' \
                        f'&qft={self.get_filter(self.img_filter)}'
            
            response = requests.get(request_url, headers=self.headers, timeout=self.timeout)
            urls = re.findall('murl&quot;:&quot;(.*?)&quot;', response.text)
            counter += 1

        return urls
    
    def _is_url_valid(self, url):
        try:
            response = requests.head(url, allow_redirects=True, timeout=self.timeout)
            # Check status code to ensure it's a valid URL
            if response.status_code != 200:
                logger.debug(f"URL {url} returned status code {response.status_code}")
                return False
            
            # Check Content-Type to ensure it's an image
            content_type = response.headers.get('Content-Type', '')
            if not any(ct in content_type for ct in ['image/jpeg', 'image/png', 'image/gif', 'image/webp']):
                logger.debug(f"URL {url} returned Content-Type {content_type}")
                return False

            return True
        except requests.RequestException as e:
            logger.debug(f"Exception in checking URL validity: {e}")
            return False
        
    def get_image_url(self):
        """Runs the Bing image search and returns valid image URL."""
        logger.debug("Starting Bing image search for %s", self.query)

        urls = self.fetch_image_urls()
        if not urls:
            logger.debug("No images found on the page.")
            return None

        valid_url = []
        for url in urls:
            if self._is_url_valid(url):
                valid_url = url
                break
        logger.debug("Image URL for '%s' is %s", self.query, valid_url)
        return valid_url
