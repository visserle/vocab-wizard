import os
import logging
from pathlib import Path

from phonemizer.backend import EspeakBackend
from phonemizer.backend.espeak.wrapper import EspeakWrapper

from src.media_utils import BingImageSearch, data_str, reference_str

__all__ = ["add_phonetics", "add_images", "add_sounds"]

logger = logging.getLogger(__name__.rsplit(".", maxsplit=1)[-1])


def add_phonetics(df):
    if "Phonetics" not in df.columns:
        return df

    if os.uname().sysname == 'Darwin':
        EspeakWrapper.set_library(Path("/opt/local/bin/espeak")) # macports version of espeak

    language = "fr"
    if language == "fr":
        # to find out the language code, run the following command
        # phonemizer.backend.espeak.espeak.EspeakBackend.supported_languages()
        # and espeak --voices
        language = "fr-fr"

    backend = EspeakBackend(language="fr-fr", with_stress=True, preserve_punctuation=True)

    vocab = df.iloc[:,0]
    phonemize_it = lambda x: f"/{backend.phonemize([x], strip=True)[0]}/"
    df.Phonetics = vocab.apply(phonemize_it)
    logger.info(f"Added phonetics for {len(df)} words.")
    return df


def add_images(df, img_dir, force_replace=False):
    #TODO: add option for dalle image creation
    """Download images, add references to Anki card, and create a list of media file paths"""
    if "Image" not in df.columns:
        return df, []

    vocab = df.iloc[:,0]
    for word in vocab:
        bing = BingImageSearch(query=word, output_dir=img_dir, languages=["fr"], force_replace=force_replace)
        bing.run()
    df.Image = vocab.apply(lambda x: reference_str(x, media="img"))
    media_files = [str(img_dir / Path(data_str(word, media="img"))) for word in vocab]
    
    count = 0
    for media_file in media_files:
        if Path(media_file).exists():
            count += 1

    if count != len(media_files):
        logger.error(f"Only added {count} images for {len(media_files)} words.")
    else:
        logger.info(f"Added {count} images for {len(media_files)} words.")
    
    return df, media_files


def add_sounds(df):
    pass
