import logging
import hashlib

logger = logging.getLogger(__name__.rsplit(".", maxsplit=1)[-1])


def hash_str(input_str: str) -> str:
    """Generates a 16-character SHA-256 hash of the input string."""
    input_str = input_str.lower().strip(" .,;:!?'\"()[]{}<>")
    encoded_string = input_str.encode()
    sha256_hash = hashlib.sha256()
    sha256_hash.update(encoded_string)
    return sha256_hash.hexdigest()[:16]


def file_str(input_str: str, media_type: str) -> str:
    """Generates a filename based on the hashed input string and media type."""
    media_extensions = {
        "img": "png",
        "sound": "mp3"}
    if media_type in media_extensions:
        hashed_string = hash_str(input_str)
        return f'{media_type}_{hashed_string}.{media_extensions[media_type]}'
    raise ValueError(f"Unknown media type: {media_type}")


def reference_str(input_str: str, media_type: str) -> str:
    """Generates an HTML or markup reference for the given media type."""
    file_string = file_str(input_str, media_type)
    if media_type == "img":
        return f'<img src="{file_string}">'
    if media_type == "sound":
        return f'[sound:{file_string}]'
    raise ValueError(f"Unknown media type: {media_type}")
