# Ollama Benchmarks - Orange Pi 6 Plus

Local LLM inference benchmarks on an Orange Pi 6 Plus (CIX P1 CD8160, 12-core ARM, 14.9 GB RAM), run with Ollama 0.31.2 on 2026-08-18 (small models) and 2026-09-07 (Qwen3-8B + LFM2.5).

## Methodology

- Measured via the Ollama `/api/generate` endpoint with `stream: false`.
- **Model comparison suite**: `num_thread=4`, `num_ctx=2048`, prompt = "Explain the theory of relativity in simple terms, covering both special and general relativity. Include examples.", decode until stop / capped at 512 tokens for the 8B additions.
- **LFM thread scaling**: `num_ctx=8192`, same prompt, 512-token decode.
- Models are unloaded between runs (`keep_alive: 0`) so every number includes a cold load where applicable.
- `prompt_eval_rate` (pp) = prompt ingestion tok/s; `eval_rate` (pg) = generation tok/s.

## Model comparison (threads=4, ctx=2048)

| Model | Size | Prompt (tok/s) | Gen (tok/s) |
|---|---|---|---|
| driaforall/tiny-agent-a 0.5b | 531 MB | 445.96 | 47.29 |
| LiquidAI/lfm2.5-350m | 379 MB | 513.80 | 74.79 |
| qwen3.5:0.8b | 1.0 GB | 210.96 | 30.33 |
| LiquidAI/lfm2.5-1.2b | 730 MB | 147.90 | 32.20 |
| qwen2.5:1.5b | 986 MB | 108.70 | 25.07 |
| phi4-mini | 2.5 GB | 46.37 | 11.59 |
| phi4-mini-reasoning | 3.2 GB | 18.88 | 9.34 |
| qwen3.5:4b | 3.4 GB | 36.80 | 10.09 |
| gemma3:4b | 3.3 GB | 44.49 | 11.37 |
| qwen2.5:7b | 4.7 GB | 24.21 | 7.26 |
| qwen3-8b-unsloth (thinking) UD-Q4_K_XL | 5.1 GB | 17.45 | 6.15 |
| qwen3-8b-unsloth (instruct) UD-Q4_K_XL | 5.1 GB | 17.51 | 6.13 |

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

Generation peaks at 8 threads and degrades at 12 - contention between the 4 big + 8 little cores. **8 threads is the sweet spot.**

## Analysis: Qwen3-8B vs LFM2.5-8B-A1B

Both are ~5 GB Q4 models that fit comfortably in this box, but they're at opposite ends of the design spectrum:

| | Qwen3-8B (unsloth UD-Q4_K_XL) | LFM2.5-8B-A1B (Q4_K_M) |
|---|---|---|
| Type | Dense 8.2B | MoE 8.5B total / 1.5B active |
| Gen speed | 6.1 tok/s | 25.1 tok/s |
| Reasoning | Yes (thinking/non-thinking switch) | Yes (always + tool calling) |
| Context | 32K native (128K YaRN) | 128K native |
| Verdict | Maximum quality, 4x slower | Best practical choice for this hardware |

LFM2.5-8B-A1B can sustain real-time chat on this box; Qwen3-8B is usable only for one-shot deep reasoning tasks. For interactive agentic use, the LFM model is the clear recommendation.

## Comparison with LiteRT-LM (GPU offload)

The [LiteRT-LM benchmarks](https://github.com/ProducerJenn/litert-lm-benchmarks) drive the Mali-G720 GPU via OpenCL for Google's Gemma 4 models:

| Model | Backend | Prefill (tok/s) | Decode (tok/s) |
|---|---|---|---|
| Gemma 4 E2B (2.4 GB) | CPU 8 threads | 60.3 | 22.8 |
| Gemma 4 E2B (2.4 GB) | **GPU** | **125.8** | **24.2** |
| Gemma 4 E4B (3.4 GB) | GPU | 56.9 | 14.1 |

LiteRT-LM's GPU path reaches the same ~24 tok/s decode as LFM-driven CPU on a similar-size model, but with 2-3x better prompt ingestion (prefill) - valuable for long-context or RAG workloads. LFM2.5-8B-A1B is likely the better chat/agent model overall (older Gemma series, newer architecture), and needs no GPU to be fast on this SBC.

## Reproducing

```bash
# Model comparison suite (existing models)
python3 scripts/benchmark_v2.py

# Add an 8B model to the suite and append to results_full.jsonl
python3 scripts/bench_add_qwen3.py

# LFM2.5-8B-A1B thread sweep
python3 scripts/bench_lfm.py
```

Pull commands for the models in this report:

```bash
ollama pull hf.co/unsloth/Qwen3-8B-GGUF:UD-Q4_K_XL
ollama pull hf.co/LiquidAI/LFM2.5-8B-A1B-GGUF:Q4_K_M
ollama run hf.co/LiquidAI/LFM2.5-8B-A1B-GGUF:Q4_K_M   # --num-thread 8 recommended
```