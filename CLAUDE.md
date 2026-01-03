# CLAUDE.md - Etudes Parametriques AgCl VOF

Ce projet est une interface type COMSOL pour lancer des etudes parametriques sur les simulations VOF de gouttes AgCl.

**Objectif:** Generer des GIFs, PNGs et un fichier CSV pour integration externe.

---

## REGLES CRITIQUES

### Organisation des Fichiers

| Type | Emplacement |
|------|-------------|
| Templates OpenFOAM | `templates/` |
| Fichier parametres central | `templates/system/parameters` |
| Configuration etudes | `config/studies/` |
| Scripts Python | `scripts/` |
| Resultats par etude | `results/<study_name>/` |
| Fichiers obsoletes | `99_obsolete/` |
| Checkpoints | `02_checkpoints/` |

**INTERDIT: Creer des fichiers a la racine**

---

## Scripts Disponibles

| Script | Usage |
|--------|-------|
| `parametric_runner.py` | Lancer des etudes parametriques |
| `create_vof_gif.py` | Generer GIFs et PNGs par run |
| `create_comparison_gif.py` | Mosaique comparative de l'etude |
| `export_results_csv.py` | Exporter CSV avec tous parametres |
| `results_collector.py` | Collecter status des simulations |
| `openfoam_params.py` | Module lecture parametres |
| `generate_alpha_field.py` | Generer champ alpha initial |

---

## Commandes Principales

```bash
# Lister les etudes disponibles
python3 scripts/parametric_runner.py list

# Creer une nouvelle etude
python3 scripts/parametric_runner.py create --name viscosity_effect

# Lancer une etude
python3 scripts/parametric_runner.py run --study viscosity_effect

# Dry run (test sans execution)
python3 scripts/parametric_runner.py run --study viscosity_effect --dry

# Status d'une etude
python3 scripts/parametric_runner.py status --study viscosity_effect
```

---

## Structure du Projet

```
05_AgCl_OF_param_v5/
├── config/
│   ├── base_parameters.yaml
│   └── studies/
│       ├── example_viscosity_sweep.yaml
│       └── grid_sweep_eta_CA.yaml
├── templates/
│   ├── system/
│   │   └── parameters          ← FICHIER CENTRAL
│   ├── constant/
│   └── 0/
├── scripts/
│   ├── parametric_runner.py    # Lancer etudes
│   ├── create_vof_gif.py       # Generer GIF/PNG
│   ├── create_comparison_gif.py
│   ├── export_results_csv.py   # Export CSV
│   ├── results_collector.py
│   ├── openfoam_params.py      # Module parametres
│   └── generate_alpha_field.py
├── results/
│   └── <study_name>/
│       ├── run_*/              # Simulations OpenFOAM
│       ├── gifs/               # GIFs generes
│       ├── png/                # PNGs generes
│       └── simulations.csv     # CSV export
└── 02_checkpoints/             # lesson learn / picture of actual status
```

---

## Workflow Etudes Parametriques

### 1. Definir les parametres de base
Editer `templates/system/parameters`

### 2. Creer une etude
```bash
python3 scripts/parametric_runner.py create --name contact_angles
```

### 3. Configurer l'etude
Editer `config/studies/contact_angles.yaml`:
```yaml
name: contact_angles
description: Effet de l'angle de contact substrat

sweep:
  parameter: contact_angles.substrate
  values: [20, 35, 50, 65, 80]
```

### 4. Lancer l'etude
```bash
python3 scripts/parametric_runner.py run --study contact_angles
```

### 5. Post-traitement
```bash
# Conversion VTK
source /opt/openfoam13/etc/bashrc
for run in results/contact_angles/run_*; do
    foamToVTK -case "$run"
done

# Generer GIFs individuels
source ~/miniconda3/etc/profile.d/conda.sh && conda activate electrochemistry
python3 scripts/create_vof_gif.py --study contact_angles

# Generer GIF comparatif
python3 scripts/create_comparison_gif.py --study contact_angles

# Exporter CSV
python3 scripts/export_results_csv.py --study contact_angles
```

### Resultat attendu
```
results/contact_angles/
├── run_001_.../VTK/
├── run_002_.../VTK/
├── gifs/
│   ├── run_001_....gif
│   └── run_002_....gif
├── png/
│   ├── run_001_....png
│   └── run_002_....png
├── comparison/
│   └── contact_angles_comparison.gif
└── simulations.csv              ← CSV avec tous parametres + chemins
```

---

## Fichier Central de Parametres (Style COMSOL)

**IMPORTANT:** Tous les parametres sont centralises dans `templates/system/parameters`

### Architecture
```
templates/system/parameters     ← FICHIER CENTRAL (modifier ici)
       ↓ #include
┌──────┴──────┬──────────────┬────────────────┬─────────────┐
blockMeshDict  setFieldsDict  controlDict  transportProps  alpha.water
```

### Parametres Geometriques
| Variable | Valeur | Description |
|----------|--------|-------------|
| `x_puit` | 0.8 mm | Largeur puit |
| `y_puit` | 0.128 mm | Profondeur puit |
| `x_plateau` | 0.4 mm | Largeur plateau (isolant) |
| `x_buse` | 0.3 mm | Largeur buse |
| `y_buse` | 0.341 mm | Hauteur buse (ratio 100%) |
| `y_gap_buse` | 0.070 mm | Gap vertical puit-buse |
| `x_gap_buse` | 0.0 mm | Decalage horizontal buse |

### Parametres Physiques
| Variable | Valeur | Description |
|----------|--------|-------------|
| `rho_ink` | 3000 kg/m³ | Densite encre |
| `eta_0` | 0.5 Pa.s | Viscosite zero-shear |
| `eta_inf` | 0.167 Pa.s | Viscosite infinite-shear |
| `sigma` | 0.040 N/m | Tension de surface |

### Angles de Contact (9 independants)
| Variable | Valeur | Description |
|----------|--------|-------------|
| `CA_substrate` | 35 | Substrat (fond puit) |
| `CA_wall_isolant_left` | 90 | Paroi verticale puit gauche |
| `CA_wall_isolant_right` | 90 | Paroi verticale puit droite |
| `CA_top_isolant_left` | 60 | Plateau horizontal gauche |
| `CA_top_isolant_right` | 60 | Plateau horizontal droite |
| `CA_buse_int_left` | 90 | Buse interieur gauche |
| `CA_buse_int_right` | 90 | Buse interieur droite |
| `CA_buse_ext_left` | 180 | Buse exterieur gauche |
| `CA_buse_ext_right` | 180 | Buse exterieur droite |

---

## Format CSV Export

Le fichier `simulations.csv` contient:

```csv
study_name,run_name,run_id,gif_path,png_path,vtk_available,status,final_time_s,
x_puit,y_puit,x_buse,y_buse,y_gap_buse,x_gap_buse,ratio_surface,
rho_ink,eta_0,sigma,CA_substrate,CA_wall_isolant_left,...
```

Ce CSV peut etre utilise par des applications externes (dashboards, etc.).

---

## Skills Claude Code

| Skill | Usage |
|-------|-------|
| `openfoam-mesh-expert` | Diagnostic maillage |
| `solver-configuration` | Configuration interFoam |
| `post-processing-analysis` | Visualisation resultats |

---

## Slash Commands

| Commande | Action |
|----------|--------|
| `/startup` | Etat du projet, etudes disponibles |
| `/checkpoint` | Sauvegarder etat dans 02_checkpoints/ |
| `/run-study` | Lancer une etude parametrique |

---

**Version**: 5.4 - Projet nettoye + Export CSV
**Derniere mise a jour**: 2025-12-24
