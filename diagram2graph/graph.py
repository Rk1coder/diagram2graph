import json
import re


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON keys are not accepted.")
        result[key] = value
    return result


def parse_graph(text):
    if not isinstance(text, str) or len(text) > 24000:
        raise ValueError("Graph response must be at most 24,000 characters.")
    text = text.strip()
    if text.startswith("```json\n") and text.endswith("\n```"):
        text = text[8:-4]
    try:
        value = json.loads(text, object_pairs_hook=unique_object)
    except (ValueError, TypeError, RecursionError) as exc:
        raise ValueError("Expected one complete graph JSON object.") from exc
    return validate_graph(value)


def _fields(value, names):
    if not isinstance(value, dict) or set(value) != set(names):
        raise ValueError("Graph objects contain missing or unrecognized fields.")


def _text(value, minimum, maximum):
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise ValueError(f"Labels must contain {minimum}–{maximum} characters.")
    if value and not value.isprintable():
        raise ValueError("Labels must be printable text on one line.")
    return value.strip()


def validate_graph(value):
    _fields(value, ("nodes", "edges"))
    nodes, edges = value["nodes"], value["edges"]
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= 12:
        raise ValueError("A flowchart needs 1–12 nodes.")
    if not isinstance(edges, list) or len(edges) > 20:
        raise ValueError("A flowchart can contain at most 20 edges.")
    clean_nodes, seen = [], set()
    for node in nodes:
        _fields(node, ("id", "label", "kind"))
        identity = node["id"]
        if not isinstance(identity, str) or not re.fullmatch(
            r"[A-Za-z][A-Za-z0-9_]{0,23}", identity
        ):
            raise ValueError(
                "Node IDs must start with an ASCII letter and contain 1–24 letters, digits or underscores."
            )
        if identity in seen:
            raise ValueError("Node IDs must be unique.")
        if node["kind"] not in ("process", "decision", "terminator"):
            raise ValueError("Node kind must be process, decision or terminator.")
        clean_nodes.append(
            {"id": identity, "label": _text(node["label"], 1, 80), "kind": node["kind"]}
        )
        seen.add(identity)
    clean_edges, unique_edges = [], set()
    for edge in edges:
        _fields(edge, ("source", "target", "label"))
        source, target = edge["source"], edge["target"]
        if (
            not isinstance(source, str)
            or not isinstance(target, str)
            or source not in seen
            or target not in seen
        ):
            raise ValueError("Every edge must reference existing node IDs.")
        label = _text(edge["label"], 0, 40)
        key = (source, target, label)
        if key in unique_edges:
            raise ValueError("Duplicate directed labeled edges are not accepted.")
        unique_edges.add(key)
        clean_edges.append({"source": source, "target": target, "label": label})
    return {"nodes": clean_nodes, "edges": clean_edges}


def _mermaid_text(value):
    codes = {
        '"': "#quot;",
        "&": "#38;",
        "<": "#60;",
        ">": "#62;",
        "|": "#124;",
        "#": "#35;",
        "%": "#37;",
        "`": "#96;",
        "\\": "#92;",
    }
    return "".join(codes.get(c, c) for c in value)


def to_mermaid(graph):
    graph = validate_graph(graph)
    lines = ["flowchart TD"]
    shapes = {"process": ('["', '"]'), "decision": ('{"', '"}'), "terminator": ('(["', '"])')}
    for node in graph["nodes"]:
        left, right = shapes[node["kind"]]
        lines.append(f"    node_{node['id']}{left}{_mermaid_text(node['label'])}{right}")
    for edge in graph["edges"]:
        label = f'|"{_mermaid_text(edge["label"])}"|' if edge["label"] else ""
        lines.append(f"    node_{edge['source']} -->{label} node_{edge['target']}")
    return "\n".join(lines) + "\n"
