# CHECKPOINT - 24 Décembre 2025
## Système de Paramètres Centralisés (Style COMSOL)

---

## 1. RÉSUMÉ EXÉCUTIF

### Travaux effectués depuis le dernier checkpoint (23/12/2025):

1. **Création fichier central `system/parameters`** - Source unique de vérité
2. **Modification templates OpenFOAM** - Tous utilisent `#include "parameters"`
3. **Création module Python `openfoam_params.py`** - Lecture centralisée
4. **Correction 5 scripts Python** - Élimination valeurs hardcodées
5. **Nouveaux paramètres** - `x_plateau`, `x_gap_buse` ajoutés

### Objectif atteint:
> Gérer TOUS les paramètres depuis UN SEUL fichier, comme COMSOL.

---

## 2. ARCHITECTURE CENTRALISÉE

### Avant (problématique):
```
blockMeshDict     → valeurs en dur (0.128, 0.198, 0.539...)
setFieldsDict     → valeurs en dur (0.000198, 0.000539...)
alpha.water       → CA en dur (35°, 90°, 180°...)
transportProperties → viscosité en dur
controlDict       → temps en dur
scripts Python    → rho=3000, geometry en dur
```

### Après (centralisé):
```
templates/system/parameters    ← SOURCE UNIQUE
         │
         ├──→ blockMeshDict      (#include "parameters")
         ├──→ setFieldsDict      (#include "parameters")
         ├──→ alpha.water        (#include "../system/parameters")
         ├──→ controlDict        (#include "parameters")
         ├──→ transportProperties (#include "../system/parameters")
         │
         └──→ scripts/openfoam_params.py
                    │
                    ├──→ parametric_runner.py
                    ├──→ run_parametric.py
                    ├──→ create_vtk_animation.py
                    ├──→ create_streamlit_gif.py
                    └──→ generate_alpha_field.py
```

---

## 3. FICHIER CENTRAL: `templates/system/parameters`

### Contenu complet:
```cpp
/*--------------------------------*- C++ -*----------------------------------*\
  =========                 |
  \      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \    /   O peration     | Website:  https://openfoam.org
    \  /    A nd           | Version:  13
     \/     M anipulation  |
\*---------------------------------------------------------------------------*/
FoamFile
{
    format      ascii;
    class       dictionary;
    location    "system";
    object      parameters;
}
// ============================================================================
// FICHIER CENTRAL DE PARAMETRES - Style COMSOL
// ============================================================================

// === GEOMETRY [mm] ===
x_puit          0.8;        // Largeur totale du puit
x_puit_half     0.4;        // Demi-largeur puit
y_puit          0.128;      // Profondeur du puit
x_plateau       0.4;        // Largeur du plateau isolant

x_buse          0.3;        // Largeur de la buse
x_buse_half     0.15;       // Demi-largeur buse
y_buse          0.341;      // Hauteur colonne encre dans buse

y_gap_buse      0.070;      // Gap vertical buse-puit (70 µm)
x_gap_buse      0.0;        // Décalage horizontal buse (0 = centré)

y_air           0.080;      // Hauteur couche air au-dessus puit
x_isolant       0.8;        // Largeur totale isolant

// === Valeurs dérivées (calculées) ===
y_buse_bottom   0.198;      // y_puit + y_gap_buse
y_buse_top      0.539;      // y_buse_bottom + y_buse
y_air_top       0.278;      // y_buse_bottom + y_air

// === Conversions SI [m] pour OpenFOAM ===
x_puit_m        0.0008;
x_puit_half_m   0.0004;
y_puit_m        0.000128;
x_buse_m        0.0003;
x_buse_half_m   0.00015;
y_buse_m        0.000341;
y_gap_buse_m    0.00007;
x_gap_buse_m    0.0;
y_buse_bottom_m 0.000198;
y_buse_top_m    0.000539;
y_air_top_m     0.000278;
x_isolant_m     0.0008;

// === PHYSICS - Ink ===
rho_ink         3000;       // Density [kg/m³]
eta_0           0.5;        // Zero-shear viscosity [Pa.s]
eta_inf         0.167;      // Infinite-shear viscosity [Pa.s]
lambda          0.15;       // Carreau time constant [s]
n_carreau       0.7;        // Carreau exponent [-]
nu_0            1.667e-4;   // Kinematic viscosity η₀/ρ [m²/s]
nu_inf          5.567e-5;   // Kinematic viscosity η∞/ρ [m²/s]
sigma           0.040;      // Surface tension [N/m]

// === PHYSICS - Air ===
rho_air         1.2;        // Density [kg/m³]
mu_air          1e-5;       // Dynamic viscosity [Pa.s]
nu_air          8.33e-6;    // Kinematic viscosity [m²/s]

// === CONTACT ANGLES [degrees] ===
CA_substrate            35;     // Substrat (or) - hydrophile
CA_wall_isolant_left    90;     // Paroi verticale isolant gauche
CA_wall_isolant_right   90;     // Paroi verticale isolant droite
CA_top_isolant_left     60;     // Surface horizontale isolant gauche
CA_top_isolant_right    60;     // Surface horizontale isolant droite
CA_buse_int_left        90;     // Paroi intérieure buse gauche
CA_buse_int_right       90;     // Paroi intérieure buse droite
CA_buse_ext_left        180;    // Paroi extérieure buse gauche
CA_buse_ext_right       180;    // Paroi extérieure buse droite

// === NUMERICAL ===
endTime         0.1;        // Simulation time [s]
writeInterval   0.002;      // Output interval [s]
deltaT          1e-6;       // Initial timestep [s]
maxCo           0.3;        // Max Courant number
maxAlphaCo      0.3;        // Max alpha Courant number
maxDeltaT       1e-3;       // Max timestep [s]

// === MESH ===
cell_size       5.0;        // Target cell size [µm]
```

---

## 4. TEMPLATES OPENFOAM MODIFIÉS

### 4.1 `templates/system/blockMeshDict`
```cpp
#include "parameters"

// Calculs des positions
x_buse_left  #calc "-$x_buse_half + $x_gap_buse";
x_buse_right #calc "$x_buse_half + $x_gap_buse";

vertices
(
    // Utilise variables: $x_puit_half, $y_puit, $x_buse_left, etc.
    (-$x_puit_half 0.0 0.0)
    ...
);
```

### 4.2 `templates/system/setFieldsDict`
```cpp
#include "parameters"

// Variables en mètres avec décalage x_gap_buse
x_buse_left_m   #calc "-$x_buse_half_m + $x_gap_buse_m";
x_buse_right_m  #calc "$x_buse_half_m + $x_gap_buse_m";

regions
(
    boxToCell
    {
        box ($x_buse_left_m $y_buse_bottom_m -1) ($x_buse_right_m $y_buse_top_m 1);
        ...
    }
);
```

### 4.3 `templates/0/alpha.water`
```cpp
#include "../system/parameters"

boundaryField
{
    substrate
    {
        type            contactAngle;
        theta0          $CA_substrate;
        ...
    }
    wall_isolant_left
    {
        type            contactAngle;
        theta0          $CA_wall_isolant_left;
        ...
    }
    // ... 9 angles de contact au total
}
```

### 4.4 `templates/system/controlDict`
```cpp
#include "parameters"

endTime         $endTime;
writeInterval   $writeInterval;
deltaT          $deltaT;
```

### 4.5 `templates/constant/transportProperties`
```cpp
#include "../system/parameters"

phases (water air);

water
{
    transportModel  Newtonian;
    nu              $nu_0;
    rho             $rho_ink;
}

air
{
    transportModel  Newtonian;
    nu              $nu_air;
    rho             $rho_air;
}

sigma           $sigma;
```

---

## 5. MODULE PYTHON: `scripts/openfoam_params.py`

### Fonctions principales:
```python
def read_parameters(case_dir: Path = None) -> dict:
    """Lit le fichier system/parameters OpenFOAM."""

def get_parameter(params: dict, key: str, default=None):
    """Récupère un paramètre avec valeur par défaut."""

def get_geometry(params: dict = None) -> dict:
    """Retourne tous les paramètres géométriques [mm]."""

def get_contact_angles(params: dict = None) -> dict:
    """Retourne tous les angles de contact [degrés]."""

def get_rho_ink(params: dict = None) -> float:
    """Densité encre [kg/m³]."""

def get_eta_0(params: dict = None) -> float:
    """Viscosité zéro-cisaillement [Pa.s]."""

def get_sigma(params: dict = None) -> float:
    """Tension de surface [N/m]."""
```

### Test du module:
```bash
$ python3 scripts/openfoam_params.py

=== OpenFOAM Parameters Reader Test ===

Geometry:
  x_puit: 0.8 mm
  y_puit: 0.128 mm
  x_buse: 0.3 mm
  y_buse: 0.341 mm
  y_gap_buse: 0.07 mm
  x_gap_buse: 0.0 mm
  x_plateau: 0.4 mm

Physics:
  rho_ink: 3000 kg/m³
  eta_0: 0.5 Pa.s
  sigma: 40.0 mN/m

Contact Angles:
  CA_substrate: 35°
  CA_wall_isolant_left: 90°
  CA_wall_isolant_right: 90°
  ... (9 angles au total)

Derived:
  S_puit: 0.1024 mm²
  S_buse: 0.1023 mm²
  ratio: 99.90%
```

---

## 6. SCRIPTS PYTHON CORRIGÉS

| Script | Valeurs supprimées | Correction |
|--------|-------------------|------------|
| `parametric_runner.py` | `RHO_INK = 3000.0` | `RHO_INK = get_rho_ink()` |
| `run_parametric.py` | `rho = 3000` | `rho = get_rho_ink()` |
| `create_vtk_animation.py` | `density: 3000`, géométrie | Lecture depuis params |
| `create_streamlit_gif.py` | Tous params en dur | Lecture depuis params |
| `generate_alpha_field.py` | 9 CA hardcodés | Lecture depuis params |

### Exemple de correction (`run_parametric.py`):
```python
# AVANT
def modify_transport_properties(case_dir, viscosity_Pa_s):
    rho = 3000  # kg/m³  ← HARDCODÉ
    nu0 = viscosity_Pa_s / rho

# APRÈS
from openfoam_params import get_rho_ink

def modify_transport_properties(case_dir, viscosity_Pa_s):
    rho = get_rho_ink()  # ← LU DEPUIS PARAMETERS
    nu0 = viscosity_Pa_s / rho
```

---

## 7. NOUVEAUX PARAMÈTRES AJOUTÉS

### 7.1 `x_plateau` - Largeur du plateau isolant
- Valeur: 0.4 mm
- Usage: Définit la largeur des plateaux isolants de chaque côté du puit

### 7.2 `x_gap_buse` - Décalage horizontal de la buse
- Valeur par défaut: 0.0 mm (centré)
- Plage: 0 à -0.05 mm
- Usage: Études paramétriques du décentrage de la buse

### 7.3 9 angles de contact indépendants
Chaque paroi a son propre angle de contact (gauche/droite séparés):
- `CA_substrate` - Substrat or
- `CA_wall_isolant_left/right` - Parois verticales isolant
- `CA_top_isolant_left/right` - Surfaces horizontales isolant
- `CA_buse_int_left/right` - Parois intérieures buse
- `CA_buse_ext_left/right` - Parois extérieures buse

---

## 8. STRUCTURE FICHIERS MODIFIÉS

```
05_AgCl_OF_param_v5/
├── templates/
│   ├── system/
│   │   ├── parameters              # CRÉÉ - fichier central
│   │   ├── blockMeshDict           # MODIFIÉ - #include
│   │   ├── setFieldsDict           # MODIFIÉ - #include
│   │   └── controlDict             # MODIFIÉ - #include
│   ├── constant/
│   │   └── transportProperties     # MODIFIÉ - #include
│   └── 0/
│       └── alpha.water             # MODIFIÉ - #include + $variables
├── scripts/
│   ├── openfoam_params.py          # CRÉÉ - module Python
│   ├── parametric_runner.py        # MODIFIÉ - import openfoam_params
│   ├── run_parametric.py           # MODIFIÉ - import openfoam_params
│   ├── create_vtk_animation.py     # MODIFIÉ - import openfoam_params
│   ├── create_streamlit_gif.py     # MODIFIÉ - import openfoam_params
│   └── generate_alpha_field.py     # MODIFIÉ - import openfoam_params
└── 02_checkpoints/
    └── CHECKPOINT_2025-12-24_centralized_parameters.md  # CE FICHIER
```

---

## 9. AVANTAGES DU SYSTÈME

1. **Source unique de vérité** - Un seul fichier à modifier
2. **Pas de risque d'incohérence** - Toutes les valeurs propagées automatiquement
3. **Facilité d'études paramétriques** - Modifier UN paramètre = impact global
4. **Lisibilité COMSOL-like** - Paramètres groupés par catégorie
5. **Python & OpenFOAM synchronisés** - Même source de données

---

## 10. COMMANDES UTILES

### Tester la lecture des paramètres:
```bash
python3 scripts/openfoam_params.py
```

### Vérifier qu'OpenFOAM lit les paramètres:
```bash
source /opt/openfoam13/etc/bashrc
cd templates
foamDictionary system/blockMeshDict -entry vertices -value
```

### Modifier un paramètre et reconstruire:
```bash
# 1. Éditer templates/system/parameters
# 2. Reconstruire le maillage
blockMesh
setFields
```

---

## 11. LIMITATIONS CONNUES

### Rendu PyVista en WSL2:
- PyVista/VTK très lent sans GPU
- Génération GIF peut bloquer
- Solution: Exécuter sur machine avec GPU ou utiliser matplotlib

### Fichiers polyMesh:
- Le maillage `constant/polyMesh` doit être régénéré si géométrie change
- Le fichier `alpha.water` avec champ interne doit être régénéré

---

## 12. PROCHAINES ÉTAPES SUGGÉRÉES

1. [ ] Régénérer maillage avec nouveau `blockMeshDict` paramétré
2. [ ] Tester étude paramétrique avec variation de `x_gap_buse`
3. [ ] Ajouter validation automatique des paramètres (plages valides)
4. [ ] Documenter dans CLAUDE.md la liste complète des paramètres

---

**Date:** 24 Décembre 2025
**Auteur:** Claude Code
**Version:** 5.3 - Paramètres Centralisés (Style COMSOL)
