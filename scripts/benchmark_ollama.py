#!/usr/bin/env python3
"""Ollama Model Benchmark - Tests speed, quality, and capabilities across models."""

import json
import time
import sys
import urllib.request
import urllib.error
from datetime import datetime

OLLAMA_HOST = "http://192.168.88.56:11434"

PROMPTS = {
    "short": "What is 2+2?",
    "medium": "Explain the difference between a stack and a queue in 3 sentences.",
    "long": "Write a detailed comparison of Python and Rust for systems programming, covering performance, safety, ergonomics, ecosystem, and use cases. Include specific examples.",
    "code": "Write a Python function that finds the longest palindromic substring in a string. Include type hints and a brief docstring.",
    "reasoning": "A farmer has 17 sheep. All but 9 die. How many sheep are left? Explain your reasoning step by step.",
}


def api_get(path):
    req = urllib.request.Request(f"{OLLAMA_HOST}{path}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def api_post(path, data, timeout=120):
    body = json.dumps(data).encode()
    req = urllib.request.Request(f"{OLLAMA_HOST}{path}", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def get_models():
    models = api_get("/api/tags")["models"]
    local = []
    for m in models:
        if m.get("remote_host"):
            continue
        local.append({
            "name": m["name"],
            "params": m["details"].get("parameter_size", "?"),
            "quant": m["details"].get("quantization_level", "?"),
            "family": m["details"].get("family", "?"),
            "ctx": m["details"].get("context_length", 0),
            "caps": m.get("capabilities", []),
        })
    return local


def benchmark_model(model_name, prompt, num_predict=256):
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"num_predict": num_predict, "temperature": 0.0, "num_ctx": 4096},
    }
    try:
        start = time.perf_counter()
        data = api_post("/api/chat", payload, timeout=180)
        elapsed = time.perf_counter() - start

        eval_count = data.get("eval_count", 0)
        prompt_eval_count = data.get("prompt_eval_count", 0)
        prompt_eval_duration = data.get("prompt_eval_duration", 0) / 1e9
        eval_duration = data.get("eval_duration", 0) / 1e9
        content = data.get("message", {}).get("content", "")

        return {
            "wall_time": round(elapsed, 2),
            "prompt_tokens": prompt_eval_count,
            "prompt_eval_speed": round(prompt_eval_count / prompt_eval_duration, 1) if prompt_eval_duration > 0 else 0,
            "gen_tokens": eval_count,
            "gen_speed": round(eval_count / eval_duration, 1) if eval_duration > 0 else 0,
            "response": content[:600],
        }
    except Exception as e:
        return {"error": str(e)[:200]}


def main():
    models = get_models()
    print(f"\n{'='*80}")
    print(f"  OLLAMA MODEL BENCHMARK - {OLLAMA_HOST}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  {len(models)} local models")
    print(f"{'='*80}\n")

    print(f"{'Model':<35} {'Params':<10} {'Quant':<8} {'Family':<12} {'Ctx':<8} {'Caps'}")
    print("-" * 105)
    for m in sorted(models, key=lambda x: x["name"]):
        caps = ", ".join(m["caps"]) if m["caps"] else "-"
        ctx = str(m["ctx"]) if m["ctx"] else "?"
        print(f"{m['name']:<35} {m['params']:<10} {m['quant']:<8} {m['family']:<12} {ctx:<8} {caps}")

    results = {}
    test_cases = [
        ("short", "Short Q&A", 64),
        ("medium", "Medium", 150),
        ("long", "Long", 350),
        ("code", "Code", 350),
        ("reasoning", "Reasoning", 150),
    ]

    for prompt_key, prompt_label, num_predict in test_cases:
        print(f"\n{'='*80}")
        print(f"  TEST: {prompt_label} (max {num_predict} tokens)")
        print(f"{'='*80}")

        for model in sorted(models, key=lambda x: x["name"]):
            name = model["name"]
            if name not in results:
                results[name] = {"info": model, "benchmarks": {}}

            print(f"  [{name}] ", end="", flush=True)
            stats = benchmark_model(name, PROMPTS[prompt_key], num_predict=num_predict)
            results[name]["benchmarks"][prompt_key] = stats

            if "error" in stats:
                print(f"ERROR: {stats['error']}")
            else:
                print(f"{stats['wall_time']}s | gen {stats['gen_speed']} tok/s ({stats['gen_tokens']}t) | prompt {stats['prompt_eval_speed']} tok/s")

    # Speed summary
    print(f"\n\n{'='*80}")
    print(f"  GENERATION SPEED RANKING (tok/s)")
    print(f"{'='*80}")
    header = f"{'#':<3} {'Model':<35}"
    for pk, label, _ in test_cases:
        header += f" {label:>10}"
    header += f" {'AVG':>8} {'Params':>8}"
    print(header)
    print("-" * len(header))

    rows = []
    for name, data in sorted(results.items()):
        speeds = []
        for pk, _, _ in test_cases:
            s = data["benchmarks"].get(pk, {})
            speeds.append(s.get("gen_speed", 0) if "error" not in s else 0)
        avg = sum(speeds) / len(speeds) if speeds else 0
        rows.append((avg, name, speeds, data["info"]["params"]))

    rows.sort(key=lambda x: -x[0])
    for i, (avg, name, speeds, params) in enumerate(rows, 1):
        row = f"{i:<3} {name:<35}"
        for s in speeds:
            row += f" {s:>10.1f}" if s > 0 else f" {'ERR':>10}"
        row += f" {avg:>7.1f} {params:>8}"
        print(row)

    # Quality samples
    print(f"\n\n{'='*80}")
    print(f"  REASONING QUALITY SAMPLES")
    print(f"{'='*80}")
    ranked = sorted(results.items(), key=lambda x: -x[1]["benchmarks"].get("reasoning", {}).get("gen_speed", 0))
    for name, data in ranked:
        r = data["benchmarks"].get("reasoning", {})
        resp = r.get("response", "")
        speed = r.get("gen_speed", 0)
        if not resp or "error" in r:
            continue
        print(f"\n--- {name} ({speed} tok/s) ---")
        print(resp[:350])
    print()

    with open("/tmp/opencode/benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("Results saved to /tmp/opencode/benchmark_results.json")


if __name__ == "__main__":
    main()
