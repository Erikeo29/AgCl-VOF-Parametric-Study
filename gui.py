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
    """Lance la simulation en arrière-plan avec nohup pour éviter les blocages."""
    log_file = run_dir / "run.log"
    pid_file = run_dir / "foam.pid"

    # OpenFOAM requires sourcing the bashrc before running commands
    foam_source = "source /opt/openfoam13/etc/bashrc"
    foam_cmd = f"foamRun -solver incompressibleVoF -case {run_dir}"

    # Lancer en arrière-plan avec nohup, redirection vers log
    full_command = f"nohup bash -c '{foam_source} && {foam_cmd}' > {log_file} 2>&1 & echo $!"

    # Lancer le processus
    result = subprocess.run(full_command, shell=True, executable='/bin/bash', capture_output=True, text=True)
    pid = result.stdout.strip()

    # Sauvegarder le PID
    pid_file.write_text(pid)

    st.success(f"Simulation lancée en arrière-plan (PID: {pid})")
    st.info(f"""
**Dossier:** `{run_dir}`

**Suivre la progression:**
```bash
tail -f {log_file}
```

**Voir les dossiers de temps:**
```bash
ls {run_dir}
```

**Arrêter la simulation:**
```bash
kill {pid}
```
    """)

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