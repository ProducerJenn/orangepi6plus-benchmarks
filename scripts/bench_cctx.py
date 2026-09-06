#!/usr/bin/env python3
"""Re-benchmark tuned higher-context models: TTFT + prefill + gen at 8 threads.
Appends phase 'cctx_sweep' to results_full.jsonl."""
import json, subprocess, time

RESULTS_FILE = "/tmp/opencode/results/results_full.jsonl"
GEN_PROMPT = (
    "Explain the theory of relativity in simple terms, covering both special "
    "and general relativity. Include examples."
)

# (model, context) - phi4 at 8K because 16K KV is too big
MODELS = [
    ("hf.co/LiquidAI/LFM2.5-8B-A1B-GGUF:Q4_K_M", 16384),
    ("lfm2.5-1.2b-16k", 16384),
    ("gemma3-4b-16k", 16384),
    ("qwen3.5-4b-16k", 16384),
    ("qwen2.5-7b-16k", 16384),
    ("phi4-mini-8k", 8192),
    ("qwen3-8b-16k", 16384),
    ("qwen3-8b-unsloth-16k", 16384),
]

def api_call(endpoint, data, timeout=300):
    payload = json.dumps(data).encode()
    try:
        r = subprocess.run(
            ["curl", "-s", "--max-time", str(timeout),
             "http://localhost:11434/api/" + endpoint,
             "-H", "Content-Type: application/json", "-d", payload],
            capture_output=True, text=True, timeout=timeout + 20)
        return json.loads(r.stdout)
    except Exception as e:
        return {"error": str(e)}

def stream_measure(model, prompt, threads=8, ctx=16384, n_predict=256):
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": True,
        "options": {"num_ctx": ctx, "num_thread": threads, "num_predict": n_predict},
    }).encode()
    start = time.time()
    proc = subprocess.Popen(
        ["curl", "-s", "-N", "--max-time", "400",
         "http://localhost:11434/api/generate",
         "-H", "Content-Type: application/json", "-d", payload],
        stdout=subprocess.PIPE, text=True, bufsize=1)
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

for model, ctx in MODELS:
    api_call("generate", {"model": model, "keep_alive": 0})
    time.sleep(1)
    api_call("generate", {
        "model": model, "prompt": "ping",
        "options": {"num_ctx": ctx, "num_thread": 8, "num_predict": 2},
        "stream": False})
    print(f"[{model}] ctx={ctx} measuring...", end=" ", flush=True)
    ttft, final = stream_measure(model, GEN_PROMPT, 8, ctx)
    if not final or "prompt_eval_count" not in final:
        print(f"FAILED: {final.get('error','no data') if isinstance(final,dict) else final}", flush=True)
    else:
        pec = final.get("prompt_eval_count", 0)
        ped = final.get("prompt_eval_duration", 0) / 1e9
        ec = final.get("eval_count", 0)
        ed = final.get("eval_duration", 0) / 1e9
        pp = round(pec / ped, 2) if ped else 0
        pg = round(ec / ed, 2) if ed else 0
        t_ms = round(ttft * 1000, 1)
        print(f"ctx={ctx} prefill={pp} tok/s gen={pg} tok/s ttft={t_ms}ms eval={ec}", flush=True)
        entry = {
            "model": model, "phase": "cctx_sweep", "threads": 8,
            "context_length": ctx, "prompt_eval_count": pec,
            "prefill_tps": pp, "prompt_eval_duration_ms": round(ped*1e3,1),
            "eval_rate": pg, "eval_count": ec, "ttft_ms": t_ms,
            "wall_to_done_sec": round(final.get("total_duration",0)/1e9,2),
        }
        with open(RESULTS_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
        print("  appended", flush=True)
    api_call("generate", {"model": model, "keep_alive": 0})
    time.sleep(1)
print("done")