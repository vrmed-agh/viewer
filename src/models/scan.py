from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from src.models.nrrd_mask import NrrdMask
from src.models.slice_data import SliceData


@dataclass
class Scan:
    series_number: int
    series_instance_uid: str
    modality: str
    slices: list[SliceData] = field(default_factory=list)
    nrrd_mask: NrrdMask | None = None
    volume: np.ndarray = field(default_factory=lambda: np.empty((0, 0, 0), dtype=np.int16))
    rescale_slope: float = 1.0
    rescale_intercept: float = 0.0
    window_center: float = 50.0
    window_width: float = 500.0

    @property
    def name(self) -> str:
        return f"Series #{self.series_number} ({self.modality})"

    @property
    def slice_count(self) -> int:
        return self.volume.shape[0] if self.volume.ndim == 3 else len(self.slices)