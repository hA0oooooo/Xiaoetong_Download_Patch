"""Probe core connectivity without displaying any session token or playback URL."""
import argparse
import json
from pathlib import Path

from xiaoetong_assistant.native import NativeClient


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--courses", action="store_true")
    args = parser.parse_args()
    client = NativeClient(Path(__file__).resolve().parents[1])
    try:
        status = client.status()
        print(json.dumps(status, ensure_ascii=False))
        if args.courses and status.get("authenticated"):
            total = sum(len(rows) for rows in client.course_pages())
            print(json.dumps({"course_count": total, "pagination_complete": True}))
    finally:
        client.close()


if __name__ == "__main__":
    main()
