"""Prepare/install/restore the bridge; never terminate a user's client process."""
import argparse
import json
from pathlib import Path

from xiaoetong_assistant.patching import inspect_fuses, install, prepare, restore, rebind

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("inspect", "prepare", "install", "restore", "rebind"))
    parser.add_argument("--client", type=Path, required=True, help="Directory containing the learner executable and resources folder")
    args = parser.parse_args()
    bridge = ROOT / "src/xiaoetong_assistant/native_bridge.cjs"
    if args.action == "inspect":
        result = inspect_fuses(args.client / "小鹅通学员版.exe")
    elif args.action == "prepare":
        result = prepare(args.client / "resources/app.asar", ROOT / "runtime/prepared-client.asar", bridge)
    elif args.action == "install":
        result = install(args.client, bridge)
    elif args.action == "rebind":
        result = rebind(args.client, bridge)
    else:
        restore(args.client)
        result = {"restored": True}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
