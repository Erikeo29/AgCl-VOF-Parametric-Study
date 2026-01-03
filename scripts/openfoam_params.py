#!/usr/bin/env python3
"""
OpenFOAM Parameters Reader Module

Reads parameters from OpenFOAM system/parameters file.
This module should be used by ALL scripts to avoid hardcoded values.

Usage:
    from openfoam_params import read_parameters, get_parameter

    params = read_parameters(case_dir)
    rho = get_parameter(params, 'rho_ink', default=3000)
"""

import re
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"


def read_parameters(case_dir: Path = None) -> dict:
    """
    Read parameters from OpenFOAM system/parameters file.

    Args:
        case_dir: Path to OpenFOAM case directory.
                  If None, reads from templates.

    Returns:
        Dictionary with all parameters
    """
    params_file = None

    if case_dir:
        case_dir = Path(case_dir)
        params_file = case_dir / "system" / "parameters"

    # Fallback to templates
    if params_file is None or not params_file.exists():
        params_file = TEMPLATES_DIR / "system" / "parameters"

    if not params_file.exists():
        print(f"Warning: parameters file not found at {params_file}")
        return get_default_parameters()

    params = {}

    with open(params_file, 'r') as f:
        content = f.read()

    # Parse OpenFOAM dictionary format: "key value;"
    # Handle: "key value;" and "key value; // comment"
    pattern = r'^\s*(\w+)\s+([^;]+);'

    for line in content.split('\n'):
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


def get_parameter(params: dict, key: str, default=None):
    """
    Get a parameter value with fallback to default.

    Args:
        params: Parameters dictionary
        key: Parameter name
        default: Default value if key not found

    Returns:
        Parameter value or default
    """
    return params.get(key, default)


def get_default_parameters() -> dict:
    """
    Return default parameters.
    These should match the values in templates/system/parameters.
    """
    return {
        # Geometry [mm]
        'x_puit': 0.8,
        'x_puit_half': 0.4,
        'y_puit': 0.128,
        'x_plateau': 0.4,
        'x_buse': 0.3,
        'x_buse_half': 0.15,
        'y_buse': 0.341,
        'y_gap_buse': 0.070,
        'x_gap_buse': 0.0,
        'y_air': 0.080,
        'x_isolant': 0.8,
        'y_buse_bottom': 0.198,
        'y_buse_top': 0.539,
        'y_air_top': 0.278,

        # Physics - Ink
        'rho_ink': 3000,        # kg/m³
        'eta_0': 0.5,           # Pa.s
        'eta_inf': 0.167,       # Pa.s
        'lambda': 0.15,         # s
        'n_carreau': 0.7,       # -
        'nu_0': 1.667e-4,       # m²/s
        'nu_inf': 5.567e-5,     # m²/s
        'sigma': 0.040,         # N/m

        # Physics - Air
        'rho_air': 1.2,         # kg/m³
        'mu_air': 1e-5,         # Pa.s
        'nu_air': 8.33e-6,      # m²/s

        # Contact angles [degrees]
        'CA_substrate': 35,
        'CA_wall_isolant_left': 90,
        'CA_wall_isolant_right': 90,
        'CA_top_isolant_left': 60,
        'CA_top_isolant_right': 60,
        'CA_buse_int_left': 90,
        'CA_buse_int_right': 90,
        'CA_buse_ext_left': 180,
        'CA_buse_ext_right': 180,

        # Numerical
        'endTime': 0.1,         # s
        'writeInterval': 0.002, # s
        'deltaT': 1e-6,         # s
        'maxCo': 0.3,
        'maxAlphaCo': 0.3,
        'maxDeltaT': 1e-3,      # s

        # Mesh
        'cell_size': 5.0,       # um
    }


def compute_derived_parameters(params: dict) -> dict:
    """
    Compute derived parameters from base parameters.

    Args:
        params: Base parameters dictionary

    Returns:
        Dictionary with derived parameters added
    """
    derived = params.copy()

    # Surface calculations [mm²]
    S_puit = params.get('x_puit', 0.8) * params.get('y_puit', 0.128)
    S_buse = params.get('x_buse', 0.3) * params.get('y_buse', 0.341)
    derived['S_puit'] = S_puit
    derived['S_buse'] = S_buse
    derived['ratio_surface'] = S_buse / S_puit if S_puit > 0 else 1.0

    # Kinematic viscosities [m²/s]
    rho = params.get('rho_ink', 3000)
    eta_0 = params.get('eta_0', 0.5)
    eta_inf = params.get('eta_inf', 0.167)
    derived['nu_0_calc'] = eta_0 / rho
    derived['nu_inf_calc'] = eta_inf / rho

    return derived


# Convenience functions for common parameters
def get_rho_ink(params: dict = None) -> float:
    """Get ink density [kg/m³]."""
    if params is None:
        params = read_parameters()
    return get_parameter(params, 'rho_ink', 3000)


def get_eta_0(params: dict = None) -> float:
    """Get zero-shear viscosity [Pa.s]."""
    if params is None:
        params = read_parameters()
    return get_parameter(params, 'eta_0', 0.5)


def get_sigma(params: dict = None) -> float:
    """Get surface tension [N/m]."""
    if params is None:
        params = read_parameters()
    return get_parameter(params, 'sigma', 0.040)


def get_geometry(params: dict = None) -> dict:
    """Get geometry parameters [mm]."""
    if params is None:
        params = read_parameters()
    return {
        'x_puit': get_parameter(params, 'x_puit', 0.8),
        'y_puit': get_parameter(params, 'y_puit', 0.128),
        'x_buse': get_parameter(params, 'x_buse', 0.3),
        'y_buse': get_parameter(params, 'y_buse', 0.341),
        'y_gap_buse': get_parameter(params, 'y_gap_buse', 0.070),
        'x_gap_buse': get_parameter(params, 'x_gap_buse', 0.0),
        'x_plateau': get_parameter(params, 'x_plateau', 0.4),
    }


def get_contact_angles(params: dict = None) -> dict:
    """Get contact angles [degrees]."""
    if params is None:
        params = read_parameters()
    return {
        'CA_substrate': get_parameter(params, 'CA_substrate', 35),
        'CA_wall_isolant_left': get_parameter(params, 'CA_wall_isolant_left', 90),
        'CA_wall_isolant_right': get_parameter(params, 'CA_wall_isolant_right', 90),
        'CA_top_isolant_left': get_parameter(params, 'CA_top_isolant_left', 60),
        'CA_top_isolant_right': get_parameter(params, 'CA_top_isolant_right', 60),
        'CA_buse_int_left': get_parameter(params, 'CA_buse_int_left', 90),
        'CA_buse_int_right': get_parameter(params, 'CA_buse_int_right', 90),
        'CA_buse_ext_left': get_parameter(params, 'CA_buse_ext_left', 180),
        'CA_buse_ext_right': get_parameter(params, 'CA_buse_ext_right', 180),
    }


if __name__ == "__main__":
    # Test: read and display parameters
    print("=== OpenFOAM Parameters Reader Test ===\n")

    params = read_parameters()

    print("Geometry:")
    geom = get_geometry(params)
    for k, v in geom.items():
        print(f"  {k}: {v} mm")

    print("\nPhysics:")
    print(f"  rho_ink: {get_rho_ink(params)} kg/m³")
    print(f"  eta_0: {get_eta_0(params)} Pa.s")
    print(f"  sigma: {get_sigma(params)*1000} mN/m")

    print("\nContact Angles:")
    ca = get_contact_angles(params)
    for k, v in ca.items():
        print(f"  {k}: {v}°")

    print("\nDerived:")
    derived = compute_derived_parameters(params)
    print(f"  S_puit: {derived['S_puit']:.4f} mm²")
    print(f"  S_buse: {derived['S_buse']:.4f} mm²")
    print(f"  ratio: {derived['ratio_surface']:.2%}")
