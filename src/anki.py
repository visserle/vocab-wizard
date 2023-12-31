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
        return genanki.guid_for(self.fields[0].strip(' ".\'').lower())
    
def read_file(file_path: str | Path) -> pd.DataFrame:
    """
    Reads a file (.txt, .md, .csv, etc.), returns a pandas DataFrame with the file name as attribute.
    """
    file_path = Path(file_path)
    encodings = ['utf-8', 'iso-8859-1', 'windows-1252']
    for encoding in encodings:
        try:
            df = pd.read_csv(file_path, sep=';', encoding=encoding)
            if not df.empty:
                df.attrs['name'] = file_path.name.rsplit(".", maxsplit=1)[0]
                df = df.replace({'\n': '<br>', '\\n': '<br>', '\\\\n': '<br>'}, regex=True)
                return df.fillna('')
        except UnicodeDecodeError:
            continue
        except pd.errors.EmptyDataError:
            continue
    raise ValueError(f"Could not read the file {file_path} with any of the provided encodings.")

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

def field(field_name, key=None, tag=None):
    """Return a field with the name of the column."""
    # in a f-string, a single '{' is escaped by doubling it
    if key == "type":
        field_str = f'{{{{type:{field_name}}}}}'
    elif key == 'edit':
        field_str = f'{{{{edit:{field_name}}}}}'
    else:
        field_str = f'{{{{{field_name}}}}}'

    if tag == 'div':
        field_str = f'<div class="{field_name.lower()}">{field_str}</div>'
    if tag == 'h1':
        field_str = f'<h1 class="one"><span>{field_str}</span></h1>'

    return field_str

def make_templates(df):
    """
    Templates are automatically generated based on the columns/fields of the DataFrame, which acts as a config.
        - The first column is always the front of the card.
        - The second column is always the back of the card.
        - A column named "Reverse" will create a back-to-front card.
        - A column named "Q&A" will create a Q&A card in the foreign language with Q: and A: prefixes accordingly.
        - A column named "Listen" will create a card with only a sound file on the front.
    """
    br, hr = '<br>', '<hr>'
    Q, A = 'Q: ', 'A: '

    # Set up templates
    model_name = "Basic Vanilla"
    qftm_1 = "".join([
        field(df.columns[0]), field("Sound"), br,
        field("Phonetics", tag='div'), hr
        ])
    aftm_1 = "".join([
        field("FrontSide"),
        field(df.columns[1]), hr,
        field("Remark", key='edit'), hr,
        field("Image"), hr,
        field("More")
        ])

    if "Listen" in df.columns:
        model_name = "Basic Listen"
        qftm_1 = "".join([
            field("Sound"), br,
            ])
        aftm_1 = "".join([
            field("FrontSide"),
            field(df.columns[0]), br,
            field("Phonetics", tag='div'), hr,
            field(df.columns[1]), hr,
            field("Remark", key='edit'), hr,
            field("Image"), hr,
            field("More")
            ])

    if "Q&A" in df.columns:
        model_name = "Basic Q&A"
        qftm_1 = "".join([
            Q, field(df.columns[0]), field("Sound"), br,
            field("Phonetics", tag='div'), hr,
            field("Q&A"), br
            ])
        aftm_1 = "".join([
            field("FrontSide"),
            A, field(df.columns[1]), field("Sound_Answer"), br,
            field("Phonetics_Answer", tag='div'), hr,
            field("Remark", key='edit'), hr,
            field("Image"), hr,
            field("More")
            ])

    if ("Q&A" in df.columns) and ("Listen" in df.columns):
        model_name = "Basic Q&A Listen"
        qftm_1 = "".join([
            Q, field("Sound"), br,
            field("Q&A"), br
            ])
        aftm_1 = "".join([
            field("FrontSide"),
            field(df.columns[0]), br,
            field("Phonetics", tag='div'), hr,
            A, field(df.columns[1]), field("Sound_Answer"), br,
            field("Phonetics_Answer", tag='div'), hr,
            field("Remark", key='edit'), hr,
            field("Image"), hr,
            field("More")
            ])

    if "Reverse" in df.columns:
        model_name = "Basic Reverse"
        if "Listen" in df.columns:
            model_name = "Basic Reverse Listen"
        qftm_2 = "".join([
            field(df.columns[1]), hr,
            field(df.columns[0], "type")
            ])
        aftm_2 = "".join([
            field("FrontSide"),
            field("Sound"), br,
            field("Phonetics", tag='div'), hr,
            field("Remark", key='edit'), hr,
            field("Image"), hr,
            field("More")
            ])

    templates =[{
            'name': 'Card 1',
            'qfmt': qftm_1,
            'afmt': aftm_1,
        }]
    if "Reverse" in df.columns:
        templates.append(
            {
            'name': 'Card 2',
            'qfmt': qftm_2,
            'afmt': aftm_2,
        })

    # Account for listening cards, reverse cards and Q&A cards
    if "Reverse" not in df.columns:
        logger.info("Only front-to-back cards will be created.")
        if "Q&A" in df.columns:
            logger.info("Cards are in Q&A format.")
    elif ("Reverse" in df.columns) and ("Q&A" in df.columns):
        logger.error("Q&A cards cannot be reversed. What would that even mean?")
    else:
        logger.info("Front-to-back and back-to-front cards will be created.")

    if "Listen" in df.columns:
        if df.Sound[0] == "":
            logger.error("Listen column obviously requires Sound column.")
            raise ValueError("Listen column requires Sound column.")
        logger.info("Front of front-to-back cards will be Sound only.")

    return model_name, templates


def make_model(df, style: str | Path = ''):
    """
    Create a model (note type) for the deck.
    """
    # style can be a string with css or a path to a css file
    if Path(style).is_file():
        with open(style, 'r') as f:
            style = f.read()

    model_name, templates = make_templates(df)

    # Generate model
    field_names = df.columns.tolist()
    # add additional fields so that we can have consistent models across different files
    field_names_to_add = ["Remark", "More", "Phonetics", "Sound", "Image"]
    for field_name in field_names_to_add:
        if field_name not in field_names:
            field_names.append(field_name)
    df.attrs['field_names'] = field_names
    fields = [{'name': field} for field in field_names] # (genanki expects this format)
    model_id = generate_integer_id(model_name)

    return genanki.Model(
        model_id=model_id,
        name=model_name,
        fields=fields,
        templates=templates,
        css=style
    )


def make_notes(df, deck, model):
    """Create a note for each row in the DataFrame."""

    header = df.attrs['field_names']
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


def make_package(deck, media_paths: list | None = None, apkg_path: str | Path = ''):
    """Create a .apkg file from a deck."""
    apkg_path = Path(apkg_path)
    my_package = genanki.Package(deck)
    if media_paths:
        my_package.media_files = media_paths
    my_package.write_to_file(apkg_path)


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
