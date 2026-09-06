# Ollama Benchmark Results - Orange Pi 6 Plus

## System Info

| Property | Value |
|----------|-------|
| CPU Model | CIX P1 CD8160 (Cortex-A720/A520) |
| CPU Count | 12 |
| RAM | 14.9 GB |
| Ollama Version | 0.31.2 |

---

## Model Comparison Results (8 threads, ctx 2048)

| Model | Size | Prompt Eval (tok/s) | Gen (tok/s) | Wall (s) | Response Length |
|-------|------|--------------------:|------------:|---------:|----------------|
| driaforall/tiny-agent-a 0.5b | 531 MB | 580.96 | 50.57 | 9.8 | 351 |
| LiquidAI/lfm2.5-350m | 379 MB | 739.73 | 78.50 | 4.5 | 205 |
| qwen3.5:0.8b | 1.0 GB | 251.80 | 31.84 | 21.9 | 512 |
| LiquidAI/lfm2.5-1.2b | 730 MB | 226.44 | 38.84 | 13.0 | 397 |
| qwen2.5:1.5b | 986 MB | 180.86 | 28.89 | 21.8 | 512 |
| phi4-mini | 2.5 GB | 79.19 | 13.54 | 34.6 | 338 |
| phi4-mini-reasoning | 3.2 GB | 65.08 | 11.04 | 55.7 | 512 |
| qwen3.5:4b | 3.4 GB | 57.02 | 11.72 | 53.2 | 512 |
| gemma3:4b | 3.3 GB | 72.06 | 13.19 | 48.8 | 512 |
| qwen2.5:7b | 4.7 GB | 41.45 | 8.10 | 75.7 | 512 |
| qwen3:latest (official 8B) | 5.2 GB | 39.43 | 7.21 | 84.9 | 512 |
| qwen3-8b-unsloth UD-Q4_K_XL (thinking) | 5.1 GB | 30.51 | 7.29 | 81.7 | 512 |
| qwen3-8b-unsloth UD-Q4_K_XL (instruct) | 5.1 GB | 30.45 | 7.34 | 83.6 | 512 |
| **LFM2.5-8B-A1B (Q4_K_M)** | **5.2 GB** | **87.38** | **25.02** | **31.8** | **512** |
| LFM2-8B-A1B (old, lfm2.5:latest) | 5.2 GB | 88.54 | 24.94 | 31.0 | 512 |

---

## 4 vs 8 Threads (generation tok/s)

| Model | 4t | 8t | Change |
|-------|---:|---:|-------:|
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

---

## Thread Scaling Test (qwen2.5:1.5b)

| Threads | Prompt Eval (tok/s) | Gen (tok/s) |
|--------:|--------------------:|------------:|
| 1 | 29.59 | 10.30 |
| 2 | 55.77 | 16.73 |
| 4 | 107.15 | 24.44 |
| 6 | 147.88 | 28.07 |
| 8 | 182.08 | 29.00 |
| 12 | 93.11 | 12.50 |

---

## Key Findings (8 threads)

1. **Best Overall**: LFM2.5-8B-A1B Q4_K_M - 25 tok/s reasoning MoE, best quality-per-speed on this board
2. **Best Eval Rate**: LiquidAI/lfm2.5-350m at 78.5 tok/s
3. **Thread Scaling**: Performance peaks at 8 threads and degrades at 12 (big.LITTLE contention)
4. **8B-class decode**: Qwen3-8B ~7.3 tok/s (3.4x slower than LFM2.5-8B-A1B)
5. **Small dense models** (0.5-1.5B) saturate by 4-6 threads; 8 threads only matters for 4B+ models