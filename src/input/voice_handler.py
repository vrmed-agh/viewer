import queue
import threading
import urllib.request
import zipfile
from pathlib import Path
from typing import Iterator

import pygame

from src.input.base import SteeringHandler
from src.input.commands import ViewerAction, ViewerCommand

MODEL_NAME = "vosk-model-small-pl-0.22"
MODEL_URL = f"https://alphacephei.com/vosk/models/{MODEL_NAME}.zip"
MODELS_DIR = Path("models")


def _ensure_model() -> Path:
    model_path = MODELS_DIR / MODEL_NAME
    if model_path.exists():
        return model_path

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = MODELS_DIR / f"{MODEL_NAME}.zip"
    print(f"[VOICE] Downloading model from {MODEL_URL}...")

    def report(block_number: int, block_size: int, total_size: int) -> None:
        if total_size <= 0:
            return
        downloaded = block_number * block_size
        percent = min(100, downloaded * 100 // total_size)
        print(f"[VOICE] Download progress: {percent}%", end="\r")

    urllib.request.urlretrieve(MODEL_URL, archive_path, reporthook=report)
    print("\n[VOICE] Extracting model...")
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(MODELS_DIR)
    archive_path.unlink()
    print("[VOICE] Model ready")
    return model_path


class VoiceSteeringHandler(SteeringHandler):
    def __init__(self) -> None:
        self._queue: queue.Queue[ViewerAction] = queue.Queue()
        self._model_path = str(_ensure_model())
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def _listen(self) -> None:
        print("[VOICE] Thread started")

        import sounddevice as sd
        import json
        from vosk import Model, KaldiRecognizer

        model_path = self._model_path
        print("[VOICE] Loading model...")
        model = Model(model_path)
        print("[VOICE] Model loaded successfully")

        recognizer = KaldiRecognizer(model, 16000)

        phrase_map: list[tuple[str, ViewerCommand]] = [
            ("włącz", ViewerCommand.TOGGLE),
            ("wyłącz", ViewerCommand.TOGGLE),
            ("następny", ViewerCommand.NEXT_SLICE),
            ("poprzedni", ViewerCommand.PREV_SLICE),
            ("przybliż", ViewerCommand.ZOOM_IN),
            ("oddal", ViewerCommand.ZOOM_OUT),
            ("przesuń w lewo", ViewerCommand.PAN_LEFT),
            ("przesuń w prawo", ViewerCommand.PAN_RIGHT),
            ("przesuń w górę", ViewerCommand.PAN_UP),
            ("przesuń w dół", ViewerCommand.PAN_DOWN),
            ("płaszczyzna czołowa", ViewerCommand.PLANE_CORONAL),
            ("płaszczyzna strzałkowa", ViewerCommand.PLANE_SAGITTAL),
            ("płaszczyzna poprzeczna", ViewerCommand.PLANE_AXIAL),
            ("powtórz", ViewerCommand.REPEAT),
            ("cofnij", ViewerCommand.UNDO),
            ("zwiększ kontrast", ViewerCommand.INCREASE_CONTRAST),
            ("zmniejsz kontrast", ViewerCommand.DECREASE_CONTRAST),
            ("zwiększ jasność", ViewerCommand.INCREASE_BRIGHTNESS),
            ("zmniejsz jasność", ViewerCommand.DECREASE_BRIGHTNESS),
            ("pokaż maski", ViewerCommand.SHOW_MASKS),
            ("ukryj maski", ViewerCommand.HIDE_MASKS),
        ]

        polish_numbers = {
            "zero": 0, "jeden": 1, "dwa": 2, "trzy": 3, "cztery": 4,
            "pięć": 5, "sześć": 6, "siedem": 7, "osiem": 8, "dziewięć": 9,
            "dziesięć": 10, "jedenaście": 11, "dwanaście": 12, "trzynaście": 13,
            "czternaście": 14, "piętnaście": 15, "szesnaście": 16,
            "siedemnaście": 17, "osiemnaście": 18, "dziewiętnaście": 19,
            "dwadzieścia": 20, "trzydzieści": 30, "czterdzieści": 40,
            "pięćdziesiąt": 50, "sześćdziesiąt": 60, "siedemdziesiąt": 70,
            "osiemdziesiąt": 80, "dziewięćdziesiąt": 90, "sto": 100,
        }

        def parse_slice_number(text: str) -> int | None:
            tokens = text.replace(",", " ").split()
            total = 0
            found = False
            for token in tokens:
                if token.isdigit():
                    return int(token)
                if token in polish_numbers:
                    total += polish_numbers[token]
                    found = True
            return total if found else None

        def callback(indata, frames, time, status):
            if status:
                print(status)

            data = bytes(indata)

            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").strip().lower()

                if not text:
                    return

                print(f"[VOICE] Heard: {text}")

                if "pokaż przekrój" in text or "przekrój numer" in text:
                    number = parse_slice_number(text)
                    if number is not None:
                        print(f"[VOICE] → COMMAND: GO_TO_SLICE {number}")
                        self._queue.put(ViewerAction(ViewerCommand.GO_TO_SLICE, number))
                        return

                for phrase, command in phrase_map:
                    if phrase in text:
                        print(f"[VOICE] → COMMAND: {command}")
                        self._queue.put(ViewerAction(command))
                        break

        with sd.InputStream(
            samplerate=16000,
            blocksize=8000,
            dtype="int16",
            channels=1,
            callback=callback,
        ):
            print("[VOICE] Listening...")
            while True:
                pass

    def steer(self, events: list[pygame.event.Event]) -> Iterator[ViewerAction]:
        while not self._queue.empty():
            yield self._queue.get_nowait()