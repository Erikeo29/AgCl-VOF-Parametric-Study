# INSTRUCTIONS POUR CLAUDE CODE - Corrections Templates OpenFOAM
**Date:** 13 décembre 2025 - 22:45  
**Objectif:** Corriger définitivement les templates OpenFOAM pour cohérence avec `base_parameters.yaml`

---

## 🎯 CONTEXTE

Le fichier `Gem_GUI_Final_Checkpoint_20251213.md` montre que **`templates/constant/physicalProperties.air` contient encore des valeurs incorrectes** qui ne correspondent pas à `config/base_parameters.yaml`.

**Problème identifié:**
- `physicalProperties.air` a `rho = 1.2` et `nu = 8.333e-06`
- `base_parameters.yaml` spécifie `rho_air: 1.0` et `nu_air: 1.48e-5`

---

## 📋 TÂCHES À EXÉCUTER

### ✅ TÂCHE 1: Corriger `templates/constant/physicalProperties.air`

**Fichier:** `templates/constant/physicalProperties.air`

**Action:** Remplacer TOUTES les lignes après les commentaires par ceci (EXACTEMENT):

```foam
viscosityModel  constant;

rho             1.0;

nu              1.48e-05;
```

**Justification:**
- `rho = 1.0` vient de `base_parameters.yaml → physical.rho_air`
- `nu = 1.48e-05` vient de `base_parameters.yaml → physical.nu_air`

**⚠️ ATTENTION:** Les valeurs actuelles `rho = 1.2` et `nu = 8.333e-06` sont FAUSSES.

---

### ✅ TÂCHE 2: Vérifier `templates/constant/momentumTransport.water`

**Fichier:** `templates/constant/momentumTransport.water`

**Action:** Vérifier que le bloc `laminar` contient EXACTEMENT:

```foam
laminar
{
    model           generalisedNewtonian;
    viscosityModel  BirdCarreau;

    nu0             5.0e-04;
    nuInf           3.33e-07;
    k               0.1;
    n               0.5;
}
```

**Justification:**
- `nu0 = 5.0e-04` = 1.5 Pa·s / 3000 kg/m³ (de `base_parameters.yaml → rheology.eta0`)
- `nuInf = 3.33e-07` = 0.001 Pa·s / 3000 kg/m³ (de `base_parameters.yaml → rheology.eta_inf`)
- `k = 0.1` (de `base_parameters.yaml → rheology.lambda`)
- `n = 0.5` (de `base_parameters.yaml → rheology.n`)

**Si différent:** Corriger pour correspondre exactement aux valeurs ci-dessus.

---

### ✅ TÂCHE 3: Vérifier `templates/constant/momentumTransport.air`

**Fichier:** `templates/constant/momentumTransport.air`

**Action:** Vérifier que le fichier contient EXACTEMENT:

```foam
simulationType  laminar;

laminar
{
    model   generalisedNewtonian;
}
```

**⚠️ IMPORTANT:** Ce fichier NE DOIT PAS contenir `viscosityModel` ni `nu` (ces paramètres vont dans `physicalProperties.air`).

---

### ✅ TÂCHE 4: Vérifier `gui.py` - Ligne 117

**Fichier:** `gui.py`

**Action:** Vérifier que la ligne 117 (dans `_modify_alpha_water_robust`) est:

```python
elif stripped.startswith('}'):
```

**PAS:**
```python
elif stripped.startswith('}')')  # ❌ FAUX
```

---

## 🧪 VALIDATION

Après avoir effectué ces corrections, exécute:

```bash
cd /home/erikeo29/17_RD_Ag_AgCl/40_AgCl_OpenFOAM/05_AgCl_OF_param_v5/templates/constant
cat physicalProperties.air
```

**Tu dois voir:**
```foam
viscosityModel  constant;

rho             1.0;

nu              1.48e-05;
```

---

## 📊 CHECKLIST COMPLÈTE

Coche chaque élément après vérification:

- [ ] `physicalProperties.air` : `rho = 1.0` (pas 1.2)
- [ ] `physicalProperties.air` : `nu = 1.48e-05` (pas 8.333e-06)
- [ ] `physicalProperties.air` : contient `viscosityModel  constant;`
- [ ] `momentumTransport.air` : NE contient PAS `viscosityModel` ni `nu`
- [ ] `momentumTransport.water` : `nu0 = 5.0e-04` (pas 1.667e-4)
- [ ] `momentumTransport.water` : `nuInf = 3.33e-07` (pas 5.56e-5)
- [ ] `momentumTransport.water` : `k = 0.1` (pas 0.15)
- [ ] `momentumTransport.water` : `n = 0.5` (pas 0.7)
- [ ] `gui.py` ligne 117: syntaxe correcte (pas de guillemet en trop)

---

## 🎯 RÉSULTAT ATTENDU

Une fois ces corrections appliquées:

1. **Interface Streamlit** démarre sans erreur
2. **Mode Dry Run** génère des fichiers corrects avec valeurs de `base_parameters.yaml`
3. **Simulation réelle** démarre sans erreur `FOAM FATAL IO ERROR`

---

## 📝 APRÈS CORRECTIONS

Rapporte-moi:
1. Liste des fichiers modifiés
2. Contenu de chaque fichier modifié (affiche avec `cat`)
3. Résultat du test Dry Run dans l'interface Streamlit

---

**FIN DES INSTRUCTIONS - Prêt pour exécution avec Claude Code**
