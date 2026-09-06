#!/usr/bin/env python3
import json, sys, time, urllib.request

MODELS = [
    "hf.co/unsloth/Qwen3-8B-GGUF:UD-Q4_K_XL",   # thinking defaults (doc settings)
    "qwen3-8b-unsloth-instruct",                 # tuned non-thinking (doc settings)
    "qwen3:latest",                              # existing baseline
]

def gen(model, prompt, n_predict=64, n_ctx=4096):
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": n_predict, "num_ctx": n_ctx},
    }
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        out = json.load(r)
    pe_t = out.get("prompt_eval_duration", 0) / 1e9
    e_t = out.get("eval_duration", 0) / 1e9
    return {
        "pe_rate": out.get("prompt_eval_count", 0) / pe_t if pe_t else 0,
        "e_rate": out.get("eval_count", 0) / e_t if e_t else 0,
        "pe_n": out.get("prompt_eval_count", 0),
        "e_n": out.get("eval_count", 0),
        "load": out.get("load_duration", 0) / 1e9,
    }

def prompt_of_words(n):
    return " ".join(f"word{i}" for i in range(n))

def run_set(model):
    print(f"=== {model} ===", flush=True)
    gen(model, prompt_of_words(10))          # warmup / load weights
    for words, tag in [(10, "short  "), (400, "medium "), (600, "long   ")]:
        r = gen(model, prompt_of_words(words))
        print(
            f"{tag} prompt={r['pe_n']:>4}tok: eval {r['pe_rate']:5.1f} tok/s | "
            f"gen {r['e_rate']:5.1f} tok/s ({r['e_n']:>3} tok) | load {r['load']*1000:6.0f}ms",
            flush=True,
        )

for m in MODELS:
    try:
        run_set(m)
    except Exception as e:
        print(f"FAILED {m}: {e}", flush=True)