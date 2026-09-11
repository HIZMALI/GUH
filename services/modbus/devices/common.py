from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class Register:
    name: str
    address: int
    width: int
    scale: float
    signed: bool
    unit: str
    source: str
    page: int
    convention: str = "PDU zero-based"
    note: str = ""


def words_checked(words: Sequence[int], width: int | None = None) -> list[int]:
    values = list(words)
    if width is not None and len(values) != width:
        raise ValueError(f"Expected {width} registers, received {len(values)}")
    if any(type(word) is not int or not 0 <= word <= 0xFFFF for word in values):
        raise ValueError("Registers must be uint16 integers")
    return values


def decode_integer(words: Sequence[int], *, signed: bool = False,
                   word_order: str = "big") -> int:
    values = words_checked(words)
    if not values:
        raise ValueError("Missing registers")
    if word_order not in ("big", "little"):
        raise ValueError("word_order must be big or little")
    if word_order == "little":
        values.reverse()
    value = 0
    for word in values:
        value = (value << 16) | word
    bits = 16 * len(values)
    return value - (1 << bits) if signed and value & (1 << (bits - 1)) else value


def read_value(registers: Mapping[int, int], spec: Register, word_order: str) -> int | float:
    words = [registers[spec.address + offset] for offset in range(spec.width)]
    value = decode_integer(words, signed=spec.signed, word_order=word_order)
    return value if spec.scale == 1 else value * spec.scale
