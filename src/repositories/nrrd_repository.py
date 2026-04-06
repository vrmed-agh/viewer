from src.models.dataset import Dataset
from src.repositories.base import Repository


class NrrdRepository(Repository):
    def load(self, path: str, dataset_name: str) -> Dataset:
        raise NotImplementedError(
            "NrrdRepository is not yet implemented. "
            "Install pynrrd and implement NRRD loading here."
        )