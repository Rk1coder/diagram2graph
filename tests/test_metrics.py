from diagram2graph.metrics import score_graph


def test_edge_direction_is_scored_independently_from_node_ids():
    expected = {
        "nodes": [
            {"id": "a", "label": "Start", "kind": "terminator"},
            {"id": "b", "label": "Save", "kind": "process"},
        ],
        "edges": [{"source": "a", "target": "b", "label": ""}],
    }
    actual = {
        "nodes": [
            {"id": "x", "label": "START", "kind": "terminator"},
            {"id": "y", "label": "Save", "kind": "process"},
        ],
        "edges": [{"source": "y", "target": "x", "label": ""}],
    }
    score = score_graph(expected, actual)
    assert score["nodes"]["f1"] == 1
    assert score["edges"]["f1"] == 0
    assert score["exact_graph"] is False


def test_extra_nodes_and_edges_reduce_precision():
    expected = {
        "nodes": [
            {"id": "a", "label": "Start", "kind": "terminator"},
            {"id": "b", "label": "Save", "kind": "process"},
        ],
        "edges": [{"source": "a", "target": "b", "label": ""}],
    }
    actual = {
        "nodes": expected["nodes"] + [{"id": "c", "label": "Extra", "kind": "process"}],
        "edges": expected["edges"] + [{"source": "b", "target": "c", "label": ""}],
    }
    score = score_graph(expected, actual)
    assert score["nodes"]["precision"] == 2 / 3
    assert score["nodes"]["recall"] == 1
    assert score["edges"]["precision"] == 0.5


def test_repeated_labels_do_not_produce_an_unqualified_structure_score():
    graph = {
        "nodes": [
            {"id": "a", "label": "Wait", "kind": "process"},
            {"id": "b", "label": "Wait", "kind": "process"},
        ],
        "edges": [],
    }
    score = score_graph(graph, graph)
    assert score["label_identity_ambiguous"] is True
    assert score["edges"] is None and score["exact_graph"] is None
