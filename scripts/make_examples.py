"""Draw original fixed flowcharts independently from the reconstruction renderer."""

import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def node(identity, label, kind="process"):
    return {"id": identity, "label": label, "kind": kind}


def edge(source, target, label=""):
    return {"source": source, "target": target, "label": label}


def fixtures():
    return [
        {
            "id": "linear",
            "title": "File processing",
            "size": [800, 780],
            "graph": {
                "nodes": [
                    node("a", "Start", "terminator"),
                    node("b", "Read file"),
                    node("c", "Validate"),
                    node("d", "Save"),
                    node("e", "Finish", "terminator"),
                ],
                "edges": [edge("a", "b"), edge("b", "c"), edge("c", "d"), edge("d", "e")],
            },
            "positions": {
                "a": [400, 120],
                "b": [400, 260],
                "c": [400, 400],
                "d": [400, 540],
                "e": [400, 680],
            },
            "routes": [
                [[400, 155], [400, 225]],
                [[400, 295], [400, 365]],
                [[400, 435], [400, 505]],
                [[400, 575], [400, 645]],
            ],
        },
        {
            "id": "branch",
            "title": "Approval workflow",
            "size": [840, 800],
            "graph": {
                "nodes": [
                    node("a", "Request", "terminator"),
                    node("b", "Approved?", "decision"),
                    node("c", "Publish"),
                    node("d", "Revise"),
                    node("e", "Done", "terminator"),
                ],
                "edges": [
                    edge("a", "b"),
                    edge("b", "c", "Yes"),
                    edge("b", "d", "No"),
                    edge("c", "e"),
                    edge("d", "e"),
                ],
            },
            "positions": {
                "a": [420, 120],
                "b": [420, 300],
                "c": [200, 500],
                "d": [640, 500],
                "e": [420, 700],
            },
            "routes": [
                [[420, 155], [420, 240]],
                [[290, 300], [200, 300], [200, 465]],
                [[550, 300], [640, 300], [640, 465]],
                [[200, 535], [200, 620], [420, 620], [420, 665]],
                [[640, 535], [640, 620], [420, 620], [420, 665]],
            ],
            "edge_labels": {"1": [225, 280], "2": [580, 280]},
        },
        {
            "id": "loop",
            "title": "Release checks",
            "size": [860, 920],
            "graph": {
                "nodes": [
                    node("a", "Start", "terminator"),
                    node("b", "Run tests"),
                    node("c", "Passed?", "decision"),
                    node("d", "Release"),
                    node("e", "Fix issues"),
                    node("f", "Done", "terminator"),
                ],
                "edges": [
                    edge("a", "b"),
                    edge("b", "c"),
                    edge("c", "d", "Yes"),
                    edge("c", "e", "No"),
                    edge("e", "b", "Retry"),
                    edge("d", "f"),
                ],
            },
            "positions": {
                "a": [230, 120],
                "b": [230, 280],
                "c": [230, 470],
                "d": [230, 670],
                "e": [620, 470],
                "f": [230, 840],
            },
            "routes": [
                [[230, 155], [230, 245]],
                [[230, 315], [230, 410]],
                [[230, 530], [230, 635]],
                [[360, 470], [510, 470]],
                [[730, 470], [790, 470], [790, 280], [340, 280]],
                [[230, 705], [230, 805]],
            ],
            "edge_labels": {"2": [250, 570], "3": [410, 445], "4": [700, 255]},
        },
    ]


def main():
    records = []
    for fixture in fixtures():
        image = Image.new("RGB", tuple(fixture["size"]), "white")
        draw = ImageDraw.Draw(image)
        draw.text((40, 35), fixture["title"], font=ImageFont.load_default(size=24), fill="#283950")
        for index, route in enumerate(fixture["routes"]):
            route = [tuple(p) for p in route]
            draw.line(route, fill="#364c65", width=3)
            tip, before = route[-1], route[-2]
            angle = math.atan2(tip[1] - before[1], tip[0] - before[0])
            draw.polygon(
                [
                    tip,
                    (tip[0] - 13 * math.cos(angle - 0.45), tip[1] - 13 * math.sin(angle - 0.45)),
                    (tip[0] - 13 * math.cos(angle + 0.45), tip[1] - 13 * math.sin(angle + 0.45)),
                ],
                fill="#364c65",
            )
            label = fixture["graph"]["edges"][index]["label"]
            if label:
                draw.text(
                    tuple(fixture["edge_labels"][str(index)]),
                    label,
                    font=ImageFont.load_default(size=20),
                    fill="#25394e",
                )
        for item in fixture["graph"]["nodes"]:
            x, y = fixture["positions"][item["id"]]
            box = (x - 110, y - 35, x + 110, y + 35)
            if item["kind"] == "terminator":
                draw.ellipse(box, fill="#edf6f1", outline="#364c65", width=3)
            elif item["kind"] == "decision":
                draw.polygon(
                    [(x, y - 60), (x + 130, y), (x, y + 60), (x - 130, y)],
                    fill="#fff6df",
                    outline="#364c65",
                    width=3,
                )
            else:
                draw.rectangle(box, fill="#f1f6fe", outline="#364c65", width=3)
            draw.text(
                (x, y),
                item["label"],
                font=ImageFont.load_default(size=22),
                fill="#152d48",
                anchor="mm",
            )
        path = ROOT / "examples" / (fixture["id"] + ".png")
        image.save(path)
        records.append(
            {
                "id": fixture["id"],
                "image": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "expected": fixture["graph"],
            }
        )
    (ROOT / "examples/tasks.json").write_text(json.dumps(records, indent=2) + "\n")
    print("Created three original fixtures with fixed graphs and checksums.")


if __name__ == "__main__":
    main()
