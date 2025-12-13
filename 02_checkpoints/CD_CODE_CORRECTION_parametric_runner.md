# CODE CORRIGÉ : parametric_runner.py

**Date**: 2025-12-13  
**Bug Fixé**: Conversion η (Pa·s) → ν (m²/s) dans sweep de viscosité

---

## MÉTHODE CORRIGÉE

Remplacer la méthode `_modify_transport_properties` dans `scripts/parametric_runner.py` par cette version :

```python
def _modify_transport_properties(self, param: str, value):
    """
    Modifie constant/transportProperties pour Carreau.
    
    CRITIQUE: Gère les conversions d'unités automatiquement
    - eta0, eta_inf (Pa·s) → nu0, nuInf (m²/s) via division par rho
    - lambda, n → écrits directement (sans dimension ou déjà corrects)
    
    Args:
        param: Nom du paramètre ('eta0', 'eta_inf', 'lambda', 'n')
        value: Valeur en unités PHYSIQUES (voir config YAML)
    """
    file_path = self.case_dir / "constant" / "transportProperties"
    if not file_path.exists():
        print(f"Warning: {file_path} not found")
        return
    
    content = file_path.read_text()
    
    # ========================================================================
    # VISCOSITÉS : Conversion η (Pa·s) → ν (m²/s)
    # ========================================================================
    if param in ['eta0', 'eta_inf']:
        # 1. Extraire la densité depuis le fichier
        import re
        rho_match = re.search(r'rho\s+(\d+\.?\d*)', content)
        if not rho_match:
            print(f"❌ Erreur: densité 'rho' non trouvée dans {file_path}")
            print(f"   Le fichier doit contenir: rho <valeur>; dans le bloc water")
            return
        
        rho = float(rho_match.group(1))
        
        # 2. Conversion CRITIQUE : ν = η / ρ
        nu_value = value / rho
        
        # 3. Mapping vers nomenclature OpenFOAM
        param_map = {
            'eta0': 'nu0',      # Viscosité zero-shear
            'eta_inf': 'nuInf'  # Viscosité infinite-shear
        }
        of_param = param_map[param]
        
        # 4. Remplacer dans le fichier avec notation scientifique
        pattern = rf'({of_param}\s+)[^;]+(;)'
        replacement = rf'\g<1>{nu_value:.6e}\2'
        new_content = re.sub(pattern, replacement, content)
        
        file_path.write_text(new_content)
        
        # 5. Feedback utilisateur
        print(f"  ✓ {param} = {value} Pa·s → {of_param} = {nu_value:.6e} m²/s")
        print(f"    (conversion: η/ρ = {value}/{rho})")
    
    # ========================================================================
    # AUTRES PARAMÈTRES : Écriture directe (pas de conversion)
    # ========================================================================
    elif param in ['lambda', 'n']:
        # Ces paramètres sont déjà dans les bonnes unités (temps ou sans dimension)
        param_map = {
            'lambda': 'k',  # Temps de relaxation (s)
            'n': 'n'        # Exposant loi puissance (sans dimension)
        }
        of_param = param_map.get(param, param)
        
        pattern = rf'({of_param}\s+)[^;]+(;)'
        replacement = rf'\g<1>{value}\2'
        new_content = re.sub(pattern, replacement, content)
        
        file_path.write_text(new_content)
        print(f"  ✓ {param} = {value} (pas de conversion)")
    
    else:
        print(f"⚠️  Warning: Paramètre '{param}' non reconnu pour transportProperties")
```

---

## VALIDATION DE LA CORRECTION

### Test Unitaire

Créer `scripts/test_unit_conversion.py` :

```python
#!/usr/bin/env python3
"""
Test unitaire : Validation conversion η → ν dans parametric_runner.py

Usage:
    python3 scripts/test_unit_conversion.py
"""

import sys
from pathlib import Path
import tempfile
import shutil

# Ajouter le chemin du script à tester
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from parametric_runner import ParameterModifier


def create_test_case():
    """Crée un cas de test minimal."""
    test_dir = Path(tempfile.mkdtemp(prefix="test_param_"))
    
    # Créer structure minimale
    (test_dir / "constant").mkdir()
    
    # Fichier transportProperties de test
    transport_content = """
    phases (water air);
    
    water
    {
        transportModel  Carreau;
        rho             3000;
        
        Carreau
        {
            nu0         9.999e-99;  // Valeur bidon, sera remplacée
            nuInf       5.56e-5;
            lambda      0.15;
            n           0.7;
        }
    }
    """
    
    (test_dir / "constant" / "transportProperties").write_text(transport_content)
    
    return test_dir


def test_eta0_conversion():
    """Test: eta0 (Pa·s) → nu0 (m²/s) avec rho."""
    print("\n=== Test 1: Conversion eta0 → nu0 ===")
    
    # Setup
    test_case = create_test_case()
    modifier = ParameterModifier(test_case)
    
    # Paramètres de test
    eta0_test = 0.5      # Pa·s
    rho_expected = 3000  # kg/m³
    nu0_expected = eta0_test / rho_expected  # = 1.667e-4 m²/s
    
    print(f"Input: eta0 = {eta0_test} Pa·s")
    print(f"Densité: rho = {rho_expected} kg/m³")
    print(f"Attendu: nu0 = {nu0_expected:.6e} m²/s")
    
    # Appliquer modification
    modifier.set_parameter('rheology.eta0', eta0_test)
    
    # Vérifier
    content = (test_case / "constant" / "transportProperties").read_text()
    
    # Chercher nu0 dans le fichier
    import re
    nu0_match = re.search(r'nu0\s+([\d.e+-]+)', content)
    
    if not nu0_match:
        print("❌ ÉCHEC: nu0 non trouvé dans le fichier")
        cleanup(test_case)
        return False
    
    nu0_actual = float(nu0_match.group(1))
    
    print(f"Obtenu: nu0 = {nu0_actual:.6e} m²/s")
    
    # Tolérance 0.1%
    relative_error = abs(nu0_actual - nu0_expected) / nu0_expected
    
    if relative_error < 0.001:
        print(f"✅ SUCCÈS: Erreur relative = {relative_error*100:.3f}%")
        cleanup(test_case)
        return True
    else:
        print(f"❌ ÉCHEC: Erreur relative = {relative_error*100:.1f}% (> 0.1%)")
        cleanup(test_case)
        return False


def test_multiple_eta0_values():
    """Test: Plusieurs valeurs de eta0."""
    print("\n=== Test 2: Sweep de viscosités ===")
    
    test_values = [0.5, 1.0, 1.5, 2.0, 3.0]
    rho = 3000
    
    all_passed = True
    
    for eta0 in test_values:
        test_case = create_test_case()
        modifier = ParameterModifier(test_case)
        
        nu0_expected = eta0 / rho
        
        modifier.set_parameter('rheology.eta0', eta0)
        
        content = (test_case / "constant" / "transportProperties").read_text()
        import re
        nu0_match = re.search(r'nu0\s+([\d.e+-]+)', content)
        nu0_actual = float(nu0_match.group(1))
        
        relative_error = abs(nu0_actual - nu0_expected) / nu0_expected
        
        if relative_error < 0.001:
            print(f"  ✓ eta0={eta0} Pa·s → nu0={nu0_actual:.6e} m²/s (OK)")
        else:
            print(f"  ✗ eta0={eta0} Pa·s → nu0={nu0_actual:.6e} m²/s (ERREUR: {relative_error*100:.1f}%)")
            all_passed = False
        
        cleanup(test_case)
    
    if all_passed:
        print("✅ Tous les tests de sweep passés")
    else:
        print("❌ Certains tests de sweep ont échoué")
    
    return all_passed


def cleanup(test_dir):
    """Nettoie le répertoire de test."""
    shutil.rmtree(test_dir, ignore_errors=True)


def main():
    print("="*60)
    print("TESTS UNITAIRES: Conversion η → ν")
    print("="*60)
    
    test1 = test_eta0_conversion()
    test2 = test_multiple_eta0_values()
    
    print("\n" + "="*60)
    print("RÉSUMÉ")
    print("="*60)
    
    if test1 and test2:
        print("✅ TOUS LES TESTS PASSÉS")
        print("\nLe script parametric_runner.py gère correctement")
        print("la conversion η (Pa·s) → ν (m²/s)")
        return 0
    else:
        print("❌ CERTAINS TESTS ONT ÉCHOUÉ")
        print("\nVérifier l'implémentation de _modify_transport_properties")
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

### Lancer les Tests

```bash
cd ~/17_RD_Ag_AgCl/40_AgCl_OpenFOAM/05_AgCl_OF_param_v5

# Exécuter les tests
python3 scripts/test_unit_conversion.py

# Output attendu si correction OK:
# ================================================================
# TESTS UNITAIRES: Conversion η → ν
# ================================================================
# 
# === Test 1: Conversion eta0 → nu0 ===
# Input: eta0 = 0.5 Pa·s
# Densité: rho = 3000 kg/m³
# Attendu: nu0 = 1.666667e-04 m²/s
#   ✓ eta0 = 0.5 Pa·s → nu0 = 1.666667e-04 m²/s (conversion: η/ρ = 0.5/3000)
# Obtenu: nu0 = 1.666667e-04 m²/s
# ✅ SUCCÈS: Erreur relative = 0.000%
# 
# === Test 2: Sweep de viscosités ===
#   ✓ eta0=0.5 Pa·s → nu0=1.666667e-04 m²/s (OK)
#   ✓ eta0=1.0 Pa·s → nu0=3.333333e-04 m²/s (OK)
#   ✓ eta0=1.5 Pa·s → nu0=5.000000e-04 m²/s (OK)
#   ✓ eta0=2.0 Pa·s → nu0=6.666667e-04 m²/s (OK)
#   ✓ eta0=3.0 Pa·s → nu0=1.000000e-03 m²/s (OK)
# ✅ Tous les tests de sweep passés
# 
# ================================================================
# RÉSUMÉ
# ================================================================
# ✅ TOUS LES TESTS PASSÉS
```

---

## APPLICATION DE LA CORRECTION

### Étapes

1. **Sauvegarder la version actuelle**
   ```bash
   cd scripts/
   cp parametric_runner.py parametric_runner.py.BACKUP_2025-12-13
   ```

2. **Éditer le fichier**
   ```bash
   # Ouvrir dans votre éditeur préféré
   code parametric_runner.py
   # ou
   vim parametric_runner.py
   ```

3. **Remplacer la méthode `_modify_transport_properties`**
   - Chercher la méthode (ligne ~90-110)
   - Supprimer l'ancienne version
   - Coller la nouvelle version de ce fichier

4. **Sauvegarder**

5. **Créer le script de test**
   ```bash
   # Copier le code du test unitaire ci-dessus
   vim scripts/test_unit_conversion.py
   chmod +x scripts/test_unit_conversion.py
   ```

6. **Exécuter les tests**
   ```bash
   python3 scripts/test_unit_conversion.py
   ```

7. **Si tests OK, commit**
   ```bash
   git add scripts/parametric_runner.py scripts/test_unit_conversion.py
   git commit -m "FIX: Conversion η→ν (Pa·s → m²/s) + tests unitaires"
   ```

---

## RELANCER L'ÉTUDE CORRIGÉE

Une fois la correction validée par les tests :

```bash
# 1. Sauvegarder les résultats invalides
cd results/
mv example_viscosity_sweep example_viscosity_sweep_INVALID_BACKUP_2025-12-13

# 2. Relancer l'étude avec script corrigé
cd ..
python3 scripts/parametric_runner.py run --study example_viscosity_sweep

# 3. Post-traitement (quand terminé)
for run in results/example_viscosity_sweep/run_*; do
    foamToVTK -case "$run"
done

python3 scripts/create_comparison_gif.py --study example_viscosity_sweep --fps 5

# 4. Vérifier les résultats
ls -lh results/example_viscosity_sweep/comparison/
# Doit montrer: example_viscosity_sweep_comparison.gif
```

---

## VALIDATION DES RÉSULTATS CORRIGÉS

### Vérifications Manuelles

```bash
# Vérifier les valeurs dans les fichiers générés
for run in results/example_viscosity_sweep/run_*; do
    echo "=== $run ==="
    grep -A2 "nu0" $run/constant/transportProperties
done

# Output attendu:
# === results/example_viscosity_sweep/run_001_eta0_0.5 ===
#     nu0         1.666667e-04;  # ✅ = 0.5/3000
#
# === results/example_viscosity_sweep/run_002_eta0_1.0 ===
#     nu0         3.333333e-04;  # ✅ = 1.0/3000
#
# === results/example_viscosity_sweep/run_003_eta0_1.5 ===
#     nu0         5.000000e-04;  # ✅ = 1.5/3000
#
# === results/example_viscosity_sweep/run_004_eta0_2.0 ===
#     nu0         6.666667e-04;  # ✅ = 2.0/3000
#
# === results/example_viscosity_sweep/run_005_eta0_3.0 ===
#     nu0         1.000000e-03;  # ✅ = 3.0/3000
```

### Vérification Visuelle

Le nouveau GIF `example_viscosity_sweep_comparison.gif` doit montrer :

- **Run 1 (η₀=0.5)** : Étalement rapide et large
- **Run 2 (η₀=1.0)** : Intermédiaire
- **Run 3 (η₀=1.5)** : Valeur de base (template)
- **Run 4 (η₀=2.0)** : Étalement plus lent
- **Run 5 (η₀=3.0)** : Étalement le plus lent, diamètre final le plus petit

**Différences visuellement claires** entre les 5 cas.

---

## CHECKPOINT

✅ **Code corrigé fourni**  
✅ **Tests unitaires fournis**  
✅ **Procédure de validation définie**  
✅ **Instructions de relance documentées**

**Prochaine étape**: Appliquer la correction et relancer l'étude.

---

**Auteur**: Claude  
**Date**: 2025-12-13  
**Pour**: Projet 05_AgCl_OF_param_v5
