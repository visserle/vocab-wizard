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

import pandas as pd
import genanki


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

def read_file(df_file):
    encodings = ['utf-8', 'iso-8859-1', 'windows-1252']
    for encoding in encodings:
        try:
            # Read the file using pandas
            df = pd.read_csv(df_file, encoding=encoding)
            # Return the DataFrame if it's not empty
            if not df.empty:
                return df.fillna('')
        except UnicodeDecodeError:
            continue
        except pd.errors.EmptyDataError:
            continue
    raise ValueError(f"Could not read the file {df_file} with any of the provided encodings.")


def make_deck(deck_name):
    deck_id = generate_unique_id(deck_name + str(time.time()))
    return genanki.Deck(
        deck_id,
        deck_name
    )

def make_model(deck_name, fields, style: str | Path = ''):
    style = Path(style)
    if style.is_file():
        with open(style, 'r') as f:
            style = f.read()

    model_id = generate_unique_id(deck_name)
    fields = [{'name': field} for field in fields]
    templates = [
        {
            'name': 'Card 1',
            'qfmt': '{{Front}}{{Audio}}',
            'afmt': '{{FrontSide}} <hr> {{Back}} <hr> {{Extra}} <hr> {{Image}} <hr> {{More}}',
        },
        {
            'name': 'Card 2',
            'qfmt': '{{Back}}{{Audio}}',
            'afmt': '{{FrontSide}} <hr> {{Front}}{{Audio}} <hr> {{Extra}} <hr> {{Image}} <hr> {{More}}',
        },
    ]
    return genanki.Model(
        model_id,
        name="Basic (opt. reversed)",
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

def make_package(deck, media_files: list | None = None, output_dir: str | Path = ''):
    output_dir = Path(output_dir)
    my_package = genanki.Package(deck)
    if media_files:
        my_package.media_files = media_files
    my_package.write_to_file(output_dir / f"{deck.name}.apkg")


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

def main():
    parser = argparse.ArgumentParser(description='Create Anki decks from CSV or simple Markdown files.')
    parser.add_argument('file', help='File to import (CSV or Markdown). The file must have a header row that defines the fields for the Anki cards.')
    parser.add_argument('--deck-name', default=None, help='Optional: Custom name for the Anki deck. If not provided, the deck name is derived from the file name.')
    parser.add_argument('--package-name', default=None, help='Optional: Custom name for the Anki package file (without .apkg extension). If not provided, the package name is the same as the deck name.')

    args = parser.parse_args()

    file_name = args.file
    deck_name = args.deck_name if args.deck_name else os.path.splitext(os.path.basename(file_name))[0]
    package_name = args.package_name if args.package_name else deck_name + '.apkg'

    if not os.path.exists(file_name):
        print(f"Error: The file {file_name} does not exist.")
        return

    try:
        file_data = read_file(file_name)
    except ValueError as e:
        print(e)
        return
    
    deck = make_deck(deck_name)
    model = make_model(deck_name, file_data.columns, "style.css")
    successful_cards, total_rows = make_note(deck, model, file_data)
    make_package(deck, media_files=None)

    print(f"Anki package '{package_name}' created successfully.")
    print(f"Created {successful_cards} cards out of {total_rows} possible lines.")
    

if __name__ == "__main__":
    main()
