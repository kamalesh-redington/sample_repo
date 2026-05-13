from pathlib import Path
from typing import List
from source.base import DataSource


class LocalFileSource(DataSource):

    def __init__(self, config):
        self.path = Path(config["source"]["path"])

    def download(self) -> List[str]:
        files = []

        if self.path.is_file():
            return [str(self.path)]

        for file in self.path.glob("**/*"):
            if file.is_file():
                files.append(str(file))

        return files
