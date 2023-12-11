import logging
from pathlib import Path

import openai
from openai import OpenAI


logger = logging.getLogger(__name__.rsplit(".", maxsplit=1)[-1])

def dall_e(prompt, model="dall-e-3"):
    """
    Generates a image url from a prompt using OpenAI's DALL-E API.
    Outputs can be weird, especially for dall-e-2.

    Prices: $0.02 for dall-e-2, $0.04 for dall-e-3 as of 2023-12
    from https://community.openai.com/t/howto-use-the-new-python-library-to-call-api-dall-e-and-save-and-display-images/495741#how-to-use-dall-e-3-in-the-api-1
    """
    client = OpenAI()
    try:
        response = client.images.generate(
            model=model,
            prompt=f"Create a funny/interesting picture that helps to memorize the following term: '{prompt}'",
            size="1024x1024",
            quality="standard",
            n=1,
            response_format="url"
        )
        img_url = response.data[0].url
        return img_url
    except openai.OpenAIError as e:
        logger.error(f"Error in generating image from prompt '{prompt}': {e}")
        return None


def whisper(vocab, sound_path, voice="alloy"):
    """
    Generates a sound file from a vocab using OpenAI's API.
    """
    client = OpenAI()
    response = client.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=vocab,
        )
    response.stream_to_file(sound_path)
