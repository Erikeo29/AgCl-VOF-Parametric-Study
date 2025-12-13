# Checkpoint: Développement de l'Interface Graphique - 13/12/2025

Ce fichier sert de point de sauvegarde pour l'état fonctionnel de l'interface graphique (GUI) développée avec Streamlit pour le pilotage des simulations OpenFOAM.

Après une série d'itérations et de débogages, les problèmes suivants ont été résolus :
- Incohérences entre les paramètres par défaut (`base_parameters.yaml`) et la géométrie réelle (`blockMeshDict`).
- Erreurs de syntaxe et de logique dans le script `gui.py` causant des plantages au démarrage (`IndexError`, `SyntaxError`).
- Corruption des fichiers de cas OpenFOAM (`physicalProperties.air`, `momentumTransport.water`, `alpha.water`) lors de leur modification par le script, menant à des erreurs du solveur (`FATAL IO ERROR`).

L'état final du code ci-dessous est fonctionnel et permet de :
1.  Lancer une interface avec `streamlit run gui.py`.
2.  Modifier les paramètres de simulation.
3.  Lancer une simulation qui démarre et tourne correctement.

---

## 1. Fichier `gui.py` (Final)

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
        # Corrected regex to capture both x and y coordinates in one pass
        pattern = r'^\s*\(\s*([-+]?[0-9.]+\s*)\s+([-+]?[0-9.]+\s*)\s'
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
        for category, param_dict in params.items():
            if isinstance(param_dict, dict):
                for param, value in param_dict.items():
                    self.set_parameter(f"{category}.{param}", value)
    
    def set_parameter(self, param_path: str, value):
        section, param = param_path.split('.', 1)
        methods = {'rheology': self._modify_rheology, 'contact_angles': self._modify_alpha_water, 'surface': self._modify_surface_tension, 'numerical': self._modify_control_dict, 'process': self._modify_process, 'physical': self._modify_physical_properties}
        methods.get(section, lambda p, v: self.log.append(f"Warning: Section '{section}' non supportée"))(param, value)

    def _apply_params_line_by_line(self, file_path: Path, params_to_set: dict):
        if not file_path.exists(): self.log.append(f"  ⚠ {file_path.name} non trouvé"); return
        lines, new_lines, modified_keys = file_path.read_text().split('\n'), [], set()
        for line in lines:
            key_in_line = next((k for k in params_to_set if line.strip().startswith(k + ' ')), None)
            if key_in_line:
                new_lines.append(f"{key_in_line}{' ' * (16 - len(key_in_line))}{params_to_set[key_in_line]};")
                self.log.append(f"  ✓ {key_in_line} = {params_to_set[key_in_line]} in {file_path.name}")
                modified_keys.add(key_in_line)
            else: new_lines.append(line)
        file_path.write_text('\n'.join(new_lines))

    def _modify_rheology(self, param: str, value):
        RHO_INK = st.session_state.params.get('physical', {}).get('rho_ink', 3000.0)
        param_map = {'eta0': 'nu0', 'eta_inf': 'nuInf', 'lambda': 'k', 'n': 'n'}
        of_param = param_map.get(param, param)
        formatted_value = f"{value / RHO_INK:.6e}" if param in ['eta0', 'eta_inf'] else str(value)
        self._apply_params_line_by_line(self.case_dir / "constant/momentumTransport.water", {of_param: formatted_value})
        if param == 'eta0': self._apply_params_line_by_line(self.case_dir / "constant/physicalProperties.water", {'nu': formatted_value})

    def _modify_physical_properties(self, param: str, value):
        if param.startswith('rho_'):
            phase = "water" if "ink" in param else "air"
            self._apply_params_line_by_line(self.case_dir / f"constant/physicalProperties.{phase}", {'rho': value})
        elif param == 'nu_air':
            self._apply_params_line_by_line(self.case_dir / "constant/physicalProperties.air", {'nu': value})

    def _modify_alpha_water(self, surface: str, angle: float):
        file_path = self.case_dir / "0" / "alpha.water"
        if not file_path.exists(): self.log.append(f"  ⚠ {file_path.name} non trouvé"); return
        lines, new_lines, in_block, modified = file_path.read_text().split('\n'), [], False, False
        for line in lines:
            stripped = line.strip()
            if not in_block and stripped == surface: in_block = True
            elif in_block and stripped.startswith('}'): in_block = False
            elif in_block and stripped.startswith('theta0'):
                new_lines.append(f"        theta0          {int(float(angle))};")
                modified = True; continue
            new_lines.append(line)
        if modified: file_path.write_text('\n'.join(new_lines)); self.log.append(f"  ✓ {surface} theta0 = {angle}°")
        else: self.log.append(f"  - Bloc/theta0 non trouvé pour '{surface}'")

    def _modify_surface_tension(self, param: str, value): self._apply_params_line_by_line(self.case_dir / "constant/phaseProperties", {'sigma': value})
    def _modify_control_dict(self, param: str, value): self._apply_params_line_by_line(self.case_dir / "system/controlDict", {param: value})
    def _modify_process(self, param: str, value):
        if param == 'end_time': self._modify_control_dict('endTime', value)
        else: self.log.append(f"  ⚠ {param}: modification non implémentée")

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
            st.write(f"**Contenu de `{p}`:**"); 
            st.code(p.read_text(), language='foam')
    else:
        run_simulation_in_st(case_dir)

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
GÉOMÉTRIE
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

viscosityModel  constant;

rho             1.2;

nu              8.333e-06;


// ************************************************************************* //
```
