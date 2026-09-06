#!/usr/bin/env python3
"""Ollama CPU Benchmark Suite v2 - targeted reruns + scaling tests"""
import json, subprocess, time, os, sys
from datetime import datetime

RESULTS_DIR = "/tmp/opencode/results"
os.makedirs(RESULTS_DIR, exist_ok=True)
RESULTS_FILE = os.path.join(RESULTS_DIR, "results_full.jsonl")

GEN_PROMPT = (
    "Explain the theory of relativity in simple terms, covering both special "
    "and general relativity. Include examples."
)

# All models with sizes (skip qwen3:latest - too slow on ARM)
MODELS = [
    ("driaforall/tiny-agent-a:0.5b", 531),
    ("LiquidAI/lfm2.5-350m:latest", 379),
    ("qwen3.5:0.8b", 1000),
    ("LiquidAI/lfm2.5-1.2b-instruct:latest", 730),
    ("qwen2.5:1.5b", 986),
    ("phi4-mini:latest", 2500),
    ("phi4-mini-reasoning:latest", 3200),
    ("qwen3.5:4b", 3400),
    ("gemma3:4b", 3300),
    ("qwen2.5:7b", 4700),
]

THREAD_CONFIGS = [1, 2, 4, 6, 8, 12]
CONTEXT_LENGTHS = [2048, 4096, 8192]


def api_call(endpoint, data):
    payload = json.dumps(data)
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "180",
             f"http://localhost:11434/api/{endpoint}",
             "-H", "Content-Type: application/json",
             "-d", payload],
            capture_output=True, text=True, timeout=200
        )
        return json.loads(result.stdout)
    except Exception as e:
        return {"error": str(e)}


def unload_model(model):
    api_call("generate", {"model": model, "keep_alive": 0})
    time.sleep(1)


def run_benchmark(model, threads, ctx, phase, prompt=GEN_PROMPT, timeout=180):
    unload_model(model)
    time.sleep(1)

    print(f"  [{phase}] {model} threads={threads} ctx={ctx} ... ", end="", flush=True)

    start = time.time()
    response = api_call("generate", {
        "model": model,
        "prompt": prompt,
        "options": {"num_ctx": ctx, "num_thread": threads},
        "stream": False
    })
    wall_time = time.time() - start

    if "error" in response or "prompt_eval_count" not in response:
        err = response.get("error", "no data in response")
        print(f"FAILED: {err}")
        return {
            "model": model, "phase": phase, "threads": threads,
            "context_length": ctx, "error": str(err)
        }

    pec = response.get("prompt_eval_count", 0)
    ped = response.get("prompt_eval_duration", 0)
    ec = response.get("eval_count", 0)
    ed = response.get("eval_duration", 0)
    td = response.get("total_duration", 0)
    ld = response.get("load_duration", 0)

    pp_rate = round(pec / (ped / 1e9), 2) if ped > 0 else 0
    pg_rate = round(ec / (ed / 1e9), 2) if ed > 0 else 0

    print(f"pp={pp_rate} tok/s, pg={pg_rate} tok/s, wall={wall_time:.1f}s")

    entry = {
        "model": model, "phase": phase, "threads": threads,
        "context_length": ctx,
        "prompt_eval_count": pec,
        "prompt_eval_duration_ms": round(ped / 1e6, 1),
        "prompt_eval_rate": pp_rate,
        "eval_count": ec,
        "eval_duration_ms": round(ed / 1e6, 1),
        "eval_rate": pg_rate,
        "total_duration_ms": round(td / 1e6, 1),
        "load_duration_ms": round(ld / 1e6, 1),
        "wall_time_sec": round(wall_time, 2),
        "response_length": len(response.get("response", ""))
    }

    unload_model(model)
    time.sleep(2)
    return entry


def append_result(entry):
    with open(RESULTS_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    print("=" * 55)
    print("  Ollama CPU Benchmark Suite v2")
    print("=" * 55)

    with open(RESULTS_FILE, "w") as f:
        f.write(json.dumps({
            "type": "system_info",
            "cpu_model": "CIX P1 CD8160 (Cortex-A720/A520)",
            "cpu_count": 12,
            "ram_gb": 14.9,
            "ollama_version": "0.31.2",
            "date": datetime.now().isoformat()
        }) + "\n")

    # Phase 1: All models
    print("\n>>> Phase 1: Model Comparison (4 threads, 2048 ctx)")
    print("-" * 55)
    for model, size in MODELS:
        result = run_benchmark(model, 4, 2048, "model_compare")
        result["model_size_mb"] = size
        append_result(result)
    print()

    # Phase 2: Thread scaling on 3 representative models
    scale_models = [
        ("qwen2.5:1.5b", "1.5b"),
        ("qwen3.5:4b", "4b"),
        ("phi4-mini:latest", "phi4"),
    ]
    for model, label in scale_models:
        print(f">>> Phase 2: Thread Scaling ({model})")
        print("-" * 55)
        for t in THREAD_CONFIGS:
            result = run_benchmark(model, t, 2048, f"thread_scaling_{label}")
            append_result(result)
        print()

    # Phase 3: Context length on 2 models
    ctx_models = [
        ("qwen2.5:1.5b", "1.5b"),
        ("qwen3.5:4b", "4b"),
    ]
    for model, label in ctx_models:
        print(f">>> Phase 3: Context Length Impact ({model})")
        print("-" * 55)
        for c in CONTEXT_LENGTHS:
            result = run_benchmark(model, 4, c, f"ctx_impact_{label}")
            append_result(result)
        print()

    print("=" * 55)
    print(f"  All benchmarks complete!")
    print(f"  Results: {RESULTS_FILE}")
    print("=" * 55)


if __name__ == "__main__":
    main()
