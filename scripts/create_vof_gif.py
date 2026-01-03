#!/usr/bin/env python3
"""
Generate Streamlit-compatible GIFs and PNGs from OpenFOAM VOF results.

Format: 640x480, white background, black phase, annotations matching FEM style.
All parameters are read from the OpenFOAM 'system/parameters' file.

Usage:
    python3 create_streamlit_gif.py --study streamlit_vof
    python3 create_streamlit_gif.py --run results/streamlit_vof/run_001_xxx
"""

import os
import sys
import argparse
import json
import re
from pathlib import Path

# Check for required packages
try:
    import pyvista as pv
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    import imageio
except ImportError as e:
    print(f"Missing package: {e}")
    print("Install with: pip install pyvista numpy pillow imageio")
    sys.exit(1)

# =============================================================================
# CONFIGURATION - Match FEM style
# =============================================================================
WIDTH, HEIGHT = 640, 480
FPS = 10
BACKGROUND = 'white'
PHASE_COLOR = 'black'
WALL_COLOR = 'black'
WALL_LINE_WIDTH = 2
FONT_SIZE = 11

# Wall patches to render as black lines
WALL_PATCHES = [
    'substrate',
    'wall_isolant_left',
    'wall_isolant_right',
    'wall_buse_left_int',
    'wall_buse_right_int',
    'wall_buse_left_ext',
    'wall_buse_right_ext',
    'top_isolant_left',
    'top_isolant_right'
]

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"
TEMPLATES_DIR = PROJECT_ROOT / "templates"


# =============================================================================
# OPENFOAM PARAMETERS READER
# =============================================================================
def read_openfoam_parameters(case_dir: Path) -> dict:
    """
    Read parameters from OpenFOAM system/parameters file.

    Args:
        case_dir: Path to OpenFOAM case directory

    Returns:
        Dictionary with all parameters
    """
    params_file = case_dir / "system" / "parameters"

    # Fallback to templates if not in case
    if not params_file.exists():
        params_file = TEMPLATES_DIR / "system" / "parameters"

    if not params_file.exists():
        print(f"Warning: parameters file not found, using defaults")
        return get_default_parameters()

    params = {}

    with open(params_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Parse OpenFOAM dictionary format: "key value;"
    # Handle both "key value;" and "key value; // comment"
    pattern = r'^\s*(\w+)\s+([^;]+);'

    for line in content.split('\n'):
        # Skip comments and empty lines
        line = line.strip()
        if not line or line.startswith('//') or line.startswith('/*'):
            continue

        match = re.match(pattern, line)
        if match:
            key = match.group(1)
            value_str = match.group(2).strip()

            # Try to convert to number
            try:
                if '.' in value_str or 'e' in value_str.lower():
                    value = float(value_str)
                else:
                    value = int(value_str)
            except ValueError:
                value = value_str

            params[key] = value

    return params


def get_default_parameters() -> dict:
    """Return default parameters if file not found."""
    return {
        # Geometry
        'x_puit': 0.8,
        'y_puit': 0.128,
        'x_buse': 0.3,
        'y_buse': 0.341,
        'y_gap_buse': 0.070,
        'x_gap_buse': 0.0,
        'x_plateau': 0.4,
        # Physics
        'rho_ink': 3000,
        'eta_0': 0.5,
        'sigma': 0.040,
        # Contact angles
        'CA_substrate': 35,
        'CA_wall_isolant_left': 90,
        'CA_wall_isolant_right': 90,
        'CA_top_isolant_left': 60,
        'CA_top_isolant_right': 60,
        'CA_buse_int_left': 90,
        'CA_buse_int_right': 90,
        # Numerical
        'endTime': 0.1,
    }


def get_run_parameters(run_dir: Path) -> dict:
    """
    Extract parameters from run directory.
    First reads from system/parameters, then overrides with values from run name.
    """
    # Read base parameters from OpenFOAM file
    params = read_openfoam_parameters(run_dir)

    # Parse run name for overridden values: run_001_eta00.5_wall_isolant_left35_substrate75
    name = run_dir.name

    match = re.search(r'eta0([\d.]+)', name)
    if match:
        params['eta_0'] = float(match.group(1))

    match = re.search(r'wall_isolant_left(\d+)', name)
    if match:
        params['CA_wall_isolant_left'] = int(match.group(1))
        # wall_isolant_right reste constant (defaut 90), ne pas copier left!

    match = re.search(r'substrate(\d+)', name)
    if match:
        params['CA_substrate'] = int(match.group(1))

    return params


# =============================================================================
# ANNOTATION GENERATION - Match FEM template exactly
# =============================================================================
def create_annotation_text(params: dict, time_ms: float) -> dict:
    """
    Create annotation text matching FEM template style.

    Template layout:
    - Top left: temps, time dispense, density, viscosity, surface tension
    - Top right: ratio, hauteur buse vs well, shift buse, dimensions
    - Bottom: CA values positioned near their respective walls
    """
    # Calculate derived values
    S_puit = params.get('x_puit', 0.8) * params.get('y_puit', 0.128)
    S_buse = params.get('x_buse', 0.3) * params.get('y_buse', 0.341)
    ratio = S_buse / S_puit if S_puit > 0 else 1.0

    y_gap_um = params.get('y_gap_buse', 0.070) * 1000  # mm to um
    x_gap_um = params.get('x_gap_buse', 0.0) * 1000    # mm to um
    x_buse_um = params.get('x_buse', 0.3) * 1000      # mm to um
    y_puit_um = params.get('y_puit', 0.128) * 1000    # mm to um

    return {
        'top_left': [
            f"temps: {time_ms:.1f} ms",
            f"time dispense={params.get('endTime', 0.1)*1000:.0f} ms",
            f"density={params.get('rho_ink', 3000):.0f} kg/m3",
            f"viscosity={params.get('eta_0', 0.5):.1f} Pa.s",
            f"surface tension={params.get('sigma', 0.04)*1000:.0f} mN/m",
        ],
        'top_right': [
            f"ratio surface buse/well: {ratio:.2f}",
            f"hauteur buse vs well: {y_gap_um:.0f} um",
            f"shift buse en X vs centre: {x_gap_um:.0f} um",
            f"diam. buse= {x_buse_um:.0f}um",
            f"diam. well= {params.get('x_puit', 0.8):.2f}mm",
            f"height well= {y_puit_um:.0f}um",
        ],
        # Contact angles - positioned near walls
        'CA_top_isolant_left': params.get('CA_top_isolant_left', 60),
        'CA_top_isolant_right': params.get('CA_top_isolant_right', 60),
        'CA_wall_isolant_left': params.get('CA_wall_isolant_left', 90),
        'CA_wall_isolant_right': params.get('CA_wall_isolant_right', 90),
        'CA_substrate': params.get('CA_substrate', 35),
    }


def add_annotations(image: np.ndarray, params: dict, time_ms: float,
                    geometry_bounds: dict = None) -> np.ndarray:
    """
    Add FEM-style annotations to image.

    Args:
        image: Input image array
        params: Simulation parameters
        time_ms: Current time in milliseconds
        geometry_bounds: Dict with x_min, x_max, y_min, y_max in pixels
    """
    img = Image.fromarray(image)
    draw = ImageDraw.Draw(img)

    # Try to load a font
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", FONT_SIZE)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", FONT_SIZE - 1)
    except:
        font = ImageFont.load_default()
        font_small = font

    annotations = create_annotation_text(params, time_ms)

    # === TOP LEFT annotations === Y=120
    y = 120
    for line in annotations['top_left']:
        draw.text((10, y), line, fill='black', font=font)
        y += 14

    # === TOP RIGHT annotations === Y=120, marge droite=30
    y = 120
    for line in annotations['top_right']:
        # Right-align text avec marge 30px
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        draw.text((WIDTH - text_width - 30, y), line, fill='black', font=font)
        y += 14

    # === BOTTOM - CA values near walls ===
    # Positions fixes demandées par l'utilisateur

    # CA on plateaus (top_isolant) - X=100/500, Y=280
    draw.text((100, 280),
              f"CA={annotations['CA_top_isolant_left']:.1f}°",
              fill='black', font=font_small)
    draw.text((500, 280),
              f"CA={annotations['CA_top_isolant_right']:.1f}°",
              fill='black', font=font_small)

    # CA on vertical walls (wall_isolant) - X=130/470, Y=300
    draw.text((130, 300),
              f"CA={annotations['CA_wall_isolant_left']:.1f}°",
              fill='black', font=font_small)
    draw.text((470, 300),
              f"CA={annotations['CA_wall_isolant_right']:.1f}°",
              fill='black', font=font_small)

    # CA on substrate (center) - X=290, Y=320 (remonté)
    draw.text((290, 320),
              f"CA={annotations['CA_substrate']:.1f}°",
              fill='black', font=font_small)

    return np.array(img)


def load_wall_patches(vtk_dir: Path, time_index: str) -> list:
    """Load wall patch VTK files for a given time index."""
    wall_meshes = []

    for patch_name in WALL_PATCHES:
        patch_dir = vtk_dir / patch_name
        if not patch_dir.exists():
            continue

        # Find the matching time file
        vtk_files = list(patch_dir.glob(f"{patch_name}_{time_index}.vtk"))
        if vtk_files:
            try:
                mesh = pv.read(str(vtk_files[0]))
                wall_meshes.append((patch_name, mesh))
            except Exception:
                pass

    return wall_meshes


def compute_geometry_bounds(mesh, wall_meshes: list, params: dict = None) -> dict:
    """
    Compute pixel positions for geometry elements based on mesh bounds.
    Position CA annotations near the actual puit walls, not domain edges.
    """
    # Get mesh bounds
    bounds = mesh.bounds  # (xmin, xmax, ymin, ymax, zmin, zmax)
    x_min, x_max = bounds[0], bounds[1]
    y_min, y_max = bounds[2], bounds[3]

    # Compute scale factors (geometry to pixels)
    # Leave margins for annotations
    margin_x = 80
    margin_y_top = 100
    margin_y_bottom = 70

    plot_width = WIDTH - 2 * margin_x
    plot_height = HEIGHT - margin_y_top - margin_y_bottom

    scale_x = plot_width / (x_max - x_min) if x_max > x_min else 1
    scale_y = plot_height / (y_max - y_min) if y_max > y_min else 1
    scale = min(scale_x, scale_y)

    # Center offset
    geom_width = (x_max - x_min) * scale
    geom_height = (y_max - y_min) * scale
    offset_x = margin_x + (plot_width - geom_width) / 2
    offset_y = margin_y_top + (plot_height - geom_height) / 2

    def geom_to_pixel_x(x):
        return offset_x + (x - x_min) * scale

    def geom_to_pixel_y(y):
        # Flip Y axis (pixel Y increases downward)
        return HEIGHT - margin_y_bottom - (y - y_min) * scale

    # Get puit geometry from params (in mm, mesh is in m so convert)
    if params:
        x_puit_half_m = params.get('x_puit_half', 0.4) * 0.001  # mm to m
        y_puit_m = params.get('y_puit', 0.128) * 0.001  # mm to m
    else:
        x_puit_half_m = 0.0004  # 0.4 mm default
        y_puit_m = 0.000128  # 0.128 mm default

    # Position CA near the puit walls (not domain edges)
    # Left wall of puit is at x = -x_puit_half_m
    # Right wall of puit is at x = +x_puit_half_m
    x_left_puit_px = geom_to_pixel_x(-x_puit_half_m)
    x_right_puit_px = geom_to_pixel_x(x_puit_half_m)
    x_center_px = geom_to_pixel_x(0)
    y_substrate_px = geom_to_pixel_y(0)  # substrate is at y=0

    return {
        'x_left_wall': x_left_puit_px - 70,      # Just left of left puit wall
        'x_right_wall': x_right_puit_px + 5,     # Just right of right puit wall
        'x_center': x_center_px - 30,            # Centered under substrate
        'y_substrate': y_substrate_px - 30,      # Remonté: proche du substrat
        'y_plateau': y_substrate_px - 60,        # Remonté: proche des parois
    }


def render_vtk_frame(vtk_file: Path, params: dict, time_ms: float,
                     vtk_dir: Path = None) -> np.ndarray:
    """Render a single VTK file to an image array with wall geometry."""
    # Read VTK file
    mesh = pv.read(str(vtk_file))

    # Extract time index from filename for matching wall patches
    filename = vtk_file.stem
    time_index = filename.split('_')[-1]

    # Setup plotter
    plotter = pv.Plotter(off_screen=True, window_size=[WIDTH, HEIGHT])
    plotter.background_color = BACKGROUND

    # Add mesh with alpha.water scalar (phase field)
    if 'alpha.water' in mesh.array_names:
        # Threshold to show only liquid phase (alpha > 0.5)
        thresholded = mesh.threshold(0.5, scalars='alpha.water')
        if thresholded.n_points > 0:
            plotter.add_mesh(thresholded, color=PHASE_COLOR, show_edges=False)
    else:
        # Fallback: show full mesh
        plotter.add_mesh(mesh, color=PHASE_COLOR, opacity=0.5)

    # Add wall patches as black lines
    wall_meshes = []
    if vtk_dir:
        wall_meshes = load_wall_patches(vtk_dir, time_index)
        for patch_name, wall_mesh in wall_meshes:
            try:
                # Extract boundary edges from wall patches
                edges = wall_mesh.extract_feature_edges(
                    boundary_edges=True,
                    feature_edges=False,
                    manifold_edges=False
                )
                if edges.n_points > 0:
                    plotter.add_mesh(edges, color=WALL_COLOR, line_width=WALL_LINE_WIDTH)
            except Exception:
                pass

    # Set camera for 2D axisymmetric view (side view)
    plotter.camera_position = 'xy'
    plotter.camera.zoom(1.2)

    # Capture frame
    img = plotter.screenshot(return_img=True)
    plotter.close()

    # Compute geometry bounds for annotation positioning
    geometry_bounds = compute_geometry_bounds(mesh, wall_meshes, params)

    # Add annotations
    img_annotated = add_annotations(img, params, time_ms, geometry_bounds)

    return img_annotated


def process_run(run_dir: Path, output_dir: Path) -> tuple:
    """Process a single run: generate GIF and final PNG."""
    print(f"\nProcessing: {run_dir.name}")

    vtk_dir = run_dir / "VTK"
    if not vtk_dir.exists():
        print(f"  ERROR: VTK directory not found: {vtk_dir}")
        return None, None

    # Find all VTK files
    vtk_files = list(vtk_dir.glob("*.vtk"))

    # Filter to internal mesh files (main series, not boundary patch directories)
    internal_files = [f for f in vtk_files if re.match(r'.*_\d+\.vtk$', f.name)]

    # Sort numerically by time index
    def extract_time_index(filepath):
        match = re.search(r'_(\d+)\.vtk$', filepath.name)
        return int(match.group(1)) if match else 0

    internal_files = sorted(internal_files, key=extract_time_index)

    if not internal_files:
        print(f"  ERROR: No VTK files found in {vtk_dir}")
        return None, None

    print(f"  Found {len(internal_files)} VTK files")

    # Get parameters from run directory (reads system/parameters)
    params = get_run_parameters(run_dir)
    print(f"  Parameters loaded: eta_0={params.get('eta_0')}, "
          f"CA_substrate={params.get('CA_substrate')}, "
          f"y_gap_buse={params.get('y_gap_buse')}")

    # Render frames
    # Time step from writeInterval in parameters (default 2ms)
    write_interval = params.get('writeInterval', 0.002)
    time_step_ms = write_interval * 1000

    frames = []
    for i, vtk_file in enumerate(internal_files):
        time_ms = i * time_step_ms

        try:
            frame = render_vtk_frame(vtk_file, params, time_ms, vtk_dir=vtk_dir)
            frames.append(frame)

            if i % 10 == 0:
                print(f"  Frame {i+1}/{len(internal_files)} (t={time_ms:.1f}ms)")
        except Exception as e:
            print(f"  Warning: Could not render {vtk_file.name}: {e}")

    if not frames:
        print(f"  ERROR: No frames rendered")
        return None, None

    # Create output paths
    run_name = run_dir.name
    gif_path = output_dir / "gifs" / f"{run_name}.gif"
    png_path = output_dir / "png" / f"{run_name}.png"

    # Ensure output directories exist
    gif_path.parent.mkdir(parents=True, exist_ok=True)
    png_path.parent.mkdir(parents=True, exist_ok=True)

    # Save GIF
    print(f"  Saving GIF: {gif_path}")
    imageio.mimsave(str(gif_path), frames, fps=FPS, loop=0)

    # Save final frame as PNG
    print(f"  Saving PNG: {png_path}")
    Image.fromarray(frames[-1]).save(str(png_path))

    return gif_path, png_path


def process_study(study_name: str):
    """Process all runs in a study."""
    study_dir = RESULTS_DIR / study_name

    if not study_dir.exists():
        print(f"ERROR: Study not found: {study_dir}")
        return

    # Find all run directories
    run_dirs = sorted([d for d in study_dir.iterdir()
                       if d.is_dir() and d.name.startswith('run_')])

    print(f"=== Processing Study: {study_name} ===")
    print(f"Found {len(run_dirs)} runs")

    results = []
    for run_dir in run_dirs:
        gif_path, png_path = process_run(run_dir, study_dir)
        if gif_path:
            results.append({
                'run': run_dir.name,
                'gif': str(gif_path),
                'png': str(png_path),
                'parameters': get_run_parameters(run_dir)
            })

    # Save results summary
    summary_file = study_dir / "visual_outputs.json"
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n=== Summary ===")
    print(f"GIFs generated: {len([r for r in results if r['gif']])}")
    print(f"PNGs generated: {len([r for r in results if r['png']])}")
    print(f"Output directory: {study_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate Streamlit-compatible GIFs/PNGs from VOF results")
    parser.add_argument('--study', help='Study name to process')
    parser.add_argument('--run', help='Single run directory to process')

    args = parser.parse_args()

    if args.study:
        process_study(args.study)
    elif args.run:
        run_dir = Path(args.run)
        output_dir = run_dir.parent
        process_run(run_dir, output_dir)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
