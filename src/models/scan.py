from dataclasses import dataclass, field

from src.models.nrrd_mask import NrrdMask
from src.models.slice_data import SliceData


@dataclass
class Scan:
    series_number: int
    series_instance_uid: str
    modality: str
    slices: list[SliceData] = field(default_factory=list)
    nrrd_mask: NrrdMask | None = None
    series_description: str = ""
    plane: str = "unknown"
    is_localizer: bool = False

    @property
    def name(self) -> str:
        description = f" - {self.series_description}" if self.series_description else ""
        return f"Series #{self.series_number} ({self.modality}, {self.plane_display_name}){description}"

    @property
    def slice_count(self) -> int:
        return len(self.slices)

    @property
    def plane_display_name(self) -> str:
        if self.is_localizer:
            return "lokalizator"

        mapping = {
            "axial": "osiowa",
            "coronal": "czołowa",
            "sagittal": "strzałkowa",
            "unknown": "nieznana",
            "localizer": "lokalizator",
        }
        return mapping.get(self.plane, self.plane)

    @property
    def is_volume(self) -> bool:
        return not self.is_localizer and self.slice_count > 1
