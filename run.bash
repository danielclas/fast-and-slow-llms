# =============================================================================
# LLM Agents Runner Configuration
# =============================================================================
# Edit the parameters below and then just run: ./run.bash

# Required Parameters
DATASET="dataset/dataset_inputs_150.jsonl"  # Path to input JSONL dataset
RUN_DIR="runs/intelligent_routing_0.5_confidence_$(date +%Y%m%d_%H%M%S)"   # Output directory (auto-timestamped)

# Model Configuration
S1_MODEL="gpt-4o-mini"      # Model for S1 agent (fast/cheap)
S2_MODEL="gpt-5-2025-08-07"           # Model for S2 agent (deliberative/expensive)

# Routing Configuration
AGENT=""                    # Force specific agent: "S1", "S2", or "" for intelligent routing
CONFIDENCE_THRESHOLD=0.7    # Confidence threshold for routing decisions (0.0-1.0)

# =============================================================================
# Script Execution 
# =============================================================================

set -e  # Exit on any error

echo "🚀 Starting LLM Agents Run"
echo "=================================="
echo "Dataset: $DATASET"
echo "Output Dir: $RUN_DIR"
echo "S1 Model: $S1_MODEL"
echo "S2 Model: $S2_MODEL"
echo "Agent Override: ${AGENT:-"None (intelligent routing)"}"
echo "Confidence Threshold: $CONFIDENCE_THRESHOLD"
echo "=================================="

# Validate required files exist
if [[ ! -f "$DATASET" ]]; then
    echo "❌ Error: Dataset file not found: $DATASET"
    exit 1
fi

if [[ ! -f "runner.py" ]]; then
    echo "❌ Error: runner.py not found in current directory"
    exit 1
fi

# Build the command
CMD="python runner.py --dataset \"$DATASET\" --run-dir \"$RUN_DIR\""
CMD="$CMD --s1-model \"$S1_MODEL\" --s2-model \"$S2_MODEL\""
CMD="$CMD --confidence-threshold $CONFIDENCE_THRESHOLD"

# Add agent override if specified
if [[ -n "$AGENT" ]]; then
    CMD="$CMD --agent \"$AGENT\""
fi

echo "Running: $CMD"
echo ""

# Execute the command
eval $CMD

echo ""
echo "✅ Run completed! Results saved to: $RUN_DIR"
