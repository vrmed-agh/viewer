from dataclasses import dataclass, field

from src.models.slice_data import SliceData


@dataclass
class Scan:
    series_number: int
    series_instance_uid: str
    modality: str
    slices: list[SliceData] = field(default_factory=list)
    nrrd_mask: object = None

    @property
    def name(self) -> str:
        return f"Series #{self.series_number} ({self.modality})"

    @property
    def slice_count(self) -> int:
        return len(self.slices)