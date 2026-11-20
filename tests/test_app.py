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


def test_queued_edit_from_prior_browser_revision_cannot_undo_newer_graph(tmp_path):
    path = tmp_path / "input.png"
    Image.new("RGB", (40, 40)).save(path)
    service = Service(Engine(), tmp_path / "reports")
    original = service.extract(path)
    state = {"token": "original", "input": str(path), "report_id": original["report"]["id"]}
    first = rename_node(original["report"]["id"], "b", "Newest label", state, service=service)
    stale = apply_graph("{broken old JSON", original["report"]["id"], state, service=service)
    assert all(isinstance(v, dict) and v.get("__type__") == "update" for v in stale)
    assert service.get_report(first[5])["graph"]["nodes"][1]["label"] == "Newest label"


def test_edit_api_requires_the_revision_visible_at_click_time():
    from app import build_app

    demo = build_app()
    api = demo.get_api_info()
    parameters = api["named_endpoints"]["/edit"]["parameters"]
    assert any(p["parameter_name"] == "report_id" for p in parameters)


def test_background_edit_error_cannot_clear_a_newer_result(tmp_path):
    path = tmp_path / "input.png"
    Image.new("RGB", (40, 40)).save(path)
    service = Service(Engine(), tmp_path / "reports")
    original = service.extract(path)
    for operation in ("apply", "rename"):
        state = {"token": "original", "report_id": original["report"]["id"]}

        class InterruptedService:
            def get_report(self, report_id):
                return service.get_report(report_id)

            def edit(self, report_id, graph):
                state.update(token="newer", report_id="newer-report")
                raise RuntimeError("Interrupted backend")

        if operation == "apply":
            result = apply_graph(
                json.dumps(GRAPH), original["report"]["id"], state, service=InterruptedService()
            )
        else:
            result = rename_node(
                original["report"]["id"], "b", "New label", state, service=InterruptedService()
            )
        assert all(isinstance(v, dict) and v.get("__type__") == "update" for v in result)
