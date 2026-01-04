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

# Import centralized parameters reader
from openfoam_params import read_parameters, get_rho_ink

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
        elif section == 'geometry':
            self._modify_geometry(param, value)
        else:
            print(f"Warning: Section '{section}' non supportée")
    
    def _modify_transport_properties(self, param: str, value):
        """Modifie les paramètres de rhéologie dans system/parameters.

        Le template momentumTransport.water utilise #include et des variables
        $nu_0, $nu_inf, etc. On modifie donc le fichier parameters.

        IMPORTANT: Conversion viscosité dynamique → cinématique
        - eta0, eta_inf sont en Pa·s (viscosité dynamique)
        - OpenFOAM attend nu0, nuInf, nu en m²/s (viscosité cinématique)
        - Conversion: nu = eta / rho (rho lu depuis system/parameters)
        """
        import re

        # Densité de l'encre (lue depuis parameters)
        RHO_INK = get_rho_ink()

        # Mapping vers les noms de variables dans parameters
        param_map = {
            'eta0': ('eta_0', 'nu_0'),      # (param dynamique, param cinématique)
            'eta_inf': ('eta_inf', 'nu_inf'),
            'lambda': ('k_carreau', None),
            'n': ('n_carreau', None)
        }

        if param not in param_map:
            print(f"  ⚠ Paramètre rhéologique '{param}' non supporté")
            return

        eta_param, nu_param = param_map[param]

        # Fichier parameters
        params_file = self.case_dir / "system" / "parameters"
        if not params_file.exists():
            print(f"  ⚠ system/parameters non trouvé")
            return

        content = params_file.read_text()

        # Modifier la viscosité dynamique (eta)
        pattern = rf'^({eta_param}\s+)([\d.eE+-]+)(\s*;)'
        new_content = re.sub(pattern, rf'\g<1>{value}\3', content, flags=re.MULTILINE)

        # Si c'est une viscosité, calculer et modifier aussi la version cinématique
        if nu_param:
            nu_value = value / RHO_INK
            print(f"  → Conversion: η = {value} Pa·s → ν = {nu_value:.6e} m²/s (ρ = {RHO_INK} kg/m³)")

            pattern = rf'^({nu_param}\s+)([\d.eE+-]+)(\s*;)'
            new_content = re.sub(pattern, rf'\g<1>{nu_value:.6e}\3', new_content, flags=re.MULTILINE)

            print(f"  ✓ {eta_param} = {value} Pa·s, {nu_param} = {nu_value:.6e} m²/s dans parameters")
        else:
            print(f"  ✓ {eta_param} = {value} dans parameters")

        params_file.write_text(new_content)
    
    def _modify_alpha_water(self, surface: str, angle: float):
        """Modifie system/parameters pour les angles de contact.

        Les angles sont definis dans parameters avec CA_<surface> et
        references dans alpha.water via $CA_<surface>.
        """
        file_path = self.case_dir / "system" / "parameters"
        if not file_path.exists():
            print(f"Warning: {file_path} not found")
            return

        content = file_path.read_text()

        # Le parametre dans parameters est CA_<surface>
        param_name = f"CA_{surface}"

        import re
        # Pattern pour trouver CA_xxx suivi d'une valeur numerique
        pattern = rf'^({param_name}\s+)\d+(\s*;.*?)$'
        replacement = rf'\g<1>{int(angle)}\2'
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        if new_content != content:
            file_path.write_text(new_content)
            print(f"  ✓ {param_name} = {int(angle)}° dans parameters")
        else:
            print(f"  ⚠ {param_name} non trouve dans parameters")
    
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
        """Modifie les parametres numeriques dans system/parameters.

        NOTE: controlDict utilise #include "parameters" et des variables
        comme $endTime, $writeInterval, etc. On modifie donc parameters.
        """
        import re

        params_file = self.case_dir / "system" / "parameters"
        if not params_file.exists():
            print(f"  ⚠ system/parameters non trouvé")
            return

        content = params_file.read_text()

        # Modifier le parametre dans parameters
        pattern = rf'^({param}\s+)([\d.eE+-]+)(\s*;)'
        new_content = re.sub(pattern, rf'\g<1>{value}\3', content, flags=re.MULTILINE)

        if new_content != content:
            params_file.write_text(new_content)
            print(f"  ✓ {param} = {value} dans parameters")
        else:
            print(f"  ⚠ {param} non trouvé dans parameters")
    
    def _modify_process(self, param: str, value):
        """Modifie les paramètres de processus dans system/parameters.

        Pour dispense_time:
        - dispense_time [s]: temps pour vider la buse
        - dispense_velocity [m/s] = y_ink [mm] * 1e-3 / dispense_time [s]
        - dispense_end [s] = dispense_time
        """
        import re

        if param == 'end_time':
            self._modify_control_dict('endTime', value)
            return

        if param == 'dispense_time':
            params_file = self.case_dir / "system" / "parameters"
            if not params_file.exists():
                print(f"  ⚠ system/parameters non trouvé")
                return

            content = params_file.read_text()

            # Lire y_ink depuis le fichier
            match = re.search(r'^y_ink\s+([\d.eE+-]+)\s*;', content, re.MULTILINE)
            if not match:
                print(f"  ⚠ y_ink non trouvé dans parameters")
                return

            y_ink = float(match.group(1))  # en mm

            # Calculer la vitesse: v = y_ink [mm] * 1e-3 / dispense_time [s]
            dispense_velocity = y_ink * 0.001 / value  # m/s

            # Mettre à jour dispense_time
            new_content = re.sub(
                r'^(dispense_time\s+)([\d.eE+-]+)(\s*;)',
                rf'\g<1>{value}\3',
                content,
                flags=re.MULTILINE
            )

            # Mettre à jour dispense_velocity
            new_content = re.sub(
                r'^(dispense_velocity\s+)([\d.eE+-]+)(\s*;)',
                rf'\g<1>{dispense_velocity:.6f}\3',
                new_content,
                flags=re.MULTILINE
            )

            # Mettre à jour dispense_end = dispense_time
            new_content = re.sub(
                r'^(dispense_end\s+)([\d.eE+-]+)(\s*;)',
                rf'\g<1>{value}\3',
                new_content,
                flags=re.MULTILINE
            )

            params_file.write_text(new_content)
            print(f"  ✓ dispense_time = {value*1000:.0f} ms → velocity = {dispense_velocity*1000:.2f} mm/s (y_ink = {y_ink} mm)")

    def _modify_geometry(self, param: str, value):
        """Modifie les paramètres géométriques dans system/parameters.

        Quand on modifie y_buse, on doit aussi recalculer:
        - y_buse_top = y_buse_bottom + y_buse
        - y_buse_top_m = y_buse_top * 1e-3
        - y_ink = y_buse (buse 100% remplie)
        - y_ink_top = y_buse_top
        - y_ink_top_m = y_buse_top_m

        Pour ratio_surface, on calcule y_buse à partir du ratio:
        - S_puit = x_puit * y_puit = 0.8 * 0.128 = 0.1024 mm²
        - y_buse = ratio * S_puit / x_buse
        """
        import re

        params_file = self.case_dir / "system" / "parameters"
        if not params_file.exists():
            print(f"  ⚠ system/parameters non trouvé")
            return

        content = params_file.read_text()

        # Cas spécial: ratio_surface → calculer y_buse
        if param == 'ratio_surface':
            # Constantes géométriques
            S_PUIT = 0.8 * 0.128  # mm² = 0.1024
            X_BUSE = 0.3  # mm

            y_buse = value * S_PUIT / X_BUSE
            print(f"  → ratio_surface = {value} → y_buse = {y_buse:.3f} mm")

            # Modifier ratio_surface
            new_content = re.sub(
                r'^(ratio_surface\s+)([\d.eE+-]+)(\s*;)',
                rf'\g<1>{value}\3',
                content,
                flags=re.MULTILINE
            )

            # Modifier y_buse et dérivées
            new_content = re.sub(
                r'^(y_buse\s+)([\d.eE+-]+)(\s*;)',
                rf'\g<1>{y_buse:.3f}\3',
                new_content,
                flags=re.MULTILINE
            )

            # Lire y_buse_bottom pour calculer les positions
            match = re.search(r'^y_buse_bottom\s+([\d.eE+-]+)\s*;', new_content, re.MULTILINE)
            if match:
                y_buse_bottom = float(match.group(1))
                y_buse_top = y_buse_bottom + y_buse
                y_buse_top_m = y_buse_top * 0.001

                # y_buse_top
                new_content = re.sub(
                    r'^(y_buse_top\s+)([\d.eE+-]+)(\s*;)',
                    rf'\g<1>{y_buse_top:.3f}\3',
                    new_content,
                    flags=re.MULTILINE
                )
                # y_buse_top_m
                new_content = re.sub(
                    r'^(y_buse_top_m\s+)([\d.eE+-]+)(\s*;)',
                    rf'\g<1>{y_buse_top_m:.6f}\3',
                    new_content,
                    flags=re.MULTILINE
                )
                # y_ink = y_buse (100% remplie)
                new_content = re.sub(
                    r'^(y_ink\s+)([\d.eE+-]+)(\s*;)',
                    rf'\g<1>{y_buse:.3f}\3',
                    new_content,
                    flags=re.MULTILINE
                )
                # y_ink_top = y_buse_top
                new_content = re.sub(
                    r'^(y_ink_top\s+)([\d.eE+-]+)(\s*;)',
                    rf'\g<1>{y_buse_top:.3f}\3',
                    new_content,
                    flags=re.MULTILINE
                )
                # y_ink_top_m = y_buse_top_m
                new_content = re.sub(
                    r'^(y_ink_top_m\s+)([\d.eE+-]+)(\s*;)',
                    rf'\g<1>{y_buse_top_m:.6f}\3',
                    new_content,
                    flags=re.MULTILINE
                )

                print(f"  ✓ ratio={value} → y_buse={y_buse:.3f}mm, y_ink={y_buse:.3f}mm, y_buse_top={y_buse_top:.3f}mm")

            params_file.write_text(new_content)
            return

        # Modifier le paramètre demandé (capture uniquement la valeur numérique)
        pattern = rf'(^{param}\s+)([\d.eE+-]+)(\s*;)'
        new_content = re.sub(pattern, rf'\g<1>{value}\3', content, flags=re.MULTILINE)

        # Si c'est y_buse, recalculer les valeurs dérivées
        if param == 'y_buse':
            # Lire y_buse_bottom depuis le fichier (valeur numérique uniquement)
            match = re.search(r'^y_buse_bottom\s+([\d.eE+-]+)\s*;', new_content, re.MULTILINE)
            if match:
                y_buse_bottom = float(match.group(1))
                y_buse_top = y_buse_bottom + value
                y_buse_top_m = y_buse_top * 0.001  # mm to m

                # Mettre à jour y_buse_top
                new_content = re.sub(
                    r'^(y_buse_top\s+)([\d.eE+-]+)(\s*;)',
                    rf'\g<1>{y_buse_top:.3f}\3',
                    new_content,
                    flags=re.MULTILINE
                )

                # Mettre à jour y_buse_top_m
                new_content = re.sub(
                    r'^(y_buse_top_m\s+)([\d.eE+-]+)(\s*;)',
                    rf'\g<1>{y_buse_top_m:.6f}\3',
                    new_content,
                    flags=re.MULTILINE
                )

                # Mettre à jour y_ink = y_buse (100% remplie)
                new_content = re.sub(
                    r'^(y_ink\s+)([\d.eE+-]+)(\s*;)',
                    rf'\g<1>{value:.3f}\3',
                    new_content,
                    flags=re.MULTILINE
                )
                # y_ink_top = y_buse_top
                new_content = re.sub(
                    r'^(y_ink_top\s+)([\d.eE+-]+)(\s*;)',
                    rf'\g<1>{y_buse_top:.3f}\3',
                    new_content,
                    flags=re.MULTILINE
                )
                # y_ink_top_m = y_buse_top_m
                new_content = re.sub(
                    r'^(y_ink_top_m\s+)([\d.eE+-]+)(\s*;)',
                    rf'\g<1>{y_buse_top_m:.6f}\3',
                    new_content,
                    flags=re.MULTILINE
                )

                print(f"  ✓ y_buse = {value} mm → y_buse_top = {y_buse_top:.3f} mm, y_ink = {value} mm")
            else:
                print(f"  ✓ y_buse = {value} mm (y_buse_bottom non trouvé, dérivées non calculées)")
        elif param == 'x_gap_buse':
            # Mettre à jour x_gap_buse_m aussi
            x_gap_buse_m = value * 0.001  # mm to m
            new_content = re.sub(
                r'^(x_gap_buse_m\s+)([\d.eE+-]+)(\s*;)',
                rf'\g<1>{x_gap_buse_m:.6f}\3',
                new_content,
                flags=re.MULTILINE
            )
            print(f"  ✓ x_gap_buse = {value} mm → x_gap_buse_m = {x_gap_buse_m:.6f} m")
        else:
            print(f"  ✓ {param} = {value} dans parameters")

        params_file.write_text(new_content)


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
    
    def _generate_grid_combinations(self, parameters: list) -> list:
        """Génère toutes les combinaisons pour un grid sweep.

        Args:
            parameters: Liste de dicts avec 'name' et 'values'

        Returns:
            Liste de dicts avec toutes les combinaisons
        """
        from itertools import product

        # Extraire les noms et valeurs
        names = [p['name'] for p in parameters]
        value_lists = [p['values'] for p in parameters]

        # Générer toutes les combinaisons
        combinations = []
        for combo in product(*value_lists):
            combinations.append(dict(zip(names, combo)))

        return combinations

    def _make_run_name(self, index: int, params: dict) -> str:
        """Crée un nom de run lisible à partir des paramètres."""
        parts = [f"run_{index:03d}"]
        for key, value in params.items():
            short_key = key.split('.')[-1]
            # Formater la valeur
            if isinstance(value, float):
                if value == int(value):
                    val_str = str(int(value))
                else:
                    val_str = str(value)
            else:
                val_str = str(value)
            parts.append(f"{short_key}{val_str}")
        return "_".join(parts)

    def run_study(self, study_name: str, dry_run: bool = False):
        """Exécute une étude paramétrique (simple ou grid)."""
        study_file = CONFIG_DIR / "studies" / f"{study_name}.yaml"

        if not study_file.exists():
            print(f"❌ Étude non trouvée: {study_file}")
            return

        with open(study_file) as f:
            config = yaml.safe_load(f)

        sweep = config.get('sweep', {})
        sweep_type = config.get('sweep_type', 'simple')
        start_index = config.get('start_index', 1)  # Support continuation

        # Déterminer le type de sweep
        if sweep_type == 'grid' or 'parameters' in sweep:
            # Grid sweep multi-paramètres
            parameters = sweep.get('parameters', [])
            if not parameters:
                print("❌ Configuration grid sweep invalide: 'parameters' manquant")
                return

            combinations = self._generate_grid_combinations(parameters)
            param_names = [p['name'] for p in parameters]

            print(f"\n=== ÉTUDE GRID: {study_name} ===")
            print(f"Type: Grid sweep multi-paramètres")
            print(f"Paramètres: {param_names}")
            for p in parameters:
                print(f"  - {p['name']}: {p['values']}")
            print(f"Combinaisons: {len(combinations)}")
            if start_index > 1:
                print(f"Index début: {start_index} (run_{start_index:03d} à run_{start_index + len(combinations) - 1:03d})")

        else:
            # Simple sweep (rétrocompatibilité)
            param_path = sweep.get('parameter')
            values = sweep.get('values', [])

            if not param_path or not values:
                print("❌ Configuration sweep invalide")
                return

            combinations = [{param_path: v} for v in values]
            param_names = [param_path]

            print(f"\n=== ÉTUDE: {study_name} ===")
            print(f"Paramètre: {param_path}")
            print(f"Valeurs: {values}")

        print(f"Simulations: {len(combinations)}")
        print()

        # Créer dossier résultats pour cette étude
        # Utilise output_dir ou name du config si spécifié, sinon nom du fichier
        output_name = config.get('output_dir', config.get('name', study_name))
        study_results = RESULTS_DIR / output_name
        study_results.mkdir(exist_ok=True)

        # Sauvegarder la config
        shutil.copy(study_file, study_results / "study_config.yaml")

        results_summary = []

        for i, params in enumerate(combinations, start_index):
            run_name = self._make_run_name(i, params)
            run_dir = study_results / run_name

            print(f"\n--- Simulation {i}/{start_index + len(combinations) - 1} ---")
            for key, val in params.items():
                print(f"  {key} = {val}")

            if dry_run:
                print(f"  [DRY RUN] Créerait: {run_dir}")
                results_summary.append({
                    'run': run_name,
                    'parameters': params,
                    'status': 'DRY_RUN'
                })
                continue

            # Copier les templates
            if run_dir.exists():
                shutil.rmtree(run_dir)

            shutil.copytree(TEMPLATES_DIR / "0", run_dir / "0")
            shutil.copytree(TEMPLATES_DIR / "constant", run_dir / "constant")
            shutil.copytree(TEMPLATES_DIR / "system", run_dir / "system")

            # Modifier TOUS les paramètres du sweep
            modifier = ParameterModifier(run_dir)
            for param_path, value in params.items():
                modifier.set_parameter(param_path, value)

            # Appliquer les overrides (end_time, writeInterval, etc.)
            overrides = config.get('overrides', {})
            for section, section_params in overrides.items():
                for param, value in section_params.items():
                    full_path = f"{section}.{param}"
                    print(f"  [override] {full_path} = {value}")
                    modifier.set_parameter(full_path, value)

            # Lancer la simulation
            print(f"  Génération maillage (blockMesh)...")
            print(f"  Initialisation champ alpha (setFields)...")
            log_file = run_dir / "run.log"

            try:
                # Source OpenFOAM, blockMesh (regénère le maillage), setFields puis foamRun
                cmd = f"source /opt/openfoam13/etc/bashrc && cd {run_dir} && blockMesh > blockMesh.log 2>&1 && setFields > setFields.log 2>&1 && foamRun -solver incompressibleVoF > run.log 2>&1"
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
                'parameters': params,
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
