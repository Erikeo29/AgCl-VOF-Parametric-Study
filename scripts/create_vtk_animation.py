#!/usr/bin/env python3
"""
Create Comsol-style animation from OpenFOAM VTK files using PyVista.
- White background (air)
- Black ink (alpha > 0.5)
- Black geometry edges
- Parameter annotations
"""

import os
import sys
import numpy as np
import pyvista as pv
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.collections import PatchCollection
import imageio.v2 as imageio
import re

# Disable interactive plotting
pv.OFF_SCREEN = True

def read_simulation_params(case_dir):
    """Read actual simulation parameters from case files."""
    params = {
        'density': 3000,
        'viscosity': 1.5,
        'surface_tension': 40,
        'dispense_time': 80,
        'CA_left': 15,
        'CA_right': 160,
        'CA_substrate': 35,
    }

    case_path = Path(case_dir)

    # Read from simulation_config.txt if exists (parametric study)
    config_file = case_path / 'simulation_config.txt'
    if config_file.exists():
        with open(config_file, 'r') as f:
            for line in f:
                if ':' in line and not line.startswith('#'):
                    key, val = line.split(':', 1)
                    key = key.strip()
                    val = val.strip()
                    if key == 'viscosity_Pa_s':
                        params['viscosity'] = float(val)
                    elif key == 'CA_left':
                        params['CA_left'] = float(val)
                    elif key == 'CA_right':
                        params['CA_right'] = float(val)
                    elif key == 'CA_substrate':
                        params['CA_substrate'] = float(val)

    # Read viscosity from transportProperties if not from config
    tp_file = case_path / 'constant' / 'transportProperties'
    if tp_file.exists():
        with open(tp_file, 'r') as f:
            content = f.read()
            # Find mu value in water block
            match = re.search(r'water\s*\{[^}]*mu\s+([\d.]+)', content, re.DOTALL)
            if match:
                params['viscosity'] = float(match.group(1))

    return params

def get_vtk_files(vtk_dir):
    """Get sorted list of VTK files with their time values."""
    vtk_path = Path(vtk_dir)

    # Find all main VTK files (not patches)
    vtk_files = []
    for f in vtk_path.glob("*.vtk"):
        # Filter out patch files (in subdirectories)
        if f.parent == vtk_path:
            # Extract timestep number from filename like "78_12345.vtk"
            match = re.search(r'_(\d+)\.vtk$', f.name)
            if match:
                timestep = int(match.group(1))
                vtk_files.append((timestep, f))

    # Sort by timestep
    vtk_files.sort(key=lambda x: x[0])
    return vtk_files

def create_frame_pyvista(vtk_file, time_ms, output_file, params):
    """Create a single frame using PyVista."""

    # Read VTK mesh
    mesh = pv.read(str(vtk_file))

    # Get alpha field
    if 'alpha.water' in mesh.array_names:
        alpha = mesh['alpha.water']
    else:
        print(f"No alpha.water field in {vtk_file}")
        return False

    # Get cell centers
    centers = mesh.cell_centers().points

    # Scale to mm
    scale = 1000
    x = centers[:, 0] * scale
    y = centers[:, 1] * scale

    # Geometry dimensions (mm)
    puit_left = -0.4
    puit_right = 0.4
    puit_height = 0.128

    buse_left = -0.15
    buse_right = 0.15
    buse_bottom = 0.158
    buse_top = params.get('buse_top', 0.598)

    gap_height = 0.158

    # Create matplotlib figure
    fig, ax = plt.subplots(figsize=(10, 12), facecolor='white')
    ax.set_facecolor('white')

    # Find ink cells (alpha > 0.5)
    ink_mask = alpha > 0.5

    # Determine cell size for visualization
    cell_size = 0.006  # mm

    # Draw ink cells
    ink_patches = []
    for i in np.where(ink_mask)[0]:
        rect = mpatches.Rectangle(
            (x[i] - cell_size/2, y[i] - cell_size/2),
            cell_size, cell_size,
            linewidth=0
        )
        ink_patches.append(rect)

    if ink_patches:
        ink_collection = PatchCollection(ink_patches, facecolor='black', edgecolor='none')
        ax.add_collection(ink_collection)

    # Draw geometry outlines
    lw = 1.5

    # Substrate
    ax.plot([puit_left, puit_right], [0, 0], 'k-', linewidth=2)

    # Puit walls
    ax.plot([puit_left, puit_left], [0, puit_height], 'k-', linewidth=lw)
    ax.plot([puit_right, puit_right], [0, puit_height], 'k-', linewidth=lw)

    # Isolant top
    ax.plot([-0.8, puit_left], [puit_height, puit_height], 'k-', linewidth=lw)
    ax.plot([puit_right, 0.8], [puit_height, puit_height], 'k-', linewidth=lw)

    # Buse walls
    ax.plot([buse_left, buse_left], [buse_bottom, buse_top], 'k-', linewidth=lw)
    ax.plot([buse_right, buse_right], [buse_bottom, buse_top], 'k-', linewidth=lw)
    ax.plot([buse_left, buse_right], [buse_top, buse_top], 'k-', linewidth=lw)

    # Buse exterior
    ax.plot([buse_left, buse_left], [gap_height, buse_bottom], 'k--', linewidth=1)
    ax.plot([buse_right, buse_right], [gap_height, buse_bottom], 'k--', linewidth=1)

    # Set limits
    ax.set_xlim(-0.55, 0.55)
    ax.set_ylim(-0.05, buse_top + 0.1)
    ax.set_aspect('equal')
    ax.axis('off')

    # Annotations
    ax.text(0.02, 0.98, f"temps: {time_ms:.2f} ms", transform=ax.transAxes,
            fontsize=11, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    # Parameters
    param_text = f"""time dispense={params.get('dispense_time', 0.08)*1000:.1f} ms
density={params.get('density', 3000)} kg/m³
viscosity={params.get('viscosity', 1.5)} Pa·s
surface tension={params.get('surface_tension', 40)} mN/m"""
    ax.text(0.02, 0.92, param_text, transform=ax.transAxes,
            fontsize=9, verticalalignment='top', fontfamily='monospace')

    # Geometry info
    geom_text = f"""diam. buse= {(buse_right-buse_left)*1000:.0f}µm
diam. well= {(puit_right-puit_left)*1000:.0f}µm
height well= {puit_height*1000:.0f}µm
height buse= {(buse_top-buse_bottom)*1000:.0f}µm"""
    ax.text(0.98, 0.92, geom_text, transform=ax.transAxes,
            fontsize=9, verticalalignment='top', horizontalalignment='right', fontfamily='monospace')

    # Contact angles (support both lowercase and uppercase keys)
    ca_left = params.get('ca_left', params.get('CA_left', 15))
    ca_right = params.get('ca_right', params.get('CA_right', 160))
    ca_substrate = params.get('ca_substrate', params.get('CA_substrate', 35))
    ca_buse_ext = params.get('ca_buse_ext', params.get('CA_buse_ext', 180))

    ax.text(puit_left - 0.02, puit_height + 0.01, f"CA={ca_left}°", fontsize=9, ha='right')
    ax.text(puit_right + 0.02, puit_height + 0.01, f"CA={ca_right}°", fontsize=9, ha='left')
    ax.text(0, -0.025, f"CA={ca_substrate}°", fontsize=9, ha='center')
    ax.text(buse_left - 0.02, (buse_bottom + buse_top)/2, f"CA={ca_buse_ext}°",
            fontsize=8, ha='right', rotation=90, va='center')

    # Ink stats
    n_ink = np.sum(ink_mask)
    n_total = len(alpha)
    ax.text(0.5, 0.02, f"Ink: {n_ink}/{n_total} ({100*n_ink/n_total:.1f}%)",
            transform=ax.transAxes, fontsize=8, ha='center', fontfamily='monospace')

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, facecolor='white', bbox_inches='tight')
    plt.close()

    return True

def create_animation(case_dir, output_gif, params=None):
    """Create animation from VTK files."""

    if params is None:
        params = {
            'dispense_time': 0.08,
            'density': 3000,
            'viscosity': 1.5,
            'surface_tension': 40,
            'buse_top': 0.598,
            'ca_left': 15,
            'ca_right': 160,
            'ca_substrate': 35,
            'ca_buse_ext': 180
        }

    case_path = Path(case_dir)
    vtk_dir = case_path / "VTK"

    if not vtk_dir.exists():
        print(f"VTK directory not found: {vtk_dir}")
        print("Run 'foamToVTK -case <case_dir>' first")
        return

    # Get VTK files
    vtk_files = get_vtk_files(vtk_dir)

    if not vtk_files:
        print("No VTK files found!")
        return

    print(f"Found {len(vtk_files)} VTK files")

    # Map timestep indices to actual times (0.005s intervals = 5ms)
    # We need to figure out the time step from the file index
    # Based on simulation: 61 timesteps from 0 to 300ms (5ms intervals)
    total_time_ms = 300.0
    n_files = len(vtk_files)

    # Create frames directory
    frames_dir = case_path / "frames_vtk"
    frames_dir.mkdir(exist_ok=True)

    # Generate frames
    frame_files = []
    for i, (timestep, vtk_file) in enumerate(vtk_files):
        # Estimate time in ms (linear mapping)
        time_ms = i * total_time_ms / (n_files - 1) if n_files > 1 else 0

        print(f"Processing frame {i+1}/{len(vtk_files)} (t={time_ms:.2f} ms)")
        frame_file = frames_dir / f"frame_{i:04d}.png"

        success = create_frame_pyvista(vtk_file, time_ms, frame_file, params)
        if success:
            frame_files.append(frame_file)

    if not frame_files:
        print("No frames generated!")
        return

    # Create GIF
    print(f"Creating GIF: {output_gif}")
    images = [imageio.imread(str(f)) for f in frame_files]
    imageio.mimsave(output_gif, images, duration=0.1, loop=0)

    print(f"Animation saved to: {output_gif}")
    print(f"Frames saved in: {frames_dir}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python create_vtk_animation.py <case_directory> [output.gif]")
        print("Example: python scripts/create_vtk_animation.py results/78 results/78/animation_vtk.gif")
        sys.exit(1)

    case_dir = sys.argv[1]
    output_gif = sys.argv[2] if len(sys.argv) > 2 else f"{case_dir}/animation_vtk.gif"

    # Read actual parameters from simulation files
    params = read_simulation_params(case_dir)
    # Add fixed geometry parameters
    params['dispense_time'] = 80  # ms
    params['surface_tension'] = 40  # mN/m
    params['buse_top'] = 0.598
    params['ca_buse_ext'] = 180

    print(f"Using parameters: viscosity={params['viscosity']} Pa·s, CA_left={params['CA_left']}°, CA_right={params['CA_right']}°")

    create_animation(case_dir, output_gif, params)
