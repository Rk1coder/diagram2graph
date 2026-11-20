import hashlib
import os
import threading

MODEL_ID = "Qwen/Qwen3-VL-2B-Instruct"
REVISION = "89644892e4d85e24eaac8bacfd4f463576704203"
PROMPT = """Read the printed flowchart in this image. Return only one complete JSON object with exactly two keys: nodes and edges.
nodes is an array of objects with exactly: id, label, kind. Assign short unique IDs n1, n2, etc. Copy the text inside each visible node. kind must be process (rectangle), decision (diamond), or terminator (oval/start/end).
edges is an array of objects with exactly: source, target, label. source and target reference node IDs. Follow the visible arrow direction carefully, including loops and branches. Copy arrow labels such as Yes or No; use an empty string for an unlabeled arrow.
Ignore the title and text outside nodes/arrows. Do not invent missing nodes, edges or labels. Maximum 12 nodes and 20 edges. No explanation or extra fields."""


class Engine:
    model_id = MODEL_ID
    revision = REVISION
    prompt_sha256 = hashlib.sha256(PROMPT.encode()).hexdigest()

    def __init__(self):
        self._model = None
        self._processor = None
        self._lock = threading.Lock()
        self.settings = {
            "device": "cpu",
            "dtype": "float32",
            "min_pixels": 65536,
            "max_pixels": 262144,
            "max_new_tokens": 768,
            "image_processor": "fast",
            "threads": max(1, min(16, int(os.environ.get("D2G_THREADS", "4")))),
        }

    def predict(self, image):
        import torch
        from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

        with self._lock:
            if self._model is None:
                torch.set_num_threads(self.settings["threads"])
                self._processor = AutoProcessor.from_pretrained(
                    MODEL_ID,
                    revision=REVISION,
                    min_pixels=self.settings["min_pixels"],
                    max_pixels=self.settings["max_pixels"],
                    use_fast=True,
                    trust_remote_code=False,
                )
                self._model = Qwen3VLForConditionalGeneration.from_pretrained(
                    MODEL_ID,
                    revision=REVISION,
                    dtype=torch.float32,
                    device_map="cpu",
                    attn_implementation="sdpa",
                    trust_remote_code=False,
                    weights_only=True,
                ).eval()
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": PROMPT},
                    ],
                }
            ]
            inputs = self._processor.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_dict=True,
                return_tensors="pt",
            )
            with torch.inference_mode():
                generated = self._model.generate(
                    **inputs,
                    max_new_tokens=self.settings["max_new_tokens"],
                    do_sample=False,
                    use_cache=True,
                    temperature=None,
                    top_p=None,
                    top_k=None,
                )
            return self._processor.batch_decode(
                generated[:, inputs.input_ids.shape[1] :],
                skip_special_tokens=True,
            )[0].strip()
