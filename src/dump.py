"""
Copied from https://github.com/PaperclipBadger/gpt-flashcards/blob/main/dump.py

You can use dump.py to dump the contents of an Anki package as CSV files, which is useful for debugging (it saves you making a round trip to Anki desktop).

poetry run python dump.py WithGPT.apkg
"""

import csv
import pathlib
import shutil
import sys

from src.anki import read_package


collection = read_package(sys.argv[1])

output_path = pathlib.Path("deck")
shutil.rmtree(output_path, ignore_errors=True)
output_path.mkdir()

for note in collection.notes:
    keys = list(note.fields.keys())
    keys.append("tags")

    values = list(note.fields.values())
    values.append(", ".join(note.tags))

    row = dict(zip(keys, values))

    path = pathlib.Path(f"deck/{note.model.name}.csv")
    write_header = not path.exists()

    with open(path, "a") as f:
        writer = csv.DictWriter(f, keys)

        if write_header:
            writer.writeheader()

        writer.writerow(row)