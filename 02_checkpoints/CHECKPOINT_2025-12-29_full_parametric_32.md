# CHECKPOINT - Étude Paramétrique 32 Combinaisons

**Date**: 2025-12-29
**Étude**: full_parametric_32
**Statut**: ✅ TERMINÉE - 32/32 simulations

---

## Objectif

Étude paramétrique complète pour explorer l'effet de 5 paramètres sur le comportement de mouillage de l'encre AgCl.

---

## Paramètres Variables (2^5 = 32 combinaisons)

| Paramètre | Valeur 1 | Valeur 2 | Description |
|-----------|----------|----------|-------------|
| CA_wall_isolant_left | 30° | 60° | Angle paroi verticale gauche |
| CA_top_isolant_left | 30° | 60° | Angle plateau horizontal gauche |
| eta_0 | 0.5 Pa.s | 1.5 Pa.s | Viscosité zero-shear |
| eta_inf | 0.001 Pa.s | 0.1 Pa.s | Viscosité infinite-shear |
| ratio_surface | 0.8 | 1.2 | Ratio surface buse/puit |

## Paramètres Fixes

| Paramètre | Valeur | Description |
|-----------|--------|-------------|
| CA_wall_isolant_right | 120° | Paroi verticale droite |
| CA_top_isolant_right | 120° | Plateau horizontal droite |
| CA_substrate | 35° | Fond du puit |
| rho_ink | 3000 kg/m³ | Densité encre |
| sigma | 0.040 N/m | Tension de surface |
| endTime | 200 ms | Durée simulation |

---

## Fichiers Générés

```
results/full_parametric_32/
├── run_001_wall_isolant_left30_top_isolant_left30_eta00.5_eta_inf0.001_ratio_surface0.8/
├── run_002_...
├── ...
├── run_032_wall_isolant_left60_top_isolant_left60_eta01.5_eta_inf0.1_ratio_surface1.2/
├── gifs/                    # 32 animations GIF
├── png/                     # 32 images finales PNG
├── simulations.csv          # Export avec tous paramètres
├── study_config.yaml        # Configuration de l'étude
└── summary.json             # Résumé JSON
```

---

## Format du CSV

Le fichier `simulations.csv` contient les colonnes suivantes:

### Métadonnées
- study_name, run_name, run_id
- gif_path, png_path, vtk_available
- status, final_time_s

### Géométrie
- x_puit, y_puit, x_buse, y_buse
- y_gap_buse, x_gap_buse, x_plateau
- ratio_surface

### Physique
- rho_ink, eta_0, eta_inf, sigma
- lambda_carreau, n_carreau

### Angles de Contact
- CA_substrate
- CA_wall_isolant_left, CA_wall_isolant_right
- CA_top_isolant_left, CA_top_isolant_right
- CA_buse_int_left, CA_buse_int_right
- CA_buse_ext_left, CA_buse_ext_right

### Numérique
- endTime, writeInterval, deltaT, maxCo

---

## Modifications Apportées au Projet

### 1. Script `parametric_runner.py`

- Ajout support `ratio_surface` → calcul automatique de y_buse
- Modification des viscosités via `system/parameters` (pas momentumTransport.water)
- Calcul automatique y_ink = y_buse (buse 100% remplie)

### 2. Script `create_vof_gif.py`

Positions des annotations ajustées:
```python
# Texte haut: Y = 120
# CA plateau gauche: (100, 280)
# CA plateau droit: (500, 280)
# CA paroi gauche: (130, 300)
# CA paroi droit: (470, 300)
# CA substrat: (290, 320)
```

### 3. Fichier `templates/system/parameters`

Paramètres fixes modifiés:
```cpp
CA_wall_isolant_right   120;    // [deg]
CA_top_isolant_right    120;    // [deg]
```

---

## Durée d'Exécution

- **31 simulations**: ~15h (batch initial)
- **run_020**: ~2h (relancé manuellement)
- **Post-processing (VTK + GIF)**: ~1h
- **Total**: ~18h

---

## Commandes Utiles

```bash
# Lister les études
python3 scripts/parametric_runner.py list

# Status d'une étude
python3 scripts/parametric_runner.py status --study full_parametric_32

# Régénérer les GIFs
python3 scripts/create_vof_gif.py --study full_parametric_32

# Exporter le CSV
python3 scripts/export_results_csv.py --study full_parametric_32

# Vérifier l'avancement
./scripts/check_study_status.sh full_parametric_32
```

---

## Observations Préliminaires

À analyser depuis les GIFs et le CSV:
- Effet du ratio_surface sur le volume débordant
- Influence de eta_0 vs eta_inf sur la dynamique
- Asymétrie gauche/droite selon les CA

---

## Prochaines Étapes Suggérées

1. **Analyse statistique** du CSV pour identifier les paramètres dominants
2. **Comparaison visuelle** des GIFs par groupe de paramètres
3. **Étude complémentaire** avec d'autres valeurs de CA ou ratio
4. **Dashboard Streamlit** pour explorer les résultats interactivement

---

**Checkpoint créé par**: Claude Code
**Version projet**: 5.4
