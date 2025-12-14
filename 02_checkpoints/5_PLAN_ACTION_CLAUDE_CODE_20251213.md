# 🎯 PLAN D'ACTION COMPLET - Claude Code
**Date:** 13 décembre 2025 - 22:50  
**Objectif:** Finaliser les corrections templates OpenFOAM

---

## 📚 DOCUMENTS CRÉÉS POUR TOI

J'ai créé 4 fichiers dans ton projet :

1. **`02_checkpoints/INSTRUCTIONS_CLAUDE_CODE_20251213.md`**  
   → Instructions détaillées pour Claude Code (COMMENCE PAR LÀ)

2. **`02_checkpoints/RÉSUMÉ_PROBLÈME_20251213.md`**  
   → Explication du problème (pour ta compréhension)

3. **`validate_templates.sh`**  
   → Script de validation automatique (à exécuter après corrections)

4. **`02_checkpoints/PLAN_ACTION_CLAUDE_CODE_20251213.md`** (CE FICHIER)  
   → Plan d'action complet

---

## 🚀 ÉTAPES À SUIVRE

### ÉTAPE 1️⃣ : Ouvre Claude Code

Lance Claude Code dans ton terminal WSL :

```bash
cd /home/erikeo29/17_RD_Ag_AgCl/40_AgCl_OpenFOAM/05_AgCl_OF_param_v5
```

### ÉTAPE 2️⃣ : Donne-lui les instructions

Copie-colle ceci dans Claude Code :

```
Lis le fichier 02_checkpoints/INSTRUCTIONS_CLAUDE_CODE_20251213.md
et exécute toutes les tâches qu'il contient.
```

### ÉTAPE 3️⃣ : Claude Code va corriger

Il va :
- ✅ Corriger `templates/constant/physicalProperties.air`
- ✅ Vérifier `templates/constant/momentumTransport.water`
- ✅ Vérifier `templates/constant/momentumTransport.air`
- ✅ Vérifier `gui.py` ligne 117

### ÉTAPE 4️⃣ : Valide les corrections

Une fois Claude Code a terminé, exécute le script de validation :

```bash
chmod +x validate_templates.sh
./validate_templates.sh
```

**Tu dois voir :**
```
✅ ✅ ✅ TOUS LES TESTS PASSENT ! ✅ ✅ ✅
```

### ÉTAPE 5️⃣ : Test Dry Run

Lance l'interface Streamlit :

```bash
streamlit run gui.py
```

Puis :
1. ✅ Active "Mode Débogage (Dry Run)"
2. ✅ Clique "🚀 Lancer une nouvelle simulation"
3. ✅ Vérifie dans "DRY RUN - Contenu des fichiers générés"

**Tu dois voir dans `physicalProperties.air` :**
```foam
rho             1.0;
nu              1.48e-05;
```

**PAS:**
```foam
rho             1.2;        ← ❌ FAUX
nu              8.333e-06;  ← ❌ FAUX
```

---

## 🔍 FICHIERS À CORRIGER (RÉSUMÉ RAPIDE)

### 1. `templates/constant/physicalProperties.air`

**AVANT (Gemini - FAUX) :**
```foam
rho             1.2;
nu              8.333e-06;
```

**APRÈS (Claude - CORRECT) :**
```foam
viscosityModel  constant;
rho             1.0;
nu              1.48e-05;
```

### 2. `templates/constant/momentumTransport.water`

**DOIT CONTENIR :**
```foam
nu0             5.0e-04;
nuInf           3.33e-07;
k               0.1;
n               0.5;
```

### 3. `templates/constant/momentumTransport.air`

**NE DOIT PAS CONTENIR :**
- `viscosityModel` (va dans physicalProperties.air)
- `nu` (va dans physicalProperties.air)

---

## 📊 CHECKLIST VALIDATION FINALE

Après que Claude Code a fini, vérifie :

- [ ] Script `validate_templates.sh` passe tous les tests
- [ ] Interface Streamlit démarre sans erreur
- [ ] Mode Dry Run génère `rho = 1.0` et `nu = 1.48e-05`
- [ ] Aucune erreur `FOAM FATAL IO ERROR` dans les logs

---

## 🆘 EN CAS DE PROBLÈME

Si quelque chose ne fonctionne pas :

1. **Vérifie le contenu actuel des templates :**
   ```bash
   cat templates/constant/physicalProperties.air
   cat templates/constant/momentumTransport.water
   ```

2. **Compare avec `base_parameters.yaml` :**
   ```bash
   cat config/base_parameters.yaml
   ```

3. **Rapporte-moi** :
   - Quel fichier pose problème
   - Le contenu actuel du fichier
   - Le message d'erreur (si applicable)

---

## 🎯 OBJECTIF FINAL

**Quand tout est OK :**

Tu pourras lancer des simulations OpenFOAM via l'interface Streamlit **sans erreur**, et modifier les paramètres rhéologiques (eta0, eta_inf, etc.) **directement depuis l'interface**.

---

**🚀 Prêt à démarrer avec Claude Code ! 🚀**

**Commence par ÉTAPE 1 ci-dessus ↑↑↑**
