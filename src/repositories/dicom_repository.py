from collections import defaultdict

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

        slices: list[SliceData] = []
        for file_instance in instances:
            dcm = pydicom.dcmread(file_instance.path)
            slice_data = self._build_slice(dcm)
            slices.append(slice_data)

        slices.sort(key=lambda slice_data: slice_data.instance_number)

        return Scan(
            series_number=series_number,
            series_instance_uid=series_uid,
            modality=modality,
            slices=slices,
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