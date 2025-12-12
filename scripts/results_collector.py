#!/usr/bin/env python3
"""
Results Collector for Parametric Studies
=========================================
Extrait les métriques de toutes les simulations d'une étude.

Usage:
    python3 results_collector.py --study study_name
    python3 results_collector.py --study study_name --plot
"""

import argparse
import json
import csv
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"


def collect_results(study_name: str, generate_plots: bool = False):
    """Collecte les résultats d'une étude."""
    study_dir = RESULTS_DIR / study_name
    
    if not study_dir.exists():
        print(f"❌ Étude non trouvée: {study_dir}")
        return
    
    # Charger la config
    config_file = study_dir / "study_config.yaml"
    if config_file.exists():
        import yaml
        with open(config_file) as f:
            config = yaml.safe_load(f)
    else:
        config = {}
    
    # Trouver tous les runs
    runs = sorted(study_dir.glob("run_*"))
    
    if not runs:
        print(f"❌ Aucun run trouvé dans {study_dir}")
        return
    
    print(f"\n=== COLLECTE: {study_name} ===")
    print(f"Runs trouvés: {len(runs)}")
    
    results = []
    
    for run_dir in runs:
        run_data = {'name': run_dir.name}
        
        # Extraire la valeur du paramètre depuis le nom
        parts = run_dir.name.split('_')
        if len(parts) >= 4:
            run_data['param_value'] = parts[-1]
        
        # Vérifier le status
        log_file = run_dir / "run.log"
        if log_file.exists():
            content = log_file.read_text()
            if "End" in content:
                run_data['status'] = "OK"
                # Extraire le temps final
                for line in content.split('\n'):
                    if line.startswith("Time = "):
                        try:
                            run_data['final_time'] = float(line.split('=')[1].strip())
                        except:
                            pass
            elif "FOAM FATAL" in content:
                run_data['status'] = "ERROR"
            else:
                run_data['status'] = "RUNNING"
        else:
            run_data['status'] = "NO_LOG"
        
        # Chercher les derniers résultats temporels
        time_dirs = [d for d in run_dir.iterdir() if d.is_dir() and d.name.replace('.', '').isdigit()]
        if time_dirs:
            last_time = max(time_dirs, key=lambda d: float(d.name))
            run_data['last_timestep'] = last_time.name
        
        results.append(run_data)
        
        status_icon = "✅" if run_data['status'] == "OK" else "❌" if run_data['status'] == "ERROR" else "🔄"
        print(f"  {status_icon} {run_dir.name}: {run_data.get('status', '?')}")
    
    # Sauvegarder en CSV
    csv_file = study_dir / "results_summary.csv"
    if results:
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        print(f"\n📊 Résumé sauvegardé: {csv_file}")
    
    # Générer plots si demandé
    if generate_plots:
        print("\n⚠️ Génération de plots non implémentée (requires matplotlib)")
        print("   Utilisez ParaView pour visualiser les résultats")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Collecte les résultats d'une étude paramétrique")
    parser.add_argument('--study', required=True, help='Nom de l\'étude')
    parser.add_argument('--plot', action='store_true', help='Générer des graphiques')
    
    args = parser.parse_args()
    collect_results(args.study, args.plot)


if __name__ == "__main__":
    main()
