from __future__ import annotations

import json
import pathlib
import subprocess
from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any, Optional, Union

DATA_PATH = pathlib.Path(r"H:\Borderlands\BL3 Data")
JWP_PATH = r"H:\JWP.exe"

DATA_VERSION = 21

JSON = dict[str, Any]


class _AbstractAsset(ABC):
    _full_path: pathlib.Path
    path: str

    def __init__(self, path: Union[str, pathlib.Path]) -> None:
        if isinstance(path, str) and path[0] == "/":
            path = path[1:]
        self._full_path = (DATA_PATH / path).resolve()

        try:
            self._full_path.relative_to(DATA_PATH)
        except ValueError:
            self._full_path = DATA_PATH

        parts = self._full_path.relative_to(DATA_PATH).parts
        if len(parts) < 1:
            self.path = "/"
        else:
            self.path = "/" + "/".join(parts) + "/"

    def __repr__(self) -> str:
        return f"{self.__class__.__qualname__}(\"{self.path}\")"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, _AbstractAsset):
            return False
        return self._full_path == other._full_path

    @property
    def parent(self) -> AssetFolder:
        if self._full_path == DATA_PATH:
            if isinstance(self, AssetFolder):
                return self
            else:
                return AssetFolder(self._full_path)
        return AssetFolder(self._full_path.parent)

    @property
    def name(self) -> str:
        return self._full_path.stem

    @abstractmethod
    def exists(self) -> bool:
        raise NotImplementedError

    def glob(self, pattern: str) -> Iterator[_AbstractAsset]:
        if pattern[0] == "/":
            pattern = pattern[1:]

        known_paths = set()
        for path in self._full_path.glob(pattern):
            trimmed_path = path.with_suffix("")
            if trimmed_path in known_paths:
                continue
            known_paths.add(trimmed_path)

            if path.is_dir():
                yield AssetFolder(path)
            elif path.is_file():
                yield AssetFile(path)


class AssetFile(_AbstractAsset):
    _asset_path: pathlib.Path
    _json_path: pathlib.Path

    _data: Optional[list[JSON]]

    def __init__(self, path: Union[str, pathlib.Path]) -> None:
        super().__init__(path)

        self.path = self.path[:-1]

        if self._full_path.suffix != "":
            self.path = self.path[:-len(self._full_path.suffix)]
            self._full_path = self._full_path.with_suffix("")

        self._asset_path = self._full_path.with_suffix(".uasset")
        self._json_path = self._full_path.with_suffix(".json")

        self._data = None

    def exists(self) -> bool:
        return self._asset_path.exists()

    def as_folder(self) -> AssetFolder:
        return AssetFolder(self._full_path)

    def _load_data(self) -> None:
        with self._json_path.open(encoding="utf-8") as file:
            self._data = json.load(file)

    def _run_jwp(self) -> None:
        subprocess.run(
            [JWP_PATH, "serialize", str(self._full_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    def _update_serialization(self) -> None:
        if not self.exists():
            self._data = None
            return

        if not self._json_path.exists():
            self._run_jwp()
            # If the serialized path still doesn't exist then JWP failed
            if not self._json_path.exists():
                self._data = None
                return

        self._load_data()

        if self._data is None or len(self._data) < 1:
            return

        if "_apoc_data_ver" not in self._data[0] or self._data[0]["_apoc_data_ver"] < DATA_VERSION:
            self._run_jwp()
            self._load_data()

    @property
    def data(self) -> list[JSON]:
        if self._data is None:
            if not self.exists():
                raise FileNotFoundError(f"Could not find asset file at '{self._asset_path}'")
            self._update_serialization()
            if self._data is None:
                raise RuntimeError(f"Unable to serialize asset file '{self._asset_path}'")
        return self._data

    def iter_exports_of_class(self, *cls: str) -> Iterator[JSON]:
        for export in self.data:
            if export["export_type"] in cls:
                yield export

    def get_single_export(self, *cls: str) -> JSON:
        gen = self.iter_exports_of_class(*cls)
        first: JSON
        try:
            first = next(gen)
        except (GeneratorExit, StopIteration) as ex:
            raise ValueError(
                "There are no exports of classes "
                + ", ".join(f"'{c}'" for c in cls)
            ) from ex
        try:
            next(gen)
        except (GeneratorExit, StopIteration):
            return first
        raise ValueError(
            "There are multiple exports of classes "
            + ", ".join(f"'{c}'" for c in cls)
        )


class AssetFolder(_AbstractAsset):
    def exists(self) -> bool:
        return self._full_path.exists()

    def __truediv__(self, other: Union[str, pathlib.Path, _AbstractAsset]) -> AssetFolder:
        if not isinstance(other, (str, pathlib.Path, _AbstractAsset)):
            raise TypeError(f"Invalid type to append to path '{type(other)}'")

        new_path: pathlib.Path
        if isinstance(other, _AbstractAsset):
            new_path = self._full_path / other._full_path
        else:
            new_path = self._full_path / other
        new_path.resolve()

        try:
            new_path.relative_to(DATA_PATH)
        except ValueError:
            new_path = DATA_PATH

        return AssetFolder(new_path)

    def as_file(self) -> AssetFile:
        return AssetFile(self._full_path)

    def child_files(self) -> Iterator[AssetFile]:
        if not self.exists:
            raise FileNotFoundError(f"Could not find directory at '{self._full_path}'")
        for child in self._full_path.iterdir():
            if child.is_file() and child.suffix == ".uasset":
                yield AssetFile(child.relative_to(DATA_PATH))

    def child_folders(self) -> Iterator['AssetFolder']:
        if not self.exists:
            raise FileNotFoundError(f"Could not find directory at '{self._full_path}'")
        for child in self._full_path.iterdir():
            if child.is_dir():
                yield AssetFolder(child.relative_to(DATA_PATH))

    def search_child_files(self, prefix: str) -> Iterator[AssetFile]:
        if not self.exists:
            raise FileNotFoundError(f"Could not find directory at '{self._full_path}'")
        prefix = prefix.lower()
        for child in self._full_path.glob("**/*"):
            if child.suffix == ".uasset" and child.stem.lower().startswith(prefix):
                yield AssetFile(child.relative_to(DATA_PATH))


_glob_root = AssetFolder("/")


def glob(pattern: str) -> Iterator[_AbstractAsset]:
    yield from _glob_root.glob(pattern)
