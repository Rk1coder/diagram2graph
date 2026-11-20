"""Measure actual model extraction on every frozen original development fixture."""

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from diagram2graph.metrics import score_graph  # noqa: E402
from diagram2graph.model import PROMPT, Engine  # noqa: E402
from diagram2graph.service import Service  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("artifacts/evaluation.json"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    tasks = json.loads((root / "examples/tasks.json").read_text())
    service = Service(Engine())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    image_dir = args.output.parent / "images"
    image_dir.mkdir(exist_ok=True)
    rows = []
    for task in tasks:
        path = root / "examples" / task["image"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == task["sha256"], (
            "Fixture changed; define a new dataset version."
        )
        row = {
            "id": task["id"],
            "image": task["image"],
            "expected": task["expected"],
            "source_sha256": task["sha256"],
            "model": {"id": service.engine.model_id, "revision": service.engine.revision},
            "settings": service.engine.settings,
            "prompt_sha256": service.engine.prompt_sha256,
        }
        started = time.perf_counter()
        try:
            result = service.extract(path)
            row["report"] = result["report"]
            row["score"] = score_graph(task["expected"], result["report"]["graph"])
            for suffix, key in [("svg", "svg_path"), ("png", "png_path"), ("mmd", "mermaid_path")]:
                shutil.copyfile(result[key], image_dir / (task["id"] + "." + suffix))
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
            if hasattr(exc, "raw_prediction"):
                row["raw_prediction"] = exc.raw_prediction
        row["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        rows.append(row)
        record = {
            "scope": "Three original development fixtures; not an independent benchmark.",
            "prompt": PROMPT,
            "results": rows,
            "total": len(rows),
            "errors": sum("error" in r for r in rows),
        }
        args.output.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
        print(task["id"], row.get("score", row.get("error")), flush=True)
    return 1 if any("error" in row for row in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
