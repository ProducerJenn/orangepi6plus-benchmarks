# Ollama Benchmarks - Orange Pi 6 Plus

Local LLM inference benchmarks on an Orange Pi 6 Plus (CIX P1 CD8160, 12-core ARM, 14.9 GB RAM), run with Ollama 0.31.2.

## Methodology

- Measured via the Ollama `/api/generate` endpoint.
- **Comparison suite**: `num_thread=8` (measured sweet spot), `num_ctx=2048`, prompt = "Explain the theory of relativity in simple terms, covering both special and general relativity. Include examples.", capped at 512 decode tokens.
- **TTFT measurement**: Model warmed with a 4-token preload first; then the prompt streamed to capture time-to-first-token on a loaded model (no load overhead). Measured with curl + python line-by-line timing.
- `prefill_tps` = prompt ingest tok/s; `eval_rate` = generation tok/s; `TTFT` = warm time to first token (ms).
- An earlier suite ran at `num_thread=4` (preserved in `results_full.jsonl` phase `model_compare`).

## Model comparison (threads=8, ctx=2048, warm)

| Model | Size | Max ctx | Prefill (tok/s) | Gen (tok/s) | TTFT (ms) |
|---|---|---:|---:|---:|---:|
| LiquidAI/lfm2.5-350m | 379 MB | 128K | 739.57 | 76.47 | 253 |
| driaforall/tiny-agent-a 0.5b | 531 MB | 32K | 532.65 | 54.10 | 479 |
| qwen2.5:1.5b | 986 MB | 32K | 304.80 | 28.57 | 615 |
| qwen3.5:0.8b | 1.0 GB | 262K | 254.58 | 31.27 | 919 |
| LiquidAI/lfm2.5-1.2b | 730 MB | 128K | 233.24 | 39.23 | 468 |
| phi4-mini-reasoning | 3.2 GB | 128K | 126.15 | 11.10 | 1029 |
| phi4-mini | 2.5 GB | 128K | 77.23 | 13.05 | 839 |
| gemma3:4b | 3.3 GB | 128K | 73.24 | 13.10 | 1260 |
| qwen2.5:7b | 4.7 GB | 32K | 71.73 | 8.16 | 1228 |
| qwen3.5:4b | 3.4 GB | 262K | 57.21 | 11.67 | 1327 |
| qwen3:latest (official 8B) | 5.2 GB | 40K | 39.55 | 7.27 | 1182 |
| qwen3-8b-unsloth (instruct) | 5.1 GB | 40K | 30.50 | 7.34 | 1466 |
| qwen3-8b-unsloth (thinking) | 5.1 GB | 40K | 30.23 | 7.31 | 1317 |
| **LFM2.5-8B-A1B (Q4_K_M)** | **5.2 GB** | **128K** | **88.56** | **24.62** | **804** |
| LFM2-8B-A1B (old `lfm2.5:latest`) | 5.2 GB | 128K | 88.80 | 24.50 | 850 |

Test ctx = 2048 (8192 for LFM thread scaling). Max ctx = model-declared native ceiling; Ollama runtime default is 4096 unless overridden. (GGUF metadata). Benchmarks ran at 2048/8192; KV cache for full native context wouldn't fit this 14.9 GB box on the largest models.

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