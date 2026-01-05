#!/bin/bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate electrochemistry
unset DISPLAY
export PYVISTA_OFF_SCREEN=true

cd /home/erikeo29/17_RD_Ag_AgCl/40_AgCl_OpenFOAM/05_AgCl_OF_param_v5

for run in results/dispense_time_sweep/run_*; do
    echo "=== GIF: $(basename $run) ==="
    python3 scripts/create_vof_gif.py --run "$run" 2>&1 | grep -E "Saving|Error|Creating"
done

echo "=== Done ==="
