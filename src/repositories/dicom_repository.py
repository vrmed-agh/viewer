from __future__ import annotations

from collections import defaultdict

import numpy as np
import pydicom
from pydicom.fileset import FileSet

from src.models.dataset import Dataset
from src.models.scan import Scan
from src.models.slice_data import SliceData
from src.repositories.base import Repository


class DicomRepository(Repository):
    def load(self, path: str, dataset_name: str) -> Dataset:
        file_set = FileSet(path)
        scan_map: dict[str, list] = defaultdict(list)

        for file_instance in file_set:
            record = file_instance.node._record
            if str(getattr(record, "DirectoryRecordType", "")).upper() != "IMAGE":
                continue
            series_record = file_instance.node.parent._record
            modality = str(getattr(series_record, "Modality", ""))
            if modality != "CT":
                continue
            series_uid = str(series_record.SeriesInstanceUID)
            scan_map[series_uid].append(file_instance)

        scans: list[Scan] = []
        for series_uid, instances in scan_map.items():
            scan = self._build_scan(series_uid, instances)
            if scan.slice_count > 0:
                scans.append(scan)

        scans.sort(key=lambda scan: scan.series_number)
        return Dataset(dataset_name=dataset_name, scans=scans)

    def _build_scan(self, series_uid: str, instances: list) -> Scan:
        series_record = instances[0].node.parent._record
        series_number = int(getattr(series_record, "SeriesNumber", 0))
        modality = str(getattr(series_record, "Modality", "CT"))
        series_description = str(getattr(series_record, "SeriesDescription", "") or "").strip()

        slices: list[SliceData] = []
        first_dcm = None
        for file_instance in instances:
            dcm = pydicom.dcmread(file_instance.path)
            if first_dcm is None:
                first_dcm = dcm
                if not series_description:
                    series_description = str(getattr(dcm, "SeriesDescription", "") or "").strip()
            slice_data = self._build_slice(dcm)
            slices.append(slice_data)

        slices.sort(key=lambda slice_data: (slice_data.instance_number, slice_data.slice_location))
        is_localizer = self._is_localizer_like(first_dcm, series_description, len(slices))
        plane = "localizer" if is_localizer else self._detect_plane(first_dcm, series_description)

        return Scan(
            series_number=series_number,
            series_instance_uid=series_uid,
            modality=modality,
            slices=slices,
            series_description=series_description,
            plane=plane,
            is_localizer=is_localizer,
        )

    def _build_slice(self, dcm) -> SliceData:
        pixel_array = dcm.pixel_array
        instance_number = int(getattr(dcm, "InstanceNumber", 0))
        slice_location = float(getattr(dcm, "SliceLocation", 0.0))

        window_center = getattr(dcm, "WindowCenter", 50.0)
        window_width = getattr(dcm, "WindowWidth", 500.0)
        if hasattr(window_center, "__iter__"):
            window_center = float(list(window_center)[0])
        if hasattr(window_width, "__iter__"):
            window_width = float(list(window_width)[0])

        return SliceData(
            pixel_array=pixel_array,
            instance_number=instance_number,
            slice_location=slice_location,
            rows=int(dcm.Rows),
            cols=int(dcm.Columns),
            rescale_slope=float(getattr(dcm, "RescaleSlope", 1.0)),
            rescale_intercept=float(getattr(dcm, "RescaleIntercept", 0.0)),
            window_center=float(window_center),
            window_width=float(window_width),
        )

    def _is_localizer_like(self, dcm, series_description: str, slice_count: int) -> bool:
        if slice_count <= 1:
            return True

        desc = (series_description or "").lower()
        desc_tokens = ("scout", "localizer", "locator", "topogram", "surview", "survey")
        if any(token in desc for token in desc_tokens):
            return True

        image_type = getattr(dcm, "ImageType", None)
        if image_type is not None:
            joined = " ".join(str(value).lower() for value in image_type)
            if any(token in joined for token in desc_tokens + ("projection",)):
                return True

        return False

    def _detect_plane(self, dcm, series_description: str) -> str:
        plane_from_iop = self._plane_from_image_orientation(dcm)
        if plane_from_iop is not None:
            return plane_from_iop
        return self._plane_from_description(series_description)

    def _plane_from_image_orientation(self, dcm) -> str | None:
        orientation = getattr(dcm, "ImageOrientationPatient", None)
        if orientation is None:
            return None
        try:
            values = [float(value) for value in orientation]
        except Exception:
            return None
        if len(values) != 6:
            return None

        row = np.array(values[:3], dtype=float)
        col = np.array(values[3:], dtype=float)
        normal = np.cross(row, col)
        if not np.any(np.isfinite(normal)):
            return None

        dominant_axis = int(np.argmax(np.abs(normal)))
        if dominant_axis == 0:
            return "sagittal"
        if dominant_axis == 1:
            return "coronal"
        return "axial"

    def _plane_from_description(self, description: str) -> str:
        text = (description or "").lower()
        if any(token in text for token in ("sag", "strza", "sagittal")):
            return "sagittal"
        if any(token in text for token in ("cor", "czol", "czoł", "frontal", "coronal")):
            return "coronal"
        if any(token in text for token in ("axi", "osiow", "osi", "trans", "poprz")):
            return "axial"
        return "unknown"
