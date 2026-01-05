#!/usr/bin/env python3
"""
Overflow Analysis Script
========================
Analyse quantitative de l'overflow depuis les donnees VTK.

Mesure l'extension de l'encre (alpha > seuil) et compare avec les bords du puit
pour determiner s'il y a overflow et de combien.

Usage:
    python3 analyze_overflow.py --run results/study/run_001
    python3 analyze_overflow.py --study study_name
    python3 analyze_overflow.py --study study_name --update-csv
"""

import argparse
import sys
from pathlib import Path
import numpy as np

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))
from openfoam_params import read_parameters

# Geometry constants (from parameters)
X_PUIT_HALF = 0.4  # mm - demi-largeur du puit
X_PUIT_LEFT = -X_PUIT_HALF  # mm - bord gauche du puit
X_PUIT_RIGHT = X_PUIT_HALF   # mm - bord droit du puit


def analyze_overflow_vtk(run_dir: Path, alpha_threshold: float = 0.5) -> dict:
    """
    Analyse l'overflow depuis les fichiers VTK.

    Args:
        run_dir: Chemin vers le dossier run
        alpha_threshold: Seuil alpha pour considerer comme encre (default 0.5)

    Returns:
        dict avec:
            - ink_x_min: Extension min X de l'encre [mm]
            - ink_x_max: Extension max X de l'encre [mm]
            - overflow_left: Distance overflow gauche [um] (>0 si overflow)
            - overflow_right: Distance overflow droite [um] (>0 si overflow)
            - has_overflow_left: bool
            - has_overflow_right: bool
            - time: Temps de la mesure [s]
    """
    try:
        import pyvista as pv
    except ImportError:
        print("Error: PyVista required. Install with: pip install pyvista")
        return None

    run_dir = Path(run_dir)
    vtk_dir = run_dir / "VTK"

    if not vtk_dir.exists():
        print(f"  Warning: VTK directory not found: {vtk_dir}")
        return None

    # Trouver les fichiers VTK (format OpenFOAM: run_XXX_stepNUM.vtk)
    vtk_files = list(vtk_dir.glob("run_*.vtk"))
    if not vtk_files:
        vtk_files = list(vtk_dir.glob("*.vtk"))

    if not vtk_files:
        print(f"  Warning: No VTK files found in {vtk_dir}")
        return None

    # Trier par numero de step (dernier element apres _)
    def get_step_num(f):
        try:
            return int(f.stem.split('_')[-1])
        except:
            return 0

    vtk_files = sorted(vtk_files, key=get_step_num)

    # Prendre le dernier fichier (temps final)
    last_vtk = vtk_files[-1]

    # Le temps sera lu depuis le fichier de simulation
    time_s = None

    # Lire les parametres pour avoir les vraies dimensions
    params = read_parameters(run_dir)
    x_puit_half = params.get('x_puit_half', X_PUIT_HALF)
    x_puit_left = -x_puit_half
    x_puit_right = x_puit_half

    # Lire le fichier VTK
    try:
        mesh = pv.read(last_vtk)
    except Exception as e:
        print(f"  Error reading VTK: {e}")
        return None

    # Chercher le champ alpha
    alpha_field = None
    for name in ['alpha.water', 'alpha_water', 'alpha']:
        if name in mesh.array_names:
            alpha_field = name
            break

    if alpha_field is None:
        # Essayer dans cell_data
        for name in mesh.cell_data.keys():
            if 'alpha' in name.lower():
                alpha_field = name
                break

    if alpha_field is None:
        print(f"  Warning: Alpha field not found. Available: {mesh.array_names}")
        return None

    # Extraire les cellules avec encre (alpha > seuil)
    alpha = mesh[alpha_field]

    # Obtenir les centres des cellules
    if hasattr(mesh, 'cell_centers'):
        centers = mesh.cell_centers().points
    else:
        centers = mesh.points

    # Filtrer les cellules avec encre
    ink_mask = alpha > alpha_threshold

    if not np.any(ink_mask):
        print(f"  Warning: No ink found (alpha > {alpha_threshold})")
        return {
            'ink_x_min': None,
            'ink_x_max': None,
            'overflow_left_um': 0,
            'overflow_right_um': 0,
            'has_overflow_left': False,
            'has_overflow_right': False,
            'time_s': time_s
        }

    ink_centers = centers[ink_mask]

    # Coordonnees X de l'encre (en metres dans OpenFOAM)
    ink_x = ink_centers[:, 0]

    # Convertir en mm (OpenFOAM utilise metres)
    ink_x_mm = ink_x * 1000

    ink_x_min = np.min(ink_x_mm)
    ink_x_max = np.max(ink_x_mm)

    # Calculer overflow (en um)
    # Overflow gauche: si encre depasse x_puit_left (vers la gauche, donc negatif)
    overflow_left_um = max(0, (x_puit_left - ink_x_min) * 1000)

    # Overflow droit: si encre depasse x_puit_right (vers la droite)
    overflow_right_um = max(0, (ink_x_max - x_puit_right) * 1000)

    return {
        'ink_x_min_mm': ink_x_min,
        'ink_x_max_mm': ink_x_max,
        'overflow_left_um': overflow_left_um,
        'overflow_right_um': overflow_right_um,
        'has_overflow_left': overflow_left_um > 0,
        'has_overflow_right': overflow_right_um > 0,
        'time_s': time_s,
        'x_puit_left_mm': x_puit_left,
        'x_puit_right_mm': x_puit_right
    }


def analyze_run(run_dir: Path, verbose: bool = True) -> dict:
    """Analyse un run et affiche les resultats."""
    run_dir = Path(run_dir)
    run_name = run_dir.name

    if verbose:
        print(f"\n=== Analyse: {run_name} ===")

    result = analyze_overflow_vtk(run_dir)

    if result is None:
        if verbose:
            print("  ❌ Analyse impossible")
        return None

    if verbose:
        print(f"  Temps: {result['time_s']:.3f} s" if result['time_s'] else "  Temps: N/A")
        print(f"  Extension encre X: [{result['ink_x_min_mm']:.3f}, {result['ink_x_max_mm']:.3f}] mm")
        print(f"  Bords puit: [{result['x_puit_left_mm']:.3f}, {result['x_puit_right_mm']:.3f}] mm")

        if result['has_overflow_left']:
            print(f"  ✓ OVERFLOW GAUCHE: {result['overflow_left_um']:.1f} µm")
        else:
            print(f"  ✗ Pas d'overflow gauche")

        if result['has_overflow_right']:
            print(f"  ✓ OVERFLOW DROIT: {result['overflow_right_um']:.1f} µm")
        else:
            print(f"  ✗ Pas d'overflow droit")

    return result


def analyze_study(study_name: str, update_csv: bool = False) -> list:
    """Analyse tous les runs d'une etude."""
    project_root = Path(__file__).parent.parent
    study_dir = project_root / "results" / study_name

    if not study_dir.exists():
        print(f"Error: Study not found: {study_dir}")
        return []

    runs = sorted([d for d in study_dir.iterdir() if d.is_dir() and d.name.startswith('run_')])

    print(f"\n{'='*60}")
    print(f"ANALYSE OVERFLOW: {study_name}")
    print(f"{'='*60}")
    print(f"Runs: {len(runs)}")

    results = []
    for run_dir in runs:
        result = analyze_run(run_dir, verbose=True)
        if result:
            result['run_name'] = run_dir.name
            results.append(result)

    # Resume
    print(f"\n{'='*60}")
    print("RESUME")
    print(f"{'='*60}")

    overflow_left_count = sum(1 for r in results if r.get('has_overflow_left'))
    overflow_right_count = sum(1 for r in results if r.get('has_overflow_right'))

    print(f"Overflow gauche: {overflow_left_count}/{len(results)} runs")
    print(f"Overflow droit: {overflow_right_count}/{len(results)} runs")

    # Tableau resume
    print(f"\n{'Run':<60} {'OV Left':>10} {'OV Right':>10}")
    print("-" * 82)
    for r in results:
        left = f"{r['overflow_left_um']:.1f} µm" if r['has_overflow_left'] else "-"
        right = f"{r['overflow_right_um']:.1f} µm" if r['has_overflow_right'] else "-"
        # Truncate run name
        name = r['run_name'][:58] + ".." if len(r['run_name']) > 60 else r['run_name']
        print(f"{name:<60} {left:>10} {right:>10}")

    # Mise a jour CSV si demande
    if update_csv:
        update_study_csv(study_name, results)

    return results


def update_study_csv(study_name: str, results: list):
    """Met a jour le CSV de l'etude avec les colonnes overflow."""
    import csv

    project_root = Path(__file__).parent.parent
    csv_path = project_root / "results" / study_name / "simulations.csv"

    if not csv_path.exists():
        print(f"\nWarning: CSV not found: {csv_path}")
        return

    # Lire le CSV existant
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames.copy()

    # Ajouter les nouvelles colonnes si necessaire
    new_fields = ['overflow_left_um', 'overflow_right_um', 'has_overflow']
    for field in new_fields:
        if field not in fieldnames:
            fieldnames.append(field)

    # Creer un dict des resultats par run_name
    results_dict = {r['run_name']: r for r in results}

    # Mettre a jour les rows
    for row in rows:
        run_name = row.get('run_name', '')
        if run_name in results_dict:
            r = results_dict[run_name]
            row['overflow_left_um'] = f"{r['overflow_left_um']:.1f}"
            row['overflow_right_um'] = f"{r['overflow_right_um']:.1f}"
            row['has_overflow'] = 'YES' if (r['has_overflow_left'] or r['has_overflow_right']) else 'NO'
        else:
            row['overflow_left_um'] = ''
            row['overflow_right_um'] = ''
            row['has_overflow'] = ''

    # Ecrire le CSV mis a jour
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n✓ CSV mis a jour: {csv_path}")


def main():
    parser = argparse.ArgumentParser(description='Analyse overflow depuis VTK')
    parser.add_argument('--run', type=str, help='Chemin vers un run specifique')
    parser.add_argument('--study', type=str, help='Nom de l\'etude a analyser')
    parser.add_argument('--update-csv', action='store_true', help='Mettre a jour le CSV avec les resultats')
    parser.add_argument('--threshold', type=float, default=0.5, help='Seuil alpha (default: 0.5)')

    args = parser.parse_args()

    if args.run:
        analyze_run(Path(args.run))
    elif args.study:
        analyze_study(args.study, update_csv=args.update_csv)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
