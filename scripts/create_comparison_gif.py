#!/usr/bin/env python3
"""
Génère une mosaïque GIF comparant toutes les simulations d'une étude paramétrique.

Usage:
    python3 create_comparison_gif.py --study <study_name>
    python3 create_comparison_gif.py --study example_viscosity_sweep
"""

import argparse
import pyvista as pv
import numpy as np
from pathlib import Path
import imageio
import json
import yaml

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"


def get_vtk_files(case_path):
    """Récupère les fichiers VTK triés par temps."""
    vtk_dir = case_path / "VTK"
    if not vtk_dir.exists():
        return []
    files = sorted(vtk_dir.glob("*_*.vtk"), key=lambda f: float(f.stem.split('_')[-1]))
    return files


def get_study_info(study_name):
    """Récupère les infos de l'étude depuis le YAML."""
    study_dir = RESULTS_DIR / study_name
    config_file = study_dir / "study_config.yaml"
    
    if config_file.exists():
        with open(config_file) as f:
            config = yaml.safe_load(f)
        return config
    return {}


def create_frame(vtk_files_per_case, frame_idx, labels):
    """Crée une frame avec toutes les simulations côte à côte."""
    pv.set_plot_theme('document')
    
    n_cases = len(vtk_files_per_case)
    
    # Adapter le layout selon le nombre de cas
    if n_cases <= 5:
        shape = (1, n_cases)
        window_size = (300 * n_cases, 400)
    else:
        cols = min(5, n_cases)
        rows = (n_cases + cols - 1) // cols
        shape = (rows, cols)
        window_size = (300 * cols, 400 * rows)
    
    plotter = pv.Plotter(shape=shape, off_screen=True, window_size=window_size)
    
    for i, (vtk_files, label) in enumerate(zip(vtk_files_per_case, labels)):
        if n_cases <= 5:
            row, col = 0, i
        else:
            row, col = i // 5, i % 5
        
        plotter.subplot(row, col)
        
        if frame_idx < len(vtk_files):
            mesh = pv.read(vtk_files[frame_idx])
            if 'alpha.water' in mesh.array_names:
                plotter.add_mesh(mesh, scalars='alpha.water', cmap='coolwarm', 
                               clim=[0, 1], show_scalar_bar=False)
            else:
                plotter.add_mesh(mesh, color='lightblue')
        
        plotter.add_text(label, position='upper_edge', font_size=10, color='black')
        plotter.view_xy()
        plotter.camera.zoom(1.2)
    
    img = plotter.screenshot(return_img=True)
    plotter.close()
    return img


def main():
    parser = argparse.ArgumentParser(description="Génère un GIF comparatif pour une étude paramétrique")
    parser.add_argument('--study', required=True, help='Nom de l\'étude')
    parser.add_argument('--fps', type=int, default=5, help='Images par seconde (défaut: 5)')
    args = parser.parse_args()
    
    study_dir = RESULTS_DIR / args.study
    
    if not study_dir.exists():
        print(f"❌ Étude non trouvée: {study_dir}")
        return
    
    # Récupérer les infos de l'étude
    config = get_study_info(args.study)
    param_name = config.get('sweep', {}).get('parameter', 'param').split('.')[-1]
    
    # Trouver tous les runs
    runs = sorted(study_dir.glob("run_*"))
    
    if not runs:
        print(f"❌ Aucun run trouvé dans {study_dir}")
        return
    
    print(f"=== Génération GIF comparatif: {args.study} ===")
    print(f"Runs trouvés: {len(runs)}")
    
    # Charger les fichiers VTK
    vtk_files_per_case = []
    labels = []
    
    for run_dir in runs:
        vtk_files = get_vtk_files(run_dir)
        if not vtk_files:
            print(f"  ⚠️ Pas de VTK pour {run_dir.name} - lancez foamToVTK d'abord")
            continue
        
        vtk_files_per_case.append(vtk_files)
        
        # Extraire la valeur du paramètre depuis le nom du run
        parts = run_dir.name.split('_')
        if len(parts) >= 3:
            value = parts[-1]
            label = f"{param_name}={value}"
        else:
            label = run_dir.name
        
        labels.append(label)
        print(f"  ✓ {run_dir.name}: {len(vtk_files)} fichiers VTK")
    
    if not vtk_files_per_case:
        print("❌ Aucun fichier VTK trouvé. Lancez d'abord:")
        print(f"   for run in results/{args.study}/run_*; do foamToVTK -case \"$run\"; done")
        return
    
    # Nombre de frames = minimum parmi tous les cas
    n_frames = min(len(f) for f in vtk_files_per_case)
    
    # Sous-échantillonner pour avoir ~30 frames max
    step = max(1, n_frames // 30)
    frame_indices = list(range(0, n_frames, step))
    
    print(f"\nGénération de {len(frame_indices)} frames...")
    
    frames = []
    for i, idx in enumerate(frame_indices):
        print(f"  Frame {i+1}/{len(frame_indices)}", end='\r')
        img = create_frame(vtk_files_per_case, idx, labels)
        frames.append(img)
    
    print(f"\nSauvegarde du GIF...")
    
    # Créer le dossier comparison
    output_dir = study_dir / "comparison"
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / f"{args.study}_comparison.gif"
    duration = 1.0 / args.fps
    imageio.mimsave(output_file, frames, duration=duration, loop=0)
    
    print(f"\n✅ GIF créé: {output_file}")
    print(f"   Taille: {output_file.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
