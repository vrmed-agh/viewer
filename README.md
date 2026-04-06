# VRMed Viewer

Przeglądarka obrazów DICOM 2D.

![Screenshot](screenshot.png)

## Instalacja

Projekt używa menadżera pakietów `uv` zamiast `pip` czy `poetry`, ponieważ `uv` jest już praktycznie standardowym dla Pythona.
Zainstaluj go zgodnie z instrukcjami na [stronie](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Dane

Dane wrzucamy do katalogu `data/`, np.:

```
data/
  Zatoki 1/
    DICOMDIR
    DICOM/
      ...
```

## Uruchomienie

```bash
uv run main.py --dataset "Zatoki 1"
```

## Autorzy
- Paweł Grzywa
- Hubert Piechura
- Sonia Stanula
- Ewa Komórkiewicz
- Piotr Dusza
- Mateusz Woźniak