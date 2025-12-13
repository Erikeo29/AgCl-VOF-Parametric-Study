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
        pattern = r'^\s*\(\s*([-+]?[0-9]*\.?[0-9]+)\s+([-+]?[0-9]*\.?[0-9]+)'
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
        # This is a more structured way to apply parameters
        # Group all modifications for a file together
        
        # Physical Properties
        phys_air_params = {'rho': params['physical']['rho_air'], 'nu': params['physical']['nu_air']}
        self._apply_params_line_by_line(self.case_dir / "constant/physicalProperties.air", phys_air_params)
        
        phys_water_params = {'rho': params['physical']['rho_ink']}
        if 'eta0' in params['rheology']:
             RHO_INK = params.get('physical', {}).get('rho_ink', 3000.0)
             phys_water_params['nu'] = f"{params['rheology']['eta0'] / RHO_INK:.6e}"
        self._apply_params_line_by_line(self.case_dir / "constant/physicalProperties.water", phys_water_params)
        
        # Rheology
        self._modify_rheology(params['rheology'])

        # Contact Angles
        self._modify_alpha_water_robust(params['contact_angles'])

        # Surface Tension
        self._apply_params_line_by_line(self.case_dir / "constant/phaseProperties", params['surface'])
        
        # Control Dict
        control_params = params['numerical'].copy()
        if 'end_time' in params['process']:
            control_params['endTime'] = params['process']['end_time']
        self._apply_params_line_by_line(self.case_dir / 'system' / 'controlDict', control_params)
    
    def _apply_params_line_by_line(self, file_path: Path, params_to_set: dict):
        if not file_path.exists(): self.log.append(f"  ⚠ {file_path.name} non trouvé"); return
        lines = file_path.read_text().split('\n')
        new_lines = []
        
        modified_keys_this_call = set() # Track keys that were actually modified

        for line in lines:
            stripped_line = line.strip()
            
            key_to_match = None
            for k in params_to_set:
                # Use regex to find the keyword as a whole word at the start of the stripped line
                # followed by whitespace or a semicolon. This is more robust.
                if re.match(rf'^{re.escape(k)}\s*;', stripped_line) or re.match(rf'^{re.escape(k)}\s+', stripped_line):
                    key_to_match = k
                    break
            
            if key_to_match:
                value = params_to_set[key_to_match]
                # Preserve original indentation
                indent = line[:len(line) - len(line.lstrip())]
                new_lines.append(f"{indent}{key_to_match}{' ' * (16 - len(key_to_match))}{value};")
                new_lines.append(new_line)
                self.log.append(f"  ✓ Set {key_to_match} = {value} in {file_path.name}")
                modified_keys_this_call.add(key_to_match)
            else: # This else ensures unmatched lines are copied
                new_lines.append(line)
        
        file_path.write_text('\n'.join(new_lines))
        # Log any keys that were supposed to be set but weren't found in the file
        for key in set(params_to_set.keys()) - modified_keys_this_call:
            self.log.append(f"  - Keyword '{key}' non trouvé dans {file_path.name}")


    def _modify_rheology(self, rheology_params):
        RHO_INK = st.session_state.params.get('physical', {}).get('rho_ink', 3000.0)
        param_map = {'eta0': 'nu0', 'eta_inf': 'nuInf', 'lambda': 'k', 'n': 'n'}
        
        # Prepare params for momentumTransport.water
        mt_water_params = {}
        for param, value in rheology_params.items():
            of_param = param_map.get(param)
            if of_param:
                formatted_value = f"{value / RHO_INK:.6e}" if param in ['eta0', 'eta_inf'] else str(value)
                mt_water_params[of_param] = formatted_value
        
        self._apply_params_line_by_line(self.case_dir / "constant/momentumTransport.water", mt_water_params)

        # Legacy transportProperties
        tr_params = {}
        for param, value in rheology_params.items():
            of_param = param_map.get(param)
            if of_param:
                formatted_value = f"{value / RHO_INK:.6e}" if param in ['eta0', 'eta_inf'] else str(value)
                tr_params[of_param] = formatted_value
        self._apply_params_line_by_line(self.case_dir / "constant/transportProperties", tr_params)


    def _modify_physical_properties(self, param: str, value):
        # This function is now superseded by apply_all logic which builds phys_air_params and phys_water_params
        # and calls _apply_params_line_by_line once for each.
        # This function will not be called directly for rho/nu, but kept for future expansion if needed.
        self.log.append(f"  ⚠ _modify_physical_properties called directly for {param}. Should be handled by apply_all.")
        

    def _modify_alpha_water_robust(self, angle_params: dict):
        file_path = self.case_dir / "0" / "alpha.water"
        if not file_path.exists(): self.log.append(f"  ⚠ {file_path.name} non trouvé"); return
        
        lines = file_path.read_text().split('\n')
        new_lines = []
        in_target_block = False
        current_surface = None
        
        for line in lines:
            stripped = line.strip()
            
            # Find the start of a boundary patch block we want to modify
            if not in_target_block:
                for surface_name in angle_params.keys():
                    if stripped == surface_name:
                        in_target_block = True
                        current_surface = surface_name
                        break
            
            if in_target_block:
                if stripped.startswith('theta0'):
                    angle = angle_params.get(current_surface)
                    if angle is not None:
                        new_lines.append(f"        theta0          {int(float(angle))};")
                        self.log.append(f"  ✓ {current_surface} theta0 = {angle}°")
                        continue # Skip appending the old line
                elif stripped.startswith('}')'): # End of current block
                    in_target_block = False
                    current_surface = None
            
            new_lines.append(line)
        
        file_path.write_text('\n'.join(new_lines))


    def _modify_surface_tension(self, param: str, value): self._apply_params_line_by_line(self.case_dir / "constant/phaseProperties", {param: value})
    def _modify_control_dict(self, param: str, value): self._apply_params_line_by_line(self.case_dir / "system/controlDict", {param: value})
    def _modify_process(self, param: str, value):
        if param == 'end_time': self._apply_params_line_by_line(self.case_dir / 'system' / 'controlDict', {'endTime': value})
        else: self.log.append(f"  ⚠ {param}: modification non implémentée")
    
    # This legacy method is no longer used due to _apply_params_line_by_line
    def _modify_file_content_legacy(self, file_path, pattern, replacement, msg):
        if not file_path.exists(): self.log.append(f"  ⚠ {file_path.name} non trouvé"); return
        content = file_path.read_text()
        new_content, count = re.subn(pattern, replacement, content, flags=re.MULTILINE)
        if count > 0: file_path.write_text(new_content); self.log.append(f"  ✓ {msg}")
        else: self.log.append(f"  - Pattern non trouvé pour '{msg.split('=')[0].strip()}'")

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
    log_content = "🚀 Lancement de la simulation...\n"
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
        st.write("Création du dossier...")
        case_dir.mkdir(parents=True, exist_ok=True) # Ensure dir exists before copytree
        st.write("Copiage des templates..."); shutil.copytree(TEMPLATES_DIR, case_dir, dirs_exist_ok=True)
        st.write("Application des paramètres..."); 
        modifier = ParameterModifier(case_dir)
        modifier.apply_all(st.session_state.params)
        st.text("\n".join(modifier.log)); 
        status.update(label="Préparation terminée", state="complete")
    
    if debug_mode:
        st.subheader("🕵️‍♂️ DRY RUN - Contenu des fichiers générés")
        files_to_check = ["constant/physicalProperties.air", "constant/momentumTransport.air", "constant/momentumTransport.water", "0/alpha.water"]
        for f_rel_path in files_to_check:
            p = case_dir / f_rel_path
            st.write(f"**Contenu de `{p}`:**"); st.code(p.read_text(), language='foam')
    else: run_simulation_in_st(case_dir)

with st.expander("État Actuel des Paramètres (Debug)"): st.json(st.session_state.params)