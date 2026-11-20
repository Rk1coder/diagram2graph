from collections import Counter

from diagram2graph.graph import validate_graph


def _normalize(text):
    return " ".join(text.casefold().split())


def _counts(expected, actual):
    true_positive = sum((expected & actual).values())
    expected_count, actual_count = sum(expected.values()), sum(actual.values())
    if expected_count == actual_count == 0:
        precision = recall = 1.0
    else:
        precision = true_positive / actual_count if actual_count else 0.0
        recall = true_positive / expected_count if expected_count else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "true_positive": true_positive,
        "expected": expected_count,
        "predicted": actual_count,
    }


def score_graph(expected, actual):
    expected, actual = validate_graph(expected), validate_graph(actual)
    labels = [{n["id"]: _normalize(n["label"]) for n in g["nodes"]} for g in (expected, actual)]
    node_counts = [Counter(mapping.values()) for mapping in labels]
    ambiguous = any(any(count > 1 for count in counts.values()) for counts in node_counts)
    nodes = _counts(*node_counts)
    if ambiguous:
        return {
            "nodes": nodes,
            "edges": None,
            "shape_accuracy": None,
            "exact_graph": None,
            "label_identity_ambiguous": True,
        }
    edge_counts = [
        Counter(
            (mapping[e["source"]], mapping[e["target"]], _normalize(e["label"])) for e in g["edges"]
        )
        for g, mapping in zip((expected, actual), labels, strict=True)
    ]
    edges = _counts(*edge_counts)
    shapes = [{_normalize(n["label"]): n["kind"] for n in g["nodes"]} for g in (expected, actual)]
    matches = sum(shapes[1].get(label) == kind for label, kind in shapes[0].items())
    return {
        "nodes": nodes,
        "edges": edges,
        "shape_accuracy": matches / len(expected["nodes"]),
        "exact_graph": node_counts[0] == node_counts[1]
        and edge_counts[0] == edge_counts[1]
        and shapes[0] == shapes[1],
        "label_identity_ambiguous": False,
    }
