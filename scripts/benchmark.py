#!/usr/bin/env python3
"""Ollama CPU Benchmark Suite"""
import json
import subprocess
import time
import os
import sys
from datetime import datetime

RESULTS_DIR = "/tmp/opencode/results"
os.makedirs(RESULTS_DIR, exist_ok=True)

RESULTS_FILE = os.path.join(RESULTS_DIR, "results.jsonl")

GEN_PROMPT = (
    "Explain the theory of relativity in simple terms, covering both special "
    "and general relativity. Include examples."
)

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
    ("qwen3:latest", 5200),
]

THREAD_CONFIGS = [1, 2, 4, 6, 8, 12]
CONTEXT_LENGTHS = [2048, 4096, 8192]


def api_call(endpoint, data):
    """Make an API call to Ollama."""
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
    """Unload a model from memory."""
    api_call("generate", {"model": model, "keep_alive": 0})
    time.sleep(1)


def run_benchmark(model, threads, ctx, phase, prompt=GEN_PROMPT):
    """Run a single benchmark and return results."""
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

    if "error" in response:
        print("FAILED:", response["error"])
        return {
            "model": model, "phase": phase, "threads": threads,
            "context_length": ctx, "error": response["error"]
        }

    prompt_eval_count = response.get("prompt_eval_count", 0)
    prompt_eval_dur_ns = response.get("prompt_eval_duration", 0)
    eval_count = response.get("eval_count", 0)
    eval_dur_ns = response.get("eval_duration", 0)
    total_dur_ns = response.get("total_duration", 0)
    load_dur_ns = response.get("load_duration", 0)

    pp_rate = round(prompt_eval_count / (prompt_eval_dur_ns / 1e9), 2) if prompt_eval_dur_ns > 0 else 0
    pg_rate = round(eval_count / (eval_dur_ns / 1e9), 2) if eval_dur_ns > 0 else 0

    print(f"pp={pp_rate} tok/s, pg={pg_rate} tok/s, wall={wall_time:.1f}s")

    entry = {
        "model": model,
        "phase": phase,
        "threads": threads,
        "context_length": ctx,
        "prompt_eval_count": prompt_eval_count,
        "prompt_eval_duration_ms": round(prompt_eval_dur_ns / 1e6, 1),
        "prompt_eval_rate": pp_rate,
        "eval_count": eval_count,
        "eval_duration_ms": round(eval_dur_ns / 1e6, 1),
        "eval_rate": pg_rate,
        "total_duration_ms": round(total_dur_ns / 1e6, 1),
        "load_duration_ms": round(load_dur_ns / 1e6, 1),
        "wall_time_sec": round(wall_time, 2),
        "response_length": len(response.get("response", ""))
    }

    unload_model(model)
    time.sleep(2)
    return entry


def get_system_info():
    """Gather system information."""
    info = {}
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if "model name" in line.lower():
                    info["cpu_model"] = line.split(":", 1)[1].strip()
                    break
    except:
        info["cpu_model"] = "unknown"

    info["cpu_count"] = os.cpu_count()
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemTotal"):
                info["ram_kb"] = int(line.split()[1])
                info["ram_gb"] = round(info["ram_kb"] / 1024 / 1024, 1)
                break

    info["ollama_version"] = subprocess.run(
        ["ollama", "--version"], capture_output=True, text=True
    ).stdout.strip()
    info["platform"] = subprocess.run(
        ["uname", "-a"], capture_output=True, text=True
    ).stdout.strip()
    info["date"] = datetime.now().isoformat()
    return info


def main():
    print("=" * 50)
    print("  Ollama CPU Benchmark Suite")
    print("=" * 50)

    sys_info = get_system_info()
    print(f"  CPU: {sys_info['cpu_model']}")
    print(f"  Cores: {sys_info['cpu_count']}, RAM: {sys_info['ram_gb']} GB")
    print(f"  Ollama: {sys_info['ollama_version']}")
    print(f"  Date: {sys_info['date']}")
    print()

    all_results = []

    # Write header
    with open(RESULTS_FILE, "w") as f:
        f.write(json.dumps({"type": "system_info", **sys_info}) + "\n")

    # Phase 1: Model comparison
    print(">>> Phase 1: Model Comparison (4 threads, 2048 ctx)")
    print("-" * 50)
    for model, size in MODELS:
        result = run_benchmark(model, 4, 2048, "model_compare")
        result["model_size_mb"] = size
        all_results.append(result)
        with open(RESULTS_FILE, "a") as f:
            f.write(json.dumps(result) + "\n")
    print()

    # Phase 2: Thread scaling
    for test_model, test_label in [
        ("qwen2.5:1.5b", "1.5b"),
        ("qwen3.5:4b", "4b"),
        ("phi4-mini:latest", "phi4"),
    ]:
        print(f">>> Phase 2: Thread Scaling ({test_model})")
        print("-" * 50)
        for t in THREAD_CONFIGS:
            result = run_benchmark(test_model, t, 2048, f"thread_scaling_{test_label}")
            all_results.append(result)
            with open(RESULTS_FILE, "a") as f:
                f.write(json.dumps(result) + "\n")
        print()

    # Phase 3: Context length
    for test_model, test_label in [
        ("qwen2.5:1.5b", "1.5b"),
        ("qwen3.5:4b", "4b"),
    ]:
        print(f">>> Phase 3: Context Length Impact ({test_model})")
        print("-" * 50)
        for c in CONTEXT_LENGTHS:
            result = run_benchmark(test_model, 4, c, f"ctx_impact_{test_label}")
            all_results.append(result)
            with open(RESULTS_FILE, "a") as f:
                f.write(json.dumps(result) + "\n")
        print()

    print("=" * 50)
    print(f"  Benchmark Complete! {len(all_results)} tests run.")
    print(f"  Results: {RESULTS_FILE}")
    print("=" * 50)


if __name__ == "__main__":
    main()
