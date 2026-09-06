#!/usr/bin/env python3
"""Measure warm TTFT + prefill tok/s for all local models at 8 threads / 2048 ctx.
Appends phase 'model_ttft_t8' to results_full.jsonl."""
import json, subprocess, time

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

def api_call(endpoint, data, timeout=300):
    payload = json.dumps(data).encode()
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", str(timeout),
             "http://localhost:11434/api/" + endpoint,
             "-H", "Content-Type: application/json", "-d", payload],
            capture_output=True, text=True, timeout=timeout + 20
        )
        return json.loads(result.stdout)
    except Exception as e:
        return {"error": str(e)}

def stream_measure(model, prompt, threads=8, ctx=2048, n_predict=512):
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": True,
        "options": {"num_ctx": ctx, "num_thread": threads, "num_predict": n_predict},
    }).encode()
    start = time.time()
    proc = subprocess.Popen(
        ["curl", "-s", "-N", "--max-time", "300",
         "http://localhost:11434/api/generate",
         "-H", "Content-Type: application/json", "-d", payload],
        stdout=subprocess.PIPE, text=True, bufsize=1
    )
    ttft = None
    final = {}
    for line in proc.stdout:
        if ttft is None:
            ttft = time.time() - start
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("done"):
            final = obj
    proc.wait()
    return ttft, final

print("=== TTFT + prefill sweep: 8 threads, 2048 ctx ===", flush=True)
for m in MODELS:
    api_call("generate", {"model": m, "keep_alive": 0})
    time.sleep(1)
    # warmup: load weights with a tiny request
    api_call("generate", {
        "model": m, "prompt": "ping",
        "options": {"num_ctx": 2048, "num_thread": 8, "num_predict": 4},
        "stream": False,
    })
    print(f"  [{m}] warm, measuring ... ", end="", flush=True)
    ttft, final = stream_measure(m, GEN_PROMPT)
    if not final or "prompt_eval_count" not in final:
        print(f"FAILED: {final.get('error', 'no data') if isinstance(final, dict) else final}", flush=True)
    else:
        pec = final.get("prompt_eval_count", 0)
        ped = final.get("prompt_eval_duration", 0) / 1e9
        ec = final.get("eval_count", 0)
        ed = final.get("eval_duration", 0) / 1e9
        pp = round(pec / ped, 2) if ped else 0
        pg = round(ec / ed, 2) if ed else 0
        ttft_ms = round(ttft * 1000, 1)
        print(f"ttft={ttft_ms}ms, prefill={pp} tok/s, gen={pg} tok/s (eval={ec} tok)", flush=True)
        entry = {
            "model": m, "phase": "model_ttft_t8", "threads": 8,
            "context_length": 2048, "prompt_eval_count": pec,
            "prefill_tps": pp, "prompt_eval_duration_ms": round(ped * 1e3, 1),
            "eval_rate": pg, "eval_count": ec,
            "ttft_ms": ttft_ms,
            "wall_to_done_sec": round(final.get("total_duration", 0) / 1e9, 2),
        }
        with open(RESULTS_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
        print("  appended", flush=True)
    api_call("generate", {"model": m, "keep_alive": 0})
    time.sleep(1)
print("done", flush=True)