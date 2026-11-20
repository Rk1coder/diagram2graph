# Diagram2Graph Implementation Plan

> Execute inline with superpowers:executing-plans; maintain a per-plan ledger.

**Goal:** Locally tested image-to-graph app with editable exports, actual-output GIF,
stage commits, and verified GitHub publication.

**Architecture:** Strict bounded graph schema; deterministic layout/render/export;
lazy local Qwen adapter; isolated versioned service; English Gradio workbench.

**Tech Stack:** Python 3.12, Gradio, Transformers, CPU PyTorch, Pillow, NetworkX.

**Spec:** `docs/superpowers/specs/2026-11-20-diagram2graph-design.md`

## Global Constraints

- Printed English flowcharts, <=12 nodes, <=20 edges; validated PNG/JPEG <=10 MiB.
- Pinned model, no remote model code or rendering APIs; loopback port7865.
- Strict JSON fields/references, escaped labels, honest model/user provenance.
- Separate commits, local tests first, real outputs/GIF, no assistant attribution.

## Review Focus

- Bad/duplicate JSON, dangling edges, repeated labels and cycles: Task1 tests.
- SVG/Mermaid text injection and reserved IDs: Task1 tests plus Mermaid parsing.
- Corrupt/animated images and restart cache expiration: Task2 regression tests.
- Stale results and edits linked to the wrong source: Task2/3 tests and browser checks.
- GIF correctness and benchmark annotations consistent with visible arrows: Task3 QA.

### Task 1: Graph schema, renderer, and original fixtures

Files: `diagram2graph/graph.py`, `render.py`, `tests/test_graph.py`, `test_render.py`,
`scripts/make_examples.py`, `examples/`.
Interfaces: `parse_graph(text)->dict`, `validate_graph(dict)->dict`,
`to_mermaid(graph)->str`, `render_svg(graph)->str`, `render_png(graph)->Image`.

- [ ] Write failing validation/export/layout tests, observe RED.
- [ ] Implement bounded schema, deterministic layout and escaped SVG/PNG/Mermaid.
- [ ] Draw three independent fixtures; inspect labels and arrow directions.
- [ ] Run complete suite/lint; commit a testable graph/export core.

### Task 2: Actual extraction, report service and editing

Files: `model.py`, `images.py`, `storage.py`, `service.py`, `scripts/evaluate.py`, tests.
Interfaces: `Engine.predict(image)->str`, `Service.extract(path)->dict`,
`Service.edit(report,graph)->dict`, `score_graph(expected,actual)->dict`.

- [ ] Write failing service/provenance/score/image/cache tests, observe RED.
- [ ] Add pinned local adapter, versioned exports, strict editing and cache cleanup.
- [ ] Run actual extraction on all fixed fixtures; retain successes and failures.
- [ ] Run full suite/lint, document measurements, commit model/service evidence.

### Task 3: Workbench, real GIF, documentation and publication

Files: `app.py`, tests, `scripts/make_demo.py`, README/docs, CI, actual output assets.

- [ ] Write failing callback/invalidation tests; implement English UI and live edits.
- [ ] Run full tests and actual browser extraction/edit/download-link checks.
- [ ] Capture real states; assemble and verify labeled time-compressed looping GIF.
- [ ] Fresh whole-branch review; fix important findings with RED->GREEN tests.
- [ ] Commit stages; publish complete Git history and actual images/GIF after tests.
- [ ] Verify remote source parity, README media, CI, source archive and Git bundle.
