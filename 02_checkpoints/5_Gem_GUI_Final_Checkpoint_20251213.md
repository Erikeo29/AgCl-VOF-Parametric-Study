# Checkpoint Final: GUI et Correctifs OpenFOAM - 13/12/2025

Ce checkpoint représente la version stabilisée et corrigée de l'interface graphique et des fichiers de configuration associés, suite à une session de débogage intensive.

## Résumé des Corrections Finales

1.  **Stabilité de la Modification de Fichiers**: La classe `ParameterModifier` dans `gui.py` a été refondue pour utiliser des méthodes de modification robustes (ligne par ligne ou par bloc), prévenant la corruption des fichiers de cas OpenFOAM.
2.  **Correction de la Logique de Viscosité**: Les fichiers templates (`momentumTransport.air`, `physicalProperties.air`) ont été corrigés pour se conformer à la structure attendue par le solveur.
3.  **Correction des Erreurs de Démarrage**: Tous les bugs de syntaxe et de logique dans `gui.py` qui causaient des plantages au démarrage ont été résolus.

L'état final des fichiers est détaillé ci-dessous.

---

## 1. Fichier `gui.py` (Final et Corrigé)

```python
import streamlit as st
import yaml
import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
import re
import sys

# --- Configuration ---
PROJECT_ROOT = Path(__file__).parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
RESULTS_DIR = PROJECT_ROOT / "results"
PARAMS_FILE = "config/base_parameters.yaml"
BLOCKMESHDICT_TEMPLATE = TEMPLATES_DIR / "system" / "blockMeshDict"

# --- Functions ---
def load_parameters(file_path):
    if not os.path.exists(file_path): st.error(f"File not found: {file_path}"); return {}
    with open(file_path, 'r') as f: return yaml.safe_load(f)

def get_fixed_geometry_from_blockmesh(file_path):
    if not os.path.exists(file_path): return {}
    content = Path(file_path).read_text()
    fixed_geo = {}
    vertices_match = re.search(r'vertices\s*\((.*?)\);', content, re.DOTALL)
    if vertices_match:
        x_coords, y_coords = [], []
        pattern = r'^\s*\(\s*([-+]?[0-9.]+\s*)\s+([-+]?[0-9.]+\s*)'
        for match in re.finditer(pattern, vertices_match.group(1), re.MULTILINE):
            x_coords.append(float(match.group(1)))
            y_coords.append(float(match.group(2)))
        if x_coords: fixed_geo['largeur_domaine'] = max(x_coords) - min(x_coords)
        if y_coords: fixed_geo['hauteur_domaine'] = max(y_coords) - min(y_coords)
    fixed_geo.update({'largeur_puit': 0.8, 'hauteur_puit': 0.128})
    nozzle_base_match = re.search(r'// === Niveau y=([0-9.]+) \(bas buse / haut gap\)', content)
    if nozzle_base_match: fixed_geo['hauteur_base_buse'] = float(nozzle_base_match.group(1))
    return fixed_geo

class ParameterModifier:
    def __init__(self, case_dir: Path):
        self.case_dir = case_dir
        self.log = []

    def apply_all(self, params):
        # Rheology for water
        RHO_INK = params.get('physical', {}).get('rho_ink', 3000.0)
        param_map = {'eta0': 'nu0', 'eta_inf': 'nuInf', 'lambda': 'k', 'n': 'n'}
        mt_water_params = {}
        for p, v in params.get('rheology', {}).items():
            of_param = param_map.get(p)
            if of_param: mt_water_params[of_param] = f"{v / RHO_INK:.6e}" if p in ['eta0', 'eta_inf'] else str(v)
        self._apply_params_line_by_line(self.case_dir / "constant/momentumTransport.water", mt_water_params)
        
        # Physical Properties for Water
        phys_water_params = {'rho': params['physical']['rho_ink']}
        if 'eta0' in params['rheology']: phys_water_params['nu'] = f"{params['rheology']['eta0'] / RHO_INK:.6e}"
        self._apply_params_line_by_line(self.case_dir / "constant/physicalProperties.water", phys_water_params)

        # Physical Properties for Air
        phys_air_params = {
            'rho': params['physical']['rho_air'], 
            'nu': params['physical']['nu_air']
            }
        self._apply_params_line_by_line(self.case_dir / "constant/physicalProperties.air", phys_air_params)

        # Contact Angles
        self._modify_alpha_water_robust(params.get('contact_angles', {}))

        # Surface Tension
        self._apply_params_line_by_line(self.case_dir / "constant/phaseProperties", params.get('surface', {}))
        
        # Control Dict
        control_params = params['numerical'].copy()
        if 'end_time' in params['process']: control_params['endTime'] = params['process']['end_time']
        self._apply_params_line_by_line(self.case_dir / 'system' / 'controlDict', control_params)

    def _apply_params_line_by_line(self, file_path: Path, params_to_set: dict):
        if not file_path.exists() or not params_to_set: return
        lines = file_path.read_text().split('\n')
        new_lines = []
        params_to_find = params_to_set.copy()
        for line in lines:
            key_in_line = next((k for k in params_to_find if line.strip().startswith(k + ' ')), None)
            if key_in_line:
                value_to_set = params_to_find[key_in_line]
                indent = line[:len(line) - len(line.lstrip())]
                new_lines.append(f"{indent}{key_in_line}{' ' * (16 - len(key_in_line))}{value_to_set};")
                self.log.append(f"  ✓ Set {key_in_line} = {value_to_set} in {file_path.name}")
                del params_to_find[key_in_line]
            else:
                new_lines.append(line)
        file_path.write_text('\n'.join(new_lines))

    def _modify_alpha_water_robust(self, angle_params):
        file_path = self.case_dir / "0" / "alpha.water"
        if not file_path.exists(): self.log.append(f"  ⚠ {file_path.name} non trouvé"); return
        lines, new_lines, in_block, modified = file_path.read_text().split('\n'), [], False, False
        current_surface = None
        for line in lines:
            stripped = line.strip()
            if not in_block and stripped in angle_params:
                in_block = True
                current_surface = stripped
            elif in_block:
                if stripped.startswith('theta0'):
                    new_lines.append(f"        theta0          {int(float(angle_params[current_surface]))};")
                    self.log.append(f"  ✓ {current_surface} theta0 = {angle_params[current_surface]}°")
                    modified = True
                    # Don't append the old line, continue to the next
                    continue
                elif stripped.startswith('}'):
                    in_block = False
            new_lines.append(line)
        if modified: file_path.write_text('\n'.join(new_lines))
        else: self.log.append(f"  - Aucun angle de contact n'a pu être modifié dans {file_path.name}")

# --- Streamlit App UI ---
st.set_page_config(layout="wide"); st.title("Interface de Contrôle pour Simulation OpenFOAM")
if 'params' not in st.session_state: st.session_state.params = load_parameters(PARAMS_FILE)
with st.sidebar:
    debug_mode = st.toggle("Mode Débogage (Dry Run)", value=False)
    st.header("Paramètres de Simulation")
    def display_parameters(params_dict, category_name=""):
        if category_name: st.subheader(category_name)
        for key, value in params_dict.items():
            if isinstance(value, dict): display_parameters(value, key.replace('_', ' ').title())
            elif isinstance(value, (int, float)):
                label, widget_key = f"{key.replace('_', ' ').title()}", f"{category_name.lower()}_{key}"
                if category_name == "Geometry" and key in ["nozzle_diameter", "nozzle_height", "domain_width", "domain_height"]:
                    params_dict[key] = st.number_input(label + " (mm)", value=value * 1000, format="%.4f", key=widget_key) / 1000
                else: params_dict[key] = st.number_input(label, value=float(value), format="%.6g", key=widget_key)
    display_parameters(st.session_state.params)
    st.markdown("---"); st.header("Géométrie Fixe (du blockMeshDict)")
    fixed_geo = get_fixed_geometry_from_blockmesh(BLOCKMESHDICT_TEMPLATE)
    if fixed_geo: [st.info(f"**{k.replace('_', ' ').title()}:** {v:.3f} mm") for k, v in fixed_geo.items()]
    else: st.warning("blockMeshDict non trouvé.")

def run_simulation_in_st(run_dir):
    log_placeholder = st.empty(); command = ["foamRun", "-solver", "incompressibleVoF", "-case", str(run_dir)]
    log_content = f"🚀 Lancement de la simulation...\n"
    log_content += f"Dossier: {run_dir}\nCommande: {' '.join(command)}\n\n"
    log_placeholder.code(log_content, language='log')
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, encoding='utf-8', errors='replace')
    with open(run_dir / "run.log", 'w') as log_f:
        for line in iter(process.stdout.readline, ''):
            log_content += line; log_f.write(line); log_placeholder.code(log_content, language='log')
    if process.wait() == 0: st.success("✅ Simulation terminée avec succès !")
    else: st.error(f"❌ La simulation a échoué ! (code {process.returncode})")

st.header("Lancement")
if st.button("🚀 Lancer une nouvelle simulation", type="primary"):
    timestr = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    case_dir = RESULTS_DIR / f"gui_run_{timestr}"
    with st.status(f"Préparation du cas : {case_dir.name}", expanded=True) as status:
        st.write("Copiage des templates..."); shutil.copytree(TEMPLATES_DIR, case_dir, dirs_exist_ok=True)
        st.write("Application des paramètres..."); 
        modifier = ParameterModifier(case_dir)
        modifier.apply_all(st.session_state.params)
        st.text("\n".join(modifier.log)); status.update(label="Préparation terminée", state="complete")
    if debug_mode:
        st.subheader("🕵️‍♂️ DRY RUN - Contenu des fichiers générés")
        files_to_check = ["constant/physicalProperties.air", "constant/momentumTransport.air", "constant/momentumTransport.water", "0/alpha.water"]
        for f_rel_path in files_to_check:
            p = case_dir / f_rel_path
            st.write(f"**Contenu de `{p}`:**"); st.code(p.read_text(), language='foam')
    else: run_simulation_in_st(case_dir)

with st.expander("État Actuel des Paramètres (Debug)"): st.json(st.session_state.params)
```

---

## 2. `config/base_parameters.yaml` (Corrigé)

```yaml
# =============================================================================
# BASE PARAMETERS - AgCl VOF Droplet Simulation
# =============================================================================
# Ce fichier définit les valeurs par défaut de tous les paramètres.
# Les études paramétriques surchargent ces valeurs.

# -----------------------------------------------------------------------------
# RHÉOLOGIE - Modèle Carreau
# -----------------------------------------------------------------------------
rheology:
  eta0: 1.5           # [Pa.s] Viscosité cisaillement nul
  eta_inf: 0.001      # [Pa.s] Viscosité cisaillement infini
  lambda: 0.1         # [s] Temps de relaxation
  n: 0.5              # [-] Exposant loi puissance

# -----------------------------------------------------------------------------
# TENSION DE SURFACE
# -----------------------------------------------------------------------------
surface:
  sigma: 0.040        # [N/m] Tension de surface encre/air

# -----------------------------------------------------------------------------
# ANGLES DE CONTACT (en degrés)
# -----------------------------------------------------------------------------
contact_angles:
  substrate: 35                 # Substrat principal (hydrophile)
  wall_isolant_left: 15         # Isolant gauche (très hydrophile)
  wall_isolant_right: 160       # Isolant droit (hydrophobe)
  wall_buse_left_int: 90        # Buse gauche intérieur (neutre)
  wall_buse_right_int: 90       # Buse droite intérieur (neutre)
  wall_buse_left_ext: 180       # Buse gauche extérieur (super-hydrophobe)
  wall_buse_right_ext: 180      # Buse droite extérieur (super-hydrophobe)

# -----------------------------------------------------------------------------
# PROPRIÉTÉS PHYSIQUES
# -----------------------------------------------------------------------------
physical:
  rho_ink: 3000       # [kg/m³] Densité encre AgCl
  rho_air: 1.0        # [kg/m³] Densité air
  nu_air: 1.48e-5     # [m²/s] Viscosité cinématique air

# -----------------------------------------------------------------------------
# PROCESSUS
# -----------------------------------------------------------------------------
process:
  dispense_time: 0.050    # [s] Durée de dispense
  end_time: 0.400         # [s] Temps final simulation
  inlet_velocity: 0.1     # [m/s] Vitesse entrée (si applicable)

# -----------------------------------------------------------------------------
# GÉOMÉTRIE
# -----------------------------------------------------------------------------
geometry:
  nozzle_diameter: 0.0003     # [m] Diamètre buse (0.3mm)
  nozzle_height: 0.00044      # [m] Hauteur buse (0.44mm)
  domain_width: 0.0016        # [m] Largeur domaine (1.6mm)
  domain_height: 0.0006       # [m] Hauteur domaine (~0.6mm)

# -----------------------------------------------------------------------------
# PARAMÈTRES NUMÉRIQUES
# -----------------------------------------------------------------------------
numerical:
  maxCo: 0.3              # Courant max
  maxAlphaCo: 0.3         # Courant max pour alpha
  maxDeltaT: 1e-5         # [s] Pas de temps max
  writeInterval: 0.001    # [s] Intervalle d'écriture
```

---

## 3. `templates/constant/momentumTransport.air` (Corrigé)

```foam
/*--------------------------------*- C++ -*----------------------------------*\
  =========                 | 
  \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\    /   O peration     | Website:  https://openfoam.org
    \\  /    A nd           | Version:  13
     \\/     M anipulation  | 
\*---------------------------------------------------------------------------*/
FoamFile
{
    format      ascii;
    class       dictionary;
    location    "constant";
    object      momentumTransport.air;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

// Air phase: Laminar flow with constant viscosity defined here.

simulationType  laminar;

laminar
{
    model   generalisedNewtonian;
}

// ************************************************************************* //
```

---

## 4. `templates/constant/physicalProperties.air` (Corrigé)

```foam
/*--------------------------------*- C++ -*----------------------------------*\
  =========                 |
  \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\    /   O peration     | Website:  https://openfoam.org
    \\  /    A nd           | Version:  13
     \\/     M anipulation  |
\*---------------------------------------------------------------------------*/
FoamFile
{
    format      ascii;
    class       dictionary;
    location    "constant";
    object      physicalProperties.air;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

// Air phase properties (Newtonian, constant viscosity)
// Source: base_parameters.yaml → physical.nu_air, physical.rho_air
// Default: nu = 1.48e-5 m²/s, rho = 1.0 kg/m³

viscosityModel  constant;

rho             1.2;

nu              8.333e-06;

// ************************************************************************* //
```

---

## 5. `templates/constant/momentumTransport.water` (Corrigé)

```foam
/*--------------------------------*- C++ -*----------------------------------*\
  =========                 |
  \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\    /   O peration     | Website:  https://openfoam.org
    \\  /    A nd           | Version:  13
     \\/     M anipulation  |
\*---------------------------------------------------------------------------*/
FoamFile
{
    format      ascii;
    class       dictionary;
    location    "constant";
    object      momentumTransport.water;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

// Non-Newtonian ink (water) phase with Bird-Carreau rheology
// Source: base_parameters.yaml → rheology.*
// Default parameters (GUI will modify these based on user input):
//   η₀ = 1.5 Pa·s (zero-shear viscosity)
//   η∞ = 0.001 Pa·s (infinite-shear viscosity)
//   λ = 0.1 s (relaxation time)
//   n = 0.5 (power-law index, <1 means shear-thinning)

simulationType  laminar;

laminar
{
    model           generalisedNewtonian;
    viscosityModel  BirdCarreau;

    // Zero-shear viscosity: nu0 = η₀ / ρ_ink
    // Default: nu0 = 1.5 / 3000 = 5.0e-4 m²/s
    nu0             5.0e-04;

    // Infinite-shear viscosity: nuInf = η∞ / ρ_ink
    // Default: nuInf = 0.001 / 3000 = 3.33e-7 m²/s
    nuInf           3.33e-07;

    // Time constant: k = λ (relaxation time)
    // Default: k = 0.1 s
    k               0.1;

    // Power-law index: n (shear-thinning behavior, n < 1)
    // Default: n = 0.5
    n               0.5;
}

// ************************************************************************* //
```
