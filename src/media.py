import os
import logging
from pathlib import Path

from phonemizer.backend import EspeakBackend
from phonemizer.backend.espeak.wrapper import EspeakWrapper

from src.media_utils import BingImageSearch, data_str, reference_str

__all__ = ["add_phonetics", "add_images", "add_sounds"]

logger = logging.getLogger(__name__.rsplit(".", maxsplit=1)[-1])


def add_phonetics(df):
    """
    Add automatically created phonetics to a dataframe using the espeak library.

    On macos this requires the macports version of espeak-ng:
    https://ports.macports.org/port/espeak-ng/
    
    Not tested on other platforms.
    """
    # Skip function if no phonetics columns
    if not ("Phonetics" in df.columns or "Phonetics_2" in df.columns):
        return df

    # Set espeak library path for macos
    if os.uname().sysname == 'Darwin':
        EspeakWrapper.set_library(Path("/opt/local/bin/espeak")) # macports version

    # Correct language code if necessary
    language = "fr" # TODO: make this an option
    if language == "fr":
        # to find out specific language codes run phonemizer.backend.espeak.espeak.EspeakBackend.supported_languages()
        language = "fr-fr"

    # Set up espeak function
    backend = EspeakBackend(language=language, with_stress=True, preserve_punctuation=True)
    phonemize_it = lambda x: f"/{backend.phonemize([str(x)], strip=True)[0]}/"

    # Add phonetics to dataframe
    if "Phonetics" in df.columns:
        vocab = df.iloc[:, 0]
        df.Phonetics = vocab.apply(phonemize_it)
    if "Phonetics_2" in df.columns:
        vocab = df.iloc[:, 1]
        df.Phonetics_2 = vocab.apply(phonemize_it)

    logger.info(f"Added phonetics for {len(df)} words.")
    return df


def add_images(df, img_dir, force_replace=False):
    """
    Add images to a dataframe using the Bing Image Search API.

    TODO: add option for dalle image creation
    """
    # Skip function if no image column
    if "Image" not in df.columns:
        return df, []

    # Prepare vocabulary
    vocab = df.iloc[:,0]
    vocab = vocab.apply(lambda x: x.strip(' ."'))

    # Download images
    for word in vocab:
        bing = BingImageSearch(query=word, output_dir=img_dir, languages=["fr"], force_replace=force_replace)
        bing.run()

    # Add references for Anki to dataframe
    df.Image = vocab.apply(lambda x: reference_str(x, media="img"))

    # Create list of image file paths
    img_files = [str(img_dir / Path(data_str(word, media="img"))) for word in vocab]

    # Check that all images were downloaded
    count = 0
    for img_file in img_files:
        if Path(img_file).exists():
            count += 1

    if count != len(img_files):
        logger.error(f"Only added {count} images for {len(img_files)} words.")
    else:
        logger.info(f"Added {count} images for {len(img_files)} words.")
    return df, img_files


def add_sounds(df, sound_dir, force_replace=False):
    
    df.Sound = df.Sound.apply(lambda x: x.strip(' ."'))

    pass
