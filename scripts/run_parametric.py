#!/usr/bin/env python3
"""
Parametric study runner for AgCl VOF simulations.

Reads configurations from parametric_study.csv and runs simulations
with varying contact angles, nozzle position, and viscosity.

Usage:
    python3 scripts/run_parametric.py                    # Run all pending
    python3 scripts/run_parametric.py --sim 80 81 82    # Run specific sims
    python3 scripts/run_parametric.py --dry-run         # Preview changes only
"""

import csv
import sys
import os
import shutil
import subprocess
import re
from pathlib import Path
from datetime import datetime

# Project root
PROJECT_DIR = Path(__file__).parent.parent
CSV_FILE = PROJECT_DIR / "parametric_study.csv"
RESULTS_DIR = PROJECT_DIR / "results"

def read_csv_configs(csv_path):
    """Read parametric configurations from CSV file."""
    configs = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            config = {
                'sim_id': int(row['sim_id']),
                'CA_left': float(row['CA_left']),
                'CA_right': float(row['CA_right']),
                'CA_substrate': float(row['CA_substrate']),
                'CA_buse_int': float(row['CA_buse_int']),
                'CA_buse_ext': float(row['CA_buse_ext']),
                'buse_x_offset_mm': float(row['buse_x_offset_mm']),
                'viscosity_Pa_s': float(row['viscosity_Pa_s']),
                'description': row['description']
            }
            configs.append(config)
    return configs

def get_completed_sims():
    """Get list of already completed simulation IDs."""
    completed = []
    if RESULTS_DIR.exists():
        for d in RESULTS_DIR.iterdir():
            if d.is_dir() and d.name.isdigit():
                # Check if simulation actually completed
                run_log = d / "run.log"
                if run_log.exists():
                    with open(run_log, 'r') as f:
                        content = f.read()
                        if "End" in content or "Finalising" in content:
                            completed.append(int(d.name))
    return completed

def modify_alpha_water_template(config):
    """
    Modify the generate_alpha_field.py to use custom contact angles.
    Returns the modified script content.
    """
    # Read the original script
    script_path = PROJECT_DIR / "scripts" / "generate_alpha_field.py"
    with open(script_path, 'r') as f:
        content = f.read()

    # Create modified boundary conditions
    bc_template = f'''boundaryField
{{
    // === Faces 2D (empty) ===
    front
    {{
        type            empty;
    }}

    back
    {{
        type            empty;
    }}

    // === Substrat (fond du puit) ===
    substrate
    {{
        type            contactAngle;
        theta0          {config['CA_substrate']};
        limit           gradient;
        value           uniform 0;
    }}

    // === Paroi verticale de l'isolant GAUCHE ===
    wall_isolant_left
    {{
        type            contactAngle;
        theta0          {config['CA_left']};
        limit           gradient;
        value           uniform 0;
    }}

    // === Paroi verticale de l'isolant DROITE ===
    wall_isolant_right
    {{
        type            contactAngle;
        theta0          {config['CA_right']};
        limit           gradient;
        value           uniform 0;
    }}

    // === Surface horizontale de l'isolant GAUCHE ===
    top_isolant_left
    {{
        type            contactAngle;
        theta0          {config['CA_left']};
        limit           gradient;
        value           uniform 0;
    }}

    // === Surface horizontale de l'isolant DROITE ===
    top_isolant_right
    {{
        type            contactAngle;
        theta0          {config['CA_right']};
        limit           gradient;
        value           uniform 0;
    }}

    // === Paroi INTERIEURE de la buse GAUCHE ===
    wall_buse_left_int
    {{
        type            contactAngle;
        theta0          {config['CA_buse_int']};
        limit           gradient;
        value           uniform 1;
    }}

    // === Paroi EXTERIEURE de la buse GAUCHE ===
    wall_buse_left_ext
    {{
        type            contactAngle;
        theta0          {config['CA_buse_ext']};
        limit           gradient;
        value           uniform 0;
    }}

    // === Paroi INTERIEURE de la buse DROITE ===
    wall_buse_right_int
    {{
        type            contactAngle;
        theta0          {config['CA_buse_int']};
        limit           gradient;
        value           uniform 1;
    }}

    // === Paroi EXTERIEURE de la buse DROITE ===
    wall_buse_right_ext
    {{
        type            contactAngle;
        theta0          {config['CA_buse_ext']};
        limit           gradient;
        value           uniform 0;
    }}

    // === Inlet (haut de la buse) ===
    inlet
    {{
        type            fixedValue;
        value           uniform 0;
    }}

    // === Atmosphere (sortie air) ===
    atmosphere
    {{
        type            inletOutlet;
        inletValue      uniform 0;
        value           uniform 0;
    }}

    // === Outlet lateral GAUCHE ===
    outlet_left
    {{
        type            inletOutlet;
        inletValue      uniform 0;
        value           uniform 0;
    }}

    // === Outlet lateral DROITE ===
    outlet_right
    {{
        type            inletOutlet;
        inletValue      uniform 0;
        value           uniform 0;
    }}
}}

// ************************************************************************* //
'''

    # Replace the boundaryField section
    start_marker = '        f.write("""boundaryField'
    end_marker = '// ************************************************************************* //\n""")'

    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker) + len(end_marker)

    if start_idx > 0 and end_idx > start_idx:
        modified_content = content[:start_idx] + f'        f.write("""{bc_template}""")' + content[end_idx:]
        return modified_content

    return None

def modify_transport_properties(case_dir, viscosity_Pa_s):
    """Modify transportProperties for given viscosity."""
    tp_file = case_dir / "constant" / "transportProperties"

    with open(tp_file, 'r') as f:
        content = f.read()

    # Calculate kinematic viscosity (nu = mu / rho)
    rho = 3000  # kg/m³
    nu0 = viscosity_Pa_s / rho
    nuInf = nu0 / 3  # Maintain ratio

    # Replace mu value
    content = re.sub(r'mu\s+[\d.e+-]+;', f'mu              {viscosity_Pa_s};', content)

    # Replace nu0 in Carreau block
    content = re.sub(r'nu0\s+[\d.e+-]+;', f'nu0         {nu0:.6e};', content)

    # Replace nuInf
    content = re.sub(r'nuInf\s+[\d.e+-]+;', f'nuInf       {nuInf:.6e};', content)

    # Update comment
    content = re.sub(
        r'// Pa·s \(η₀.*\)',
        f'// Pa·s (η₀ = {viscosity_Pa_s} Pa.s - parametric)',
        content
    )

    with open(tp_file, 'w') as f:
        f.write(content)

    return True

def modify_blockmesh_offset(case_dir, x_offset_mm):
    """Modify blockMeshDict for nozzle x-offset (horizontal shift)."""
    if abs(x_offset_mm) < 1e-6:
        return True  # No modification needed

    bm_file = case_dir / "system" / "blockMeshDict"

    with open(bm_file, 'r') as f:
        content = f.read()

    # Current nozzle x coordinates (from geometry):
    # x_buse_left = -0.15 mm
    # x_buse_right = 0.15 mm
    # Offset shifts both by the same amount

    x_buse_left_old = -0.15
    x_buse_right_old = 0.15

    x_buse_left_new = x_buse_left_old + x_offset_mm
    x_buse_right_new = x_buse_right_old + x_offset_mm

    # Use regex to replace x coordinates in vertices
    # Format in blockMeshDict: (x y z) where x is -0.15 or 0.15 for nozzle
    import re

    # Replace -0.15 (buse left x) - be careful with context
    # Only replace when it's clearly the nozzle coordinate
    content = re.sub(
        r'\(\s*-0\.15\s+0\.158\s',
        f'( {x_buse_left_new} 0.158 ',
        content
    )
    content = re.sub(
        r'\(\s*-0\.15\s+0\.278\s',
        f'( {x_buse_left_new} 0.278 ',
        content
    )
    content = re.sub(
        r'\(\s*-0\.15\s+0\.598\s',
        f'( {x_buse_left_new} 0.598 ',
        content
    )

    # Replace 0.15 (buse right x)
    content = re.sub(
        r'\(\s*0\.15\s+0\.158\s',
        f'( {x_buse_right_new} 0.158 ',
        content
    )
    content = re.sub(
        r'\(\s*0\.15\s+0\.278\s',
        f'( {x_buse_right_new} 0.278 ',
        content
    )
    content = re.sub(
        r'\(\s*0\.15\s+0\.598\s',
        f'( {x_buse_right_new} 0.598 ',
        content
    )

    with open(bm_file, 'w') as f:
        f.write(content)

    return True

def setup_case(sim_id, config, dry_run=False):
    """Setup simulation case directory with modified parameters."""
    case_dir = RESULTS_DIR / str(sim_id)

    print(f"\n{'='*60}")
    print(f"Setting up SIM {sim_id}: {config['description']}")
    print(f"{'='*60}")
    print(f"  CA_left:      {config['CA_left']}°")
    print(f"  CA_right:     {config['CA_right']}°")
    print(f"  CA_substrate: {config['CA_substrate']}°")
    print(f"  CA_buse_int:  {config['CA_buse_int']}°")
    print(f"  CA_buse_ext:  {config['CA_buse_ext']}°")
    print(f"  Buse X offset: {config['buse_x_offset_mm']} mm")
    print(f"  Viscosity:    {config['viscosity_Pa_s']} Pa·s")

    if dry_run:
        print("  [DRY RUN - no changes made]")
        return True

    # Create case directory
    if case_dir.exists():
        print(f"  WARNING: {case_dir} already exists, removing...")
        shutil.rmtree(case_dir)

    case_dir.mkdir(parents=True)

    # Copy template directories
    for subdir in ['0', 'constant', 'system']:
        src = PROJECT_DIR / subdir
        dst = case_dir / subdir
        if src.exists():
            shutil.copytree(src, dst)
            print(f"  Copied {subdir}/")

    # Modify transportProperties for viscosity
    if abs(config['viscosity_Pa_s'] - 1.5) > 0.01:  # Different from default
        modify_transport_properties(case_dir, config['viscosity_Pa_s'])
        print(f"  Modified transportProperties (viscosity={config['viscosity_Pa_s']})")

    # Modify blockMeshDict for nozzle X offset (horizontal)
    if abs(config['buse_x_offset_mm']) > 1e-6:
        modify_blockmesh_offset(case_dir, config['buse_x_offset_mm'])
        print(f"  Modified blockMeshDict (X offset={config['buse_x_offset_mm']}mm)")

    # Generate alpha.water with custom contact angles
    generate_alpha_with_config(case_dir, config)
    print(f"  Generated alpha.water with custom contact angles")

    # Save config summary
    config_file = case_dir / "simulation_config.txt"
    with open(config_file, 'w') as f:
        f.write(f"# Simulation {sim_id} Configuration\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n\n")
        for key, value in config.items():
            f.write(f"{key}: {value}\n")

    return True

def generate_alpha_with_config(case_dir, config):
    """Generate alpha.water field with custom contact angles."""

    mesh_dir = case_dir / "constant" / "polyMesh"

    # Read cell zone labels for buse
    cellzones_file = mesh_dir / "cellZones"
    buse_cells = []

    with open(cellzones_file, 'r') as f:
        content = f.read()

    zone_start = content.find("\nbuse\n")
    if zone_start >= 0:
        labels_start = content.find("cellLabels", zone_start)
        if labels_start >= 0:
            count_start = content.find("\n", labels_start) + 1
            count_end = content.find("\n", count_start)
            paren_start = content.find("(", count_end) + 1
            paren_end = content.find(")", paren_start)
            labels_text = content[paren_start:paren_end]
            buse_cells = [int(x) for x in labels_text.split()]

    # Read number of cells from owner
    owner_file = mesh_dir / "owner"
    with open(owner_file, 'r') as f:
        owner_content = f.read()

    lines = owner_content.split('\n')
    foam_end = -1
    for i, line in enumerate(lines):
        if line.strip() == '}':
            foam_end = i
            break

    max_owner = -1
    in_data = False
    for i in range(foam_end + 1, len(lines)):
        stripped = lines[i].strip()
        if not stripped:
            continue
        if stripped == '(':
            in_data = True
            continue
        if stripped == ')':
            break
        if in_data:
            try:
                val = int(stripped)
                if val > max_owner:
                    max_owner = val
            except ValueError:
                continue

    num_cells = max_owner + 1
    buse_set = set(buse_cells)

    # Write alpha.water
    output_file = case_dir / "0" / "alpha.water"

    with open(output_file, 'w') as f:
        f.write(f'''/*--------------------------------*- C++ -*----------------------------------*\\
  =========                 |
  \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\\\    /   O peration     | Website:  https://openfoam.org
    \\\\  /    A nd           | Version:  13
     \\\\/     M anipulation  |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    format      ascii;
    class       volScalarField;
    location    "0";
    object      alpha.water;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

// PARAMETRIC STUDY - SIM {config['sim_id']}
// Description: {config['description']}
// CA_left={config['CA_left']}, CA_right={config['CA_right']}, CA_substrate={config['CA_substrate']}
// Viscosity={config['viscosity_Pa_s']} Pa.s, Buse_X_offset={config['buse_x_offset_mm']}mm

dimensions      [];

''')

        # Internal field
        f.write(f"internalField   nonuniform List<scalar>\n{num_cells}\n(\n")
        for cell_id in range(num_cells):
            f.write("1\n" if cell_id in buse_set else "0\n")
        f.write(")\n;\n\n")

        # Boundary field with custom contact angles
        f.write(f'''boundaryField
{{
    front {{ type empty; }}
    back {{ type empty; }}

    substrate
    {{
        type            contactAngle;
        theta0          {config['CA_substrate']};
        limit           gradient;
        value           uniform 0;
    }}

    wall_isolant_left
    {{
        type            contactAngle;
        theta0          {config['CA_left']};
        limit           gradient;
        value           uniform 0;
    }}

    wall_isolant_right
    {{
        type            contactAngle;
        theta0          {config['CA_right']};
        limit           gradient;
        value           uniform 0;
    }}

    top_isolant_left
    {{
        type            contactAngle;
        theta0          {config['CA_left']};
        limit           gradient;
        value           uniform 0;
    }}

    top_isolant_right
    {{
        type            contactAngle;
        theta0          {config['CA_right']};
        limit           gradient;
        value           uniform 0;
    }}

    wall_buse_left_int
    {{
        type            contactAngle;
        theta0          {config['CA_buse_int']};
        limit           gradient;
        value           uniform 1;
    }}

    wall_buse_left_ext
    {{
        type            contactAngle;
        theta0          {config['CA_buse_ext']};
        limit           gradient;
        value           uniform 0;
    }}

    wall_buse_right_int
    {{
        type            contactAngle;
        theta0          {config['CA_buse_int']};
        limit           gradient;
        value           uniform 1;
    }}

    wall_buse_right_ext
    {{
        type            contactAngle;
        theta0          {config['CA_buse_ext']};
        limit           gradient;
        value           uniform 0;
    }}

    inlet
    {{
        type            fixedValue;
        value           uniform 0;
    }}

    atmosphere
    {{
        type            inletOutlet;
        inletValue      uniform 0;
        value           uniform 0;
    }}

    outlet_left
    {{
        type            inletOutlet;
        inletValue      uniform 0;
        value           uniform 0;
    }}

    outlet_right
    {{
        type            inletOutlet;
        inletValue      uniform 0;
        value           uniform 0;
    }}
}}

// ************************************************************************* //
''')

def run_simulation(sim_id, dry_run=False):
    """Run OpenFOAM simulation for given case."""
    case_dir = RESULTS_DIR / str(sim_id)

    if dry_run:
        print(f"  [DRY RUN - would run simulation in {case_dir}]")
        return True

    print(f"\n  Running simulation {sim_id}...")

    # Source OpenFOAM and run
    cmd = f'''
    cd {case_dir}
    source /opt/openfoam13/etc/bashrc
    blockMesh > blockMesh.log 2>&1
    foamRun -solver incompressibleVoF > run.log 2>&1
    '''

    result = subprocess.run(cmd, shell=True, executable='/bin/bash')

    # Check if completed
    run_log = case_dir / "run.log"
    if run_log.exists():
        with open(run_log, 'r') as f:
            content = f.read()
            if "End" in content or "Finalising" in content:
                print(f"  ✓ SIM {sim_id} completed successfully")
                return True
            else:
                print(f"  ✗ SIM {sim_id} may have failed - check run.log")
                return False

    print(f"  ✗ SIM {sim_id} failed - no run.log found")
    return False

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Run parametric study')
    parser.add_argument('--sim', nargs='+', type=int, help='Specific simulation IDs to run')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without running')
    parser.add_argument('--skip-completed', action='store_true', default=True, help='Skip already completed sims')
    parser.add_argument('--list', action='store_true', help='List all configurations')
    args = parser.parse_args()

    # Read configurations
    configs = read_csv_configs(CSV_FILE)
    print(f"Loaded {len(configs)} configurations from {CSV_FILE}")

    if args.list:
        print("\nConfigurations:")
        print("-" * 80)
        for c in configs:
            print(f"  {c['sim_id']:3d}: {c['description']:<30} CA={c['CA_left']}/{c['CA_right']}, "
                  f"visc={c['viscosity_Pa_s']}, Xoff={c['buse_x_offset_mm']}")
        return

    # Get completed simulations
    completed = get_completed_sims() if args.skip_completed else []
    if completed:
        print(f"Already completed: {completed}")

    # Filter configurations
    if args.sim:
        configs = [c for c in configs if c['sim_id'] in args.sim]
        print(f"Running {len(configs)} specified simulations")
    else:
        configs = [c for c in configs if c['sim_id'] not in completed]
        print(f"Running {len(configs)} pending simulations")

    if not configs:
        print("No simulations to run!")
        return

    # Run simulations
    success = 0
    failed = 0

    for config in configs:
        sim_id = config['sim_id']

        # Setup case
        if setup_case(sim_id, config, dry_run=args.dry_run):
            # Run simulation
            if run_simulation(sim_id, dry_run=args.dry_run):
                success += 1
            else:
                failed += 1
        else:
            failed += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY: {success} succeeded, {failed} failed")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
