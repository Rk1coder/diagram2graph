import xml.etree.ElementTree as ET

from diagram2graph.render import render_png, render_svg


def test_svg_is_valid_and_contains_all_nodes_edges_without_scripts():
    graph = {
        "nodes": [
            {"id": "a", "label": "<script>alert(1)</script>", "kind": "process"},
            {"id": "b", "label": "Approved?", "kind": "decision"},
        ],
        "edges": [
            {"source": "a", "target": "b", "label": "Yes"},
            {"source": "b", "target": "a", "label": "Retry"},
        ],
    }
    text = render_svg(graph)
    root = ET.fromstring(text)
    ns = {"s": "http://www.w3.org/2000/svg"}
    assert len(root.findall(".//s:g[@data-node-id]", ns)) == 2
    assert len(root.findall(".//s:path[@data-edge]", ns)) == 2
    assert root.findall(".//s:script", ns) == []
    assert "alert(1)" in "".join(root.itertext())
    image = render_png(graph)
    assert image.mode == "RGB"
    assert 100 < image.width < 4096 and 100 < image.height < 4096
    assert image.getbbox() is not None


def test_render_is_deterministic_for_disconnected_graph():
    graph = {"nodes": [{"id": str(x), "label": "x", "kind": "process"} for x in []], "edges": []}
    graph["nodes"] = [
        {"id": "a", "label": "First", "kind": "terminator"},
        {"id": "b", "label": "Second", "kind": "process"},
    ]
    assert render_svg(graph) == render_svg(graph)
    assert render_png(graph).tobytes() == render_png(graph).tobytes()
