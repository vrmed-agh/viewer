import difflib
import json
import queue
import re
import threading
import unicodedata
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
SAMPLE_RATE = 16_000
BLOCKSIZE = 4_000
FUZZY_THRESHOLD = 0.72

POLISH_CHAR_TRANSLATION = str.maketrans({
    "ą": "a",
    "ć": "c",
    "ę": "e",
    "ł": "l",
    "ń": "n",
    "ó": "o",
    "ś": "s",
    "ź": "z",
    "ż": "z",
})

COMMAND_ALIASES: dict[ViewerCommand, list[str]] = {
    ViewerCommand.NEXT_SCAN: [
        "następna seria",
        "nastepna seria",
        "kolejna seria",
        "następny skan",
        "nastepny skan",
        "kolejny skan",
        "następne badanie",
        "nastepne badanie",
    ],
    ViewerCommand.PREV_SCAN: [
        "poprzednia seria",
        "poprzedni skan",
        "poprzednie badanie",
        "wcześniejsza seria",
        "wczesniejsza seria",
    ],
    ViewerCommand.NEXT_SLICE: [
        "następny przekrój",
        "nastepny przekroj",
        "kolejny przekrój",
        "kolejny przekroj",
        "następny",
        "nastepny",
        "dalej",
    ],
    ViewerCommand.PREV_SLICE: [
        "poprzedni przekrój",
        "poprzedni przekroj",
        "wcześniejszy przekrój",
        "wczesniejszy przekroj",
        "poprzedni",
        "wstecz",
        "cofnij przekrój",
        "cofnij przekroj",
    ],
    ViewerCommand.ZOOM_IN: ["przybliż", "przybliz", "powiększ", "powieksz", "zoom in"],
    ViewerCommand.ZOOM_OUT: ["oddal", "pomniejsz", "zoom out"],
    ViewerCommand.PAN_LEFT: ["przesuń w lewo", "przesun w lewo", "w lewo"],
    ViewerCommand.PAN_RIGHT: ["przesuń w prawo", "przesun w prawo", "w prawo"],
    ViewerCommand.PAN_UP: ["przesuń w górę", "przesun w gore", "w górę", "w gore"],
    ViewerCommand.PAN_DOWN: ["przesuń w dół", "przesun w dol", "w dół", "w dol"],
    ViewerCommand.PLANE_CORONAL: [
        "płaszczyzna czołowa",
        "plaszczyzna czolowa",
        "czołowa",
        "czolowa",
    ],
    ViewerCommand.PLANE_SAGITTAL: [
        "płaszczyzna strzałkowa",
        "plaszczyzna strzalkowa",
        "strzałkowa",
        "strzalkowa",
    ],
    ViewerCommand.PLANE_AXIAL: [
        "płaszczyzna poprzeczna",
        "plaszczyzna poprzeczna",
        "płaszczyzna osiowa",
        "plaszczyzna osiowa",
        "poprzeczna",
        "osiowa",
    ],
    ViewerCommand.REPEAT: ["powtórz", "powtorz", "jeszcze raz", "ponów", "ponow"],
    ViewerCommand.UNDO: ["cofnij", "undo"],
    ViewerCommand.INCREASE_CONTRAST: [
        "zwiększ kontrast",
        "zwieksz kontrast",
        "większy kontrast",
        "wiekszy kontrast",
    ],
    ViewerCommand.DECREASE_CONTRAST: [
        "zmniejsz kontrast",
        "mniejszy kontrast",
    ],
    ViewerCommand.INCREASE_BRIGHTNESS: [
        "zwiększ jasność",
        "zwieksz jasnosc",
        "jaśniej",
        "jasniej",
    ],
    ViewerCommand.DECREASE_BRIGHTNESS: [
        "zmniejsz jasność",
        "zmniejsz jasnosc",
        "ciemniej",
    ],
    ViewerCommand.SHOW_MASKS: ["pokaż maski", "pokaz maski", "włącz maski", "wlacz maski"],
    ViewerCommand.HIDE_MASKS: ["ukryj maski", "schowaj maski", "wyłącz maski", "wylacz maski"],
}


STRICT_PLANE_SECOND_WORDS: dict[str, ViewerCommand] = {
    "czolowa": ViewerCommand.PLANE_CORONAL,
    "strzalkowa": ViewerCommand.PLANE_SAGITTAL,
    "poprzeczna": ViewerCommand.PLANE_AXIAL,
    "osiowa": ViewerCommand.PLANE_AXIAL,
}

PLANE_FULL_PHRASES: dict[str, ViewerCommand] = {
    "plaszczyzna czolowa": ViewerCommand.PLANE_CORONAL,
    "plaszczyzna strzalkowa": ViewerCommand.PLANE_SAGITTAL,
    "plaszczyzna poprzeczna": ViewerCommand.PLANE_AXIAL,
    "plaszczyzna osiowa": ViewerCommand.PLANE_AXIAL,
}

PLANE_VOICE_ALIASES: dict[str, ViewerCommand] = {
    "czolowa": ViewerCommand.PLANE_CORONAL,
    "czolowej": ViewerCommand.PLANE_CORONAL,
    "czolowe": ViewerCommand.PLANE_CORONAL,
    "koronalna": ViewerCommand.PLANE_CORONAL,
    "coronal": ViewerCommand.PLANE_CORONAL,
    "strzalkowa": ViewerCommand.PLANE_SAGITTAL,
    "strzalkowej": ViewerCommand.PLANE_SAGITTAL,
    "strzalkowe": ViewerCommand.PLANE_SAGITTAL,
    "strzalkowy": ViewerCommand.PLANE_SAGITTAL,
    "sagittal": ViewerCommand.PLANE_SAGITTAL,
    "sagitalna": ViewerCommand.PLANE_SAGITTAL,
    "osiowa": ViewerCommand.PLANE_AXIAL,
    "osiowej": ViewerCommand.PLANE_AXIAL,
    "osiowe": ViewerCommand.PLANE_AXIAL,
    "osiowy": ViewerCommand.PLANE_AXIAL,
    "osowa": ViewerCommand.PLANE_AXIAL,
    "osowej": ViewerCommand.PLANE_AXIAL,
    "osowe": ViewerCommand.PLANE_AXIAL,
    "poprzeczna": ViewerCommand.PLANE_AXIAL,
    "poprzecznej": ViewerCommand.PLANE_AXIAL,
    "poprzeczne": ViewerCommand.PLANE_AXIAL,
    "poprzeczny": ViewerCommand.PLANE_AXIAL,
    "poprzednia": ViewerCommand.PLANE_AXIAL,
    "poprzedni": ViewerCommand.PLANE_AXIAL,
    "poprzednie": ViewerCommand.PLANE_AXIAL,
}

POLISH_NUMBERS: dict[str, int] = {
    "zero": 0,
    "jeden": 1,
    "jedna": 1,
    "dwa": 2,
    "trzy": 3,
    "cztery": 4,
    "pięć": 5,
    "piec": 5,
    "sześć": 6,
    "szesc": 6,
    "siedem": 7,
    "osiem": 8,
    "dziewięć": 9,
    "dziewiec": 9,
    "dziesięć": 10,
    "dziesiec": 10,
    "jedenaście": 11,
    "jedenascie": 11,
    "dwanaście": 12,
    "dwanascie": 12,
    "trzynaście": 13,
    "trzynascie": 13,
    "czternaście": 14,
    "czternascie": 14,
    "piętnaście": 15,
    "pietnascie": 15,
    "szesnaście": 16,
    "szesnascie": 16,
    "siedemnaście": 17,
    "siedemnascie": 17,
    "osiemnaście": 18,
    "osiemnascie": 18,
    "dziewiętnaście": 19,
    "dziewietnascie": 19,
    "dwadzieścia": 20,
    "dwadziescia": 20,
    "trzydzieści": 30,
    "trzydziesci": 30,
    "czterdzieści": 40,
    "czterdziesci": 40,
    "pięćdziesiąt": 50,
    "piecdziesiat": 50,
    "pięcdziesiąt": 50,
    "sześćdziesiąt": 60,
    "szescdziesiat": 60,
    "siedemdziesiąt": 70,
    "siedemdziesiat": 70,
    "osiemdziesiąt": 80,
    "osiemdziesiat": 80,
    "dziewięćdziesiąt": 90,
    "dziewiecdziesiat": 90,
    "sto": 100,
    "dwieście": 200,
    "dwiescie": 200,
    "trzysta": 300,
    "czterysta": 400,
    "pięćset": 500,
    "piecset": 500,
}

FILLER_WORDS = {
    "pokaz",
    "pokaż",
    "przekroj",
    "przekrój",
    "numer",
    "na",
    "do",
    "idź",
    "idz",
    "przejdź",
    "przejdz",
}

PLANE_GRAMMAR_PHRASES = sorted({
    "plaszczyzna",
    "płaszczyzna",
    "czolowa",
    "czołowa",
    "czolowej",
    "czołowej",
    "strzalkowa",
    "strzałkowa",
    "strzalkowej",
    "strzałkowej",
    "osiowa",
    "osiowej",
    "osowa",
    "osowej",
    "poprzeczna",
    "poprzeczne",
    "poprzecznej",
    "poprzednia",
    "poprzedni",
    "poprzednie",
    "[unk]",
})

GRAMMAR_PHRASES = sorted(
    {
        *[alias for aliases in COMMAND_ALIASES.values() for alias in aliases],
        *PLANE_FULL_PHRASES.keys(),
        *STRICT_PLANE_SECOND_WORDS.keys(),
        "plaszczyzna",
        "pokaż przekrój numer",
        "pokaz przekroj numer",
        "przekrój numer",
        "przekroj numer",
        "następna seria",
        "nastepna seria",
        "poprzednia seria",
        "następny skan",
        "nastepny skan",
        "poprzedni skan",
        *POLISH_NUMBERS.keys(),
        *[str(i) for i in range(0, 501)],
        "[unk]",
    }
)


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


def _strip_diacritics(text: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )


def _normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = text.translate(POLISH_CHAR_TRANSLATION)
    text = "".join(
        char
        for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def _match_plane_token(token: str) -> ViewerCommand | None:
    token = _normalize_text(token)
    if not token:
        return None

    direct = PLANE_VOICE_ALIASES.get(token)
    if direct is not None:
        return direct

    best_command: ViewerCommand | None = None
    best_score = 0.0
    for alias, command in PLANE_VOICE_ALIASES.items():
        score = difflib.SequenceMatcher(None, token, alias).ratio()
        if score > best_score:
            best_score = score
            best_command = command

    if best_command is not None and best_score >= 0.82:
        print(f"[VOICE] plane fuzzy: {token} ({best_score:.2f})")
        return best_command
    return None


def _extract_plane_command(text: str) -> ViewerCommand | None:
    normalized = _normalize_text(text)
    if not normalized:
        return None

    if normalized in PLANE_FULL_PHRASES:
        return PLANE_FULL_PHRASES[normalized]

    tokens = normalized.split()
    if not tokens:
        return None

    if "plaszczyzna" in tokens:
        tokens = tokens[tokens.index("plaszczyzna") + 1:]

    for token in tokens:
        command = _match_plane_token(token)
        if command is not None:
            return command

    return None


def _looks_like_plane_utterance(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False

    if "plaszczyzna" in normalized:
        return True

    for token in normalized.split():
        if token in PLANE_VOICE_ALIASES:
            return True
        for alias in PLANE_VOICE_ALIASES:
            if difflib.SequenceMatcher(None, token, alias).ratio() >= 0.78:
                return True

    return False

def _match_plane_command_strict(normalized: str) -> tuple[ViewerCommand | None, bool]:
    normalized = _normalize_text(normalized)
    if not normalized:
        return None, False

    if normalized in PLANE_FULL_PHRASES:
        return PLANE_FULL_PHRASES[normalized], True

    if normalized in STRICT_PLANE_SECOND_WORDS:
        return STRICT_PLANE_SECOND_WORDS[normalized], True

    tokens = normalized.split()
    if not tokens:
        return None, False

    if "plaszczyzna" not in tokens:
        return None, False

    idx = tokens.index("plaszczyzna")
    tail = tokens[idx + 1:]

    if len(tail) != 1:
        print(f"[VOICE] Ignored invalid plane phrase: {normalized}")
        return None, True

    command = _resolve_plane_second_word(tail[0])
    if command is None:
        print(f"[VOICE] Ignored invalid plane continuation: {tail[0]}")
        return None, True

    return command, True


def _best_command_match(text: str) -> ViewerCommand | None:
    normalized = _normalize_text(text)
    if not normalized:
        return None

    plane_command, was_plane_phrase = _match_plane_command_strict(normalized)
    if was_plane_phrase:
        return plane_command

    alias_pairs: list[tuple[str, ViewerCommand]] = []
    for command, aliases in COMMAND_ALIASES.items():
        for alias in aliases:
            alias_pairs.append((_normalize_text(alias), command))
    alias_pairs.sort(key=lambda item: len(item[0]), reverse=True)

    for alias, command in alias_pairs:
        if alias and alias in normalized:
            return command

    best_score = 0.0
    best_command: ViewerCommand | None = None
    for alias, command in alias_pairs:
        score = difflib.SequenceMatcher(None, normalized, alias).ratio()
        if score > best_score:
            best_score = score
            best_command = command

        normalized_tokens = normalized.split()
        alias_tokens = alias.split()
        window_size = len(alias_tokens)
        if window_size <= len(normalized_tokens):
            for index in range(len(normalized_tokens) - window_size + 1):
                window = " ".join(normalized_tokens[index:index + window_size])
                score = difflib.SequenceMatcher(None, window, alias).ratio()
                if score > best_score:
                    best_score = score
                    best_command = command

    if best_score >= FUZZY_THRESHOLD:
        print(f"[VOICE] fuzzy match: {best_command} ({best_score:.2f})")
        return best_command

    return None


def _parse_slice_number(text: str) -> int | None:
    normalized = _normalize_text(text)
    if not normalized:
        return None

    digit_match = re.search(r"\b(\d{1,3})\b", normalized)
    if digit_match:
        return int(digit_match.group(1))

    tokens = [token for token in normalized.split() if token not in FILLER_WORDS]
    total = 0
    found = False
    for token in tokens:
        if token.isdigit():
            return int(token)
        value = POLISH_NUMBERS.get(token)
        if value is not None:
            total += value
            found = True
    return total if found else None


def _is_go_to_slice_command(text: str) -> bool:
    normalized = _normalize_text(text)
    triggers = [
        "pokaz przekroj",
        "przekroj numer",
        "pokaz przekroj numer",
        "idz do przekroju",
        "przejdz do przekroju",
    ]
    return any(trigger in normalized for trigger in triggers)


class VoiceSteeringHandler(SteeringHandler):
    def __init__(self) -> None:
        self._queue: queue.Queue[ViewerAction] = queue.Queue()
        self._model_path = str(_ensure_model())
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def _listen(self) -> None:
        print("[VOICE] Thread started")

        import sounddevice as sd
        from vosk import KaldiRecognizer, Model

        print("[VOICE] Loading model...")
        model = Model(self._model_path)
        print("[VOICE] Model loaded successfully")

        recognizer = KaldiRecognizer(
            model,
            SAMPLE_RATE,
            json.dumps(GRAMMAR_PHRASES, ensure_ascii=False),
        )
        plane_recognizer = KaldiRecognizer(
            model,
            SAMPLE_RATE,
            json.dumps(PLANE_GRAMMAR_PHRASES, ensure_ascii=False),
        )
        recognizer.SetWords(False)
        plane_recognizer.SetWords(False)

        def callback(indata, frames, time, status) -> None:
            if status:
                print(f"[VOICE] audio status: {status}")

            audio = bytes(indata)
            plane_recognizer.AcceptWaveform(audio)
            if not recognizer.AcceptWaveform(audio):
                return

            result = json.loads(recognizer.Result())
            plane_result = json.loads(plane_recognizer.Result())
            text = result.get("text", "").strip()
            plane_text = plane_result.get("text", "").strip()
            if not text and not plane_text:
                return

            heard_text = text or plane_text
            print(f"[VOICE] Heard: {heard_text}")
            if plane_text and plane_text != heard_text:
                print(f"[VOICE] Plane-heard: {plane_text}")

            if _is_go_to_slice_command(heard_text):
                number = _parse_slice_number(heard_text)
                if number is not None:
                    print(f"[VOICE] → COMMAND: GO_TO_SLICE {number}")
                    self._queue.put(ViewerAction(ViewerCommand.GO_TO_SLICE, number))
                    return

            if _looks_like_plane_utterance(heard_text):
                plane_command = _extract_plane_command(plane_text) or _extract_plane_command(heard_text)
                if plane_command is not None:
                    print(f"[VOICE] → COMMAND: {plane_command}")
                    self._queue.put(ViewerAction(plane_command))
                else:
                    print("[VOICE] No plane match")
                return

            command = _best_command_match(heard_text)
            if command is not None:
                print(f"[VOICE] → COMMAND: {command}")
                self._queue.put(ViewerAction(command))
            else:
                print("[VOICE] No command match")

        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCKSIZE,
            dtype="int16",
            channels=1,
            callback=callback,
        ):
            print("[VOICE] Listening...")
            while not self._stop_event.wait(0.1):
                pass

    def steer(self, events: list[pygame.event.Event]) -> Iterator[ViewerAction]:
        while not self._queue.empty():
            yield self._queue.get_nowait()