"""Minimal native-session list and selected-resource download CLI."""
import argparse
import threading
from pathlib import Path

from xiaoetong_assistant.jobs import download_resource
from xiaoetong_assistant.native import NativeClient

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("list","download"))
    parser.add_argument("--course",required=True)
    parser.add_argument("--select",help="Comma-separated 1-based resource indices")
    parser.add_argument("--output",type=Path,default=None)
    args = parser.parse_args()
    client = NativeClient(ROOT)
    try:
        matches = [row for page in client.course_pages() for row in page if args.course in str(row.get("title",""))]
        if len(matches) != 1:
            raise ValueError("Course title must identify exactly one course")
        resources = client.resources(matches[0])
        videos = [item for item in resources if item.resource_type in (3, 51) and item.unlocked and not item.trial]
        for index,item in enumerate(videos,1):
            print(f"{index}. {item.title}",flush=True)
        if args.action == "list":
            print(f"Resources: {len(videos)}")
            return
        if not args.output:
            raise ValueError("--output is required for downloads")
        if not args.select:
            raise ValueError("--select is required for downloads")
        selection = [int(value) for value in args.select.split(",")]
        if not selection or len(selection) != len(set(selection)) or any(index < 1 or index > len(videos) for index in selection):
            raise ValueError("Invalid resource selection")
        for index in selection:
            item = videos[index-1]
            destination, _ = download_resource(client, item, args.output.resolve(), threading.Event())
            print(f"Saved: {destination}", flush=True)

    finally:
        client.close()


if __name__ == "__main__":
    main()
