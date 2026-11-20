import hashlib
import io
import json
import os
import re
import shutil
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from diagram2graph.graph import parse_graph, to_mermaid, validate_graph
from diagram2graph.images import load_image
from diagram2graph.render import render_png, render_svg
from diagram2graph.storage import private_cache


class ExtractionError(ValueError):
    def __init__(self, message, raw_prediction):
        super().__init__(message)
        self.raw_prediction = raw_prediction


class Service:
    def __init__(self, engine, root=None, max_reports=24):
        self.engine = engine
        self.root = private_cache(
            root or Path(tempfile.gettempdir()) / f"diagram2graph-reports-{os.getuid()}"
        )
        self.max_reports = max_reports
        self._lock = threading.RLock()
        self.prune()

    def prune(self, *, now=None, reserve=0):
        now = time.time() if now is None else now
        with self._lock:
            directories = sorted(
                (p for p in self.root.glob("r-*") if p.is_dir() and not p.is_symlink()),
                key=lambda p: p.stat().st_mtime,
            )
            fresh = []
            for p in directories:
                if now - p.stat().st_mtime > 3600:
                    shutil.rmtree(p)
                else:
                    fresh.append(p)
            for p in fresh[: max(0, len(fresh) - max(0, self.max_reports - reserve))]:
                shutil.rmtree(p)

    def _export(self, graph, report):
        self.prune(reserve=1)
        identity = "r-" + uuid.uuid4().hex
        directory = self.root / identity
        directory.mkdir(mode=0o700)
        report = {
            **report,
            "id": identity,
            "graph": graph,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            (directory / "diagram.svg").write_text(render_svg(graph))
            render_png(graph).save(directory / "diagram.png")
            (directory / "diagram.mmd").write_text(to_mermaid(graph))
            (directory / "report.json").write_text(
                json.dumps(report, indent=2, ensure_ascii=False) + "\n"
            )
        except Exception:
            shutil.rmtree(directory)
            raise
        return {
            "report": report,
            "svg_path": str(directory / "diagram.svg"),
            "png_path": str(directory / "diagram.png"),
            "mermaid_path": str(directory / "diagram.mmd"),
            "report_path": str(directory / "report.json"),
        }

    def extract(self, path):
        image = load_image(path)
        original_sha = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        with self._lock:
            start = time.perf_counter()
            raw = self.engine.predict(image)
            try:
                graph = parse_graph(raw)
            except ValueError as exc:
                raise ExtractionError(str(exc), raw) from exc
            seconds = round(time.perf_counter() - start, 3)
            report = {
                "schema_version": 1,
                "origin": "model",
                "parent_report_id": None,
                "model": {"id": self.engine.model_id, "revision": self.engine.revision},
                "prompt_sha256": getattr(self.engine, "prompt_sha256", None),
                "settings": getattr(self.engine, "settings", {}),
                "input_file_sha256": original_sha,
                "normalized_image_sha256": hashlib.sha256(buffer.getvalue()).hexdigest(),
                "input_size": list(image.size),
                "raw_prediction": raw,
                "model_graph": graph,
                "inference_seconds": seconds,
                "notice": "Model extraction; inspect every label and arrow.",
            }
            return self._export(graph, report)

    def edit(self, report_id, graph):
        graph = validate_graph(graph)
        with self._lock:
            original = self.get_report(report_id)
            report = {
                **original,
                "origin": "user_edit",
                "parent_report_id": report_id,
                "notice": "User-edited graph; the original model extraction remains in model_graph.",
            }
            return self._export(graph, report)

    def get_report(self, report_id):
        if not isinstance(report_id, str) or not re.fullmatch(r"r-[0-9a-f]{32}", report_id):
            raise ValueError("Extract a diagram before editing.")
        with self._lock:
            self.prune()
            path = self.root / report_id / "report.json"
            if not path.is_file() or path.is_symlink():
                raise ValueError("This report expired. Extract the diagram again.")
            return json.loads(path.read_text())
