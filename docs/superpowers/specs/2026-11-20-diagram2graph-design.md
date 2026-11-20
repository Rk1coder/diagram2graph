# Diagram2Graph: local-first design

## Intent and scope

Convert printed English flowchart images into editable graph structure and Mermaid,
SVG and PNG exports. Build locally, test actual model extraction, keep meaningful
stage commits, then publish source and real output images/GIF on GitHub. Public UI
and documentation are English with no assistant attribution. The GIF records actual
application states; any compressed waiting time is labeled.

## Approach

Chosen: pinned local Qwen3-VL -> strict graph JSON -> deterministic local rendering
and Mermaid generation. Existing ClickGuide image/cache hardening is reused.
Direct image-to-Mermaid generation was considered but lacks a reliable editable
intermediate representation. External rendering APIs were rejected for local use.
Graphviz is absent, so a bounded Python layout/SVG/PNG renderer avoids another
system dependency. Exported Mermaid is editable in Mermaid-compatible tools;
in-app label and advanced graph editing regenerate the local previews and files.

## Contract

- Python 3.12, Gradio 6.11.0, Transformers 4.57.6, PyTorch CPU float32, Pillow.
- `Qwen/Qwen3-VL-2B-Instruct` revision `89644892e4d85e24eaac8bacfd4f463576704203`;
  trust_remote_code=False, weights-only, lazy serialized inference, four CPU threads,
  65536–262144 image pixels, greedy decoding, at most 768 generated tokens.
- One PNG/JPEG <=10 MiB, <=12 million pixels, <=4096 pixels per edge. Validate
  integrity, reject animation, normalize EXIF and composite transparency over white.
- One complete JSON object, optionally one complete JSON code fence. Reject duplicate
  keys and extra fields. Top-level keys: nodes, edges. At most 12 nodes and 20 edges.
- Nodes: unique ASCII id of 1–24 characters, visible label of 1–80 printable characters,
  kind in process/decision/terminator. Edges: source, target, label of 0–40 printable
  characters. References must exist; duplicate directed labeled edges are rejected.
  Disconnected nodes and cycles are allowed. No hidden placeholders or invented nodes.
- Node IDs are prefixed on export; text is escaped for SVG, Mermaid and HTML. Rendering
  never executes model output or calls a remote service. Reconstructed layout is not
  an exact recreation of the source image.
- UI: upload, actual source preview, extract, inspect reconstructed graph, quick label
  edits and advanced JSON structure edits, downloads. Expose extraction errors plainly.
  Changing inputs clears stale outputs and invalidates outstanding completions.
- An edit creates a new export revision retaining original model extraction metadata;
  edited outputs are labeled user edits, never scored as raw model predictions.
- Original reports and private Gradio cache expire after one hour including restart,
  at most 24 managed reports; only immutable original public fixtures bypass expiration.
- Runtime bind defaults to loopback, port 7865. No paid resources or deployment required.

## Evidence

Three original, independently drawn fixtures with fixed graph annotations before
inference: a linear flow, a branching flow, and a loop. Model sees image pixels only.
Measure label-based node/edge precision, recall and F1, plus exact graph and shape
agreement. IDs are not semantic labels. Report duplicate-label ambiguity explicitly.
Keep every raw prediction, failure, elapsed time, source checksum and revision.
These development examples do not establish general accuracy.

Inspect one real extraction and one actual edit in a browser. Capture actual UI
frames for a time-compressed GIF, verify frames/duration/loop and GitHub rendering.
CI runs deterministic tests without downloading model weights; actual model runs are
separately recorded.

## Visual reference lock

Primary: existing local ClickGuide workbench, already approved in this workflow.
Secondary: Mermaid flowchart node/edge conventions and bundled typography/craft.
Live design-reference connector is known unavailable in this session; no subscription.
Use a light neutral canvas, one system sans, blue primary actions, large side-by-side
source/reconstruction panels, and edit/download controls below. Status reflects
source state and model/user provenance. No marketing hero or decorative imagery.

## Boundaries

Printed flowcharts only in this release; handwritten diagrams, UML/ER/sequence
diagrams, spatial fidelity, reliable absence detection, and general benchmarks are
future work. An extraction is a model suggestion; users must inspect arrows/labels.
