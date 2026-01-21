from datetime import datetime, timezone
from sheets import append_row

def main():
    ts = datetime.now(timezone.utc).isoformat()
    append_row("events", [
        ts,
        "system",
        "Repo setup test",
        "GitHub Actions ran successfully"
    ])
    print("✅ Test row written to Google Sheet")

if __name__ == "__main__":
    main()
