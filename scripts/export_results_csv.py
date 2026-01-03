#!/usr/bin/env python3
"""
Export Results to CSV for External Applications
================================================
Generates a CSV file containing all simulation parameters and output file paths.
This CSV can be used by external applications (e.g., Streamlit dashboard).

Usage:
    python3 export_results_csv.py --study example_viscosity_sweep
    python3 export_results_csv.py --all

Output:
    results/<study>/simulations.csv
"""

import argparse
import csv
from pathlib import Path
from openfoam_params import read_parameters, get_geometry, get_contact_angles

# =============================================================================
# CONFIGURATION
# =============================================================================
PROJECT_ROOT = Path(__file__).parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"
TEMPLATES_DIR = PROJECT_ROOT / "templates"

# CSV columns
CSV_COLUMNS = [
    # Identification
    'study_name',
    'run_name',
    'run_id',

    # Output files
    'gif_path',
    'png_path',
    'vtk_available',

    # Simulation status
    'status',
    'final_time_s',

    # Geometry [mm]
    'x_puit',
    'y_puit',
    'x_buse',
    'y_buse',
    'y_gap_buse',
    'x_gap_buse',
    'x_plateau',
    'ratio_surface',

    # Physics
    'rho_ink',
    'eta_0',
    'eta_inf',
    'sigma',
    'lambda_carreau',
    'n_carreau',

    # Contact angles [degrees]
    'CA_substrate',
    'CA_wall_isolant_left',
    'CA_wall_isolant_right',
    'CA_top_isolant_left',
    'CA_top_isolant_right',
    'CA_buse_int_left',
    'CA_buse_int_right',
    'CA_buse_ext_left',
    'CA_buse_ext_right',

    # Numerical
    'endTime',
    'writeInterval',
    'deltaT',
    'maxCo',
]


def get_run_status(run_dir: Path) -> tuple:
    """Check simulation status from log file."""
    log_file = run_dir / "run.log"

    if not log_file.exists():
        return "NO_LOG", None

    content = log_file.read_text()

    # Extract final time
    final_time = None
    for line in reversed(content.split('\n')):
        if line.startswith("Time = "):
            try:
                final_time = float(line.split('=')[1].strip())
                break
            except:
                pass

    if "End" in content or "Finalising" in content:
        return "OK", final_time
    elif "FOAM FATAL" in content:
        return "ERROR", final_time
    else:
        return "RUNNING", final_time


def find_output_files(run_dir: Path, study_dir: Path) -> dict:
    """Find GIF and PNG files for a run."""
    run_name = run_dir.name

    # Check in study's gifs/png folders
    gif_path = study_dir / "gifs" / f"{run_name}.gif"
    png_path = study_dir / "png" / f"{run_name}.png"

    # Also check in run directory directly
    if not gif_path.exists():
        gif_path = run_dir / f"{run_name}.gif"
    if not png_path.exists():
        png_path = run_dir / f"{run_name}.png"

    # Check for VTK directory
    vtk_available = (run_dir / "VTK").exists()

    return {
        'gif_path': str(gif_path) if gif_path.exists() else '',
        'png_path': str(png_path) if png_path.exists() else '',
        'vtk_available': vtk_available,
    }


def extract_run_id(run_name: str) -> int:
    """Extract run ID from name like 'run_001_eta0_0.5'."""
    parts = run_name.split('_')
    if len(parts) >= 2 and parts[1].isdigit():
        return int(parts[1])
    return 0


def process_run(run_dir: Path, study_name: str) -> dict:
    """Process a single run and extract all information."""
    run_name = run_dir.name
    study_dir = run_dir.parent

    # Read parameters from run's system/parameters (or templates as fallback)
    params = read_parameters(run_dir)
    geom = get_geometry(params)
    ca = get_contact_angles(params)

    # Get status
    status, final_time = get_run_status(run_dir)

    # Find output files
    files = find_output_files(run_dir, study_dir)

    # Calculate ratio
    S_puit = geom.get('x_puit', 0.8) * geom.get('y_puit', 0.128)
    S_buse = geom.get('x_buse', 0.3) * geom.get('y_buse', 0.341)
    ratio = S_buse / S_puit if S_puit > 0 else 1.0

    return {
        # Identification
        'study_name': study_name,
        'run_name': run_name,
        'run_id': extract_run_id(run_name),

        # Output files
        'gif_path': files['gif_path'],
        'png_path': files['png_path'],
        'vtk_available': files['vtk_available'],

        # Status
        'status': status,
        'final_time_s': final_time if final_time else '',

        # Geometry
        'x_puit': geom.get('x_puit', ''),
        'y_puit': geom.get('y_puit', ''),
        'x_buse': geom.get('x_buse', ''),
        'y_buse': geom.get('y_buse', ''),
        'y_gap_buse': geom.get('y_gap_buse', ''),
        'x_gap_buse': geom.get('x_gap_buse', ''),
        'x_plateau': geom.get('x_plateau', ''),
        'ratio_surface': f"{ratio:.4f}",

        # Physics
        'rho_ink': params.get('rho_ink', ''),
        'eta_0': params.get('eta_0', ''),
        'eta_inf': params.get('eta_inf', ''),
        'sigma': params.get('sigma', ''),
        'lambda_carreau': params.get('lambda', ''),
        'n_carreau': params.get('n_carreau', ''),

        # Contact angles
        'CA_substrate': ca.get('CA_substrate', ''),
        'CA_wall_isolant_left': ca.get('CA_wall_isolant_left', ''),
        'CA_wall_isolant_right': ca.get('CA_wall_isolant_right', ''),
        'CA_top_isolant_left': ca.get('CA_top_isolant_left', ''),
        'CA_top_isolant_right': ca.get('CA_top_isolant_right', ''),
        'CA_buse_int_left': ca.get('CA_buse_int_left', ''),
        'CA_buse_int_right': ca.get('CA_buse_int_right', ''),
        'CA_buse_ext_left': ca.get('CA_buse_ext_left', ''),
        'CA_buse_ext_right': ca.get('CA_buse_ext_right', ''),

        # Numerical
        'endTime': params.get('endTime', ''),
        'writeInterval': params.get('writeInterval', ''),
        'deltaT': params.get('deltaT', ''),
        'maxCo': params.get('maxCo', ''),
    }


def export_study(study_name: str) -> Path:
    """Export all runs in a study to CSV."""
    study_dir = RESULTS_DIR / study_name

    if not study_dir.exists():
        print(f"ERROR: Study not found: {study_dir}")
        return None

    # Find all run directories
    run_dirs = sorted([d for d in study_dir.iterdir()
                       if d.is_dir() and d.name.startswith('run_')])

    if not run_dirs:
        print(f"ERROR: No runs found in {study_dir}")
        return None

    print(f"\n=== Exporting: {study_name} ===")
    print(f"Found {len(run_dirs)} runs")

    # Process all runs
    results = []
    for run_dir in run_dirs:
        data = process_run(run_dir, study_name)
        results.append(data)

        status_icon = "OK" if data['status'] == "OK" else "ERR" if data['status'] == "ERROR" else "..."
        gif_icon = "GIF" if data['gif_path'] else "---"
        png_icon = "PNG" if data['png_path'] else "---"
        print(f"  [{status_icon}] {data['run_name']} [{gif_icon}] [{png_icon}]")

    # Write CSV
    csv_path = study_dir / "simulations.csv"

    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nExported: {csv_path}")
    print(f"  - {len(results)} simulations")
    print(f"  - {len([r for r in results if r['gif_path']])} GIFs")
    print(f"  - {len([r for r in results if r['png_path']])} PNGs")
    print(f"  - {len([r for r in results if r['status'] == 'OK'])} completed")

    return csv_path


def export_all_studies():
    """Export all studies found in results directory."""
    if not RESULTS_DIR.exists():
        print(f"ERROR: Results directory not found: {RESULTS_DIR}")
        return

    # Find study directories (those containing run_* folders)
    studies = []
    for d in RESULTS_DIR.iterdir():
        if d.is_dir():
            runs = list(d.glob("run_*"))
            if runs:
                studies.append(d.name)

    if not studies:
        print("No studies found")
        return

    print(f"Found {len(studies)} studies: {studies}")

    for study in studies:
        export_study(study)


def main():
    parser = argparse.ArgumentParser(
        description="Export simulation results to CSV")
    parser.add_argument('--study', help='Study name to export')
    parser.add_argument('--all', action='store_true', help='Export all studies')

    args = parser.parse_args()

    if args.all:
        export_all_studies()
    elif args.study:
        export_study(args.study)
    else:
        parser.print_help()
        print("\nAvailable studies:")
        if RESULTS_DIR.exists():
            for d in sorted(RESULTS_DIR.iterdir()):
                if d.is_dir() and list(d.glob("run_*")):
                    print(f"  - {d.name}")


if __name__ == "__main__":
    main()
