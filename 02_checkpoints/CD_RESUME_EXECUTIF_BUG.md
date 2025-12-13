# RÉSUMÉ EXÉCUTIF : Bug Critique Étude Viscosité

**Statut**: 🔴 **BUG CRITIQUE**  
**Impact**: ❌ **Résultats INVALIDES**  
**Temps fix**: ⏱️ 15 minutes (code) + 3h (relance simulations)

---

## DIAGNOSTIC EN 3 LIGNES

1. **Les 5 GIFs sont identiques car ils représentent le même comportement physique**
2. **Bug**: Script écrit η (Pa·s) comme ν (m²/s) sans diviser par ρ → viscosités 3000× trop élevées
3. **Résultat**: Fluide "gelé" (comme du goudron), aucune variation visible

---

## CHIFFRES CLÉS

| Paramètre | Valeur ACTUELLE | Valeur CORRECTE | Erreur |
|-----------|----------------|-----------------|---------|
| ν₀ (run 1) | 0.5 m²/s | 0.000167 m²/s | ×3000 |
| ν₀ (run 5) | 3.0 m²/s | 0.001000 m²/s | ×3000 |

**Contexte**: Viscosité eau = 10⁻⁶ m²/s  
**Vos simulations**: 0.5 à 3.0 m²/s = **500 000× à 3 000 000× plus visqueux que l'eau**

---

## ACTION IMMÉDIATE (15 min)

```bash
# 1. Lire analyse complète
cat 02_checkpoints/CHECKPOINT_2025-12-13_ANALYSE_BUG_VISCOSITY.md

# 2. Appliquer correction
cat 02_checkpoints/CODE_CORRECTION_parametric_runner.md

# 3. Copier code corrigé dans scripts/parametric_runner.py
#    (Méthode _modify_transport_properties, ligne ~90)

# 4. Tester
python3 scripts/test_unit_conversion.py

# 5. Si OK, relancer
python3 scripts/parametric_runner.py run --study example_viscosity_sweep
```

---

## CE QUI VA CHANGER

**AVANT (invalide)**:
- Tous GIFs identiques
- Fluide immobile
- 36 min/simulation

**APRÈS (corrigé)**:
- GIFs clairement différents
- Étalement 4-10× plus rapide pour η₀=0.5 vs η₀=3.0
- ~2-5 min/simulation

---

## FICHIERS À CONSULTER

1. **Analyse complète**: `02_checkpoints/CHECKPOINT_2025-12-13_ANALYSE_BUG_VISCOSITY.md`  
   → Explication détaillée, physique, métriques

2. **Code + tests**: `02_checkpoints/CODE_CORRECTION_parametric_runner.md`  
   → Code corrigé, tests unitaires, validation

3. **Ce fichier**: Résumé pour action rapide

---

## POURQUOI CE BUG ?

Script fait: `nu0 = eta0` (INCORRECT)  
Devrait faire: `nu0 = eta0 / rho` (CORRECT)

OpenFOAM attend des viscosités **cinématiques** (m²/s),  
mais le YAML fournit des viscosités **dynamiques** (Pa·s).

**Formule**: ν = η / ρ

---

## VALIDATION POST-FIX

```bash
# Vérifier valeurs dans les nouveaux runs
for run in results/example_viscosity_sweep/run_*; do
    grep "nu0" $run/constant/transportProperties
done

# Attendu:
# run_001: nu0  1.667e-04;  # = 0.5/3000  ✅
# run_002: nu0  3.333e-04;  # = 1.0/3000  ✅
# run_003: nu0  5.000e-04;  # = 1.5/3000  ✅
# run_004: nu0  6.667e-04;  # = 2.0/3000  ✅
# run_005: nu0  1.000e-03;  # = 3.0/3000  ✅
```

---

**Pour Claude Code**: Consulter les 2 autres fichiers checkpoint pour détails complets et code.
