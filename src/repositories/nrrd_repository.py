import numpy as np
import nrrd

from src.models.nrrd_mask import NrrdMask


class NrrdRepository:
    # Pliki NRRD z maskami segmentacji nie mają ustalonej kolejności osi –
    # w zależności od narzędzia, które je zapisało, oś "slice" może być
    # pierwsza, druga albo trzecia. Żeby móc indeksować wolumen
    # `mask.volume[slice_index]` tak samo jak slice DICOM, szukamy osi o
    # długości równej liczbie przekrojów i przenosimy ją na pozycję 0.
    def load_mask(self, file_path: str, series_number: int, expected_slice_count: int) -> NrrdMask:
        data, _ = nrrd.read(file_path)

        slice_axis = self._find_slice_axis(data, expected_slice_count)
        if slice_axis is not None and slice_axis != 0:
            data = np.moveaxis(data, slice_axis, 0)

        return NrrdMask(volume=data, series_number=series_number)

    # Zakładamy, że tylko jedna z osi ma długość równą liczbie przekrojów
    # DICOM; jeśli żadna nie pasuje, zwracamy None i load_mask zachowa
    # oryginalny układ (co może spowodować błąd przy odczycie przekroju,
    # ale sygnalizuje rozjazd między DICOM a maską).
    def _find_slice_axis(self, data: np.ndarray, expected_slice_count: int) -> int | None:
        for axis, length in enumerate(data.shape):
            if length == expected_slice_count:
                return axis
        return None