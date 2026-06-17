import re

CYR_TO_LAT = {"А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H",
              "О": "O", "Р": "P", "С": "C", "Т": "T", "У": "Y", "Х": "X"}
LAT_TO_CYR = {v: k for k, v in CYR_TO_LAT.items()}

_LETTERS = "АВЕКМНОРСТУХABEKMHOPCTYX"
_PLATE_RE = re.compile(rf"^[{_LETTERS}]\d{{3}}[{_LETTERS}]{{2}}\d{{2,3}}$", re.IGNORECASE)


def normalize(text: str) -> str:
    text = text.strip().upper()
    return "".join(CYR_TO_LAT.get(ch, ch) for ch in text)


def is_valid(text: str) -> bool:
    return bool(_PLATE_RE.match(normalize(text)))


def display(plate: str) -> str:
    return "".join(LAT_TO_CYR.get(ch, ch) for ch in plate.upper())


def deeplink(plate: str) -> str:
    return f"delimobil://map/car/{plate}"
