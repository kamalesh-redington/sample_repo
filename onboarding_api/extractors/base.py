from abc import ABC, abstractmethod

class DocumentExtractor(ABC):

    @abstractmethod
    def extract_text(self, file_path: str) -> str:
        raise NotImplementedError
