import os
import logging
from urllib.request import Request, urlopen
from urllib.parse import urlsplit, quote_plus
import re
from pathlib import Path
import io
from PIL import Image
import hashlib


logger = logging.getLogger(__name__.rsplit(".", maxsplit=1)[-1])


def hash_str(input_str):
    """Generates a 16-character SHA-256 hash of the input string."""
    try:
        encoded_string = input_str.encode()
        sha256_hash = hashlib.sha256()
        sha256_hash.update(encoded_string)
        return sha256_hash.hexdigest()[:16]
    except AttributeError:
        raise ValueError("Input must be a string")

def data_str(input_str, media="img"):
    """Generates a filename based on the hashed input string and media type."""
    media_extensions = {
        "img": "png",
        "sound": "mp3"
    }

    if media in media_extensions:
        hashed_string = hash_str(input_str)
        return f'{media}_{hashed_string}.{media_extensions[media]}'
    else:
        raise ValueError(f"Unknown media type: {media}")

def reference_str(input_str, media="img"):
    """Generates an HTML or markup reference for the given media type."""
    try:
        data_string = data_str(input_str, media)
        if media == "img":
            return f'<img src="{data_string}">'
        elif media == "sound":
            return f'[sound:{data_string}]'
    except ValueError as e:
        print(e)
        return None


class BingImageSearch:
    """Class for downloading images from Bing image search."""
    DEFAULT_USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11'
    IMAGE_FORMATS = ["jpe", "jpeg", "jfif", "exif", "tiff", "gif", "bmp", "png", "webp", "jpg"]

    def __init__(self, query, output_dir, languages=None, force_replace=False, verbose=False, adult='off', timeout=10, img_filter=''):
        self.query = query
        self.query_hash = hash_str(query)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.adult = adult
        self.img_filter = img_filter
        self.force_replace = force_replace
        self.verbose = verbose
        self.timeout = timeout
        self.headers = {
            'User-Agent': self.DEFAULT_USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
            'Accept-Encoding': 'none',
            'Connection': 'keep-alive'
        }
        if languages is None:
            languages = ['en-US', 'en']
        accept_language = ','.join([f'{lang};q={1 / len(languages)}' for lang in languages])
        self.headers['Accept-Language'] = accept_language
        self.link_count = 10


    @staticmethod
    def get_filter(shorthand):
        """Returns the filter query parameter for Bing image search."""
        filter_map = {
            'line': "+filterui:photo-linedrawing",
            'linedrawing': "+filterui:photo-linedrawing",
            'photo': "+filterui:photo-photo",
            'clipart': "+filterui:photo-clipart",
            'transparent': "+filterui:photo-transparent"
        }
        return filter_map.get(shorthand, "")


    def check_existing_files(self):
        """Checks for existing files matching the query hash."""
        file_pattern = f"*{self.query_hash}*"
        existing_files = list(self.output_dir.rglob(file_pattern))

        if existing_files and not self.force_replace:
            logger.debug(f"Found existing file(s) for hash '{self.query_hash}', skipping download")
            return existing_files

        return None


    def fetch_image_links(self):
        """Fetches image links from Bing."""
        request_url = f'https://www.bing.com/images/async?q={quote_plus(self.query)}' \
                    f'&first=0&count={self.link_count}&adlt={self.adult}' \
                    f'&qft={self.get_filter(self.img_filter)}'

        request = Request(request_url, headers=self.headers)

        html = None
        count = 0
        while not html:
            with urlopen(request) as response:
                html = response.read().decode('utf8')
            count += 1
            if count > 5:
                break
        if not html:
            logger.debug("No more images are available")
            return None

        return re.findall('murl&quot;:&quot;(.*?)&quot;', html)


    def download_image(self, link):
        """Downloads an image from a link."""
        try:
            url_path = Path(urlsplit(link).path)
            url_img = url_path.name.split('?')[0]
            img_type = url_img.split(".")[-1].lower() if '.' in url_img else "jpg"
            img_type = img_type if img_type in self.IMAGE_FORMATS else "jpg"
            img_path = Path(self.output_dir) / f"img_{self.query_hash}.{img_type}"
            logger.debug(f"Downloading Image from {link}")

            if self.save_image(link, img_path):
                logger.debug(f"Image saved to {img_path}")
                return True
        except Exception as e:
            logger.debug(f"[Error] Issue downloading image from {link}: {e}")
        return False


    def save_image(self, link, file_path):
        """Saves an resized image from a given link to the specified file path in PNG format."""
        def _resize_image(image):
            if image.width > 800:
                scale_factor = 800 / image.width
                new_height = int(image.height * scale_factor)
                image = image.resize((800, new_height), Image.Resampling.LANCZOS)
            return image

        try:
            request = Request(link, None, self.headers)
            with urlopen(request, timeout=self.timeout) as response:
                image_data = response.read()
                image = Image.open(io.BytesIO(image_data))
                image = _resize_image(image)
                png_path = file_path.with_suffix('.png')

                image.save(png_path, 'PNG')
        except Exception as e:
            logger.debug(f'[Error] Could not save image from {link}: {e}')
            return False
        return True

    def run(self):
        """Runs the Bing image download process."""
        # Check for existing files
        existing_files = self.check_existing_files()
        if existing_files:
            return existing_files[0].name

        # Start Bing image search
        logger.debug("Starting Bing image search")

        links = self.fetch_image_links()
        if not links:
            logger.debug("No images found on the page.")
            return None

        # Download images
        for link in links:
            logger.debug(f"Found image link: {link}")

            if self.download_image(link):
                logger.info(f"Successfully downloaded image '{self.query}'.")
                return True

        logger.error(f"[Error] No images were successfully downloaded for '{self.query}'.")
        return None
