from abc import ABC, abstractmethod


class ObjectStore(ABC):

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def save(self, key, data):
        pass

    @abstractmethod
    def read(self, key):
        pass

    @abstractmethod
    def list_objects(self):
        pass