# AgCl VOF Parametric Study

Interface type COMSOL pour lancer des études paramétriques sur des simulations VOF (Volume of Fluid) de gouttes d'encre AgCl avec OpenFOAM.

## Fonctionnalités

- **Configuration YAML** des paramètres de simulation
- **Études paramétriques** avec balayage automatique de paramètres
- **Post-traitement automatique** : conversion VTK + GIF comparatif
- **Comparaison visuelle** côte à côte de toutes les simulations

## Installation

### Prérequis

- OpenFOAM 13
- Python 3.8+
- PyVista, imageio, PyYAML

```bash
pip install pyvista imageio pyyaml
```

## Utilisation rapide

### 1. Lister les études disponibles
```bash
python3 scripts/parametric_runner.py list
```

### 2. Créer une nouvelle étude
```bash
python3 scripts/parametric_runner.py create --name viscosity_effect
```

### 3. Configurer l'étude
Éditer `config/studies/viscosity_effect.yaml`:
```yaml
name: viscosity_effect
description: Effet de la viscosité sur l'étalement

sweep:
  parameter: rheology.eta0
  values: [0.5, 1.0, 1.5, 2.0, 3.0]
```

### 4. Lancer l'étude
```bash
python3 scripts/parametric_runner.py run --study viscosity_effect
```

### 5. Post-traitement (automatique)
```bash
# Conversion VTK
source /opt/openfoam13/etc/bashrc
for run in results/viscosity_effect/run_*; do
    foamToVTK -case "$run"
done

# GIF comparatif
python3 scripts/create_comparison_gif.py --study viscosity_effect
```

## Structure du projet

```
├── config/
│   ├── base_parameters.yaml      # Paramètres par défaut
│   └── studies/                  # Définitions d'études
├── templates/                    # Templates OpenFOAM (0/, constant/, system/)
├── scripts/
│   ├── parametric_runner.py      # Lanceur d'études
│   ├── results_collector.py      # Extraction métriques
│   └── create_comparison_gif.py  # Génération GIF comparatif
├── results/                      # Résultats par étude
│   └── <study_name>/
│       ├── run_XXX/              # Simulations individuelles
│       └── comparison/           # GIFs comparatifs
└── CLAUDE.md                     # Documentation détaillée
```

## Paramètres modifiables

| Paramètre | Description | Fichier OpenFOAM |
|-----------|-------------|------------------|
| `rheology.eta0` | Viscosité η₀ (Pa·s) | transportProperties |
| `rheology.n` | Exposant Carreau | transportProperties |
| `surface.sigma` | Tension de surface (N/m) | transportProperties |
| `contact_angles.substrate` | Angle de contact substrat (°) | alpha.water |
| `contact_angles.wall_isolant_left` | Angle isolant gauche (°) | alpha.water |
| `contact_angles.wall_isolant_right` | Angle isolant droit (°) | alpha.water |
| `numerical.maxCo` | Nombre de Courant max | controlDict |
| `process.end_time` | Temps de simulation (s) | controlDict |

## Exemple de résultat

Une étude paramétrique génère automatiquement un GIF comparatif montrant l'effet du paramètre étudié sur l'étalement de la goutte:

```
results/viscosity_effect/comparison/viscosity_effect_comparison.gif
```

## Simulation

- **Solver**: `foamRun -solver incompressibleVoF` (OpenFOAM 13)
- **Méthode**: VOF multiphase, 2D
- **Rhéologie**: Carreau non-newtonien
- **Application**: Étalement de gouttes d'encre AgCl pour électrodes imprimées

## Licence

MIT

## Auteur

Généré avec [Claude Code](https://claude.com/claude-code)
