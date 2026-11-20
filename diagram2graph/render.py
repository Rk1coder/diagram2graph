import html
import math

import networkx as nx
from PIL import Image, ImageDraw, ImageFont

from diagram2graph.graph import validate_graph

WIDTH, HEIGHT = 260, 128
COLORS = {"process": "#edf4ff", "decision": "#fff4dc", "terminator": "#eaf7f0"}


def _layout(graph):
    order = {node["id"]: index for index, node in enumerate(graph["nodes"])}
    network = nx.DiGraph()
    network.add_nodes_from(order)
    network.add_edges_from((e["source"], e["target"]) for e in graph["edges"])
    components = [
        sorted(group, key=order.get) for group in nx.strongly_connected_components(network)
    ]
    condensed = nx.condensation(network, components)
    levels = {}
    for component in nx.topological_sort(condensed):
        levels[component] = max(
            (levels[p] + len(components[p]) for p in condensed.predecessors(component)), default=0
        )
    rows = {}
    for component, members in enumerate(components):
        for offset, identity in enumerate(members):
            rows.setdefault(levels[component] + offset, []).append(identity)
    columns = max(map(len, rows.values()))
    canvas_width = columns * (WIDTH + 64) + 150
    canvas_height = (max(rows) + 1) * (HEIGHT + 80) + 80
    positions = {}
    for rank, identities in rows.items():
        identities.sort(key=order.get)
        start = (canvas_width - 100 - len(identities) * (WIDTH + 64)) / 2 + 32
        for index, identity in enumerate(identities):
            positions[identity] = (
                start + index * (WIDTH + 64) + WIDTH / 2,
                50 + rank * (HEIGHT + 80) + HEIGHT / 2,
            )
    return positions, int(canvas_width), int(canvas_height)


def _wrapped(label, font, limit):
    lines, current = [], ""
    for char in label:
        if current and font.getlength(current + char) > limit:
            lines.append(current.rstrip())
            current = char.lstrip()
        else:
            current += char
    if current:
        lines.append(current)
    return lines


def _label(node):
    for size in range(18, 9, -1):
        font = ImageFont.load_default(size=size)
        lines = _wrapped(
            node["label"], font, WIDTH * (0.58 if node["kind"] == "decision" else 0.82)
        )
        spacing = size * 1.3
        fits = len(lines) * spacing <= HEIGHT - 24
        if node["kind"] == "decision":
            fits = fits and all(
                font.getlength(line)
                <= WIDTH * (1 - abs((i - (len(lines) - 1) / 2) * spacing) / (HEIGHT / 2)) - 20
                for i, line in enumerate(lines)
            )
        if fits:
            return font, lines, size, spacing
    return font, lines, size, spacing


def _edge_curve(edge, positions, index):
    sx, sy = positions[edge["source"]]
    tx, ty = positions[edge["target"]]
    if ty > sy:
        start, end = (sx, sy + HEIGHT / 2), (tx, ty - HEIGHT / 2)
        mid = (start[1] + end[1]) / 2
        points = (start, (sx, mid), (tx, mid), end)
    else:
        lane = max(sx, tx) + WIDTH / 2 + 35 + (index % 3) * 18
        start, end = (sx + WIDTH / 2, sy), (tx + WIDTH / 2, ty)
        if sy == ty:
            lane = max(sx, tx) + WIDTH / 2 + 45
            points = (start, (lane, sy - 90), (lane, ty + 90), end)
        else:
            points = (start, (lane, sy), (lane, ty), end)
    return points


def _bezier(points, t):
    p0, p1, p2, p3 = points
    return tuple(
        (1 - t) ** 3 * p0[i]
        + 3 * (1 - t) ** 2 * t * p1[i]
        + 3 * (1 - t) * t * t * p2[i]
        + t**3 * p3[i]
        for i in (0, 1)
    )


def render_svg(graph):
    graph = validate_graph(graph)
    positions, width, height = _layout(graph)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Reconstructed flowchart">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#61718a"/></marker></defs>',
    ]
    for index, edge in enumerate(graph["edges"]):
        points = _edge_curve(edge, positions, index)
        (sx, sy), (ax, ay), (bx, by), (tx, ty) = points
        parts.append(
            f'<path data-edge="{index}" d="M {sx} {sy} C {ax} {ay}, {bx} {by}, {tx} {ty}" fill="none" stroke="#61718a" stroke-width="2" marker-end="url(#arrow)"/>'
        )
        if edge["label"]:
            x, y = _bezier(points, 0.5)
            parts.append(
                f'<text x="{x + 10}" y="{y - 8}" fill="#44536a" font-family="Arial,sans-serif" font-size="14">{html.escape(edge["label"])}</text>'
            )
    for node in graph["nodes"]:
        x, y = positions[node["id"]]
        left, top = x - WIDTH / 2, y - HEIGHT / 2
        parts.append(f'<g data-node-id="{node["id"]}"><title>{html.escape(node["label"])}</title>')
        if node["kind"] == "decision":
            parts.append(
                f'<polygon points="{x},{top} {x + WIDTH / 2},{y} {x},{y + HEIGHT / 2} {left},{y}" fill="{COLORS[node["kind"]]}" stroke="#8c9bb2" stroke-width="1.5"/>'
            )
        else:
            radius = HEIGHT / 2 if node["kind"] == "terminator" else 10
            parts.append(
                f'<rect x="{left}" y="{top}" width="{WIDTH}" height="{HEIGHT}" rx="{radius}" fill="{COLORS[node["kind"]]}" stroke="#8c9bb2" stroke-width="1.5"/>'
            )
        _, lines, size, spacing = _label(node)
        for index, line in enumerate(lines):
            text_y = y + (index - (len(lines) - 1) / 2) * spacing
            parts.append(
                f'<text x="{x}" y="{text_y}" dominant-baseline="middle" text-anchor="middle" font-family="Arial,sans-serif" font-size="{size}" fill="#172c46">{html.escape(line)}</text>'
            )
        parts.append("</g>")
    return "".join(parts) + "</svg>"


def render_png(graph):
    graph = validate_graph(graph)
    positions, width, height = _layout(graph)
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    for index, edge in enumerate(graph["edges"]):
        points = _edge_curve(edge, positions, index)
        samples = [_bezier(points, i / 40) for i in range(41)]
        draw.line(samples, fill="#61718a", width=2)
        tip = samples[-1]
        before = samples[-2]
        angle = math.atan2(tip[1] - before[1], tip[0] - before[0])
        draw.polygon(
            [
                tip,
                (tip[0] - 11 * math.cos(angle - 0.45), tip[1] - 11 * math.sin(angle - 0.45)),
                (tip[0] - 11 * math.cos(angle + 0.45), tip[1] - 11 * math.sin(angle + 0.45)),
            ],
            fill="#61718a",
        )
        if edge["label"]:
            x, y = _bezier(points, 0.5)
            draw.text(
                (x + 10, y - 10),
                edge["label"],
                font=ImageFont.load_default(size=14),
                fill="#44536a",
                anchor="ls",
            )
    for node in graph["nodes"]:
        x, y = positions[node["id"]]
        box = (x - WIDTH / 2, y - HEIGHT / 2, x + WIDTH / 2, y + HEIGHT / 2)
        if node["kind"] == "decision":
            draw.polygon(
                [(x, box[1]), (box[2], y), (x, box[3]), (box[0], y)],
                fill=COLORS[node["kind"]],
                outline="#8c9bb2",
                width=2,
            )
        else:
            draw.rounded_rectangle(
                box,
                radius=HEIGHT / 2 if node["kind"] == "terminator" else 10,
                fill=COLORS[node["kind"]],
                outline="#8c9bb2",
                width=2,
            )
        font, lines, _, spacing = _label(node)
        for index, line in enumerate(lines):
            draw.text(
                (x, y + (index - (len(lines) - 1) / 2) * spacing),
                line,
                font=font,
                fill="#172c46",
                anchor="mm",
            )
    return image
