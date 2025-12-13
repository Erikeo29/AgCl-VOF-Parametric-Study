#!/usr/bin/env python3
"""
Parametric Study Runner for OpenFOAM VOF Simulations
=====================================================
Interface type COMSOL pour lancer des études paramétriques.

Usage:
    python3 parametric_runner.py create --name study_name
    python3 parametric_runner.py run --study study_name
    python3 parametric_runner.py status --study study_name
    python3 parametric_runner.py list
"""

import argparse
import yaml
import os
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import json

# =============================================================================
# CONFIGURATION
# =============================================================================
PROJECT_ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
CONFIG_DIR = PROJECT_ROOT / "config"
RESULTS_DIR = PROJECT_ROOT / "results"
LOGS_DIR = PROJECT_ROOT / "logs"

# =============================================================================
# PARAMETER MODIFIER
# =============================================================================
class ParameterModifier:
    """Modifie les fichiers OpenFOAM selon les paramètres YAML."""
    
    def __init__(self, case_dir: Path):
        self.case_dir = case_dir
    
    def set_parameter(self, param_path: str, value):
        """
        Modifie un paramètre dans les fichiers OpenFOAM.
        
        Args:
            param_path: Chemin pointé (ex: 'rheology.eta0')
            value: Nouvelle valeur
        """
        section, param = param_path.split('.', 1)
        
        if section == 'rheology':
            self._modify_transport_properties(param, value)
        elif section == 'contact_angles':
            self._modify_alpha_water(param, value)
        elif section == 'surface':
            self._modify_surface_tension(param, value)
        elif section == 'numerical':
            self._modify_control_dict(param, value)
        elif section == 'process':
            self._modify_process(param, value)
        else:
            print(f"Warning: Section '{section}' non supportée")
    
    def _modify_transport_properties(self, param: str, value):
        """Modifie les fichiers de rhéologie OpenFOAM 13.

        OpenFOAM 13 avec incompressibleVoF utilise:
        - constant/momentumTransport.water → modèle BirdCarreau (nu0, nuInf, k, n)
        - constant/physicalProperties.water → viscosité de base (nu)

        IMPORTANT: Conversion viscosité dynamique → cinématique
        - eta0, eta_inf sont en Pa·s (viscosité dynamique)
        - OpenFOAM attend nu0, nuInf, nu en m²/s (viscosité cinématique)
        - Conversion: nu = eta / rho (avec rho = 3000 kg/m³ pour encre Ag/AgCl)
        """
        import re

        # Densité de l'encre Ag/AgCl (kg/m³)
        RHO_INK = 3000.0

        # Mapping des paramètres Carreau
        param_map = {
            'eta0': 'nu0',
            'eta_inf': 'nuInf',
            'lambda': 'k',
            'n': 'n'
        }

        of_param = param_map.get(param, param)

        # Conversion pour les viscosités (Pa·s → m²/s)
        if param in ['eta0', 'eta_inf']:
            nu_value = value / RHO_INK
            print(f"  → Conversion: η = {value} Pa·s → ν = {nu_value:.6e} m²/s (ρ = {RHO_INK} kg/m³)")
            formatted_value = f"{nu_value:.6e}"
        else:
            formatted_value = str(value)

        # =====================================================================
        # 1. Modifier momentumTransport.water (fichier principal pour Carreau)
        # =====================================================================
        momentum_file = self.case_dir / "constant" / "momentumTransport.water"
        if momentum_file.exists():
            content = momentum_file.read_text()
            pattern = rf'({of_param}\s+)[^;]+(;)'
            new_content = re.sub(pattern, rf'\g<1>{formatted_value}\2', content)
            momentum_file.write_text(new_content)
            print(f"  ✓ {of_param} = {formatted_value} dans momentumTransport.water")
        else:
            print(f"  ⚠ momentumTransport.water non trouvé")

        # =====================================================================
        # 2. Modifier physicalProperties.water (viscosité de base nu)
        # =====================================================================
        if param == 'eta0':
            phys_file = self.case_dir / "constant" / "physicalProperties.water"
            if phys_file.exists():
                content = phys_file.read_text()
                pattern = r'(nu\s+)[^;]+(;)'
                new_content = re.sub(pattern, rf'\g<1>{formatted_value}\2', content)
                phys_file.write_text(new_content)
                print(f"  ✓ nu = {formatted_value} dans physicalProperties.water")

        # =====================================================================
        # 3. Modifier transportProperties (rétrocompatibilité)
        # =====================================================================
        transport_file = self.case_dir / "constant" / "transportProperties"
        if transport_file.exists():
            content = transport_file.read_text()
            pattern = rf'({of_param}\s+)[^;]+(;)'
            new_content = re.sub(pattern, rf'\g<1>{formatted_value}\2', content)
            transport_file.write_text(new_content)
            print(f"  ✓ {of_param} = {formatted_value} dans transportProperties")
    
    def _modify_alpha_water(self, surface: str, angle: float):
        """Modifie 0/alpha.water pour les angles de contact."""
        file_path = self.case_dir / "0" / "alpha.water"
        if not file_path.exists():
            print(f"Warning: {file_path} not found")
            return
        
        content = file_path.read_text()
        
        # Chercher le bloc de la surface et modifier theta0
        import re
        # Pattern pour trouver theta0 dans le bloc de la surface
        pattern = rf'({surface}\s*\{{[^}}]*theta0\s+)\d+(\s*;[^}}]*\}})'
        replacement = rf'\g<1>{int(angle)}\2'
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        file_path.write_text(new_content)
        print(f"  ✓ {surface} theta0 = {angle}° dans alpha.water")
    
    def _modify_surface_tension(self, param: str, value):
        """Modifie la tension de surface."""
        file_path = self.case_dir / "constant" / "transportProperties"
        if not file_path.exists():
            return
        
        content = file_path.read_text()
        import re
        pattern = r'(sigma\s+)[^;]+(;)'
        replacement = rf'\g<1>{value}\2'
        new_content = re.sub(pattern, replacement, content)
        file_path.write_text(new_content)
        print(f"  ✓ sigma = {value} N/m")
    
    def _modify_control_dict(self, param: str, value):
        """Modifie system/controlDict."""
        file_path = self.case_dir / "system" / "controlDict"
        if not file_path.exists():
            return
        
        content = file_path.read_text()
        import re
        pattern = rf'({param}\s+)[^;]+(;)'
        replacement = rf'\g<1>{value}\2'
        new_content = re.sub(pattern, replacement, content)
        file_path.write_text(new_content)
        print(f"  ✓ {param} = {value} dans controlDict")
    
    def _modify_process(self, param: str, value):
        """Modifie les paramètres de processus."""
        if param == 'end_time':
            self._modify_control_dict('endTime', value)
        elif param == 'dispense_time':
            # Modifier setFieldsDict ou autre selon implémentation
            print(f"  ⚠ dispense_time: modification manuelle requise")


# =============================================================================
# STUDY RUNNER
# =============================================================================
class StudyRunner:
    """Gestionnaire d'études paramétriques."""
    
    def __init__(self):
        self.ensure_dirs()
    
    def ensure_dirs(self):
        """Crée les dossiers nécessaires."""
        RESULTS_DIR.mkdir(exist_ok=True)
        LOGS_DIR.mkdir(exist_ok=True)
        (CONFIG_DIR / "studies").mkdir(parents=True, exist_ok=True)
    
    def list_studies(self):
        """Liste toutes les études disponibles."""
        studies_dir = CONFIG_DIR / "studies"
        studies = list(studies_dir.glob("*.yaml"))
        
        print("\n=== ÉTUDES PARAMÉTRIQUES DISPONIBLES ===\n")
        if not studies:
            print("Aucune étude définie.")
            print(f"Créez une étude avec: python3 {sys.argv[0]} create --name <nom>")
            return
        
        for study_file in sorted(studies):
            with open(study_file) as f:
                config = yaml.safe_load(f)
            
            name = config.get('name', study_file.stem)
            desc = config.get('description', 'Pas de description')
            sweep = config.get('sweep', {})
            param = sweep.get('parameter', '?')
            values = sweep.get('values', [])
            
            # Vérifier si des résultats existent
            results_path = RESULTS_DIR / name
            status = "✅ Terminée" if results_path.exists() else "⏳ Non exécutée"
            
            print(f"📊 {name}")
            print(f"   Description: {desc}")
            print(f"   Paramètre: {param}")
            print(f"   Valeurs: {values}")
            print(f"   Status: {status}")
            print()
    
    def create_study(self, name: str):
        """Crée un template d'étude."""
        study_file = CONFIG_DIR / "studies" / f"{name}.yaml"
        
        if study_file.exists():
            print(f"❌ L'étude '{name}' existe déjà: {study_file}")
            return
        
        template = f"""# =============================================================================
# ÉTUDE PARAMÉTRIQUE: {name}
# =============================================================================
name: {name}
description: Description de l'étude

base: ../base_parameters.yaml

sweep:
  parameter: rheology.eta0  # Paramètre à varier
  values: [0.5, 1.0, 1.5, 2.0]  # Valeurs à tester

outputs:
  - spreading_diameter
  - contact_angle_left
  - contact_angle_right

execution:
  parallel: false
  timeout: 3600

postprocessing:
  generate_animations: true
  comparison_plots: true
  export_csv: true
"""
        study_file.write_text(template)
        print(f"✅ Étude créée: {study_file}")
        print(f"   Éditez ce fichier pour configurer votre étude.")
    
    def run_study(self, study_name: str, dry_run: bool = False):
        """Exécute une étude paramétrique."""
        study_file = CONFIG_DIR / "studies" / f"{study_name}.yaml"
        
        if not study_file.exists():
            print(f"❌ Étude non trouvée: {study_file}")
            return
        
        with open(study_file) as f:
            config = yaml.safe_load(f)
        
        sweep = config.get('sweep', {})
        param_path = sweep.get('parameter')
        values = sweep.get('values', [])
        
        if not param_path or not values:
            print("❌ Configuration sweep invalide")
            return
        
        # Créer dossier résultats pour cette étude
        study_results = RESULTS_DIR / study_name
        study_results.mkdir(exist_ok=True)
        
        # Sauvegarder la config
        shutil.copy(study_file, study_results / "study_config.yaml")
        
        print(f"\n=== ÉTUDE: {study_name} ===")
        print(f"Paramètre: {param_path}")
        print(f"Valeurs: {values}")
        print(f"Simulations: {len(values)}")
        print()
        
        results_summary = []
        
        for i, value in enumerate(values, 1):
            run_name = f"run_{i:03d}_{param_path.split('.')[-1]}_{value}"
            run_dir = study_results / run_name
            
            print(f"\n--- Simulation {i}/{len(values)}: {param_path} = {value} ---")
            
            if dry_run:
                print(f"  [DRY RUN] Créerait: {run_dir}")
                continue
            
            # Copier les templates
            if run_dir.exists():
                shutil.rmtree(run_dir)
            
            shutil.copytree(TEMPLATES_DIR / "0", run_dir / "0")
            shutil.copytree(TEMPLATES_DIR / "constant", run_dir / "constant")
            shutil.copytree(TEMPLATES_DIR / "system", run_dir / "system")
            
            # Modifier le paramètre
            modifier = ParameterModifier(run_dir)
            modifier.set_parameter(param_path, value)
            
            # Lancer la simulation
            print(f"  Lancement simulation...")
            log_file = run_dir / "run.log"
            
            try:
                # Source OpenFOAM et lancer
                cmd = f"source /opt/openfoam13/etc/bashrc && cd {run_dir} && foamRun -solver incompressibleVoF > run.log 2>&1"
                result = subprocess.run(
                    cmd,
                    shell=True,
                    executable='/bin/bash',
                    timeout=config.get('execution', {}).get('timeout', 3600)
                )
                
                if result.returncode == 0:
                    print(f"  ✅ Simulation terminée")
                    status = "OK"
                else:
                    print(f"  ❌ Erreur (code {result.returncode})")
                    status = "ERROR"
                    
            except subprocess.TimeoutExpired:
                print(f"  ⏱️ Timeout")
                status = "TIMEOUT"
            except Exception as e:
                print(f"  ❌ Exception: {e}")
                status = "EXCEPTION"
            
            results_summary.append({
                'run': run_name,
                'parameter': param_path,
                'value': value,
                'status': status
            })
        
        # Sauvegarder le résumé
        summary_file = study_results / "summary.json"
        with open(summary_file, 'w') as f:
            json.dump(results_summary, f, indent=2)
        
        print(f"\n=== ÉTUDE TERMINÉE ===")
        print(f"Résultats: {study_results}")
        print(f"Résumé: {summary_file}")
    
    def status(self, study_name: str):
        """Affiche le status d'une étude."""
        study_results = RESULTS_DIR / study_name
        
        if not study_results.exists():
            print(f"❌ Aucun résultat pour '{study_name}'")
            return
        
        summary_file = study_results / "summary.json"
        if summary_file.exists():
            with open(summary_file) as f:
                summary = json.load(f)
            
            print(f"\n=== STATUS: {study_name} ===\n")
            for run in summary:
                status_icon = "✅" if run['status'] == "OK" else "❌"
                print(f"{status_icon} {run['run']}: {run['parameter']} = {run['value']} [{run['status']}]")
        else:
            runs = list(study_results.glob("run_*"))
            print(f"\n=== STATUS: {study_name} ===")
            print(f"Runs trouvés: {len(runs)}")
            for run in sorted(runs):
                log = run / "run.log"
                if log.exists():
                    # Vérifier si terminé
                    content = log.read_text()
                    if "End" in content:
                        print(f"  ✅ {run.name}")
                    elif "FOAM FATAL" in content:
                        print(f"  ❌ {run.name} (erreur)")
                    else:
                        print(f"  🔄 {run.name} (en cours)")
                else:
                    print(f"  ⏳ {run.name} (pas de log)")


# =============================================================================
# MAIN
# =============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Gestionnaire d'études paramétriques OpenFOAM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  %(prog)s list                          Liste les études disponibles
  %(prog)s create --name viscosity       Crée une nouvelle étude
  %(prog)s run --study viscosity         Lance une étude
  %(prog)s run --study viscosity --dry   Test sans exécution
  %(prog)s status --study viscosity      Status d'une étude
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commande')
    
    # List
    subparsers.add_parser('list', help='Liste les études disponibles')
    
    # Create
    create_parser = subparsers.add_parser('create', help='Crée une nouvelle étude')
    create_parser.add_argument('--name', required=True, help='Nom de l\'étude')
    
    # Run
    run_parser = subparsers.add_parser('run', help='Lance une étude')
    run_parser.add_argument('--study', required=True, help='Nom de l\'étude')
    run_parser.add_argument('--dry', action='store_true', help='Dry run (pas d\'exécution)')
    
    # Status
    status_parser = subparsers.add_parser('status', help='Status d\'une étude')
    status_parser.add_argument('--study', required=True, help='Nom de l\'étude')
    
    args = parser.parse_args()
    
    runner = StudyRunner()
    
    if args.command == 'list':
        runner.list_studies()
    elif args.command == 'create':
        runner.create_study(args.name)
    elif args.command == 'run':
        runner.run_study(args.study, dry_run=args.dry)
    elif args.command == 'status':
        runner.status(args.study)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
