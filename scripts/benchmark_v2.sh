#!/bin/bash
set -euo pipefail

RESULTS_DIR="/tmp/opencode/results"
mkdir -p "$RESULTS_DIR"

RESULTS_JSON="$RESULTS_DIR/results.jsonl"
> "$RESULTS_JSON"

GEN_PROMPT="Explain the theory of relativity in simple terms, covering both special and general relativity. Include examples."

# Models to benchmark
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

THREAD_CONFIGS=(1 2 4 6 8 12)
CONTEXT_LENGTHS=(2048 4096 8192)

run_api_bench() {
  local model="$1"
  local threads="$2"
  local ctx="$3"
  local phase="$4"
  local prompt="${5:-$GEN_PROMPT}"

  # Unload model first
  curl -s http://localhost:11434/api/generate -d "{\"model\":\"$model\",\"keep_alive\":0}" > /dev/null 2>&1 || true
  sleep 1

  echo -n "  [$phase] $model threads=$threads ctx=$ctx ... "

  local response
  response=$(curl -s --max-time 180 http://localhost:11434/api/generate -d "{
    \"model\": \"$model\",
    \"prompt\": $(python3 -c "import json; print(json.dumps('$prompt'))"),
    \"options\": {\"num_ctx\": $ctx, \"num_thread\": $threads},
    \"stream\": false
  }")

  if echo "$response" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
    python3 -c "
import json, sys
r = json.loads('''$response''')
entry = {
  'model': '$model',
  'phase': '$phase',
  'threads': $threads,
  'context_length': $ctx,
  'prompt_eval_count': r.get('prompt_eval_count', 0),
  'prompt_eval_duration_ms': r.get('prompt_eval_duration', 0) / 1e6,
  'prompt_eval_rate': round(r.get('prompt_eval_count', 0) / (r.get('prompt_eval_duration', 1) / 1e9), 2) if r.get('prompt_eval_duration', 0) > 0 else 0,
  'eval_count': r.get('eval_count', 0),
  'eval_duration_ms': r.get('eval_duration', 0) / 1e6,
  'eval_rate': round(r.get('eval_count', 0) / (r.get('eval_duration', 1) / 1e9), 2) if r.get('eval_duration', 0) > 0 else 0,
  'total_duration_ms': r.get('total_duration', 0) / 1e6,
  'load_duration_ms': r.get('load_duration', 0) / 1e6,
  'response_length': len(r.get('response', ''))
}
print(json.dumps(entry))
" >> "$RESULTS_JSON"
    local pp pg
    pp=$(echo "$response" | python3 -c "import sys,json; r=json.load(sys.stdin); print(round(r.get('prompt_eval_count',0)/(r.get('prompt_eval_duration',1)/1e9),1) if r.get('prompt_eval_duration',0)>0 else 0)")
    pg=$(echo "$response" | python3 -c "import sys,json; r=json.load(sys.stdin); print(round(r.get('eval_count',0)/(r.get('eval_duration',1)/1e9),1) if r.get('eval_duration',0)>0 else 0)")
    echo "pp=${pp} tok/s, pg=${pg} tok/s"
  else
    echo "FAILED"
    echo "{\"model\":\"$model\",\"phase\":\"$phase\",\"threads\":$threads,\"context_length\":$ctx,\"error\":true}" >> "$RESULTS_JSON"
  fi

  # Unload
  curl -s http://localhost:11434/api/generate -d "{\"model\":\"$model\",\"keep_alive\":0}" > /dev/null 2>&1 || true
  sleep 2
}

echo "========================================"
echo "  Ollama CPU Benchmark Suite"
echo "  $(date)"
echo "  $(lscpu | grep 'Model name' | sed 's/Model name:\s*//')"
echo "  $(nproc) CPUs, $(free -h | awk '/Mem:/{print $2}') RAM"
echo "  Ollama $(ollama --version)"
echo "========================================"
echo ""

# Phase 1: All models, fixed threads=4
echo ">>> Phase 1: Model Comparison (4 threads, 2048 context)"
echo "---"
for entry in "${MODELS[@]}"; do
  IFS='|' read -r model size <<< "$entry"
  run_api_bench "$model" 4 2048 "model_compare"
done
echo ""

# Phase 2: Thread scaling
echo ">>> Phase 2: Thread Scaling (qwen2.5:1.5b, 2048 context)"
echo "---"
for t in "${THREAD_CONFIGS[@]}"; do
  run_api_bench "qwen2.5:1.5b" "$t" 2048 "thread_scaling_1.5b"
done

echo ""
echo ">>> Phase 2b: Thread Scaling (qwen3.5:4b, 2048 context)"
echo "---"
for t in "${THREAD_CONFIGS[@]}"; do
  run_api_bench "qwen3.5:4b" "$t" 2048 "thread_scaling_4b"
done

echo ""
echo ">>> Phase 2c: Thread Scaling (phi4-mini, 2048 context)"
echo "---"
for t in "${THREAD_CONFIGS[@]}"; do
  run_api_bench "phi4-mini:latest" "$t" 2048 "thread_scaling_phi4"
done
echo ""

# Phase 3: Context length impact
echo ">>> Phase 3: Context Length Impact (qwen2.5:1.5b, 4 threads)"
echo "---"
for c in "${CONTEXT_LENGTHS[@]}"; do
  run_api_bench "qwen2.5:1.5b" 4 "$c" "ctx_impact_1.5b"
done

echo ""
echo ">>> Phase 3b: Context Length Impact (qwen3.5:4b, 4 threads)"
echo "---"
for c in "${CONTEXT_LENGTHS[@]}"; do
  run_api_bench "qwen3.5:4b" 4 "$c" "ctx_impact_4b"
done
echo ""

echo "========================================"
echo "  Benchmark Complete"
echo "  Results: $RESULTS_JSON"
echo "========================================"
