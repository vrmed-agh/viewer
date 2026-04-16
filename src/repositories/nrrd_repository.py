import numpy as np
import nrrd

from src.models.nrrd_mask import NrrdMask


class NrrdRepository:
    def load_mask(self, file_path: str, series_number: int, expected_slice_count: int) -> NrrdMask:
        data, _ = nrrd.read(file_path)

        slice_axis = self._find_slice_axis(data, expected_slice_count)
        if slice_axis is not None and slice_axis != 0:
            data = np.moveaxis(data, slice_axis, 0)

        return NrrdMask(volume=data, series_number=series_number)

    def _find_slice_axis(self, data: np.ndarray, expected_slice_count: int) -> int | None:
        for axis, length in enumerate(data.shape):
            if length == expected_slice_count:
                return axis
        return None