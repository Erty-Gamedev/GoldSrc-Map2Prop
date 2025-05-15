import logging
from typing import Final
from pathlib import Path
from io import BufferedReader
from geoutil import EPSILON
from dataclasses import dataclass
from formats.rmf_reader import RmfReader
from formats import read_int, read_float, read_ntstring, InvalidFormatException
from formats.wad_handler import WadHandler

logger = logging.getLogger(__name__)


MAX_NOTES: Final[int] = 501

@dataclass
class DirEntry:
    offset: int
    size: int
    name: str
    notes: str
    type: int


def slugify(text: str) -> str:
    return text.casefold().replace(' ', '_')


class OLReader:
    def __init__(self, filepath: Path, outputdir: Path):
        self.filepath = filepath
        self.outputdir = outputdir
        wadhandler = WadHandler(filepath.parent, outputdir)

        with self.filepath.open('rb') as file:
            str(file.read(28))  # libHeader ("Worldcraft Prefab Library\r\n\x1a")
            version = read_float(file)
            if abs(version - 0.1) > EPSILON:
                raise InvalidFormatException("Unexpected version")
            
            self.dir_offset = read_int(file)
            self.dir_num_entries = read_int(file)
            self.notes = read_ntstring(file, MAX_NOTES)

            logger.info(f"Reading prefab library with {self.dir_num_entries} prefabs")

            self.entries: list[DirEntry] = []
            for i in range(self.dir_num_entries):
                file.seek(self.dir_offset + (i * 544), 0)
                self.entries.append(self.read_dir_entry(file))
            
            self.rmf_files: dict[str, RmfReader] = {}
            for entry in self.entries:
                file.seek(entry.offset, 0)
                reader = RmfReader(self.filepath, self.outputdir, file, wadhandler)
                self.rmf_files[slugify(entry.name)] = reader
    
    def read_dir_entry(self, file: BufferedReader):
        offset = read_int(file)
        size = read_int(file)
        name = read_ntstring(file, 31)
        notes = read_ntstring(file, MAX_NOTES)
        type = read_int(file)
        return DirEntry(offset, size, name, notes, type)
