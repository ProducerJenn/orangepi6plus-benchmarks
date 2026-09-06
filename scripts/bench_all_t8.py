#!/usr/bin/env python3
"""Rerun all locally-fitted models at 8 threads / 2048 ctx (period sweet spot).
Appends phases 'model_compare_t8' to results_full.jsonl."""
import json, subprocess, time, os

RESULTS_FILE = "/tmp/opencode/results/results_full.jsonl"
GEN_PROMPT = (
    "Explain the theory of relativity in simple terms, covering both special "
    "and general relativity. Include examples."
)

MODELS = [
    "driaforall/tiny-agent-a:0.5b",
    "LiquidAI/lfm2.5-350m:latest",
    "qwen3.5:0.8b",
    "LiquidAI/lfm2.5-1.2b-instruct:latest",
    "qwen2.5:1.5b",
    "phi4-mini:latest",
    "phi4-mini-reasoning:latest",
    "qwen3.5:4b",
    "gemma3:4b",
    "qwen2.5:7b",
    "qwen3:latest",
    "hf.co/unsloth/Qwen3-8B-GGUF:UD-Q4_K_XL",
    "qwen3-8b-unsloth-instruct",
    "hf.co/LiquidAI/LFM2.5-8B-A1B-GGUF:Q4_K_M",
    "lfm2.5:latest",
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

def run_one(model, prompt=GEN_PROMPT, threads=8, ctx=2048, n_predict=512):
    api_call("generate", {"model": model, "keep_alive": 0})
    time.sleep(1)
    print(f"  [{model}] threads={threads} ctx={ctx} ... ", end="", flush=True)
    start = time.time()
    resp = api_call("generate", {
        "model": model,
        "prompt": prompt,
        "options": {"num_ctx": ctx, "num_thread": threads, "num_predict": n_predict},
        "stream": False,
    })
    wall = time.time() - start
    if "error" in resp or "prompt_eval_count" not in resp:
        err = resp.get("error", "no data")
        print(f"FAILED: {err}")
        return None
    pec = resp.get("prompt_eval_count", 0)
    ped = resp.get("prompt_eval_duration", 0) / 1e9
    ec = resp.get("eval_count", 0)
    ed = resp.get("eval_duration", 0) / 1e9
    pp = round(pec / ped, 2) if ped else 0
    pg = round(ec / ed, 2) if ed else 0
    print(f"pp={pp} tok/s, pg={pg} tok/s, eval={ec} tok, wall={wall:.1f}s", flush=True)
    return {
        "model": model, "phase": "model_compare_t8", "threads": threads,
        "context_length": ctx, "prompt_eval_count": pec,
        "prompt_eval_duration_ms": round(ped * 1e3, 1), "prompt_eval_rate": pp,
        "eval_count": ec, "eval_duration_ms": round(ed * 1e3, 1), "eval_rate": pg,
        "total_duration_ms": round(resp.get("total_duration", 0) / 1e6, 1),
        "load_duration_ms": round(resp.get("load_duration", 0) / 1e6, 1),
        "wall_time_sec": round(wall, 2),
        "response_length": len(resp.get("response", "")),
    }

print("=== Full model sweep: 8 threads, 2048 ctx ===", flush=True)
for m in MODELS:
    entry = run_one(m)
    if entry:
        with open(RESULTS_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
        print("  appended", flush=True)
    api_call("generate", {"model": m, "keep_alive": 0})
    time.sleep(1)
print("done", flush=True)