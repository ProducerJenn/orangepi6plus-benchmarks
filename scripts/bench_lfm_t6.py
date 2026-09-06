#!/usr/bin/env python3
import json, subprocess, time

RESULTS_FILE = "/tmp/opencode/results/results_full.jsonl"
GEN_PROMPT = (
    "Explain the theory of relativity in simple terms, covering both special "
    "and general relativity. Include examples."
)
MODELS = [
    ("hf.co/LiquidAI/LFM2.5-8B-A1B-GGUF:Q4_K_M", "lfm2.5-8b-a1b-new"),
    ("lfm2.5:latest", "lfm2-8b-a1b-old"),
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

for model, alias in MODELS:
    unload_model(model)
    time.sleep(1)
    print(f"=== {alias} threads=6 ctx=8192 ===", flush=True)
    resp = api_call("generate", {
        "model": model,
        "prompt": GEN_PROMPT,
        "options": {"num_ctx": 8192, "num_thread": 6, "num_predict": 512},
        "stream": False,
    })
    if "error" in resp or "prompt_eval_count" not in resp:
        print(f"FAILED: {resp.get('error', 'no data')}")
        continue
    pec = resp.get("prompt_eval_count", 0)
    ped = resp.get("prompt_eval_duration", 0) / 1e9
    ec = resp.get("eval_count", 0)
    ed = resp.get("eval_duration", 0) / 1e9
    pp = round(pec / ped, 2) if ped else 0
    pg = round(ec / ed, 2) if ed else 0
    print(f"pp={pp} tok/s, pg={pg} tok/s, eval={ec} tok", flush=True)
    entry = {
        "model": model, "alias": alias, "phase": "lfm2_thread_6",
        "threads": 6, "context_length": 8192,
        "prompt_eval_count": pec, "prompt_eval_rate": pp,
        "eval_count": ec, "eval_duration_ms": round(ed*1e3,1), "eval_rate": pg,
        "wall_time_sec": round(resp.get("total_duration",0)/1e9,2),
        "response_length": len(resp.get("response", "")),
    }
    with open(RESULTS_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    unload_model(model)
