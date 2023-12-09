"""Get one image for one query/prompt."""

import logging
import re
from pathlib import Path
import io
import requests
from urllib.parse import quote_plus

from PIL import Image


logger = logging.getLogger(__name__.rsplit(".", maxsplit=1)[-1])


def get_image(url, img_path):
    """Downloads and saves an image from an url."""
    img_path = Path(img_path)
    # Download image
    image = download_image(url)
    if not image:
        return None
    # Resize image
    image = resize_image(image)
    # Save image
    if save_image(image, img_path):
        return img_path
    return None


def download_image(url):
    """Downloads an image from an url."""
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content))
    except Exception as e:
        logger.error(f"Error in downloading image from {url}: {e}")
        return None


def resize_image(image):
    """Resizes the image if its width is greater than the set threshold."""
    IMAGE_WIDTH_THRESHOLD = 800
    if image.width > IMAGE_WIDTH_THRESHOLD:
        scale_factor = IMAGE_WIDTH_THRESHOLD / image.width
        new_height = int(image.height * scale_factor)
        image = image.resize((IMAGE_WIDTH_THRESHOLD, new_height), Image.Resampling.LANCZOS)
    return image


def save_image(image, img_path):
    """Saves the image as a PNG file."""
    img_path = Path(img_path)
    try:
        image.save(img_path, 'PNG')
        logger.info(f"Image saved to {img_path}")
        return True
    except Exception as e:
        logger.error(f"Error in saving image to {img_path}: {e}")
        return False


class BingImageSearch:
    """Class for fetching one image URL from Bing image search query."""

    def __init__(self, query, language=None, adult='off', img_filter=''):
        self.query = query.strip('"\'') # quotes change search results to literal
        self.adult = adult
        self.img_filter = img_filter
        self.headers = self._build_headers(language)
        self.url_count = 15
        self.timeout = 5


    def _build_headers(self, language):
        DEFAULT_USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11'
        headers = {'User-Agent': DEFAULT_USER_AGENT}
        if language is None: # TODO
            language = ['en-US', 'en']
        headers['Accept-Language'] = ', '.join([f'{lang};q={1 / len(language)}' for lang in language]) # TODO
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

        return valid_url
