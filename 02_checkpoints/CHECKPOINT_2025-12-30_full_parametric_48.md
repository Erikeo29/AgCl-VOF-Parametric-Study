# CHECKPOINT - Étude Paramétrique 48 Combinaisons

**Date**: 2025-12-30
**Étude**: full_parametric_32 (étendue à 48)
**Statut**: TERMINÉE - 48/48 simulations

---

## Résumé

Extension de l'étude paramétrique initiale (32 simulations) avec 16 simulations supplémentaires explorant l'effet d'un angle de contact plateau très hydrophile (CA_top_isolant_left = 15°).

---

## Structure de l'Étude

### Phase 1 : Simulations 001-032 (étude initiale)
- **CA_top_isolant_left**: 30°, 60°
- **CA_wall_isolant_left**: 30°, 60°
- **eta_0**: 0.5, 1.5 Pa.s
- **eta_inf**: 0.001, 0.1 Pa.s
- **ratio_surface**: 0.8, 1.2
- **Combinaisons**: 2^5 = 32

### Phase 2 : Simulations 033-048 (extension CA=15°)
- **CA_top_isolant_left**: 15° (fixe, très hydrophile)
- **CA_wall_isolant_left**: 30°, 60°
- **eta_0**: 0.5, 1.5 Pa.s
- **eta_inf**: 0.001, 0.1 Pa.s
- **ratio_surface**: 0.8, 1.2
- **Combinaisons**: 2^4 = 16

---

## Paramètres Fixes (toutes simulations)

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
├── run_001_.../ à run_048_.../    # 48 dossiers simulation OpenFOAM
├── gifs/                          # 48 animations GIF
│   ├── run_001_....gif
│   └── ...
├── png/                           # 48 images finales PNG
│   ├── run_001_....png
│   └── ...
├── simulations.csv                # Export complet (48 lignes)
├── study_config.yaml              # Configuration étude
└── summary.json                   # Résumé JSON
```

---

## Améliorations Script parametric_runner.py

### Support `start_index`
Permet de continuer une étude existante avec numérotation à partir d'un index spécifique:

```yaml
# config/studies/full_parametric_32_ext_CA15.yaml
name: full_parametric_32      # Output dans même dossier
start_index: 33               # Numérotation à partir de 033
sweep:
  parameters:
    - name: contact_angles.top_isolant_left
      values: [15]            # Valeur fixe
    # ... autres paramètres
```

### Support `output_dir` / `name`
Le champ `name` dans le YAML détermine le dossier de sortie, permettant d'ajouter des simulations à une étude existante.

---

## Colonnes CSV Export

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

### Angles de Contact (9)
- CA_substrate
- CA_wall_isolant_left, CA_wall_isolant_right
- CA_top_isolant_left, CA_top_isolant_right
- CA_buse_int_left, CA_buse_int_right
- CA_buse_ext_left, CA_buse_ext_right

### Numérique
- endTime, writeInterval, deltaT, maxCo

---

## Commandes Utiles

```bash
# Lister études
python3 scripts/parametric_runner.py list

# Status étude
python3 scripts/parametric_runner.py status --study full_parametric_32

# Régénérer GIFs
python3 scripts/create_vof_gif.py --study full_parametric_32

# Exporter CSV
python3 scripts/export_results_csv.py --study full_parametric_32

# Vérifier avancement
./scripts/check_study_status.sh full_parametric_32
```

---

## Observations Clés

### Effet CA_top_isolant_left = 15° (run_033 à run_048)
- Mouillage très prononcé sur le plateau gauche
- Étalement asymétrique gauche/droite plus marqué
- Comparaison avec CA=30° et CA=60° permet d'identifier le seuil de confinement

### Paramètres Dominants (à analyser)
1. **ratio_surface**: Impact direct sur volume débordant
2. **CA_top_isolant_left**: Contrôle l'étalement sur plateau
3. **eta_0 / eta_inf**: Dynamique de l'écoulement

---

## Durée d'Exécution

| Phase | Durée |
|-------|-------|
| 32 simulations initiales | ~15h |
| 16 simulations extension | ~8h |
| Post-processing (VTK + GIF) | ~2h |
| **Total** | **~25h** |

---

## Prochaines Étapes Suggérées

1. **Analyse statistique** du CSV (corrélation paramètres/comportement)
2. **Dashboard Streamlit** pour exploration interactive
3. **Étude complémentaire** avec CA_top_isolant_left = 90° ou 120°
4. **Validation expérimentale** sur cas sélectionnés

---

**Checkpoint créé par**: Claude Code
**Version projet**: 5.5
**GitHub**: https://github.com/Erikeo29/AgCl-VOF-Parametric-Study
