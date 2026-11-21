#!/usr/bin/env python3
"""Download Mila's models from Hugging Face into one folder.

Safe by design: it only adds files. It never deletes, moves or overwrites
anything, and it skips models that are already downloaded.

Usage:
  python3 download_models.py --list
  python3 download_models.py --group voice_out ears --dest ~/MilaModels
  python3 download_models.py --id gradium/phonon-31m-en --dest ~/MilaModels
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

MANIFEST = Path(__file__).resolve().parent.parent / "models.json"


def load_models():
    data = json.loads(MANIFEST.read_text())
    return data["huggingface"]


def main():
    hf = load_models()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--list", action="store_true", help="show every model and stop")
    p.add_argument("--group", nargs="*", default=[], choices=sorted(hf), help="download whole groups")
    p.add_argument("--id", nargs="*", default=[], help="download specific Hugging Face ids")
    p.add_argument("--dest", default="~/MilaModels", help="folder to download into (default ~/MilaModels)")
    p.add_argument("--min-free-gb", type=float, default=25, help="stop if less free disk than this")
    args = p.parse_args()

    if args.list or not (args.group or args.id):
        for group, models in hf.items():
            print(f"\n[{group}]")
            for m in models:
                print(f"  {m['id']:45} {m['role']}  ({m['license']})")
        return

    wanted = [m["id"] for g in args.group for m in hf[g]] + list(args.id)
    dest = Path(args.dest).expanduser()
    dest.mkdir(parents=True, exist_ok=True)

    free_gb = shutil.disk_usage(dest).free / 1e9
    if free_gb < args.min_free_gb:
        sys.exit(f"Only {free_gb:.0f} GB free in {dest}. Free up space or pass --min-free-gb. Nothing was downloaded.")

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        sys.exit("Missing tool. Run: pip install -U huggingface_hub")

    for repo_id in wanted:
        target = dest / repo_id.replace("/", "__")
        if target.exists() and any(target.iterdir()):
            print(f"skip  {repo_id} (already in {target})")
            continue
        print(f"get   {repo_id} -> {target}")
        try:
            snapshot_download(repo_id=repo_id, local_dir=str(target))
        except Exception as e:  # keep going with the rest
            print(f"FAIL  {repo_id}: {e}")
    print("\nDone. Nothing was deleted.")


if __name__ == "__main__":
    main()
