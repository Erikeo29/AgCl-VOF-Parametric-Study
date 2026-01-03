# CHECKPOINT - 23 Décembre 2025
## Nouvelle Géométrie Ratio 100% + Étude Streamlit VOF

---

## 1. RÉSUMÉ EXÉCUTIF

### Travaux effectués depuis le dernier checkpoint (13/12/2025):

1. **Étude paramétrique streamlit_vof** - 12 simulations complètes
2. **Génération GIFs/PNGs** avec parois visibles
3. **Correction tri VTK** - ordre numérique des frames
4. **Audit géométrie** - identification incohérences fichiers
5. **Nouvelle géométrie ratio 100%** - gap 70µm, hauteur buse 0.341mm

---

## 2. ÉTUDE STREAMLIT_VOF (12 simulations)

### Paramètres étudiés:
| Paramètre | Valeurs |
|-----------|---------|
| Viscosité η₀ | 0.5, 1.5, 5.0 Pa·s |
| CA wall | 35°, 90° |
| CA substrate | 35°, 75° |

### Résultats:
- **12 simulations terminées** (100ms chacune)
- **12 GIFs** dans `results/streamlit_vof/gifs/`
- **12 PNGs** dans `results/streamlit_vof/png/`

### Fichiers créés/modifiés:
- `config/studies/streamlit_vof.yaml` - définition étude grid sweep
- `scripts/create_streamlit_gif.py` - génération GIFs avec parois

---

## 3. CORRECTION GÉNÉRATION GIFs

### Problème identifié:
- Tri alphabétique des fichiers VTK causait des "soubresauts"
- Exemple: `_1073.vtk` < `_12330.vtk` < `_1758.vtk` (alphabétique)

### Solution implémentée:
```python
def extract_time_index(filepath):
    match = re.search(r'_(\d+)\.vtk$', filepath.name)
    return int(match.group(1)) if match else 0

internal_files = sorted(internal_files, key=extract_time_index)
```

### Améliorations GIFs:
- Parois du puit visibles (lignes noires)
- Patches chargés: substrate, wall_isolant_*, wall_buse_*, top_isolant_*
- Temps correct affiché (0 → 100 ms)

---

## 4. AUDIT GÉOMÉTRIE - INCOHÉRENCES TROUVÉES

### Fichiers analysés:
| Fichier | Statut | Valeurs |
|---------|--------|---------|
| `templates/constant/polyMesh/*` | UTILISÉ | y_max=0.598mm |
| `templates/system/blockMeshDict` | OBSOLÈTE | y_max=0.628mm |
| `templates/system/setFieldsDict` | OBSOLÈTE | encre 0.19mm |
| `templates/0/alpha.water` | UTILISÉ | pré-rempli 17600 cellules |

### Géométrie ANCIENNE (incohérente):
- Puit: 0.8mm × 0.128mm = 0.1024 mm²
- Buse: 0.3mm × 0.44mm = 0.132 mm²
- **Ratio: ~129%**

---

## 5. NOUVELLE GÉOMÉTRIE - RATIO 100%

### Spécifications demandées:
- Gap: 70 µm (y = 0.128 → 0.198 mm)
- Ratio surface buse/puit: 100%

### Calculs:
```
Surface puit = 0.8 × 0.128 = 0.1024 mm²
Surface buse = 0.1024 mm² (ratio 100%)
Largeur buse = 0.3 mm (fixe)
Hauteur buse = 0.1024 / 0.3 = 0.341 mm
```

### Nouvelle géométrie:
| Élément | Y min (mm) | Y max (mm) | Hauteur (mm) |
|---------|------------|------------|--------------|
| Puit | 0.000 | 0.128 | 0.128 |
| Gap | 0.128 | 0.198 | 0.070 |
| Buse | 0.198 | 0.539 | 0.341 |
| Air haut | 0.198 | 0.278 | 0.080 |

### Fichiers modifiés:

#### `templates/system/blockMeshDict`:
- Vertices y=0.188 → y=0.198
- Vertices y=0.628 → y=0.539
- Cellules gap: 6 → 14 (70µm / 5µm)
- Cellules buse: 88 → 68 (341µm / 5µm)

#### `templates/system/setFieldsDict`:
```
box (-0.00015 0.000198 -1) (0.00015 0.000539 1)
```

---

## 6. SIMULATION TEST RATIO 100%

### Configuration:
- Durée: 50 ms
- WriteInterval: 2 ms
- 26 frames générées

### Vérification géométrie:
```
=== Région encre (alpha.water > 0.5) ===
X: -0.150 à 0.150 mm
Y: 0.198 à 0.539 mm

Largeur encre: 0.300 mm
Hauteur encre: 0.341 mm
Surface encre: 0.1023 mm²

=== VÉRIFICATION RATIO ===
Surface puit: 0.1024 mm²
Surface encre: 0.1023 mm²
RATIO: 99.9%
```

### Fichiers générés:
- `results/test_ratio100/` - simulation complète
- `results/gifs/test_ratio100.gif` - GIF validation
- `results/png/test_ratio100.png` - PNG état final

---

## 7. TEMPLATES FINALISÉS

### Mise à jour effectuée:
1. [x] `templates/constant/polyMesh/*` - 16880 cellules (ratio 100%)
2. [x] `templates/0/alpha.water` - 16880 valeurs + conditions limites contactAngle
3. [ ] Optionnel: Régénérer les 12 GIFs streamlit_vof avec ratio 100%

### Vérification cohérence:
- polyMesh: nCells = 16880 ✓
- alpha.water: 16880 valeurs ✓
- blockMeshDict: y=0.198 (gap), y=0.539 (buse top) ✓
- setFieldsDict: box (0.000198 → 0.000539) ✓

---

## 8. STRUCTURE FICHIERS MODIFIÉS

```
05_AgCl_OF_param_v5/
├── config/studies/
│   └── streamlit_vof.yaml          # CRÉÉ - étude 12 simulations
├── scripts/
│   └── create_streamlit_gif.py     # MODIFIÉ - parois + tri numérique
├── templates/system/
│   ├── blockMeshDict               # MODIFIÉ - ratio 100%, gap 70µm
│   └── setFieldsDict               # MODIFIÉ - région encre corrigée
├── results/
│   ├── streamlit_vof/              # 12 simulations complètes
│   │   ├── run_001_... à run_012_...
│   │   ├── gifs/                   # 12 GIFs
│   │   └── png/                    # 12 PNGs
│   ├── test_ratio100/              # Simulation test nouvelle géométrie
│   ├── gifs/test_ratio100.gif      # GIF validation
│   └── png/test_ratio100.png       # PNG validation
└── 02_checkpoints/
    └── CHECKPOINT_2025-12-23_ratio100_geometry.md  # CE FICHIER
```

---

## 9. COMMANDES UTILES

### Régénérer maillage + initialisation:
```bash
source /opt/openfoam13/etc/bashrc
cd results/test_ratio100
rm -rf constant/polyMesh
blockMesh
setFields
```

### Lancer simulation:
```bash
foamRun -solver incompressibleVoF
```

### Générer GIF:
```bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate electrochemistry
foamToVTK -case results/test_ratio100
python3 scripts/create_streamlit_gif.py --run results/test_ratio100
```

---

**Date:** 23 Décembre 2025
**Auteur:** Claude Code
**Version:** 5.2 - Ratio 100% (Templates finalisés)
