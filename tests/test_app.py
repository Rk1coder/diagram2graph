import json
from pathlib import Path

from PIL import Image

from app import apply_graph, extract_diagram, invalidate_source, rename_node
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

    def predict(self, image):
        return json.dumps(GRAPH)


def test_extract_and_rename_return_real_editable_exports(tmp_path):
    path = tmp_path / "input.png"
    Image.new("RGB", (40, 40)).save(path)
    service = Service(Engine(), tmp_path / "reports")
    result = extract_diagram(str(path), service=service)
    assert "<svg " in result[0]
    assert Path(result[6]).suffix == ".svg" and Path(result[7]).suffix == ".png"
    edited = rename_node(result[5], "b", "Store document", service=service)
    assert "Store document" in edited[0] and "User edit" in edited[1]
    assert json.loads(Path(edited[9]).read_text())["model_graph"]["nodes"][1]["label"] == "Save"


def test_invalid_edit_clears_exports_but_preserves_recovery_context(tmp_path):
    service = Service(Engine(), tmp_path / "reports")
    result = apply_graph('{"bad":true}', "r-" + "a" * 32, service=service)
    assert result[0] == "" and all(value is None for value in result[6:10])
    assert result[5].get("__type__") == "update"


def test_input_change_clears_results_and_prevents_obsolete_completion(tmp_path):
    path = tmp_path / "input.png"
    Image.new("RGB", (40, 40)).save(path)
    session = {"token": "old", "input": str(path)}

    class ChangingEngine(Engine):
        def predict(self, image):
            invalidate_source("new.png", session)
            return json.dumps(GRAPH)

    service = Service(ChangingEngine(), tmp_path / "reports")
    result = extract_diagram(str(path), session, service=service)
    assert all(isinstance(v, dict) and v.get("__type__") == "update" for v in result)
