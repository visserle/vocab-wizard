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

def generate_unique_id(string):
    hash_object = hashlib.sha1(string.encode())
    return int(hash_object.hexdigest(), 16) % (10 ** 10)

class MyNote(genanki.Note):
    """
    Generate a unique ID for each note based on the first field.
    """
    @property
    def guid(self):
        return genanki.guid_for(self.fields[0].strip(' ".').lower())

def read_file(df_file: str | Path) -> pd.DataFrame:
    df_file = Path(df_file)
    encodings = ['utf-8', 'iso-8859-1', 'windows-1252']
    for encoding in encodings:
        try:
            df = pd.read_csv(df_file, sep=';', encoding=encoding)
            if not df.empty:
                df.attrs['name'] = df_file.name.rsplit(".", maxsplit=1)[0]
                return df.fillna('')
        except UnicodeDecodeError:
            continue
        except pd.errors.EmptyDataError:
            continue
    raise ValueError(f"Could not read the file {df_file} with any of the provided encodings.")


def make_deck(df):
    deck_name = df.attrs['name']
    deck_id = generate_unique_id(deck_name + str(time.time()))
    return genanki.Deck(
        deck_id,
        deck_name
    )

def make_model(df, style: str | Path = ''):

    def _field(field_name):
        # in a f-string, a single '{' is escaped by doubling it
        return (f'{{{{{field_name}}}}}' if field_name in df.columns else '')
    
    def _div(field_name):
        return (f'<div class="{field_name.lower()}">{_field(field_name)}</div>' if field_name in df.columns else '')
    
    def _h1(headline):
        return f'<h1 class="one"><span>{headline}</span></h1>'

    if Path(style).is_file():
        with open(style, 'r') as f:
            style = f.read()

    deck_name = df.attrs['name']
    model_id = generate_unique_id(deck_name)

    front, back = f'{{{{{df.columns[0]}}}}}', f'{{{{{df.columns[1]}}}}}'
    br, hr = '<br>', '<hr>'

    qftm_1 = front + _field('Audio') + br + _div('Phonetics')
    aftm_1 = '{{FrontSide}}' + hr + back + _field('Audio_2') + br + _div('Phonetics_2') + _h1('Extra') + _field('Extra') + hr + _field('Image') + hr + _field('More')

    qftm_2 = back + _field('Audio_2') + br + _div('Phonetics_2')
    aftm_2 = '{{FrontSide}}' + hr + front + _field('Audio') + br + _div('Phonetics') + hr + _field('Extra') + hr + _field('Image') + hr + _field('More')

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

    if "reverse" not in [x.strip().lower() for x in df.columns]: # only front-to-back cards and no back-to-front cards
        templates = [templates[0]]
        logger.info("Only front-to-back cards will be created.")
    else:
        logger.info("Front-to-back and back-to-front cards will be created.")

    fields = [{'name': field} for field in df.columns]

    return genanki.Model(
        model_id,
        name="Basic (opt. reversed)", # TODO
        fields=fields,
        templates=templates,
        css=style
    )

def make_note(deck, model, df):
    header = list(df.columns)
    total_rows = len(df)
    successful_cards = 0

    for _, row in df.iterrows():
        row_list = row.tolist()
        if len(row_list) > len(header):
            print(f"Error: Number of fields in row exceeds header. Row: {row_list}")
            continue
        # Fill missing fields with empty string
        row_list += [''] * (len(header) - len(row_list))
        note = MyNote(
            model=model,
            fields=[str(field).strip('"') for field in row_list],
            tags=None
        )
        deck.add_note(note)
        successful_cards += 1

    return successful_cards, total_rows

def make_package(deck, media_files: list | None = None, apkg_file: str | Path = ''):
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
    """Copied from https://github.com/PaperclipBadger/gpt-flashcards/blob/main/flashcards/anki.py"""
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
