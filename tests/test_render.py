import re
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


def test_shortcut_arrow_does_not_pass_through_an_unrelated_node():
    graph = {
        "nodes": [{"id": n, "label": n, "kind": "process"} for n in ["a", "b", "c"]],
        "edges": [
            {"source": "a", "target": "b", "label": ""},
            {"source": "b", "target": "c", "label": ""},
            {"source": "a", "target": "c", "label": "Skip"},
        ],
    }
    root = ET.fromstring(render_svg(graph))
    ns = {"s": "http://www.w3.org/2000/svg"}
    rect = root.find('.//s:g[@data-node-id="b"]/s:rect', ns)
    x, y, w, h = [float(rect.attrib[k]) for k in ["x", "y", "width", "height"]]
    path = root.find('.//s:path[@data-edge="2"]', ns).attrib["d"]
    numbers = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", path)]
    points = list(zip(numbers[::2], numbers[1::2], strict=True))
    samples = []
    if "C" in path:
        for i in range(101):
            t = i / 100
            samples.append(
                tuple(
                    (1 - t) ** 3 * points[0][a]
                    + 3 * (1 - t) ** 2 * t * points[1][a]
                    + 3 * (1 - t) * t * t * points[2][a]
                    + t**3 * points[3][a]
                    for a in [0, 1]
                )
            )
    else:
        for start, end in zip(points, points[1:]):
            samples.extend(
                (start[0] + i / 100 * (end[0] - start[0]), start[1] + i / 100 * (end[1] - start[1]))
                for i in range(101)
            )
    assert not any(x + 1 < px < x + w - 1 and y + 1 < py < y + h - 1 for px, py in samples)


def test_parallel_labeled_arrows_have_distinct_paths_and_labels():
    graph = {
        "nodes": [{"id": n, "label": n, "kind": "process"} for n in ["a", "b"]],
        "edges": [{"source": "a", "target": "b", "label": label} for label in ["Yes", "No"]],
    }
    root = ET.fromstring(render_svg(graph))
    ns = {"s": "http://www.w3.org/2000/svg"}
    paths = root.findall(".//s:path[@data-edge]", ns)
    assert len({p.attrib["d"] for p in paths}) == 2
    texts = [t for t in root.findall(".//s:text", ns) if t.text in ["Yes", "No"]]
    assert len({(t.attrib["x"], t.attrib["y"]) for t in texts}) == 2


def test_long_labeled_first_row_self_loop_fits_inside_canvas():
    graph = {
        "nodes": [{"id": "a", "label": "Loop", "kind": "process"}],
        "edges": [{"source": "a", "target": "a", "label": "WWW W " * 6 + "WWW"}],
    }
    root = ET.fromstring(render_svg(graph))
    ns = {"s": "http://www.w3.org/2000/svg"}
    width, height = float(root.attrib["width"]), float(root.attrib["height"])
    for path in root.findall(".//s:path[@data-edge]", ns):
        nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", path.attrib["d"])]
        assert all(0 <= x <= width and 0 <= y <= height for x, y in zip(nums[::2], nums[1::2]))
    for text in root.findall(".//s:text", ns):
        assert float(text.attrib["y"]) - float(text.attrib["font-size"]) >= 0
