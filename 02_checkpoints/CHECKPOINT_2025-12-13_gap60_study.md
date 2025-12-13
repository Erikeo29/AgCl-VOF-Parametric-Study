# CHECKPOINT - Étude Gap 60µm Viscosité

**Date:** 2025-12-13
**Session:** Correction bug + nouvelle étude gap 60µm

---

## PROBLÈME RÉSOLU

### Bug identifié
Le script `parametric_runner.py` modifiait le mauvais fichier :
- **Modifié** : `constant/transportProperties` (ignoré par OpenFOAM 13)
- **Lu par OpenFOAM** : `constant/momentumTransport.water`

**Résultat** : Toutes les simulations avaient la même viscosité → GIFs identiques

### Correction appliquée
Fichier : `scripts/parametric_runner.py`, méthode `_modify_transport_properties()`

Modifie maintenant les 3 fichiers :
1. `constant/momentumTransport.water` → `nu0` (principal)
2. `constant/physicalProperties.water` → `nu`
3. `constant/transportProperties` → `nu0` (rétrocompatibilité)

---

## ÉTUDES RÉALISÉES

### 1. example_viscosity_sweep (gap 30µm)
- **Géométrie** : buse y = 0.158-0.598 mm, gap 30µm
- **Viscosités** : η₀ = 0.5, 1.0, 1.5, 2.0, 3.0 Pa·s
- **Résultats** : `results/example_viscosity_sweep/`
- **GIF** : `results/example_viscosity_sweep/comparison/example_viscosity_sweep_comparison.gif`

### 2. viscosity_gap60 (gap 60µm) - NOUVELLE
- **Géométrie** : buse y = 0.188-0.628 mm, gap 60µm (+30µm)
- **Viscosités** : η₀ = 0.5, 1.5, 3.0 Pa·s (3 valeurs)
- **Résultats** : `results/viscosity_gap60/`
- **GIF** : `results/viscosity_gap60/comparison/viscosity_gap60_comparison.gif`
  - Vitesse : 2 fps (3× plus lent)
  - Pause finale : 2 secondes

---

## MODIFICATIONS GÉOMÉTRIE (gap 60µm)

### Fichiers modifiés dans templates/
| Fichier | Modification |
|---------|--------------|
| `system/blockMeshDict` | y: 0.158→0.188 (bas buse), 0.598→0.628 (haut) |
| `system/setFieldsDict` | box encre: y ∈ [0.188, 0.378] mm |
| `system/topoSetDict` | box inkRegion: y ∈ [0.188, 0.378] mm |

### Nouvelles coordonnées
```
Buse:
  - Bas (gap): y = 0.188 mm
  - Haut (inlet): y = 0.628 mm
  - Largeur: x = [-0.15, 0.15] mm = 300 µm

Gap: 0.188 - 0.128 = 60 µm

Encre initiale: y ∈ [0.188, 0.378] mm (190 µm de hauteur)
```

---

## SCRIPT GIF AMÉLIORÉ

Fichier : `scripts/create_comparison_gif.py`

Nouveaux paramètres :
- `--fps` : défaut 2 (au lieu de 5)
- `--pause` : pause finale en secondes (défaut 2s)

Usage :
```bash
python3 scripts/create_comparison_gif.py --study <name> --fps 2 --pause 2
```

---

## FICHIERS CLÉS

| Fichier | Rôle |
|---------|------|
| `scripts/parametric_runner.py` | Lanceur études (CORRIGÉ) |
| `scripts/create_comparison_gif.py` | Génération GIF (AMÉLIORÉ) |
| `config/studies/viscosity_gap60.yaml` | Config étude gap 60µm |
| `templates/system/blockMeshDict` | Géométrie gap 60µm |

---

## COMMANDES UTILES

```bash
# Lister études
python3 scripts/parametric_runner.py list

# Lancer une étude
python3 scripts/parametric_runner.py run --study <name>

# Conversion VTK
source /opt/openfoam13/etc/bashrc
foamToVTK -case results/<study>/run_XXX

# Générer GIF lent avec pause
source ~/miniconda3/etc/profile.d/conda.sh && conda activate electrochemistry
python3 scripts/create_comparison_gif.py --study <name> --fps 2 --pause 2

# Créer fichiers .foam pour ParaView
touch results/<study>/run_XXX/case.foam
```

---

## PROCHAINES ÉTAPES POSSIBLES

1. Analyser différences visuelles entre gap 30µm et 60µm
2. Étude paramétrique sur l'angle de contact
3. Étude paramétrique sur la tension de surface
4. Augmenter le temps de simulation si étalement incomplet

---

**Auteur:** Claude Code
**Projet:** 05_AgCl_OF_param_v5
