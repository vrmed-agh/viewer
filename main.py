import argparse
import sys
from pathlib import Path

from src.controllers.viewer_controller import ViewerController
from src.input.keyboard_handler import KeyboardSteeringHandler
from src.input.voice_handler import VoiceSteeringHandler
from src.repositories.dicom_repository import DicomRepository
from src.repositories.nrrd_repository import NrrdRepository
from src.views.pygame_view import PygameView

DATA_ROOT = Path("data")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="VRMed 2D DICOM Viewer")
    parser.add_argument("--dataset", required=True, help='Dataset name, e.g. "Zatoki 1"')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_name = args.dataset
    dicomdir_path = DATA_ROOT / dataset_name / "DICOMDIR"

    if not dicomdir_path.exists():
        print(f"Error: DICOMDIR not found at {dicomdir_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading dataset '{dataset_name}' from {dicomdir_path}...")

    repository = DicomRepository()
    dataset = repository.load(str(dicomdir_path), dataset_name)

    if dataset.scan_count == 0:
        print("Error: No CT scans found in dataset.", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {dataset.scan_count} CT scan(s).")
    for index, scan in enumerate(dataset.scans):
        print(f"  [{index}] {scan.name}: {scan.slice_count} slices")

    # Maski segmentacji (pliki .nrrd) dopasowujemy do serii DICOM po
    # nazwie pliku: nazwa MUSI być liczbą odpowiadającą SeriesNumber,
    # np. "5.nrrd" zostanie dołączona do serii #5. Pliki o innych nazwach
    # (np. opisowych) są po cichu pomijane przez ValueError na int().
    nrrd_repository = NrrdRepository()
    dataset_dir = DATA_ROOT / dataset_name
    for nrrd_path in dataset_dir.glob("*.nrrd"):
        try:
            series_number = int(nrrd_path.stem)
        except ValueError:
            continue
        scan = next((s for s in dataset.scans if s.series_number == series_number), None)
        if scan is None:
            print(f"Warning: no scan with series number {series_number} for {nrrd_path.name}", file=sys.stderr)
            continue
        scan.nrrd_mask = nrrd_repository.load_mask(str(nrrd_path), series_number, scan.slice_count)
        print(f"  attached mask {nrrd_path.name} to series #{series_number}")

    view = PygameView()
    steering_handlers = [KeyboardSteeringHandler(), VoiceSteeringHandler()]
    controller = ViewerController(dataset, view, steering_handlers)
    controller.run()


if __name__ == "__main__":
    main()