from dataclasses import dataclass, field

from src.models.scan import Scan


@dataclass
class Dataset:
    dataset_name: str
    scans: list[Scan] = field(default_factory=list)

    @property
    def scan_count(self) -> int:
        return len(self.scans)