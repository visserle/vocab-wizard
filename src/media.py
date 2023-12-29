"""Add multiple media types to a whole dataframe."""

import platform
import logging
from pathlib import Path

from phonemizer.backend import EspeakBackend
from phonemizer.backend.espeak.wrapper import EspeakWrapper
from gtts import gTTS

from src.hash import file_str, reference_str
from src.image_creation import get_image
from src.bing import BingImageSearch
from src.openai import dall_e, whisper

logger = logging.getLogger(__name__.rsplit(".", maxsplit=1)[-1])


def add_phonetics(df, language):
    """
    Add automatically created phonetics to a dataframe using the espeak library.

    On macos this requires the macports version of espeak-ng:
    https://ports.macports.org/port/espeak-ng/
    
    Not tested on other platforms.

    Note: We also tried out the wikipron database which has a much better quality, but because it is not an algorithm it is not possible to add phonetics for new words/sentences.
    """
    # Skip function if no phonetics columns
    if not "Phonetics" in df.columns:
        return df

    # Set espeak library path for macos
    if platform.system() == 'Darwin':
        EspeakWrapper.set_library(Path("/opt/local/bin/espeak")) # macports version

    # Use specific language codes for espeak
    # run phonemizer.backend.espeak.espeak.EspeakBackend.supported_languages() to see all supported languages
    if language == "fr":
        language = "fr-fr"
    if language == "en":
        language = "en-us"

    # Set up espeak function
    if not hasattr(add_phonetics, "backend") or add_phonetics.backend.language != language:
        backend = EspeakBackend(
            language=language,
            with_stress=True,
            preserve_punctuation=True)
        add_phonetics.backend = backend # function as object to avoid reinitializing the backend
    phonemize = lambda x: f"/{add_phonetics.backend.phonemize([str(x)], strip=True)[0]}/"

    # Add phonetics to dataframe
    df.Phonetics = df.iloc[:,0].apply(phonemize)
    if "Q&A" in df.columns:
        df["Phonetics_Answer"] = df.iloc[:,1].apply(phonemize)
    logger.info(f"Added phonetics for {len(df)} words.")
    return df


def add_sounds(df, sound_dir, language, engine="gtts", force_replace=False):
    """
    Add automatically created sounds to a dataframe using the gtts library.
    """
    if engine not in ("gtts", "whisper"):
        raise ValueError(f"Unknown engine '{engine}'.")

    # Skip function if no sound column
    if not "Sound" in df.columns:
        return df, []

    # Create list of sound file paths and add references for Anki to dataframe
    sound_paths = [sound_dir / Path(file_str(vocab, "sound")) for vocab in df.iloc[:,0]]
    df.Sound = df.iloc[:,0].apply(lambda x: reference_str(x, "sound"))
    if "Q&A" in df.columns:
        sound_paths += [sound_dir / Path(file_str(vocab, "sound")) for vocab in df.iloc[:,1]]
        df["Sound_Answer"] = df.iloc[:,1].apply(lambda x: reference_str(x, "sound"))

    # Get sounds
    iterator = zip(df.iloc[:,0] if "Q&A" not in df.columns else df.iloc[:,0].to_list()+df.iloc[:,1].to_list(), sound_paths)
    for idx, (vocab, sound_path) in enumerate(iterator):
        # Check if sound already exists
        if not force_replace:
            if sound_path.exists():
                logger.debug(f"Sound for '{vocab}' already exists, skipping replacement.")
                continue
        # Create sound
        if engine == "gtts":
            tts = gTTS(vocab, lang=language)
            tts.save(sound_path)
            logger.debug(f"Sound for '{vocab}' saved to {sound_path}")
        if engine == "whisper":
            voice = ("alloy", "echo", "fable", "onyx", "nova", "shimmer")[idx % 6]
            whisper(vocab, sound_path, voice=voice)
            logger.debug(f"Sound for '{vocab}' saved to {sound_path}")

    logger.info(f"Added sounds for {len(df)} vocabularies.")
    return df, sound_paths


def add_images(df, img_dir, language, engine="bing", force_replace=False):
    if engine not in ("bing", "dall-e-2", "dall-e-3"):
        raise ValueError(f"Unknown engine '{engine}'.")

    # Skip function if no image column
    if "Image" not in df.columns:
        return df, []

    # Create list of image file paths
    img_paths = [img_dir / Path(file_str(vocab, "img")) for vocab in df.iloc[:,0]]

    # Add references for Anki to dataframe
    df.Image = df.iloc[:,0].apply(lambda x: reference_str(x, "img"))

    # Save images
    for vocab, img_path in zip(df.iloc[:,0], img_paths):
        # Check if image already exists
        if not force_replace:
            if img_path.exists():
                logger.debug(f"Image for '{vocab}' already exists, skipping replacement.")
                continue
        if engine == "bing":
            img_url = BingImageSearch(vocab, language=language).get_image_url()
        if engine == "dall-e-2":
            img_url = dall_e(vocab, model="dall-e-2")
        if engine == "dall-e-3":
            img_url = dall_e(vocab, model="dall-e-3")
        get_image(img_url, img_path)
        logger.debug(f"Image for '{vocab}' saved to {img_path}")
    logger.info(f"Added images for {len(df)} vocabularies.")
    return df, img_paths
