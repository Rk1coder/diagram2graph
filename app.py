import json
import logging
import os
import threading
import uuid
from pathlib import Path

from diagram2graph.graph import parse_graph
from diagram2graph.images import load_image
from diagram2graph.model import Engine
from diagram2graph.service import Service
from diagram2graph.storage import private_cache, prune_cache

CACHE = private_cache(os.environ.get("D2G_CACHE_DIR"))
prune_cache(CACHE)
os.environ["GRADIO_TEMP_DIR"] = str(CACHE)

import gradio as gr  # noqa: E402

ROOT = Path(__file__).resolve().parent
SERVICE = Service(Engine())
LOGGER = logging.getLogger(__name__)
CSS = """
.gradio-container{max-width:1440px!important;font-family:system-ui,sans-serif!important}
#masthead{padding:8px 0 18px;border-bottom:1px solid #dce3ed;margin-bottom:14px}
#masthead h1{font-size:32px;letter-spacing:-.025em;color:#17324c;margin-bottom:8px}
#masthead p{color:#51637b;max-width:80ch;line-height:1.5}
.graph-canvas{height:400px;overflow:auto;background:white;border:1px solid #dce3ed;border-radius:8px;display:flex;justify-content:center;align-items:flex-start}
.graph-canvas svg{width:auto;max-width:100%;height:400px;flex-shrink:0}
#extract-button{min-height:44px;font-weight:600}
#graph-status{padding:12px;background:#f3f7fc;border-radius:8px;line-height:1.5}
button:focus-visible,a:focus-visible{outline:3px solid #2563eb!important;outline-offset:3px}
"""


def _empty(message, *, preserve=False):
    return (
        "",
        message,
        "",
        gr.skip() if preserve else "",
        gr.skip() if preserve else gr.update(choices=[], value=None),
        gr.skip() if preserve else None,
        None,
        None,
        None,
        None,
    )


def invalidate_source(path, session):
    session.update(token=uuid.uuid4().hex, input=path, report_id=None)
    return _empty("Source changed. Extract the diagram to continue.")


def source_changed(path, session):
    cleared = invalidate_source(path, session)
    try:
        image = load_image(path) if path else None
    except ValueError:
        image = None
    return image, *cleared


def _pack(result):
    report = result["report"]
    graph = report["graph"]
    origin = "User edit" if report["origin"] == "user_edit" else "Model extraction"
    status = f"**{origin} · {len(graph['nodes'])} nodes · {len(graph['edges'])} arrows**\n\nOriginal inference: {report['inference_seconds']:.1f} s. Inspect labels and arrow directions. Layout is reconstructed."
    choices = [(n["label"] + " · " + n["id"], n["id"]) for n in graph["nodes"]]
    return (
        '<div class="graph-canvas">' + Path(result["svg_path"]).read_text() + "</div>",
        status,
        Path(result["mermaid_path"]).read_text(),
        json.dumps(graph, indent=2, ensure_ascii=False),
        gr.update(choices=choices, value=graph["nodes"][0]["id"]),
        report["id"],
        result["svg_path"],
        result["png_path"],
        result["mermaid_path"],
        result["report_path"],
    )


def _commit_result(result, session, ticket, expected_parent=None):
    if session is not None:
        if session["token"] != ticket or (
            expected_parent is not None and session.get("report_id") != expected_parent
        ):
            return (gr.skip(),) * 10
        session.update(token=uuid.uuid4().hex, report_id=result["report"]["id"])
    return _pack(result)


def extract_diagram(path, session=None, *, service=None):
    service = service or SERVICE
    ticket = session["token"] if session is not None else None
    if session is not None and session.get("input") not in (None, path):
        return (gr.skip(),) * 10
    if not path:
        return _empty("Upload a printed flowchart to begin.")
    try:
        result = service.extract(path)
        return _commit_result(result, session, ticket)
    except ValueError as exc:
        error = str(exc)
    except Exception:
        LOGGER.exception("Diagram extraction failed")
        error = "Local extraction failed. Check the server log and available memory, then retry."
    if session is not None and session["token"] != ticket:
        return (gr.skip(),) * 10
    return _empty(error)


def _edit(graph, report_id, session, service):
    ticket = session["token"] if session is not None else None
    if session is not None and session.get("report_id") != report_id:
        return (gr.skip(),) * 10
    return _commit_result(service.edit(report_id, graph), session, ticket, report_id)


def apply_graph(text, report_id, session=None, *, service=None):
    try:
        return _edit(parse_graph(text), report_id, session, service or SERVICE)
    except ValueError as exc:
        return _empty(str(exc), preserve=True)
    except Exception:
        LOGGER.exception("Graph editing failed")
        return _empty("Could not apply these changes. Check the server log.", preserve=True)


def rename_node(report_id, node_id, label, session=None, *, service=None):
    service = service or SERVICE
    try:
        graph = service.get_report(report_id)["graph"]
        matches = [node for node in graph["nodes"] if node["id"] == node_id]
        if len(matches) != 1:
            raise ValueError("Select an extracted node to rename.")
        matches[0]["label"] = label
        return _edit(graph, report_id, session, service)
    except ValueError as exc:
        return _empty(str(exc), preserve=True)
    except Exception:
        LOGGER.exception("Node editing failed")
        return _empty("Could not rename this node. Check the server log.", preserve=True)


def _controls(interactive):
    return [gr.update(interactive=interactive) for _ in range(4)]


def build_app():
    samples = [ROOT / "examples" / f"{name}.png" for name in ("linear", "branch", "loop")]
    gr.set_static_paths(paths=samples)
    with gr.Blocks(title="Diagram2Graph", delete_cache=(60, 3600)) as demo:
        session = gr.State({"token": "initial", "input": None, "report_id": None})
        report_id = gr.State(None)
        gr.Markdown(
            "# Diagram2Graph\nFrom a diagram image to editable structure.\n\nExtract printed flowcharts locally. Inspect the arrows, refine the labels, and export Mermaid, SVG or PNG.",
            elem_id="masthead",
        )
        with gr.Row():
            with gr.Column(scale=4, min_width=300):
                upload = gr.File(
                    label="Flowchart image · PNG/JPEG · up to 10 MiB",
                    type="filepath",
                    file_types=[".png", ".jpg", ".jpeg"],
                )
                source = gr.Image(
                    label="Original diagram",
                    interactive=False,
                    height=330,
                    format="png",
                    buttons=["download", "fullscreen"],
                )
                extract = gr.Button("Extract diagram", variant="primary", elem_id="extract-button")
                gr.Examples(
                    [[str(p)] for p in samples],
                    inputs=upload,
                    label="Original examples",
                    cache_examples=False,
                )
                gr.Markdown(
                    "First use loads the local model. Only printed flowcharts are covered in this release."
                )
            with gr.Column(scale=7, min_width=300):
                preview = gr.HTML(
                    '<div class="graph-canvas"><p style="padding:32px;color:#51637b">Your reconstructed diagram will appear here.</p></div>'
                )
                status = gr.Markdown(
                    "No model has run yet. Choose an original example or upload your own image.",
                    elem_id="graph-status",
                )
                with gr.Row():
                    svg_file = gr.File(label="SVG", interactive=False)
                    png_file = gr.File(label="PNG", interactive=False)
                    mmd_file = gr.File(label="Mermaid", interactive=False)
                    json_file = gr.File(label="JSON report", interactive=False)
        with gr.Accordion("Edit and export", open=True):
            with gr.Row():
                selected = gr.Dropdown(label="Node to rename", choices=[], value=None, scale=3)
                label = gr.Textbox(label="New label", placeholder="Replacement text", scale=4)
                rename = gr.Button("Rename node", scale=2)
            with gr.Accordion("Advanced graph structure", open=False):
                graph_json = gr.Code(
                    label="Graph JSON · nodes and arrows",
                    language="json",
                    interactive=True,
                    lines=12,
                )
                apply = gr.Button("Apply graph edits")
            with gr.Accordion("Mermaid source", open=False):
                mermaid = gr.Code(
                    label="Mermaid export", language="markdown", interactive=False, lines=8
                )
                gr.Markdown(
                    "Download the Mermaid file to edit it in any Mermaid-compatible editor. In-app edits use the validated graph structure."
                )
        outputs = [
            preview,
            status,
            mermaid,
            graph_json,
            selected,
            report_id,
            svg_file,
            png_file,
            mmd_file,
            json_file,
        ]
        controls = [upload, extract, rename, apply]
        request = extract.click(
            lambda: _controls(False), outputs=controls, queue=False, api_name=False
        )
        prediction = request.then(
            extract_diagram,
            [upload, session],
            outputs,
            api_name="extract",
            concurrency_limit=1,
            concurrency_id="graph",
        )
        prediction.then(lambda: _controls(True), outputs=controls, queue=False, api_name=False)
        upload.change(
            source_changed, [upload, session], [source, *outputs], queue=False, api_name=False
        )
        rename.click(
            rename_node,
            [report_id, selected, label, session],
            outputs,
            api_name="rename",
            concurrency_limit=1,
            concurrency_id="graph",
        )
        apply.click(
            apply_graph,
            [graph_json, report_id, session],
            outputs,
            api_name="edit",
            concurrency_limit=1,
            concurrency_id="graph",
        )
        gr.Markdown(
            "**Local-first** · Qwen3-VL-2B · User edits retain the original model graph · Temporary outputs expire after one hour."
        )
    return demo.queue(max_size=4, default_concurrency_limit=1)


def cleanup_loop():
    while not threading.Event().wait(60):
        SERVICE.prune()
        prune_cache(CACHE)


if __name__ == "__main__":
    threading.Thread(target=cleanup_loop, daemon=True).start()
    build_app().launch(
        server_name=os.environ.get("HOST", "127.0.0.1"),
        server_port=int(os.environ.get("PORT", "7865")),
        max_file_size="10mb",
        css=CSS,
        theme=gr.themes.Base(primary_hue="blue", neutral_hue="slate"),
    )
