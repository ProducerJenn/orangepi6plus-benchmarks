# Orange Pi 6 Plus - Local LLM Benchmarks

Benchmarks for running local LLMs on an **Orange Pi 6 Plus** (CIX P1 CD8160 SoC, 12-core ARM, 14.9 GB RAM) via Ollama and compare them against LiteRT-LM results.

- Full write-up: [docs/ollama-benchmarks.md](docs/ollama-benchmarks.md)
- Raw results: [results/results_full.jsonl](results/results_full.jsonl) (one JSON object per line)
- Harness scripts: [scripts/](scripts/)
- LiteRT-LM (Gemma 4, GPU offload) results: [github.com/ProducerJenn/litert-lm-benchmarks](https://github.com/ProducerJenn/litert-lm-benchmarks)

## TL;DR

| Model | Size | Threads | Gen (tok/s) | Notes |
|---|---|---|---|---|
| **LFM2.5-8B-A1B Q4_K_M** | 5.2 GB | 8 | **25.0** | Best overall: reasoning + tools, 3.4x faster than Qwen3-8B |
| Qwen3-8B unsloth UD-Q4_K_XL | 5.1 GB | 8 | 7.3 | Best absolute quality, slow |
| qwen3:latest (official 8B) | 5.2 GB | 8 | 7.2 | Same class as unsloth, no speed edge |
| qwen2.5:7b | 4.7 GB | 8 | 8.1 | Solid all-rounder |
| phi4-mini | 2.5 GB | 8 | 13.5 | Good token/memory ratio |
| qwen3.5:4b | 3.4 GB | 8 | 11.7 | 4B reasoning, sadly slow |
| lfm2.5-350m | 379 MB | 8 | 78.5 | Fastest small model |
| LiquidAI/lfm2.5-1.2b | 730 MB | 8 | 38.8 | Best small all-rounder |

All numbers at 8 threads / 2048 ctx (the measured sweet spot). 8 threads beats 4 on every model, most (+20%) on the 8B class.

## Key findings

1. **LFM2.5-8B-A1B is the clear winner** on this box: ~25 tok/s generation (only 1.5B active params per token in an 8.5B MoE) with reasoning + native tool calling. Same speed as its predecessor LFM2-8B-A1B but smarter.
2. **Qwen3-8B is 3.4x slower** (7.3 vs 25 tok/s at 8 threads) - only worth it when you need maximum reasoning depth.
3. **8 threads is the CPU sweet spot** - 12 threads adds contention on the hybrid big.LITTLE layout and hurts throughput.
4. **LiteRT-LM's GPU path** (Mali-G720, Gemma 4 E2B) reaches ~24 tok/s decode with 125 tok/s prefill - comparable decode speed to LFM's CPU but dramatically better prompt ingestion.

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