#!/bin/bash

# run_simulation.sh - Sequential simulation launcher with automatic iteration numbering
# 
# WORKFLOW:
# 1. Execute setFields in root directory (initialize phase field)
# 2. Create results/N/ directory with next iteration number
# 3. Copy 0/, constant/, system/ to results/N/
# 4. Run foamRun solver in results/N/
# 5. Log all output to results/N/run.log
#
# KEY: setFields modifies root 0/alpha.water, then case is copied with modifications
#
# Usage:
#   ./run_simulation.sh              # Runs next iteration (auto-numbered)
#   ./run_simulation.sh -n 42        # Force iteration number (for testing)

set -e  # Exit on error

CASE_ROOT=$(cd "$(dirname "$0")" && pwd)
cd "$CASE_ROOT"

# Parse arguments
FORCE_NUM=""
if [[ "$1" == "-n" && -n "$2" ]]; then
    FORCE_NUM="$2"
fi

# Find next iteration number
if [[ -z "$FORCE_NUM" ]]; then
    if [[ -d "results" ]] && [[ $(ls -d results/*/ 2>/dev/null | wc -l) -gt 0 ]]; then
        LAST_NUM=$(ls -d results/*/ 2>/dev/null | tail -1 | xargs basename)
        NEXT_NUM=$((LAST_NUM + 1))
    else
        NEXT_NUM=1
    fi
else
    NEXT_NUM=$FORCE_NUM
fi

CASE_DIR="results/$NEXT_NUM"

echo "=========================================="
echo "SIMULATION #$NEXT_NUM"
echo "=========================================="
echo ""
echo "Step 1: Initialize phase field (alpha.water)"
echo "  → Using Python script to generate non-uniform field directly"

# Delete old alpha.water to start fresh
rm -f 0/alpha.water
echo "    Deleted: 0/alpha.water"

# Generate alpha.water with proper cell-by-cell values
echo "  → Running: python3 scripts/generate_alpha_field.py"
python3 scripts/generate_alpha_field.py . 0/alpha.water || {
    echo "❌ Error generating alpha.water"
    exit 1
}
echo "  ✓ alpha.water generated with ink region initialized"
echo ""

echo "Step 2: Create case directory"
mkdir -p "$CASE_DIR"
echo "  ✓ Created: $CASE_DIR"
echo ""

echo "Step 3: Copy case files"
echo "  → Copying: 0/ constant/ system/"
cp -r 0 constant system "$CASE_DIR/"
echo "  ✓ Case files copied (with modified 0/alpha.water from setFields)"
echo ""

echo "Step 4: Run simulation"
echo "  → Executing: foamRun -solver incompressibleVoF (VOF multiphase solver)"
echo "  → Output: $CASE_DIR/run.log"
cd "$CASE_DIR"
timeout 3600 foamRun -solver incompressibleVoF -case . 2>&1 | tee run.log || {
    EXIT_CODE=$?
    echo ""
    echo "⚠️  Simulation exited with code $EXIT_CODE"
    echo "   Check $CASE_DIR/run.log for details"
    exit $EXIT_CODE
}

echo ""
echo "=========================================="
echo "SIMULATION #$NEXT_NUM COMPLETE"
echo "=========================================="
echo "Results: $CASE_DIR/"
echo "  • Timestep files: 0.*, 0.00*, etc."
echo "  • Log file: run.log"
echo ""
echo "Next steps:"
echo "  1. Check results: tail -50 $CASE_DIR/run.log"
echo "  2. Run next iteration: ./run_simulation.sh"
echo "  3. Post-process: python3 scripts/post_processor.py $CASE_DIR/"
