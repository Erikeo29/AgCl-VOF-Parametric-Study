#!/usr/bin/env python3
"""
Watch study progress and generate GIFs as simulations complete.
Runs in parallel with parametric_runner.

Usage:
    python3 watch_and_gif.py --study full_sweep_24
"""

import argparse
import subprocess
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"

def is_simulation_complete(run_dir: Path) -> bool:
    """Check if simulation is complete (has 'End' in run.log)."""
    log_file = run_dir / "run.log"
    if not log_file.exists():
        return False
    try:
        content = log_file.read_text()
        return "End" in content or "Finalising" in content
    except:
        return False

def has_vtk(run_dir: Path) -> bool:
    """Check if VTK conversion is done."""
    vtk_dir = run_dir / "VTK"
    return vtk_dir.exists() and len(list(vtk_dir.glob("*.vtk"))) > 0

def has_gif(run_dir: Path, study_dir: Path) -> bool:
    """Check if GIF is generated."""
    gif_path = study_dir / "gifs" / f"{run_dir.name}.gif"
    return gif_path.exists()

def convert_to_vtk(run_dir: Path) -> bool:
    """Convert OpenFOAM results to VTK."""
    cmd = f"source /opt/openfoam13/etc/bashrc && foamToVTK -case {run_dir} > /dev/null 2>&1"
    result = subprocess.run(cmd, shell=True, executable='/bin/bash')
    return result.returncode == 0

def generate_gif(run_dir: Path) -> bool:
    """Generate GIF for a run."""
    cmd = f"source ~/miniconda3/etc/profile.d/conda.sh && conda activate electrochemistry && python3 scripts/create_vof_gif.py --run {run_dir} > /dev/null 2>&1"
    result = subprocess.run(cmd, shell=True, executable='/bin/bash', cwd=PROJECT_ROOT)
    return result.returncode == 0

def watch_study(study_name: str, interval: int = 30):
    """Watch study and generate GIFs as simulations complete."""
    study_dir = RESULTS_DIR / study_name

    print(f"=== Watching study: {study_name} ===")
    print(f"Checking every {interval} seconds...")
    print(f"Press Ctrl+C to stop\n")

    processed = set()

    while True:
        # Find all run directories
        run_dirs = sorted([d for d in study_dir.iterdir()
                          if d.is_dir() and d.name.startswith('run_')])

        completed = 0
        with_gif = 0

        for run_dir in run_dirs:
            run_name = run_dir.name

            if is_simulation_complete(run_dir):
                completed += 1

                # Process if not already done
                if run_name not in processed:
                    print(f"\n[NEW] {run_name} completed!")

                    # Convert to VTK if needed
                    if not has_vtk(run_dir):
                        print(f"  Converting to VTK...", end=" ", flush=True)
                        if convert_to_vtk(run_dir):
                            print("OK")
                        else:
                            print("FAILED")
                            continue

                    # Generate GIF if needed
                    if not has_gif(run_dir, study_dir):
                        print(f"  Generating GIF...", end=" ", flush=True)
                        if generate_gif(run_dir):
                            print("OK")
                            processed.add(run_name)
                        else:
                            print("FAILED")
                    else:
                        processed.add(run_name)

                if has_gif(run_dir, study_dir):
                    with_gif += 1

        # Status line
        total = len(run_dirs) if run_dirs else "?"
        print(f"\r[{time.strftime('%H:%M:%S')}] Runs: {total} | Completed: {completed} | GIFs: {with_gif}    ", end="", flush=True)

        # Check if all done
        if run_dirs and completed == len(run_dirs) and with_gif == len(run_dirs):
            print(f"\n\n=== All {len(run_dirs)} simulations complete with GIFs! ===")
            break

        time.sleep(interval)

def main():
    parser = argparse.ArgumentParser(description="Watch study and generate GIFs")
    parser.add_argument('--study', required=True, help='Study name to watch')
    parser.add_argument('--interval', type=int, default=30, help='Check interval in seconds')

    args = parser.parse_args()

    try:
        watch_study(args.study, args.interval)
    except KeyboardInterrupt:
        print("\n\nStopped by user.")

if __name__ == "__main__":
    main()
