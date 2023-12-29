WORK IN PROGRESS

# vocab_wizard
Old-school vocabulary booklets are for nerds? Try out these illustrated, spoken, phonemized interactive Anki cards to get the attention of your overstimulated brain for once. Make superb learning material using completely free resources like Bing's image search, Google's text-to-speech and Phonemizer's phonemization in one go (OpenAI model support also available).

Note: At present, this project is unfinished but it does the job (for me). More to come soon.


### How to
Configure your Anki cards using the column header of the `.txt.` You want images for your cards? Add `Image` as a column, save the `.txt` and run the code (via `testing.ipnyb`as of now). 

- The first column must be in the foreign language
- In the `.txt`, new lines can be created by:
	-  putting the content of a field in quotes ("content") and adding new lines,
    -  adding `<br>` or
    -  adding `\n`
- The first column is always the vocab on the front, the second column is always the vocab on the back



### Note types # TODO
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
