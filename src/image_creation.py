"""Get one image from one url."""

import logging
from pathlib import Path
import io
import requests

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
        return True
    except Exception as e:
        logger.error(f"Error in saving image to {img_path}: {e}")
        return False
