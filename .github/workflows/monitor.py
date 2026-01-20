from sheets import append_row
from datetime import datetime, timezone

def main():
    now = datetime.now(timezone.utc).isoformat()
    append_row("events", [
        now,
        "system",
        "Repo setup test",
        "GitHub Actions ran successfully",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        1.0,
        ""
    ])
    print("✅ Test row written to Google Sheet")

if __name__ == "__main__":
    main()
