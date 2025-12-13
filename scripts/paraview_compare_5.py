# Script ParaView - Comparer 5 simulations côte à côte
# Usage: Dans ParaView: Tools > Python Shell > Run Script

from paraview.simple import *

# Chemins des simulations
base_path = "/home/erikeo29/17_RD_Ag_AgCl/40_AgCl_OpenFOAM/05_AgCl_OF_param_v5/results/example_viscosity_sweep"
cases = [
    ("run_001_eta0_0.5", "η₀=0.5"),
    ("run_002_eta0_1.0", "η₀=1.0"),
    ("run_003_eta0_1.5", "η₀=1.5"),
    ("run_004_eta0_2.0", "η₀=2.0"),
    ("run_005_eta0_3.0", "η₀=3.0"),
]

# Créer le layout
layout = GetLayout()

# Charger chaque cas
readers = []
for i, (folder, label) in enumerate(cases):
    foam_file = f"{base_path}/{folder}/case.foam"
    reader = OpenFOAMReader(FileName=foam_file)
    reader.MeshRegions = ['internalMesh']
    reader.CellArrays = ['alpha.water', 'U', 'p_rgh']
    readers.append((reader, label))
    
    # Afficher alpha.water
    display = Show(reader)
    ColorBy(display, ('CELLS', 'alpha.water'))
    display.RescaleTransferFunctionToDataRange()

print("5 simulations chargées!")
print("Utilisez le menu View > Layout pour les arranger")
