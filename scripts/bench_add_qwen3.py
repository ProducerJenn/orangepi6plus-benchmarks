#!/usr/bin/env python3
"""Add Qwen3-8B unsloth to the existing benchmark suite (matches benchmark_v2 methodology)."""
import json, subprocess, time

RESULTS_FILE = "/tmp/opencode/results/results_full.jsonl"
GEN_PROMPT = (
    "Explain the theory of relativity in simple terms, covering both special "
    "and general relativity. Include examples."
)

MODELS = [
    ("hf.co/unsloth/Qwen3-8B-GGUF:UD-Q4_K_XL", "qwen3-8b-unsloth-thinking", GEN_PROMPT),
    ("qwen3-8b-unsloth-instruct", "qwen3-8b-unsloth-instruct", GEN_PROMPT + " /no_think"),
]

def api_call(endpoint, data):
    payload = json.dumps(data)
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "300",
             "http://localhost:11434/api/" + endpoint,
             "-H", "Content-Type: application/json",
             "-d", payload],
            capture_output=True, text=True, timeout=320
        )
        return json.loads(result.stdout)
    except Exception as e:
        return {"error": str(e)}

def unload_model(model):
    api_call("generate", {"model": model, "keep_alive": 0})
    time.sleep(1)

for model, alias, prompt in MODELS:
    unload_model(model)
    time.sleep(1)
    print(f"\n=== {alias} threads=4 ctx=2048 ===", flush=True)
    start = time.time()
    resp = api_call("generate", {
        "model": model,
        "prompt": prompt,
        "options": {"num_ctx": 2048, "num_thread": 4, "num_predict": 512},
        "stream": False,
    })
    wall = time.time() - start
    if "error" in resp or "prompt_eval_count" not in resp:
        print(f"FAILED: {resp.get('error', 'no data')}")
        continue
    pec = resp.get("prompt_eval_count", 0)
    ped = resp.get("prompt_eval_duration", 0) / 1e9
    ec = resp.get("eval_count", 0)
    ed = resp.get("eval_duration", 0) / 1e9
    pp = round(pec / ped, 2) if ped else 0
    pg = round(ec / ed, 2) if ed else 0
    print(f"pp={pp} tok/s, pg={pg} tok/s, eval={ec} tok, wall={wall:.1f}s", flush=True)
    entry = {
        "model": model, "phase": "model_compare_add", "threads": 4,
        "context_length": 2048, "prompt_eval_count": pec,
        "prompt_eval_duration_ms": round(ped * 1e3, 1), "prompt_eval_rate": pp,
        "eval_count": ec, "eval_duration_ms": round(ed * 1e3, 1), "eval_rate": pg,
        "total_duration_ms": round(resp.get("total_duration", 0) / 1e6, 1),
        "load_duration_ms": round(resp.get("load_duration", 0) / 1e6, 1),
        "wall_time_sec": round(wall, 2),
        "response_length": len(resp.get("response", "")),
    }
    with open(RESULTS_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print("appended to " + RESULTS_FILE, flush=True)
    unload_model(model)