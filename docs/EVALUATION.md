# Development evaluation

Three original printed English flowcharts with graph annotations fixed before inference. This is a narrow development set, not an independent benchmark.

| Fixture | Nodes | Directed arrows | Node F1 | Edge F1 | Shapes | Exact graph | Time |
| --- | --- | --- | --- | --- | --- | --- | --- |
| linear | 5 / 5 | 4 / 4 | 1.00 | 1.00 | 1.00 | True | 95.652 s |
| branch | 5 / 5 | 5 / 5 | 1.00 | 1.00 | 1.00 | True | 91.762 s |
| loop | 6 / 6 | 6 / 6 | 1.00 | 1.00 | 1.00 | True | 101.129 s |

## Method

Each model input is the fixture pixels plus the fixed prompt stored in the run JSON. Expected graphs are never passed to the model. Source PNG checksums are checked before inference. The three figures were drawn with fixed positions and explicit arrow routes independently of the reconstruction renderer. Labels, branch directions, joins and retry direction were visually inspected before scoring.

Node labels are matched after case-folding and collapsing whitespace; punctuation is retained. IDs may differ. Precision/recall/F1 count label multisets. Directed edges match normalized source label, target label and arrow label. Shape agreement uses process/decision/terminator kinds. Exact graph additionally requires equal node/edge counts and all shapes. If either graph repeats a normalized node label, identity-based edge and shape metrics are explicitly unavailable rather than treated as a reliable match.

## Configuration

- Qwen/Qwen3-VL-2B-Instruct at 89644892e4d85e24eaac8bacfd4f463576704203.
- CPU float32, four threads, SDPA, fast image processor, greedy decoding.
- Image budget 65536–262144 pixels; maximum 768 output tokens.
- Timing includes model/processor loading on the first call but excludes network downloads and export rendering. Weights were cached. Other applications and memory pressure can affect CPU latency.
- Raw model outputs, prompt text/hash, source hashes, settings and graphs are retained in local-cpu.json.

All three development cases match in this run. Three authored diagrams cannot establish performance on unseen documents, complex routing, handwriting, tiny labels or real-world screenshots. No held-out or general-accuracy claim is made.

## Reproduce

```bash
python scripts/evaluate.py --output artifacts/evaluation.json
npm ci --ignore-scripts
npm run test:mermaid
```

Model errors are retained and cause a nonzero run exit status. New evaluator runs
record model revision, inference settings, prompt hash and total attempt duration
even when inference fails. Total attempt time includes export/scoring work; successful
reports separately retain the original inference duration. The published successful
run preserves its original report data. Deterministic tests use a fixture inference boundary; recorded runs use the actual pinned model. Export images may be re-rendered from recorded graph data after renderer changes without repeating inference. SVG/PNG layouts reconstruct topology and do not reproduce source coordinates.

## User edits and GIF

A user edit creates a new report with origin=user_edit and a parent report ID; original raw output and model_graph remain intact. Edited graphs are not substituted into extraction scores. The README GIF is assembled from actual browser captures and labels compressed waiting time. Its playback duration is unrelated to inference time.
