# CHECKPOINT - 24 Decembre 2025
## Projet Nettoye + Export CSV

---

## 1. RESUME EXECUTIF

### Travaux effectues:

1. **Nettoyage projet** - Suppression fichiers Streamlit/obsoletes
2. **Renommage scripts** - Noms coherents sans reference Streamlit
3. **Creation export_results_csv.py** - Export CSV complet
4. **Mise a jour CLAUDE.md** - Documentation v5.4

### Objectif du projet clarifie:
> Simulations OpenFOAM parametriques VOF
> Sorties: GIFs, PNGs, CSV (pour integration externe)

---

## 2. FICHIERS DEPLACES VERS 99_obsolete/

| Fichier | Raison |
|---------|--------|
| `gui.py` | Application Streamlit (hors scope) |
| `PLAN_VOF_STREAMLIT.md` | Plan obsolete |
| `run_parametric.py` | Ancien runner CSV (doublon) |
| `create_vtk_animation.py` | Doublon de create_vof_gif.py |
| `comprehensive_postprocessor.py` | Non utilise |
| `paraview_compare_5.py` | Script specifique |
| `requirements.txt` | Obsolete |
| `scripts_README.md` | Obsolete |

---

## 3. SCRIPTS CONSERVES

```
scripts/
├── parametric_runner.py      # Lancer etudes parametriques
├── create_vof_gif.py         # Generer GIF/PNG (renomme)
├── create_comparison_gif.py  # Mosaique comparative
├── export_results_csv.py     # NOUVEAU - Export CSV
├── results_collector.py      # Status simulations
├── openfoam_params.py        # Module lecture parametres
└── generate_alpha_field.py   # Champ alpha initial
```

---

## 4. NOUVEAU SCRIPT: export_results_csv.py

### Usage:
```bash
python3 scripts/export_results_csv.py --study example_viscosity_sweep
python3 scripts/export_results_csv.py --all
```

### Colonnes CSV exportees:
```
Identification:
  study_name, run_name, run_id

Fichiers:
  gif_path, png_path, vtk_available

Status:
  status, final_time_s

Geometrie [mm]:
  x_puit, y_puit, x_buse, y_buse, y_gap_buse, x_gap_buse,
  x_plateau, ratio_surface

Physique:
  rho_ink, eta_0, eta_inf, sigma, lambda_carreau, n_carreau

Angles de contact [deg]:
  CA_substrate, CA_wall_isolant_left, CA_wall_isolant_right,
  CA_top_isolant_left, CA_top_isolant_right,
  CA_buse_int_left, CA_buse_int_right,
  CA_buse_ext_left, CA_buse_ext_right

Numerique:
  endTime, writeInterval, deltaT, maxCo
```

### Test:
```
$ python3 scripts/export_results_csv.py --study example_viscosity_sweep

=== Exporting: example_viscosity_sweep ===
Found 5 runs
  [OK] run_001_eta0_0.5 [GIF] [PNG]
  [OK] run_002_eta0_1.0 [---] [---]
  ...

Exported: results/example_viscosity_sweep/simulations.csv
  - 5 simulations
  - 1 GIFs
  - 1 PNGs
  - 5 completed
```

---

## 5. RENOMMAGES EFFECTUES

| Ancien nom | Nouveau nom |
|------------|-------------|
| `create_streamlit_gif.py` | `create_vof_gif.py` |
| `streamlit_vof.yaml` | `grid_sweep_eta_CA.yaml` |

---

## 6. STRUCTURE PROJET FINALE

```
05_AgCl_OF_param_v5/
├── CLAUDE.md                   # Documentation v5.4
├── README.md
├── config/
│   ├── base_parameters.yaml
│   └── studies/
│       ├── example_viscosity_sweep.yaml
│       ├── grid_sweep_eta_CA.yaml
│       └── viscosity_gap60.yaml
├── templates/
│   ├── system/
│   │   ├── parameters          ← FICHIER CENTRAL
│   │   ├── blockMeshDict
│   │   ├── controlDict
│   │   └── setFieldsDict
│   ├── constant/
│   │   ├── physicalProperties.*
│   │   ├── momentumTransport.*
│   │   └── polyMesh/
│   └── 0/
│       └── alpha.water
├── scripts/
│   ├── parametric_runner.py
│   ├── create_vof_gif.py
│   ├── create_comparison_gif.py
│   ├── export_results_csv.py   ← NOUVEAU
│   ├── results_collector.py
│   ├── openfoam_params.py
│   └── generate_alpha_field.py
├── results/
│   ├── example_viscosity_sweep/
│   │   ├── run_001_eta0_0.5/
│   │   ├── ...
│   │   ├── gifs/
│   │   ├── png/
│   │   └── simulations.csv     ← NOUVEAU
│   ├── test_ratio100/
│   └── ...
├── 99_obsolete/                 ← Fichiers nettoyes
│   ├── gui.py
│   ├── PLAN_VOF_STREAMLIT.md
│   └── ...
└── 02_checkpoints/
```

---

## 7. WORKFLOW COMPLET

### Etape 1: Configurer parametres
```bash
vim templates/system/parameters
```

### Etape 2: Creer/lancer etude
```bash
python3 scripts/parametric_runner.py create --name ma_etude
python3 scripts/parametric_runner.py run --study ma_etude
```

### Etape 3: Post-traitement
```bash
# Conversion VTK
source /opt/openfoam13/etc/bashrc
for run in results/ma_etude/run_*; do
    foamToVTK -case "$run"
done

# Generer GIFs
source ~/miniconda3/etc/profile.d/conda.sh && conda activate electrochemistry
python3 scripts/create_vof_gif.py --study ma_etude
python3 scripts/create_comparison_gif.py --study ma_etude
```

### Etape 4: Export CSV
```bash
python3 scripts/export_results_csv.py --study ma_etude
```

### Resultat:
```
results/ma_etude/
├── run_*/VTK/
├── gifs/*.gif
├── png/*.png
├── comparison/*.gif
└── simulations.csv    ← Pour integration externe
```

---

## 8. INTEGRATION EXTERNE

Le fichier `simulations.csv` peut etre utilise par:
- Dashboards Streamlit (projet separe)
- Scripts d'analyse
- Applications web

Chemin type:
```
/home/erikeo29/17_RD_Ag_AgCl/40_AgCl_OpenFOAM/05_AgCl_OF_param_v5/
  results/<study_name>/simulations.csv
```

---

## 9. ETUDES DISPONIBLES

| Etude | Runs | Status |
|-------|------|--------|
| example_viscosity_sweep | 5 | OK |
| grid_sweep_eta_CA | 12 | OK |
| viscosity_gap60 | ? | ? |
| test_ratio100 | 1 | OK |

---

## 10. PROCHAINES ETAPES

1. [ ] Generer GIFs manquants pour toutes les etudes
2. [ ] Exporter CSV pour toutes les etudes
3. [ ] Nouvelles etudes parametriques selon besoins
4. [ ] Tester annotations GIF (Template_gif_for_legends_to_insert.png)

---

**Date:** 24 Decembre 2025
**Auteur:** Claude Code
**Version:** 5.4 - Projet nettoye + Export CSV
