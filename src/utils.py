import logging
import hashlib


logger = logging.getLogger(__name__.rsplit(".", maxsplit=1)[-1])


def check_existence(file_string, media_dir):
    """Checks for existing files matching"""
    file_pattern = f"*{file_string}"
    existing_files = list(media_dir.rglob(file_pattern))

    if existing_files:
        logger.debug(f"Found existing file(s) for '{file_string}', skipping replacement.")
        return existing_files

    return None


def hash_str(input_str: str):
    """Generates a 16-character SHA-256 hash of the input string."""
    input_str = input_str.lower().strip(" .,;:!?'\"()[]{}<>")
    encoded_string = input_str.encode()
    sha256_hash = hashlib.sha256()
    sha256_hash.update(encoded_string)
    return sha256_hash.hexdigest()[:16]


def file_str(input_str: str, media="img"):
    """Generates a filename based on the hashed input string and media type."""
    media_extensions = {
        "img": "png",
        "sound": "mp3"}
    if media in media_extensions:
        hashed_string = hash_str(input_str)
        return f'{media}_{hashed_string}.{media_extensions[media]}'
    raise ValueError(f"Unknown media type: {media}")


def reference_str(input_str: str, media="img"):
    """Generates an HTML or markup reference for the given media type."""
    file_string = file_str(input_str, media)
    if media == "img":
        return f'<img src="{file_string}">'
    if media == "sound":
        return f'[sound:{file_string}]'
    raise ValueError(f"Unknown media type: {media}")
