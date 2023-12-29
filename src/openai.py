import logging
from pathlib import Path
from urllib.parse import quote_plus

import openai


logger = logging.getLogger(__name__.rsplit(".", maxsplit=1)[-1])

def whisper(vocab, sound_path, voice="alloy"):
    """
    Generates a sound file from a vocab using OpenAI's API.
    """
    _client = openai.OpenAI()
    response = _client.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=vocab,
        )
    response.stream_to_file(sound_path)

def dall_e(prompt, model="dall-e-3"):
    """
    Generates a image url from a prompt using OpenAI's DALL-E API.
    Outputs can be weird, especially for dall-e-2.

    Prices: $0.02 for dall-e-2, $0.04 for dall-e-3 as of 2023-12
    from https://community.openai.com/t/howto-use-the-new-python-library-to-call-api-dall-e-and-save-and-display-images/495741#how-to-use-dall-e-3-in-the-api-1
    """
    client = openai.OpenAI()
    try:
        counter = 0
        img_url = None
        while not img_url and counter < 3:
            response = client.images.generate(
                model=model,
                prompt=f"Create a funny/interesting picture that helps to memorize the following term: '{prompt}'. Please do not use any text in the image. Be creative!",
                size="1024x1024",
                quality="standard",
                n=1,
                response_format="url"
            )
            img_url = response.data[0].url
            counter += 1
        logger.debug(f"Image URL for '{prompt}' is {img_url}")
        return img_url
    except openai.OpenAIError as e:
        logger.error(f"Error in generating image from prompt '{prompt}': {e}")
        return None
    

def chatgpt(prompt, model="davinci"):
    """
    Generates a chatbot response from a prompt using OpenAI's API.
    """
    client = openai.OpenAI()
    try:
        response = client.Completion.create(
            engine=model,
            prompt=f"{prompt}\n\nUser:",
            temperature=0.9,
            max_tokens=150,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0.6,
            stop=["\n", " User:"]
        )
        return response.choices[0].text.strip()
    except openai.OpenAIError as e:
        logger.error(f"Error in generating chatbot response from prompt '{prompt}': {e}")
        return None
    

"""
Note that this could be sped up by up to x3 by using asyncio, 
but it makes the code look ugly and I don't think it's worth it right now.
just be patient dude

See the following code for one way to do it.
"""

# import asyncio

# logger = logging.getLogger(__name__.rsplit(".", maxsplit=1)[-1])

# client = None
# def init_async_client():
#     global client
#     if client is None:
#        client = openai.AsyncOpenAI()


# # https://platform.openai.com/account/limits
# RATE_LIMITS = {
#     "gpt-3.5-turbo": 3500,
#     "gpt-3.5-turbo-0301": 3500,
#     "gpt-3.5-turbo-0613": 3500,
#     "gpt-3.5-turbo-1106": 3500,
#     "gpt-3.5-turbo-16k": 3500,
#     "gpt-3.5-turbo-16k-0613": 3500,
#     "gpt-3.5-turbo-instruct": 3000,
#     "gpt-3.5-turbo-instruct-0914": 3000,
#     "gpt-4": 500,
#     "gpt-4-0314": 500,
#     "gpt-4-0613": 500,
#     "gpt-4-1106-preview": 500,
#     "gpt-4-vision-preview": 80,
#     "tts-1": 50,
#     "tts-1-1106": 50,
#     "tts-1-hd": 3,
#     "tts-1-hd-1106": 3,
#     "dall-e-2": 5,
#     "dall-e-3": 5,
# }


# class RateLimiter:
#     """
#     Copied from https://github.com/PaperclipBadger/gpt-flashcards/blob/main/dump.py
#     """
#     def __init__(self, rpm: int) -> None:
#         self.sem = asyncio.Semaphore(rpm)
#         self.rpm = rpm
#         self.sleepers = set()
    
#     def sleeper_callback(self, task):
#         self.sleepers.remove(task)
#         self.sem.release()

#     async def __aenter__(self):
#         await self.sem.acquire()
#         task = asyncio.create_task(asyncio.sleep(61))
#         self.sleepers.add(task)
#         assert len(self.sleepers) <= self.rpm
#         task.add_done_callback(self.sleeper_callback)
    
#     async def __aexit__(self, exc_type, exc, tb):
#         pass

# rate_limiters = {}
# def get_rate_limiter(model: str):
#     try:
#         return rate_limiters[model]
#     except KeyError:
#         rate_limiters[model] = RateLimiter(RATE_LIMITS[model])
#         return rate_limiters[model]


# async def dall_e(prompt, model="dall-e-3"):
#     """
#     Generates a image url from a prompt using OpenAI's DALL-E API.
#     Outputs can be weird, especially for dall-e-2.

#     Prices: $0.02 for dall-e-2, $0.04 for dall-e-3 as of 2023-12
#     from https://community.openai.com/t/howto-use-the-new-python-library-to-call-api-dall-e-and-save-and-display-images/495741#how-to-use-dall-e-3-in-the-api-1
#     """
#     try:
#         async with get_rate_limiter(model):
#             response = await client.images.generate(
#                 model=model,
#                 prompt=f"Create a funny/interesting picture that helps to memorize the following term: '{prompt}'",
#                 size="1024x1024",
#                 quality="standard",
#                 n=1,
#                 response_format="url"
#             )
#             img_url = response.data[0].url
#             return img_url
#     except openai.OpenAIError as e:
#         logger.error(f"Error in generating image from prompt '{prompt}': {e}")
#         return None
#



# import in media and gather the tasks:
# async def add_images(df, img_dir, language, engine="bing", force_replace=False):
#     if engine not in ("bing", "dall-e-2", "dall-e-3"):
#         raise ValueError(f"Unknown engine '{engine}'.")

#     if "Image" not in df.columns:
#         return df, []

#     img_paths = [img_dir / Path(file_str(vocab, "img")) for vocab in df.iloc[:,0]]
#     df.Image = df.iloc[:,0].apply(lambda x: reference_str(x, "img"))

#     async def save_image(vocab, img_path):
#         if not force_replace and img_path.exists():
#             logger.debug(f"Image for '{vocab}' already exists, skipping replacement.")
#             return

#         if engine == "bing":
#             img_url = BingImageSearch(vocab, language=language).get_image_url()
#         elif engine.startswith("dall-e"):
#             img_url = await dall_e(vocab, model=engine)
#         else:
#             raise ValueError(f"Unknown engine '{engine}'.")

#         get_image(img_url, img_path)
#         logger.debug(f"Image for '{vocab}' saved to {img_path}")

#     tasks = [save_image(vocab, img_path) for vocab, img_path in zip(df.iloc[:,0], img_paths)]
#     await asyncio.gather(*tasks)

#     logger.info(f"Added images for {len(df)} vocabularies.")
#     return df, img_paths

#
# in main, finally run asyncio.run(add_images(...)) etc. pp.