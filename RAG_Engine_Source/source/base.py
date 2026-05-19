from abc import ABC, abstractmethod
from typing import List


class DataSource(ABC):
    @abstractmethod
    def download(self) -> List[str]:
        """Download files and return list of local file paths"""
        pass
