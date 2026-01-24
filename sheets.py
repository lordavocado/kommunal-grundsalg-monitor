import os
import requests
from dotenv import load_dotenv

# Load environment variables from env.local
load_dotenv('env.local')

BASE = os.environ["SHEETS_WEBAPP_URL"]

def append_row(sheet_name: str, row: list) -> None:
    payload = {"sheet": sheet_name, "row": row, "action": "append"}
    r = requests.post(BASE, json=payload, timeout=30)
    r.raise_for_status()

def get_rows(sheet_name: str) -> list:
    payload = {"sheet": sheet_name, "action": "read"}
    r = requests.post(BASE, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data.get("success"):
        raise Exception(f"Failed to read from sheet {sheet_name}: {data.get('error')}")
    return data.get("data", [])
