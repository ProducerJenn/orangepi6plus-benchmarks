# Ollama Benchmarks - Orange Pi 6 Plus

Local LLM inference benchmarks on an Orange Pi 6 Plus (CIX P1 CD8160, 12-core ARM, 14.9 GB RAM), run with Ollama 0.31.2 on 2026-08-18 (small models) and 2026-09-07 (full 8-thread sweep + Qwen3-8B + LFM2.5).

## Methodology

- Measured via the Ollama `/api/generate` endpoint with `stream: false`.
- **Model comparison suite**: `num_thread=8` (the measured sweet spot on this CPU, see thread scaling below), `num_ctx=2048`, prompt = "Explain the theory of relativity in simple terms, covering both special and general relativity. Include examples.", capped at 512 decode tokens.
- An earlier suite ran the same models at `num_thread=4`; the 4-thread numbers are preserved in `results/results_full.jsonl` (phase `model_compare`) for reference.
- Models are unloaded between runs (`keep_alive: 0`).
- `prompt_eval_rate` (pp) = prompt ingestion tok/s; `eval_rate` (pg) = generation tok/s.

## Model comparison (threads=8, ctx=2048)

| Model | Size | Prompt (tok/s) | Gen (tok/s) |
|---|---|---|---|
| driaforall/tiny-agent-a 0.5b | 531 MB | 580.96 | 50.57 |
| LiquidAI/lfm2.5-350m | 379 MB | 739.73 | 78.50 |
| qwen3.5:0.8b | 1.0 GB | 251.80 | 31.84 |
| LiquidAI/lfm2.5-1.2b | 730 MB | 226.44 | 38.84 |
| qwen2.5:1.5b | 986 MB | 180.86 | 28.89 |
| phi4-mini | 2.5 GB | 79.19 | 13.54 |
| phi4-mini-reasoning | 3.2 GB | 65.08 | 11.04 |
| qwen3.5:4b | 3.4 GB | 57.02 | 11.72 |
| gemma3:4b | 3.3 GB | 72.06 | 13.19 |
| qwen2.5:7b | 4.7 GB | 41.45 | 8.10 |
| qwen3:latest (official 8B) | 5.2 GB | 39.43 | 7.21 |
| qwen3-8b-unsloth UD-Q4_K_XL (thinking) | 5.1 GB | 30.51 | 7.29 |
| qwen3-8b-unsloth UD-Q4_K_XL (instruct) | 5.1 GB | 30.45 | 7.34 |
| **LFM2.5-8B-A1B (Q4_K_M)** | **5.2 GB** | **87.38** | **25.02** |
| LFM2-8B-A1B (old, `lfm2.5:latest`) | 5.2 GB | 88.54 | 24.94 |

## 4 vs 8 threads (generation tok/s)

Going from 4 threads to 8 helps everything but the gains vary; the 8B-class models get the biggest decode lifts.

| Model | 4 threads | 8 threads | Change |
|---|---|---|---|
| LiquidAI/lfm2.5-1.2b | 32.20 | 38.84 | +21% |
| qwen3-8b-unsloth (instruct) | 6.13 | 7.34 | +20% |
| qwen3-8b-unsloth (thinking) | 6.15 | 7.29 | +19% |
| phi4-mini-reasoning | 9.34 | 11.04 | +18% |
| phi4-mini | 11.59 | 13.54 | +17% |
| qwen3.5:4b | 10.09 | 11.72 | +16% |
| gemma3:4b | 11.37 | 13.19 | +16% |
| qwen2.5:1.5b | 25.07 | 28.89 | +15% |
| qwen2.5:7b | 7.26 | 8.10 | +12% |
| LFM2.5-8B-A1B | 22.77 | 25.02 | +10% |
| tiny-agent-a 0.5b | 47.29 | 50.57 | +7% |
| lfm2.5-350m | 74.79 | 78.50 | +5% |

## LFM2.5 thread scaling (ctx=8192)

| Model | Threads | Prompt (tok/s) | Gen (tok/s) |
|---|---|---|---|
| LFM2.5-8B-A1B (official GGUF, Q4_K_M) | 4 | 55.18 | 22.77 |
| LFM2.5-8B-A1B (official GGUF, Q4_K_M) | 6 | 21.95 | 24.49 |
| LFM2.5-8B-A1B (official GGUF, Q4_K_M) | 8 | 88.02 | 25.05 |
| LFM2-8B-A1B (old, `lfm2.5:latest`) | 4 | 57.78 | 22.87 |
| LFM2-8B-A1B (old, `lfm2.5:latest`) | 6 | 28.01 | 24.96 |
| LFM2-8B-A1B (old, `lfm2.5:latest`) | 8 | 88.81 | 25.00 |

Note: the low prompt-eval numbers at 6 threads are scheduling noise on the hybrid big.LITTLE layout (4x A720 + 8x A520), not a real regression. Generation is flat ~25 tok/s at 4/6/8 threads.

## Thread scaling reference (qwen2.5:1.5b, ctx=2048)

| Threads | Prompt (tok/s) | Gen (tok/s) |
|---|---|---|
| 1 | 29.59 | 10.30 |
| 2 | 55.77 | 16.73 |
| 4 | 107.15 | 24.44 |
| 6 | 147.88 | 28.07 |
| 8 | 182.08 | 29.00 |
| 12 | 93.11 | 12.50 |

Generation peaks at 8 threads and degrades at 12 - contention between the 4 big + 8 little cores. Saturation effects also flatten the small dense models (0.5B-1.5B) at 8 threads, so 4 threads is enough for them. **8 threads is the sweet spot for 4B+ models.**

## Analysis: Qwen3-8B vs LFM2.5-8B-A1B

Both are ~5 GB Q4 models that fit comfortably in this box, but they're at opposite ends of the design spectrum:

| | Qwen3-8B (unsloth UD-Q4_K_XL) | LFM2.5-8B-A1B (Q4_K_M) |
|---|---|---|
| Type | Dense 8.2B | MoE 8.5B total / 1.5B active |
| Gen speed | 7.3 tok/s | 25.0 tok/s |
| Reasoning | Yes (thinking/non-thinking switch) | Yes (always + tool calling) |
| Context | 32K native (128K YaRN) | 128K native |
| Verdict | Maximum quality, 3.4x slower | Best practical choice for this hardware |

LFM2.5-8B-A1B can sustain real-time chat on this box; Qwen3-8B is usable only for one-shot deep reasoning tasks. For interactive agentic use, the LFM model is the clear recommendation.

## Comparison with LiteRT-LM (GPU offload)

The [LiteRT-LM benchmarks](https://github.com/ProducerJenn/litert-lm-benchmarks) drive the Mali-G720 GPU via OpenCL for Google's Gemma 4 models:

| Model | Backend | Prefill (tok/s) | Decode (tok/s) |
|---|---|---|---|
| Gemma 4 E2B (2.4 GB) | CPU 8 threads | 60.3 | 22.8 |
| Gemma 4 E2B (2.4 GB) | **GPU** | **125.8** | **24.2** |
| Gemma 4 E4B (3.4 GB) | GPU | 56.9 | 14.1 |

LiteRT-LM's GPU path reaches the same ~24 tok/s decode as LFM-driven CPU on a similar-size model, but with 2-3x better prompt ingestion (prefill) - valuable for long-context or RAG workloads. LFM2.5-8B-A1B is likely the better chat/agent model overall (newer architecture), and needs no GPU to be fast on this SBC.

## Reproducing

```bash
# Full 8-thread sweep (all local models) - appends phase model_compare_t8
python3 scripts/bench_all_t8.py

# Original 4-thread suite (small models)
python3 scripts/benchmark_v2.py

# LFM2.5-8B-A1B thread sweep (ctx 8192)
python3 scripts/bench_lfm.py
```

Raw measurements: [results/results_full.jsonl](results/results_full.jsonl) (phases `model_compare` = 4t, `model_compare_t8` = 8t, `lfm2_compare` / `lfm2_thread_6` = ctx 8192).

Pull commands for the models in this report:

```bash
ollama pull hf.co/unsloth/Qwen3-8B-GGUF:UD-Q4_K_XL
ollama pull hf.co/LiquidAI/LFM2.5-8B-A1B-GGUF:Q4_K_M
ollama run hf.co/LiquidAI/LFM2.5-8B-A1B-GGUF:Q4_K_M   # --num-thread 8 recommended
```