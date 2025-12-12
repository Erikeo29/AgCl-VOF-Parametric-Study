# CLAUDE.md - Études Paramétriques AgCl VOF

Ce projet est une interface type COMSOL pour lancer des études paramétriques sur les simulations VOF de gouttes AgCl.

---

## RÈGLES CRITIQUES

### Organisation des Fichiers

| Type | Emplacement |
|------|-------------|
| Templates OpenFOAM | `templates/` |
| Configuration paramètres | `config/` |
| Définition études | `config/studies/` |
| Scripts Python | `scripts/` |
| Résultats par étude | `results/<study_name>/` |
| Checkpoints | `02_checkpoints/` |
| Logs | `logs/` |

**INTERDIT: Créer des fichiers à la racine**

---

## Commandes Principales

```bash
# Lister les études disponibles
python3 scripts/parametric_runner.py list

# Créer une nouvelle étude
python3 scripts/parametric_runner.py create --name viscosity_effect

# Lancer une étude
python3 scripts/parametric_runner.py run --study viscosity_effect

# Dry run (test sans exécution)
python3 scripts/parametric_runner.py run --study viscosity_effect --dry

# Status d'une étude
python3 scripts/parametric_runner.py status --study viscosity_effect

# Collecter les résultats
python3 scripts/results_collector.py --study viscosity_effect
```

---

## Structure du Projet

```
05_AgCl_OF_param_v5/
├── config/
│   ├── base_parameters.yaml      # Valeurs par défaut
│   └── studies/                  # Définitions d'études
│       └── example_viscosity_sweep.yaml
├── templates/                    # Templates OpenFOAM
│   ├── 0/
│   ├── constant/
│   └── system/
├── scripts/
│   ├── parametric_runner.py      # Lanceur d'études
│   ├── results_collector.py      # Extraction métriques
│   ├── comprehensive_postprocessor.py
│   └── create_vtk_animation.py
├── results/
│   └── <study_name>/
│       ├── study_config.yaml
│       ├── summary.json
│       └── run_XXX/
├── .claude/
│   ├── commands/
│   │   ├── checkpoint.md
│   │   ├── startup.md
│   │   └── run-study.md
│   └── skills/
└── 02_checkpoints/
```

---

## Workflow Études Paramétriques

### 1. Définir les paramètres de base
Éditer `config/base_parameters.yaml`

### 2. Créer une étude
```bash
python3 scripts/parametric_runner.py create --name contact_angles
```

### 3. Configurer l'étude
Éditer `config/studies/contact_angles.yaml`:
```yaml
name: contact_angles
description: Effet de l'angle de contact substrat

sweep:
  parameter: contact_angles.substrate
  values: [20, 35, 50, 65, 80]

outputs:
  - spreading_diameter
  - final_shape
```

### 4. Lancer l'étude
```bash
python3 scripts/parametric_runner.py run --study contact_angles
```

### 5. Analyser les résultats
```bash
python3 scripts/results_collector.py --study contact_angles
```

---

## Paramètres Disponibles

| Section | Paramètre | Fichier OF modifié |
|---------|-----------|-------------------|
| `rheology.eta0` | Viscosité η₀ | transportProperties |
| `rheology.n` | Exposant Carreau | transportProperties |
| `surface.sigma` | Tension surface | transportProperties |
| `contact_angles.substrate` | Angle substrat | alpha.water |
| `contact_angles.wall_isolant_left` | Angle isolant gauche | alpha.water |
| `contact_angles.wall_isolant_right` | Angle isolant droit | alpha.water |
| `numerical.maxCo` | Courant max | controlDict |
| `numerical.maxDeltaT` | Δt max | controlDict |
| `process.end_time` | Temps final | controlDict |

---

## Skills Claude Code

| Skill | Usage |
|-------|-------|
| `openfoam-mesh-expert` | Diagnostic maillage |
| `solver-configuration` | Configuration interFoam |
| `post-processing-analysis` | Visualisation résultats |

---

## Slash Commands

| Commande | Action |
|----------|--------|
| `/startup` | État du projet, études disponibles |
| `/checkpoint` | Sauvegarder état dans 02_checkpoints/ |
| `/run-study` | Lancer une étude paramétrique |

---

**Version**: 5.0 - Études Paramétriques
**Dernière mise à jour**: 2025-12-12
