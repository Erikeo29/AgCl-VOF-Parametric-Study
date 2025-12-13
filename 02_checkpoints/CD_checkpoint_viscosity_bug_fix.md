# CHECKPOINT - Correction Bug Étude Paramétrique Viscosité

**Date:** 2025-12-13
**Projet:** 05_AgCl_OF_param_v5
**Chemin:** /home/erikeo29/17_RD_Ag_AgCl/40_AgCl_OpenFOAM/05_AgCl_OF_param_v5

---

## PROBLÈME IDENTIFIÉ

L'étude `example_viscosity_sweep` (5 simulations avec η₀ = 0.5, 1.0, 1.5, 2.0, 3.0 Pa·s) produisait des GIF visuellement identiques.

### Cause racine

**Bug dans `scripts/parametric_runner.py`, méthode `_modify_transport_properties()`**

Le script écrivait directement la valeur de η₀ (Pa·s) dans le champ `nu0` (m²/s) **SANS conversion**.

```python
# AVANT (BUG)
pattern = rf'({of_param}\s+)[^;]+(;)'
replacement = rf'\g<1>{value}\2'  # ❌ Écrit 0.5 Pa·s comme 0.5 m²/s
```

### Conséquence

| η₀ demandé | nu0 écrit (BUG) | nu0 attendu |
|------------|-----------------|-------------|
| 0.5 Pa·s | 0.5 m²/s ❌ | 1.667e-04 m²/s |
| 1.0 Pa·s | 1.0 m²/s ❌ | 3.333e-04 m²/s |
| 3.0 Pa·s | 3.0 m²/s ❌ | 1.000e-03 m²/s |

Toutes les viscosités étaient **3000× trop élevées**, rendant le fluide quasi-solide et masquant les différences.

---

## CORRECTION APPLIQUÉE ✅

**Fichier modifié:** `scripts/parametric_runner.py`

```python
# APRÈS (CORRIGÉ)
RHO_INK = 3000.0  # kg/m³

if param in ['eta0', 'eta_inf']:
    nu_value = value / RHO_INK  # Conversion Pa·s → m²/s
    formatted_value = f"{nu_value:.6e}"
else:
    formatted_value = str(value)
```

---

## ACTIONS À EXÉCUTER

```bash
cd /home/erikeo29/17_RD_Ag_AgCl/40_AgCl_OpenFOAM/05_AgCl_OF_param_v5

# 1. Supprimer les résultats erronés
rm -rf results/example_viscosity_sweep

# 2. Relancer l'étude
python3 scripts/parametric_runner.py run --study example_viscosity_sweep

# 3. Après simulation, convertir en VTK et générer GIF
python3 scripts/batch_vtk_convert.py --study example_viscosity_sweep
python3 scripts/create_comparison_gif.py --study example_viscosity_sweep
```

---

## VÉRIFICATION POST-CORRECTION

Après relance, vérifier dans chaque `run_XXX/constant/transportProperties` :

```
run_001_eta0_0.5:  nu0 = 1.666667e-04;  ✓
run_002_eta0_1.0:  nu0 = 3.333333e-04;  ✓
run_003_eta0_1.5:  nu0 = 5.000000e-04;  ✓
run_004_eta0_2.0:  nu0 = 6.666667e-04;  ✓
run_005_eta0_3.0:  nu0 = 1.000000e-03;  ✓
```

---

## RÉSULTAT ATTENDU

Les GIF comparatifs doivent montrer :
- η₀ = 0.5 Pa·s → Étalement rapide, goutte plus plate
- η₀ = 3.0 Pa·s → Étalement lent, goutte plus haute

---

## FICHIERS CLÉS

| Fichier | Rôle |
|---------|------|
| `scripts/parametric_runner.py` | Script principal (CORRIGÉ) |
| `config/studies/example_viscosity_sweep.yaml` | Config de l'étude |
| `templates/constant/transportProperties` | Template Carreau |
| `results/example_viscosity_sweep/` | Résultats (à regénérer) |
