#!/bin/bash
set -euo pipefail

RESULTS_DIR="/tmp/opencode/results"
mkdir -p "$RESULTS_DIR"

# Test prompt for generation benchmarking
GEN_PROMPT="Explain the theory of relativity in simple terms, covering both special and general relativity. Include examples."
# Test prompt for prompt processing (longer input)
PROCESS_PROMPT="$(printf '%.0s-' {1..2000})\nSummarize the key differences between TCP and UDP protocols, including their use cases, reliability, speed, and overhead."

RESULTS_CSV="$RESULTS_DIR/benchmark_results.csv"
echo "model,size_mb,threads,context_length,pp_tokens_per_sec,pg_tokens_per_sec,total_time_sec,prompt_eval_count,eval_count" > "$RESULTS_CSV"

# Models to benchmark (name, size approximation in MB)
declare -a MODELS=(
  "driaforall/tiny-agent-a:0.5b|531"
  "LiquidAI/lfm2.5-350m:latest|379"
  "qwen3.5:0.8b|1000"
  "qwen2.5:1.5b|986"
  "LiquidAI/lfm2.5-1.2b-instruct:latest|730"
  "phi4-mini:latest|2500"
  "phi4-mini-reasoning:latest|3200"
  "qwen3.5:4b|3400"
  "gemma3:4b|3300"
  "qwen2.5:7b|4700"
  "qwen3:latest|5200"
)

# Thread configurations to test
THREAD_CONFIGS=(1 2 4 6 8 12)

# Context lengths
CONTEXT_LENGTHS=(2048 4096 8192)

run_benchmark() {
  local model="$1"
  local threads="$2"
  local ctx="$3"

  export OLLAMA_NUM_PARALLEL=1
  export OLLAMA_MAX_LOADED_MODELS=1
  export OLLAMA_NUM_THREADS="$threads"

  local model_safe
  model_safe=$(echo "$model" | tr '/:' '__')

  local outfile="$RESULTS_DIR/${model_safe}_t${threads}_ctx${ctx}.json"

  # Warm up - unload first
  ollama stop "$model" 2>/dev/null || true
  sleep 1

  # Run benchmark with JSON output
  local start_time
  start_time=$(date +%s)

  # Generation benchmark (output speed)
  local result
  result=$(timeout 120 ollama run "$model" --verbose "$GEN_PROMPT" 2>&1 || echo "TIMEOUT")

  local end_time
  end_time=$(date +%s)
  local total_time=$((end_time - start_time))

  # Extract timing info from verbose output (last few lines)
  local pp_speed="N/A"
  local pg_speed="N/A"
  local prompt_eval_count="N/A"
  local eval_count="N/A"

  # Parse the verbose timing output
  if echo "$result" | grep -q "eval rate"; then
    # Try to extract prompt eval rate
    pp_speed=$(echo "$result" | grep -oP 'prompt eval rate\s+\K[0-9.]+(?= tokens/s)' || echo "N/A")
    # Try to extract generation eval rate
    pg_speed=$(echo "$result" | grep -oP '\d+ tokens/s' | tail -1 | grep -oP '[0-9.]+' || echo "N/A")
    prompt_eval_count=$(echo "$result" | grep -oP 'prompt eval count\s+\K[0-9]+' || echo "N/A")
    eval_count=$(echo "$result" | grep -oP 'eval count\s+\K[0-9]+' || echo "N/A")
  fi

  echo "${model},${model_safe##*_},${threads},${ctx},${pp_speed},${pg_speed},${total_time},${prompt_eval_count},${eval_count}" >> "$RESULTS_CSV"
  echo "  DONE: model=$model threads=$threads ctx=$ctx pp=$pp_speed pg=$pg_speed time=${total_time}s"

  # Unload model
  ollama stop "$model" 2>/dev/null || true
  sleep 2
}

echo "=== Ollama CPU Benchmark ==="
echo "Date: $(date)"
echo "System: $(uname -a)"
echo "CPU: $(lscpu | grep 'Model name' | head -1)"
echo "RAM: $(free -h | awk '/Mem:/{print $2}')"
echo ""

# Phase 1: Test all models with 4 threads at default context
echo "--- Phase 1: Model comparison (4 threads, default context) ---"
for model_entry in "${MODELS[@]}"; do
  IFS='|' read -r model size <<< "$model_entry"
  echo "Testing: $model (${size} MB)"
  run_benchmark "$model" 4 2048
done

# Phase 2: Thread scaling test with a few representative models
echo ""
echo "--- Phase 2: Thread scaling (qwen2.5:1.5b) ---"
for threads in "${THREAD_CONFIGS[@]}"; do
  echo "Testing threads=$threads"
  run_benchmark "qwen2.5:1.5b" "$threads" 2048
done

echo ""
echo "--- Phase 2b: Thread scaling (qwen3.5:4b) ---"
for threads in "${THREAD_CONFIGS[@]}"; do
  echo "Testing threads=$threads"
  run_benchmark "qwen3.5:4b" "$threads" 2048
done

echo ""
echo "--- Phase 2c: Thread scaling (phi4-mini) ---"
for threads in "${THREAD_CONFIGS[@]}"; do
  echo "Testing threads=$threads"
  run_benchmark "phi4-mini:latest" "$threads" 2048
done

# Phase 3: Context length impact
echo ""
echo "--- Phase 3: Context length impact (qwen2.5:1.5b, 4 threads) ---"
for ctx in "${CONTEXT_LENGTHS[@]}"; do
  echo "Testing context=$ctx"
  run_benchmark "qwen2.5:1.5b" 4 "$ctx"
done

echo ""
echo "=== Benchmark Complete ==="
echo "Results saved to: $RESULTS_CSV"
cat "$RESULTS_CSV"
