import argparse
import os
import hashlib
import time
from pathlib import Path
import dataclasses
import functools
import itertools
import json
import pathlib
import sqlite3
import tempfile
import zipfile
import logging

import pandas as pd
import genanki

logger = logging.getLogger(__name__.rsplit(".", maxsplit=1)[-1])

def generate_integer_id(string):
    """Create a unique integer ID based on a string."""
    hash_object = hashlib.sha1(string.encode())
    return int(hash_object.hexdigest(), 16) % (10 ** 10)

class MyNote(genanki.Note):
    """Generate a unique ID for each note based on the first field."""
    @property
    def guid(self):
        return genanki.guid_for(self.fields[0].strip(' ".').lower())
    
def read_file(df_file: str | Path) -> pd.DataFrame:
    """
    Read a file (.txt, .md, .csv, etc.) with pandas, try different encodings if necessary.
    Returns a pandas DataFrame with the file name as attribute.
    """
    df_file = Path(df_file)
    encodings = ['utf-8', 'iso-8859-1', 'windows-1252']
    for encoding in encodings:
        try:
            df = pd.read_csv(df_file, sep=';', encoding=encoding)
            if not df.empty:
                df.attrs['name'] = df_file.name.rsplit(".", maxsplit=1)[0]
                df = df.replace({'\n': '<br>', '\\n': '<br>'}, regex=True)
                return df.fillna('')
        except UnicodeDecodeError:
            continue
        except pd.errors.EmptyDataError:
            continue
    raise ValueError(f"Could not read the file {df_file} with any of the provided encodings.")

def make_deck(df, deck_name: str | None = None):
    """Create a deck with the ID based on the name of the DataFrame."""
    df_name = df.attrs['name']
    deck_id = generate_integer_id(df_name)
    if deck_name is None:
        deck_name = df_name
    return genanki.Deck(
        deck_id,
        deck_name
    )

def make_model(df, style: str | Path = ''):
    """
    Create a model (card template) with the ID based on the name of the DataFrame.
    The template is automatically generated based on the columns/fields of the DataFrame, which acts as a config.
        - The first column is always the front of the card.
        - The second column is always the back of the card.
        - A column named "Reverse" will create a back-to-front card.
        - A column named "Q&A" will create a Q&A card in the foreign language with Q: and A: prefixes accordingly.
    """
    def _field(field_name):
        """Return a field with the name of the column if it exists in the DataFrame."""
        # in a f-string, a single '{' is escaped by doubling it
        return (f'{{{{{field_name}}}}}' if field_name in df.columns else '')
    
    def _div(field_name):
        """Return a div with the name of the column if it exists in the DataFrame."""
        return (f'<div class="{field_name.lower()}">{_field(field_name)}</div>' if field_name in df.columns else '')
    
    def _h1(headline):
        return f'<h1 class="one"><span>{headline}</span></h1>'
    
    def _prefix():
        """Return the prefixes for Q&A note."""
        if not hasattr(_prefix, "alternator"): # only initialize once
            _prefix.alternator = itertools.cycle(["Q: ", "A: "])
        return next(_prefix.alternator) if "Q&A" in df.columns else ''

    # `style` can be a string with css or a path to a css file
    if Path(style).is_file():
        with open(style, 'r') as f:
            style = f.read()

    # Create a unique ID for the model based on the name of the DataFrame
    df_name = df.attrs['name']
    model_id = generate_integer_id(df_name)

    # Create the templates for the model
    # Terrible code, but works for now. TODO: improve
    front, back = f'{{{{{df.columns[0]}}}}}', f'{{{{{df.columns[1]}}}}}'
    br, hr = '<br>', '<hr>'

    qftm_1 = _prefix() + front + _field('Sound') + br + _div('Phonetics') + hr + _field('Q&A')
    aftm_1 = '{{FrontSide}}' + hr + _prefix() + back + _field('Sound_2') + br + _div('Phonetics_2') + _h1('Extra') + _field('Extra') + hr + _field('Image') + hr + _field('More')
    
    qftm_2 = back + _field('Sound_2') + br + _div('Phonetics_2')
    aftm_2 = '{{FrontSide}}' + hr + front + _field('Sound') + br + _div('Phonetics') + hr + _field('Extra') + hr + _field('Image') + hr + _field('More')

    if "Listen" in df.columns:
        qftm_1 = _field("Sound")
        aftm_1 = '{{FrontSide}}' + br + _prefix() + front + br + _div('Phonetics') + hr + _prefix() + back + _field('Sound_2') + br + _div('Phonetics_2') + _h1('Extra') + _field('Extra') + hr + _field('Image') + hr + _field('More')

    templates = [
        {
            'name': 'Card 1',
            'qfmt': qftm_1,
            'afmt': aftm_1,
        },
        {
            'name': 'Card 2',
            'qfmt': qftm_2,
            'afmt': aftm_2,
        },
    ]

    # Account for listening cards, reverse cards and Q&A cards
    if "listen" in [x.strip().lower() for x in df.columns]:
        if "Sound" not in [x.strip().lower() for x in df.columns]:
            logger.error("Listen column requires Sound column.") # otherwise Anki will find no cards TODO: is this true? whisper integration will show the truth
            raise ValueError("Listen column requires Sound column.")
        logger.info("Front of front-to-back cards will be Sound only.")
    if "reverse" not in [x.strip().lower() for x in df.columns]: # only front-to-back cards and no back-to-front cards
        templates = [templates[0]]
        logger.info("Only front-to-back cards will be created.")
        if "Q&A" in df.columns:
            logger.info("Cards are in Q&A format.")
    else:
        logger.info("Front-to-back and back-to-front cards will be created.")

    # Generate model
    fields = [{'name': field} for field in df.columns] # (genanki expects this format)
    name = "Basic (opt. reversed)" if "Q&A" not in df.columns else "Basic (opt. reversed) Q&A"
    return genanki.Model(
        model_id,
        name=name, # TODO: create model name based on df columns card type
        fields=fields,
        templates=templates,
        css=style
    )

def make_notes(deck, model, df):
    """Create a note for each row in the DataFrame."""

    header = list(df.columns)
    total_rows = len(df)
    successful_notes = 0

    # Create a note for each row in the DataFrame
    for _, row in df.iterrows():
        row_list = row.tolist()
        if len(row_list) > len(header):
            logger.error(f"Number of fields in row exceeds header. Row: {row_list}")
            continue
        # Fill missing fields with empty string
        row_list += [''] * (len(header) - len(row_list)) # TODO: do we need this?
        note = MyNote(
            model=model,
            fields=[_str(field).strip_quotes() for field in row_list],
            tags=None
        )
        deck.add_note(note)
        successful_notes += 1

    logger.info(f"Created {successful_notes} notes out of {total_rows} possible lines.")


def make_package(deck, media_files: list | None = None, apkg_file: str | Path = ''):
    """Create a .apkg file from a deck."""
    apkg_file = Path(apkg_file)
    my_package = genanki.Package(deck)
    if media_files:
        my_package.media_files = media_files
    my_package.write_to_file(apkg_file)


@dataclasses.dataclass(frozen=True)
class Model:
    name: str
    field_names: list[str]


@dataclasses.dataclass(frozen=True)
class Note:
    model: Model
    field_contents: list[str]
    tags: set[str]

    @functools.cached_property
    def fields(self) -> dict[str, str]:
        return dict(itertools.zip_longest(self.model.field_names, self.field_contents, fillvalue=""))


@dataclasses.dataclass(frozen=True)
class Collection:
    models: list[Model]
    notes: list[Note]


def read_package(path: pathlib.Path) -> Collection:
    """
    Read a .apkg file to return a Collection object.
    Copied from https://github.com/PaperclipBadger/gpt-flashcards/blob/main/flashcards/anki.py
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = pathlib.Path(tmpdir)

        with zipfile.ZipFile(path) as zf:
            zf.extract("collection.anki2", path=tmpdir)

        with sqlite3.connect(tmpdir / "collection.anki2") as conn:
            models_json, = conn.execute("SELECT models FROM col").fetchone()
            notes_rows = conn.execute("SELECT mid,flds,tags FROM notes").fetchall()

    models = {}
    for mid, model in json.loads(models_json).items():
        name = model["name"]
        field_names = [fld["name"] for fld in model["flds"]]
        models[int(mid)] = Model(name=name, field_names=field_names)

    notes = []
    for mid, flds, tags in notes_rows:
        model = models[mid]
        fields = flds.split("\x1f")
        tags = set(tags.strip().split())
        note = Note(model=model, field_contents=fields, tags=tags)
        notes.append(note)
    
    return Collection(models, notes)


class _str(str):
    """Custom string class to implement a strip_quotes method."""
    def strip_quotes(self):
        """
        Strips quotes from the string only if it starts and ends with quotes.
        Supports both single ('') and double ("") quotes.

        This way, fields in the vocabulary file can end with a quote that won't be stripped.

        Example:
            - "easy; simple" -> will be stripped because the quotes act as delimiters to allow the usage of semicolons
            - easy, "simple" -> will not be stripped because the quotes are not at the start and end of the string (usage of semicolons is not allowed)
            - "easy; "simple"" -> returns easy; "simple"

        Without this custom method, the following would happen:
            - "easy; simple" -> easy; simple
            - easy, "simple" -> easy, "simple
        """
        if (self.startswith('"') and self.endswith('"')) or (self.startswith("'") and self.endswith("'")):
            return self[1:-1]
        return self
