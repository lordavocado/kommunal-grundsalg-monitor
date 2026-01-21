import os
import requests

BASE = os.environ["SHEETS_WEBAPP_URL"]

def append_row(sheet_name: str, row: list) -> None:
    payload = {"sheet": sheet_name, "row": row}
    r = requests.post(BASE, json=payload, timeout=30)
    r.raise_for_status()
