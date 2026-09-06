# Ollama Benchmarks - Orange Pi 6 Plus

Local LLM inference benchmarks on an Orange Pi 6 Plus (CIX P1 CD8160, 12-core ARM, 14.9 GB RAM), run with Ollama 0.31.2.

## Methodology

- Measured via the Ollama `/api/generate` endpoint.
- **Comparison suite**: `num_thread=8` (measured sweet spot), `num_ctx=2048`, prompt = "Explain the theory of relativity in simple terms, covering both special and general relativity. Include examples.", capped at 512 decode tokens.
- **TTFT measurement**: Model warmed with a 4-token preload first; then the prompt streamed to capture time-to-first-token on a loaded model (no load overhead). Measured with curl + python line-by-line timing.
- `prefill_tps` = prompt ingest tok/s; `eval_rate` = generation tok/s; `TTFT` = warm time to first token (ms).
- An earlier suite ran at `num_thread=4` (preserved in `results_full.jsonl` phase `model_compare`).

## Model comparison (threads=8, ctx=2048, warm)

| Model | Size | Max ctx | RAM @2K | Prefill (tok/s) | Gen (tok/s) | TTFT (ms) |
|---|---|---:|---:|---:|---:|---:|
| LiquidAI/lfm2.5-350m | 379 MB | 128K | 510 MB | 739.57 | 76.47 | 253 |
| driaforall/tiny-agent-a 0.5b | 531 MB | 32K | 760 MB | 532.65 | 54.10 | 479 |
| qwen2.5:1.5b | 986 MB | 32K | 1.4 GB | 304.80 | 28.57 | 615 |
| qwen3.5:0.8b | 1.0 GB | 262K | 1.4 GB | 254.58 | 31.27 | 919 |
| LiquidAI/lfm2.5-1.2b | 730 MB | 128K | 929 MB | 233.24 | 39.23 | 468 |
| phi4-mini-reasoning | 3.2 GB | 128K | 4.3 GB | 126.15 | 11.10 | 1029 |
| phi4-mini | 2.5 GB | 128K | 3.6 GB | 77.23 | 13.05 | 839 |
| gemma3:4b | 3.3 GB | 128K | 3.6 GB | 73.24 | 13.10 | 1260 |
| qwen2.5:7b | 4.7 GB | 32K | 5.1 GB | 71.73 | 8.16 | 1228 |
| qwen3.5:4b | 3.4 GB | 262K | 3.7 GB | 57.21 | 11.67 | 1327 |
| qwen3:latest (official 8B) | 5.2 GB | 40K | 5.9 GB | 39.55 | 7.27 | 1182 |
| qwen3-8b-unsloth (instruct) | 5.1 GB | 40K | 5.8 GB | 30.50 | 7.34 | 1466 |
| qwen3-8b-unsloth (thinking) | 5.1 GB | 40K | 5.8 GB | 30.23 | 7.31 | 1317 |
| **LFM2.5-8B-A1B (Q4_K_M)** | **5.2 GB** | **128K** | **5.4 GB** | **88.56** | **24.62** | **804** |
| LFM2-8B-A1B (old `lfm2.5:latest`) | 5.2 GB | 128K | 5.4 GB | 88.80 | 24.50 | 850 |

RAM @2K = resident memory at 2048 ctx from `ollama ps` (includes weights + KV cache). Test ctx = 2048 (8192 for LFM scaling, 16384 for the context comparison). Max ctx = model-declared native ceiling; Ollama runtime default is 4096.

## 4 vs 8 threads

| Model | 4t gen | 8t gen | Δ |
|---|---:|---:|---:|
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

| Threads | Prefill (tok/s) | Gen (tok/s) | TTFT (ms) |
|---:|---:|---:|---:|
| 4 | 55.18 | 22.77 | ~2100 (cold) |
| 6 | 21.95 | 24.49 | — |
| 8 | 88.02 | 25.05 | 804 (warm) |

Note: the 6-thread low-prefill figures are scheduling noise on the big.LITTLE hybrid layout (4x A720 + 8x A520), not a regression. Generation is flat ~25 tok/s at 4/6/8 threads.

## Thread scaling reference (qwen2.5:1.5b, ctx=2048)

| Threads | Prefill (tok/s) | Gen (tok/s) |
|---:|---:|---:|
| 1 | 29.59 | 10.30 |
| 2 | 55.77 | 16.73 |
| 4 | 107.15 | 24.44 |
| 6 | 147.88 | 28.07 |
| 8 | 182.08 | 29.00 |
| 12 | 93.11 | 12.50 |

Generation peaks at 8 threads; at 12, contention between the 4 big + 8 little cores makes it worse. **8 threads is the sweet spot for 4B+ models.**

## Higher-context comparison (16K vs 2K, 8 threads)

All models re-measured with tuned higher-context varients (16K; phi4-mini at 8K since its KV cache is huge). Same prompt, 256 decode tokens:

| Model | ctx | RAM | Prefill (tok/s) | Gen (tok/s) | TTFT (ms) |
|---|---|---:|---:|---:|---:|
| LiquidAI/lfm2.5-1.2b | 2048 | 929 MB | 233.24 | 39.23 | 468 |
| LiquidAI/lfm2.5-1.2b | 16384 | 1.2 GB | 235.08 | 39.79 | 431 |
| LFM2.5-8B-A1B (Q4_K_M) | 2048 | 5.4 GB | 88.56 | 24.62 | 804 |
| LFM2.5-8B-A1B (Q4_K_M) | 16384 | 5.5 GB | 88.32 | 24.51 | 951 |
| phi4-mini | 2048 | 3.6 GB | 77.23 | 13.05 | 839 |
| phi4-mini | 8192 | 5.3 GB | 78.22 | 13.59 | 869 |
| gemma3:4b | 2048 | 3.6 GB | 73.24 | 13.10 | 1260 |
| gemma3:4b | 16384 | 3.9 GB | 68.73 | 13.00 | 1335 |
| qwen2.5:7b | 2048 | 5.1 GB | 71.73 | 8.16 | 1228 |
| qwen2.5:7b | 16384 | 6.9 GB | 71.15 | 8.05 | 1209 |
| qwen3.5:4b | 2048 | 3.7 GB | 57.21 | 11.67 | 1327 |
| qwen3.5:4b | 16384 | 4.2 GB | 56.18 | 11.47 | 1325 |
| qwen3:latest (official 8B) | 2048 | 5.9 GB | 39.55 | 7.27 | 1182 |
| qwen3:latest (official 8B) | 16384 | 10 GB | 39.46 | 7.37 | 1197 |
| qwen3-8b-unsloth (instruct) | 2048 | 5.8 GB | 30.50 | 7.34 | 1466 |
| qwen3-8b-unsloth (instruct) | 16384 | 10 GB | 30.48 | 7.43 | 1496 |

**Context size is a RAM cost, not a speed cost.** Gen and prefill rates are within noise between 2K and 16K; TTFT rises only slightly (bigger KV buffer init). You pay for longer context in RAM, not throughput.

## Context sizing vs RAM (ollama `ps`)

| Model | ctx | Ram used |
|---|---|---:|
| LiquidAI/lfm2.5-1.2b | 16K | 1.2 GB |
| gemma3:4b | 16K | 3.9 GB |
| qwen3.5:4b | 16K | 4.2 GB |
| phi4-mini | 8K | 5.3 GB |
| LFM2.5-8B-A1B | 16K | ~5.5 GB |
| LFM2.5-8B-A1B | 32K | 5.9 GB |
| LFM2.5-8B-A1B | 64K | 6.7 GB |
| LFM2.5-8B-A1B | 128K (max) | 7.7 GB |
| qwen2.5:7b | 16K | 6.9 GB |
| qwen3 (official 8B) | 16K | 10 GB |
| Qwen3-8B unsloth | 16K | 10 GB |

Notes:
- `gemma3:4b`, `qwen3.5:4b`, `qwen2.5:7b` fail to load at 32K on this 14.9 GB box — 16K is their ceiling here.
- `phi4-mini` is the KV hog (32 attention heads): ~11 GB at 32K, so cap it at 8K.
- `qwen3:latest`/unsloth at 16K use **10 GB** — fits but leaves little headroom.
- LFM2.5-8B-A1B's KV is efficient (2 qwen-style KV heads): runs at **full 128K on 7.7 GB**.

## Analysis: Qwen3-8B vs LFM2.5-8B-A1B

| | Qwen3-8B (unsloth UD-Q4_K_XL) | LFM2.5-8B-A1B (Q4_K_M) |
|---|---|---|
| Type | Dense 8.2B | MoE 8.5B total / 1.5B active |
| Gen speed | 7.3 tok/s | 24.6 tok/s |
| TTFT (warm) | 1466 ms | 804 ms |
| Prefill | 30.5 tok/s | 88.6 tok/s |
| Reasoning | Yes (thinking/non-thinking switch) | Yes (always + tool calling) |
| Max ctx | 32K native (128K YaRN) | 128K native |
| Verdict | Maximum quality, 3.4x slower gen, 1.8x slower TTFT | Best practical choice for this hardware |

LFM2.5-8B-A1B delivers interactive-speed chat with sub-second TTFT; Qwen3-8B is usable for one-shot deep reasoning where latency matters less.

## Comparison with LiteRT-LM (GPU offload)

The [LiteRT-LM benchmarks](https://github.com/ProducerJenn/litert-lm-benchmarks) drive the Mali-G720 GPU via OpenCL for Google's Gemma 4 models:

| Model | Backend | Prefill (tok/s) | Decode (tok/s) |
|---|---|---:|---:|
| Gemma 4 E2B (2.4 GB) | CPU 8 threads | 60.3 | 22.8 |
| Gemma 4 E2B (2.4 GB) | **GPU** | **125.8** | **24.2** |
| Gemma 4 E4B (3.4 GB) | GPU | 56.9 | 14.1 |

LiteRT-LM's GPU path reaches the same ~24 tok/s decode as LFM2.5-8B-A1B on CPU, but with 2-3x better prefill (valuable for long-context/RAG workloads). LFM2.5-8B-A1B is likely the better chat/agent model overall (newer architecture) and needs no GPU to be fast on this SBC.

## Reproducing

```bash
# Full 8-thread sweep with TTFT + prefill
python3 scripts/bench_ttft.py

# 8-thread gen-only sweep (no streaming, faster)
python3 scripts/bench_all_t8.py

# LFM2.5-8B-A1B thread sweep (ctx 8192)
python3 scripts/bench_lfm.py
```

Raw measurements: [results/results_full.jsonl](results/results_full.jsonl) (phases `model_compare` = 4t, `model_compare_t8` = 8t gen-only, `model_ttft_t8` = 8t TTFT+prefill).

Pull commands for the models in this report:

```bash
ollama pull hf.co/unsloth/Qwen3-8B-GGUF:UD-Q4_K_XL
ollama pull hf.co/LiquidAI/LFM2.5-8B-A1B-GGUF:Q4_K_M
ollama run hf.co/LiquidAI/LFM2.5-8B-A1B-GGUF:Q4_K_M   # --num-thread 8 recommended
```