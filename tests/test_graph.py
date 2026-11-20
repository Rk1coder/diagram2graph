import copy
import json

import pytest

from diagram2graph.graph import parse_graph, to_mermaid, validate_graph


@pytest.fixture
def graph():
    return {
        "nodes": [
            {"id": "end", "label": "Start", "kind": "terminator"},
            {"id": "b", "label": "Check", "kind": "decision"},
        ],
        "edges": [{"source": "end", "target": "b", "label": ""}],
    }


def test_parse_complete_fenced_graph_and_detach_input(graph):
    parsed = parse_graph("```json\n" + json.dumps(graph) + "\n```")
    assert parsed == graph
    parsed["nodes"][0]["label"] = "Changed"
    assert graph["nodes"][0]["label"] == "Start"


@pytest.mark.parametrize(
    "change",
    [
        "dangling",
        "duplicate_id",
        "duplicate_edge",
        "extra_field",
        "invalid_shape",
        "bad_id",
        "empty_label",
        "too_long_label",
    ],
)
def test_invalid_graph_is_rejected(graph, change):
    if change == "dangling":
        graph["edges"][0]["target"] = "missing"
    elif change == "duplicate_id":
        graph["nodes"][1]["id"] = "end"
    elif change == "duplicate_edge":
        graph["edges"].append(copy.deepcopy(graph["edges"][0]))
    elif change == "extra_field":
        graph["nodes"][0]["url"] = "javascript:alert(1)"
    elif change == "invalid_shape":
        graph["nodes"][0]["kind"] = "script"
    elif change == "bad_id":
        graph["nodes"][0]["id"] = "a --> injected"
    elif change == "empty_label":
        graph["nodes"][0]["label"] = " "
    elif change == "too_long_label":
        graph["nodes"][0]["label"] = "x" * 81
    with pytest.raises(ValueError):
        validate_graph(graph)


def test_cycles_and_disconnected_nodes_are_valid(graph):
    graph["edges"].append({"source": "b", "target": "end", "label": "Retry"})
    graph["nodes"].append({"id": "c", "label": "Independent", "kind": "process"})
    assert len(validate_graph(graph)["edges"]) == 2


def test_duplicate_json_and_trailing_content_are_rejected(graph):
    raw = json.dumps(graph)
    for value in [
        raw + " extra",
        '{"nodes":[],"nodes":[],"edges":[]}',
        "```json\n" + raw,
        '{"nodes":[],"edges":[]}',
    ]:
        with pytest.raises(ValueError):
            parse_graph(value)


def test_graph_size_is_bounded(graph):
    graph["nodes"] = [{"id": f"n{i}", "label": f"Node {i}", "kind": "process"} for i in range(13)]
    graph["edges"] = []
    with pytest.raises(ValueError):
        validate_graph(graph)


def test_mermaid_preserves_direction_and_escapes_label_injection(graph):
    graph["nodes"][0]["label"] = 'end "] --> evil[" <script>'
    result = to_mermaid(graph)
    assert "node_end --> node_b" in result
    assert "<script>" not in result
    assert 'node_end(["' in result
    assert "#quot;" in result
    assert "\nclick " not in result
