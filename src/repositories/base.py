from abc import ABC, abstractmethod

from src.models.dataset import Dataset


class Repository(ABC):
    @abstractmethod
    def load(self, path: str, dataset_name: str) -> Dataset:
        ...