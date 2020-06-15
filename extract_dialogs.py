import bl3dump
import csv
import os

from typing import Set

scripts = bl3dump.AssetFolder("/Game/Dialog/Scripts/")
all_styles: Set[str] = set()

try:
    os.mkdir("dialogs")
except FileExistsError:
    pass

for folder in scripts.child_folders():
    with open(f"dialogs/{folder.name}.csv", "w", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(("Source File", "Dialog Style", "Dialog Line"))
        for asset in folder.search_child_files("DialogScript"):
            source = asset.name
            for export in asset.iter_exports_of_class("DialogPerformanceData"):
                line: str
                style: str
                try:
                    line = export["Text"]["string"]
                except KeyError:
                    continue
                try:
                    style = export["Style"][0]
                except KeyError:
                    style = ""
                all_styles.add(style)
                writer.writerow((source, style, line))

with open("dialogs/styles.txt", "w") as file:
    for style in sorted(all_styles):
        if style == "":
            continue
        file.write(style + "\n")
