# Orange Pi 6 Plus - Local LLM Benchmarks

Benchmarks for running local LLMs on an **Orange Pi 6 Plus** (CIX P1 CD8160 SoC, 12-core ARM, 14.9 GB RAM) via Ollama and compare them against LiteRT-LM results.

- Full write-up: [docs/ollama-benchmarks.md](docs/ollama-benchmarks.md)
- Raw results: [results/results_full.jsonl](results/results_full.jsonl) (one JSON object per line)
- Harness scripts: [scripts/](scripts/)
- LiteRT-LM (Gemma 4, GPU offload) results: [github.com/ProducerJenn/litert-lm-benchmarks](https://github.com/ProducerJenn/litert-lm-benchmarks)

## TL;DR

| Model | Size | Max ctx | RAM @2K | Prefill (tok/s) | Gen (tok/s) | TTFT (ms) | Notes |
|---|---|---:|---:|---:|---:|---:|---|
| **LFM2.5-8B-A1B Q4_K_M** | 5.2 GB | 128K | 5.4 GB | 88.6 | **24.6** | **804** | Best overall: reasoning + tools, 3.4x faster than Qwen3-8B |
| Qwen3-8B unsloth UD-Q4_K_XL | 5.1 GB | 40K | 5.8 GB | 30.5 | 7.3 | 1466 | Best absolute quality, slow |
| qwen3:latest (official 8B) | 5.2 GB | 40K | 5.9 GB | 39.6 | 7.3 | 1182 | Same class as unsloth |
| qwen2.5:7b | 4.7 GB | 32K | 5.1 GB | 71.7 | 8.1 | 1228 | Solid all-rounder |
| phi4-mini | 2.5 GB | 128K | 3.6 GB | 77.2 | 13.1 | 839 | Good token/memory ratio |
| qwen3.5:4b | 3.4 GB | 262K | 3.7 GB | 57.2 | 11.7 | 1327 | 4B reasoning |
| lfm2.5-350m | 379 MB | 128K | 510 MB | 740.0 | 76.5 | 253 | Fastest small model |
| LiquidAI/lfm2.5-1.2b | 730 MB | 128K | 929 MB | 233.2 | 39.2 | 468 | Best small all-rounder |

All numbers at 8 threads / 2048 ctx (measured sweet spot). TTFT = warm time to first token (model preloaded). RAM @2K = resident memory from `ollama ps` at 2048 ctx (weights + KV). Max ctx = native ceiling from GGUF metadata; Ollama's runtime default is 4096.

## Context

You can raise Ollama's context with no speed cost — it's a **RAM** cost, not a throughput cost (see the [16K comparison](docs/ollama-benchmarks.md#higher-context-comparison-16k-vs-2k-8-threads)):

| Model | Safe ctx | RAM |
|---|---:|---:|
| lfm2.5-1.2b | 16K | 1.2 GB |
| LFM2.5-8B-A1B | **128K (full)** | 7.7 GB |
| gemma3:4b | 16K (max) | 3.9 GB |
| qwen3.5:4b | 16K (max) | 4.2 GB |
| phi4-mini | 8K | 5.3 GB |
| qwen2.5:7b | 16K (max) | 6.9 GB |
| qwen3 / unsloth 8B | 16K | 10 GB |
| LFM2.5-8B-A1B @16K | 16K | 5.5 GB |

Tuned models live in Ollama as `*-16k` (e.g. `lfm2.5-8b-16k`, `qwen3-8b-16k`); phi4's KV cache is the worst (32 attention heads) so `.phi4-mini-8k` stays at 8K.

## Key findings

1. **LFM2.5-8B-A1B is the clear winner** on this box: ~25 tok/s generation (only 1.5B active params per token in an 8.5B MoE) with reasoning + native tool calling. Same speed as its predecessor LFM2-8B-A1B but smarter.
2. **Qwen3-8B is 3.4x slower** (7.3 vs 25 tok/s at 8 threads) - only worth it when you need maximum reasoning depth.
3. **8 threads is the CPU sweet spot** - 12 threads adds contention on the hybrid big.LITTLE layout and hurts throughput.
4. **Context is free speed-wise**: 2K vs 16K changes gen/prefill by <3% — bigger context only costs RAM.
5. **LiteRT-LM's GPU path** (Mali-G720, Gemma 4 E2B) reaches ~24 tok/s decode with 125 tok/s prefill - comparable decode speed to LFM's CPU but dramatically better prompt ingestion.

## Hardware

| Spec | Value |
|---|---|
| Board | Orange Pi 6 Plus |
| SoC | CIX P1 CD8160 |
| CPU | 12-core ARM (4x Cortex-A720 + 8x Cortex-A520) |
| RAM | 14.9 GB |
| OS | Linux orangepi6plus 6.1.44-cix aarch64 |
| Ollama | 0.31.2 |

## Repo layout

```
README.md                       This overview
docs/ollama-benchmarks.md       Full Ollama benchmark write-up
results/results_full.jsonl      Raw per-run measurements
scripts/                        Benchmark harness (Ollama API)
```