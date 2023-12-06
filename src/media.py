import platform
import logging
from pathlib import Path

from phonemizer.backend import EspeakBackend
from phonemizer.backend.espeak.wrapper import EspeakWrapper

from gtts import gTTS

from src.utils import file_str, reference_str, check_existence
from src.image_creation import get_image, BingImageSearch


logger = logging.getLogger(__name__.rsplit(".", maxsplit=1)[-1])


def add_phonetics(df, language="fr"):
    """
    Add automatically created phonetics to a dataframe using the espeak library.

    On macos this requires the macports version of espeak-ng:
    https://ports.macports.org/port/espeak-ng/
    
    Not tested on other platforms.

    Note: We also tried out wikipron (which has a much better quality) but it is not flexible enough for our use case.
    """
    # Skip function if no phonetics columns
    if not ("Phonetics" in df.columns or "Phonetics_2" in df.columns):
        return df

    # Set espeak library path for macos
    if platform.system() == 'Darwin':
        EspeakWrapper.set_library(Path("/opt/local/bin/espeak")) # macports version

    # Correct language code if necessary
    # to find out specific language codes run phonemizer.backend.espeak.espeak.EspeakBackend.supported_languages()
    if language == "fr":
        language = "fr-fr"

    # Set up espeak function
    if not hasattr(add_phonetics, "backend") or add_phonetics.backend.language != language:
        backend = EspeakBackend(
            language=language, 
            with_stress=True,
            preserve_punctuation=True)
        add_phonetics.backend = backend # function as object to avoid reinitializing the backend
    phonemize = lambda x: f"/{add_phonetics.backend.phonemize([str(x)], strip=True)[0]}/"

    # Add phonetics to dataframe
    if "Phonetics" in df.columns:
        df.Phonetics = df.iloc[:,0].apply(phonemize)
    if "Phonetics_2" in df.columns:
        df.Phonetics_2 = df.iloc[:,1].apply(phonemize)
    logger.info(f"Added phonetics for {len(df)} words.")

    return df


def add_sounds(df, sound_dir, language="fr", engine="gtts", force_replace=False):
    # Skip function if no sound column
    if "Sound" not in df.columns:
        return df, []

    # Get sounds
    for vocab in df.iloc[:,0]:
        # Set sound path
        sound_path = Path(sound_dir) / Path(file_str(vocab, media="sound"))
        # Check if sound already exists
        if not force_replace:
            existing_files = check_existence(sound_path.name, sound_path.parent)
            if existing_files:
                continue
        # Create sound
        if engine == "gtts":
            tts = gTTS(vocab, lang=language)
            tts.save(sound_path)
            logger.info(f"Sound for '{vocab}' saved to {sound_path}")
        if engine == "openai":
            pass
    
    df.Sound = df.iloc[:,0].apply(lambda x: reference_str(x, media="sound"))
    sound_files = [str(sound_dir / Path(file_str(vocab, media="sound"))) for vocab in df.iloc[:,0]]

    # Check that all sounds were added
    count = 0
    for sound_file in sound_files:
        if Path(sound_file).exists():
            count += 1
    if count != len(sound_files):
        logger.error(f"Only added {count} sounds for {len(sound_files)} vocab.")
    else:
        logger.info(f"Added {count} sounds for {len(sound_files)} vocab.")
    
    return df, sound_files


def add_images(df, img_dir, engine="bing", force_replace=False):
    # Skip function if no image column
    if "Image" not in df.columns:
        return df, []

    for vocab in df.iloc[:,0]:
        # Set image path
        img_path = Path(img_dir) / Path(file_str(vocab, media="img"))
        # Check if image already exists
        if not force_replace:
            existing_files = check_existence(img_path.name, img_path.parent)
            if existing_files:
                continue
        if engine == "bing":
            img_url = BingImageSearch(vocab, language="fr").get_image_url()
        if engine == "dalle":
            #img_url = dalle_image(vocab)
            pass
        get_image(img_url, img_path)

    # Add references for Anki to dataframe
    df.Image = df.iloc[:,0].apply(lambda x: reference_str(x, media="img"))

    # Create list of image file paths
    img_files = [str(img_dir / Path(file_str(vocab, media="img"))) for vocab in df.iloc[:,0]]

    # Check that all images were downloaded
    count = 0
    for img_file in img_files:
        if Path(img_file).exists():
            count += 1
    if count != len(img_files):
        logger.error(f"Only added {count} images for {len(img_files)} vocab.")
    else:
        logger.info(f"Added {count} images for {len(img_files)} vocab.")

    return df, img_files
