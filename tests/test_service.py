import json
import time
from pathlib import Path

import pytest
from PIL import Image

from diagram2graph.service import Service

GRAPH = {
    "nodes": [
        {"id": "a", "label": "Start", "kind": "terminator"},
        {"id": "b", "label": "Save", "kind": "process"},
    ],
    "edges": [{"source": "a", "target": "b", "label": ""}],
}


class Engine:
    model_id = "test-only"
    revision = "fixture"
    calls = 0

    def predict(self, image):
        self.calls += 1
        return json.dumps(GRAPH)


def test_extraction_and_edits_preserve_model_provenance(tmp_path):
    image = tmp_path / "image.png"
    Image.new("RGB", (80, 60), "white").save(image)
    engine = Engine()
    service = Service(engine, tmp_path / "reports")
    first = service.extract(image)
    changed = json.loads(json.dumps(first["report"]["graph"]))
    changed["nodes"][1]["label"] = "Store file"
    second = service.edit(first["report"]["id"], changed)
    assert engine.calls == 1
    assert second["report"]["origin"] == "user_edit"
    assert second["report"]["graph"]["nodes"][1]["label"] == "Store file"
    assert second["report"]["model_graph"]["nodes"][1]["label"] == "Save"
    assert second["report"]["parent_report_id"] == first["report"]["id"]
    assert (
        json.loads(Path(first["report_path"]).read_text())["graph"]["nodes"][1]["label"] == "Save"
    )
    assert Path(second["svg_path"]).is_file() and Path(second["png_path"]).is_file()
    assert "Store file" in Path(second["mermaid_path"]).read_text()


def test_invalid_model_output_is_not_exported_and_remains_diagnosable(tmp_path):
    class BadEngine(Engine):
        def predict(self, image):
            return '{"nodes":[],"edges":[]}'

    image = tmp_path / "image.png"
    Image.new("RGB", (20, 20)).save(image)
    service = Service(BadEngine(), tmp_path / "reports")
    with pytest.raises(ValueError) as error:
        service.extract(image)
    assert error.value.raw_prediction == '{"nodes":[],"edges":[]}'
    assert list((tmp_path / "reports").iterdir()) == []


def test_report_ids_cannot_escape_cache_and_reports_expire(tmp_path):
    image = tmp_path / "image.png"
    Image.new("RGB", (20, 20)).save(image)
    service = Service(Engine(), tmp_path / "reports", max_reports=2)
    first = service.extract(image)
    second = service.extract(image)
    third = service.extract(image)
    assert not Path(first["report_path"]).exists()
    assert Path(second["report_path"]).exists() and Path(third["report_path"]).exists()
    for identity in ["../outside", "r-missing", first["report"]["id"]]:
        with pytest.raises(ValueError):
            service.edit(identity, GRAPH)
    service.prune(now=time.time() + 4000)
    assert not Path(third["report_path"]).exists()
    assert image.exists()
