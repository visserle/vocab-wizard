WORK IN PROGRESS

# vocab_wizard
Old vocabulary booklets are for nerds? Try illustrated, spoken, phonemized, interactive Anki cards to get your overstimulated brain's attention for once.

Pros:
- Create Anki cards from a plain `.txt` file with your vocabulary
- No need to awkwardly add single notes to Anki, use multiple tools/add-ons, etc.
- Completely free to use (thanks to Bing Image Search, Google TTS and Phonemizer)
- Additional OpenAI model support (ChatGPT, Dall-e, Whisper)


Note: At present, this project is unfinished but it does the job (for me). I decided to publish already because why not. More to come.


### How to
Several note types are supported. The template of your Anki cards is automatically generated based on the columns in your `.txt` file (see example in input folder).
    - The first column is always the front of the card and should be in the foreign language.
    - The second column is always the back of the card and should be in your known language.
    - A "Reverse" column will create a back-to-front card.
    - A "Q&A" column is for Q&A cards where the front is the question and the back is the answer, both in the foreign language.
    - A "Listen" column is for cards with only a sound file on the front.
    - An "Image" column will create a card with an image on the back.
    - ...
    - TODO: Give a complete list of supported columns.
    - These columns can be combined, e.g. Listen, Sound and Image will create a card with a sound file on the front only and an additional image on the back.


Good to know:
- For the Phonemizer you need Phonemizer installed (for macos use the macports version)
- In the `.txt`, new lines for a field can be created in three ways:
    -  putting the content in quotes ("content") and adding new lines, or
    -  adding `<br>`, or
    -  adding `\n`.




TODO: Explain Note types ...
1. Vanilla
	- Front with: vocab, sound, phonetics
    - Back with: translation
    - Extra with: remark, image, ...

2. Reverse
	- added back-front 

3. Listen
   - Front with: sound only
   - Back with: vocab, phonetics, translation

4. Q&A
   - Front with: 
