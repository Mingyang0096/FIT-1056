# app/utils.py
from datetime import datetime, timezone

def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

def check_range(v: int, low: int, high: int):
    if v < low or v > high:
        raise ValueError(f"value {v} out of range [{low}, {high}]")