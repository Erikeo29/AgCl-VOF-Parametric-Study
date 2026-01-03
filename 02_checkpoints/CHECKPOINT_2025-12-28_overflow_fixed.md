# CHECKPOINT - Overflow Asymétrique Résolu

**Date**: 2025-12-28
**Simulation**: test_overflow_v4
**Statut**: ✅ SUCCÈS - Overflow asymétrique reproduit

---

## Problème Initial

Les simulations de test ne reproduisaient pas l'overflow asymétrique observé dans la simulation de référence `gui_run_2025-12-13_23-40-29`.

## Analyse et Diagnostic

### Différences identifiées avec GUI_RUN

| Paramètre | GUI_RUN | Tests précédents | Impact |
|-----------|---------|------------------|--------|
| Volume encre initial | 30% (5280 cells) | 10.7% (1798 cells) | **CRITIQUE** |
| Hauteur encre (y_ink) | 440 µm (100% buse) | 190 µm (43% buse) | **CRITIQUE** |
| CA top_isolant_left | 15° | 60° | Important |
| CA top_isolant_right | 160° | 60° | Important |

### Cause racine
La buse n'était remplie qu'à 43% au lieu de 100%. Avec insuffisamment d'encre, même avec la force piston, il n'y avait pas assez de volume pour provoquer l'overflow.

---

## Corrections Appliquées

### 1. Fichier `templates/system/parameters`

```cpp
// AVANT (incorrect)
y_ink           0.190;      // [mm] 43% de la buse
y_ink_top       0.378;      // [mm]
y_ink_top_m     0.000378;   // [m]

// APRÈS (correct - comme GUI_RUN)
y_ink           0.440;      // [mm] 100% de la buse
y_ink_top       0.628;      // [mm] = y_buse_bottom + y_buse
y_ink_top_m     0.000628;   // [m]
```

### 2. Angles de contact (déjà corrigés)

```cpp
CA_top_isolant_left     15;     // [deg] Hydrophile - permet overflow
CA_top_isolant_right    160;    // [deg] Hydrophobe - bloque overflow
```

---

## Résultats test_overflow_v4

### Configuration
- **Buse 100% remplie** à t=0
- **Volume encre**: 30.4% du domaine
- **Temps simulation**: 200 ms
- **Force piston**: 1.2 MN/m³

### Comportement observé
- ✅ Overflow asymétrique côté gauche (CA=15°)
- ✅ Pas d'overflow côté droit (CA=160°)
- ✅ Mouillage substrat correct (CA=35°)
- ✅ Encre reste connectée entre buse et puit

### Fichiers générés
- `results/test_overflow_v4/` - Simulation OpenFOAM complète
- `results/gifs/test_overflow_v4.gif` - Animation VOF
- `results/png/test_overflow_v4.png` - Image finale t=200ms

---

## Leçons Apprises

### 1. Vérifier les conditions initiales visuellement
Toujours comparer l'image à t=0 avec la référence. Le volume d'encre initial est critique.

### 2. Le comptage de cellules est fiable
```bash
grep "alpha.water" 0/alpha.water | grep -c "^1$"  # Compter cellules encre
```

### 3. Les paramètres dérivés doivent être cohérents
Si `y_ink` change, il faut aussi mettre à jour:
- `y_ink_top = y_buse_bottom + y_ink`
- `y_ink_top_m = y_ink_top * 1e-3`

### 4. setFieldsDict utilise les variables du fichier parameters
La box d'initialisation utilise `$y_ink_top_m` - pas de hardcoding.

---

## Paramètres de Référence Validés

```cpp
// GÉOMÉTRIE
x_puit          0.8;        // [mm]
y_puit          0.128;      // [mm]
x_buse          0.3;        // [mm]
y_buse          0.440;      // [mm]
y_gap_buse      0.060;      // [mm]
y_ink           0.440;      // [mm] = y_buse (100%)

// PHYSIQUE
rho_ink         3000;       // [kg/m³]
eta_0           1.0;        // [Pa.s]
eta_inf         0.001;      // [Pa.s]
sigma           0.040;      // [N/m]

// ANGLES DE CONTACT
CA_substrate            35;
CA_wall_isolant_left    15;
CA_wall_isolant_right   160;
CA_top_isolant_left     15;     // CRITIQUE pour overflow
CA_top_isolant_right    160;    // CRITIQUE pour overflow
CA_buse_int_left        90;
CA_buse_int_right       90;
CA_buse_ext_left        180;
CA_buse_ext_right       180;
```

---

## Prochaines Étapes Suggérées

1. **Étude paramétrique CA**: Balayer CA_top_isolant_left de 10° à 90°
2. **Étude viscosité**: Comparer eta_0 = 0.5, 1.0, 1.5 Pa.s
3. **Étude gap**: Varier y_gap_buse de 40 à 100 µm
4. **Export CSV**: Générer fichier pour dashboard externe

---

**Checkpoint créé par**: Claude Code
**Version projet**: 5.4
