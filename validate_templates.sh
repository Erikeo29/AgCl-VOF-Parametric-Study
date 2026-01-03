#!/bin/bash
# Script de Validation Templates OpenFOAM
# À exécuter après les corrections de Claude Code

echo "=========================================="
echo "VALIDATION TEMPLATES OPENFOAM - AgCl VOF"
echo "=========================================="
echo ""

TEMPLATES_DIR="/home/erikeo29/17_RD_Ag_AgCl/40_AgCl_OpenFOAM/05_AgCl_OF_param_v5/templates/constant"
ERRORS=0

echo "📁 Répertoire: $TEMPLATES_DIR"
echo ""

# VÉRIFICATION 1: physicalProperties.air
echo "🔍 VÉRIFICATION 1: physicalProperties.air"
echo "----------------------------------------"
FILE="$TEMPLATES_DIR/physicalProperties.air"

if [ ! -f "$FILE" ]; then
    echo "❌ ERREUR: Fichier non trouvé: $FILE"
    ERRORS=$((ERRORS + 1))
else
    # Vérifier rho = 1.0
    if grep -q "^rho.*1\.0;" "$FILE"; then
        echo "✅ rho = 1.0 (CORRECT)"
    else
        echo "❌ rho ≠ 1.0 (INCORRECT)"
        grep "^rho" "$FILE"
        ERRORS=$((ERRORS + 1))
    fi
    
    # Vérifier nu = 1.48e-05
    if grep -q "^nu.*1\.48e-05;" "$FILE"; then
        echo "✅ nu = 1.48e-05 (CORRECT)"
    else
        echo "❌ nu ≠ 1.48e-05 (INCORRECT)"
        grep "^nu" "$FILE"
        ERRORS=$((ERRORS + 1))
    fi
    
    # Vérifier viscosityModel présent
    if grep -q "^viscosityModel" "$FILE"; then
        echo "✅ viscosityModel présent (CORRECT)"
    else
        echo "❌ viscosityModel manquant (INCORRECT)"
        ERRORS=$((ERRORS + 1))
    fi
fi
echo ""

# VÉRIFICATION 2: momentumTransport.air
echo "🔍 VÉRIFICATION 2: momentumTransport.air"
echo "----------------------------------------"
FILE="$TEMPLATES_DIR/momentumTransport.air"

if [ ! -f "$FILE" ]; then
    echo "❌ ERREUR: Fichier non trouvé: $FILE"
    ERRORS=$((ERRORS + 1))
else
    # Vérifier ABSENCE de viscosityModel et nu
    if grep -q "^[[:space:]]*viscosityModel" "$FILE"; then
        echo "❌ viscosityModel présent (devrait être dans physicalProperties.air)"
        ERRORS=$((ERRORS + 1))
    else
        echo "✅ Pas de viscosityModel (CORRECT)"
    fi
    
    if grep -q "^[[:space:]]*nu[[:space:]]" "$FILE"; then
        echo "❌ nu présent (devrait être dans physicalProperties.air)"
        ERRORS=$((ERRORS + 1))
    else
        echo "✅ Pas de nu (CORRECT)"
    fi
fi
echo ""

# VÉRIFICATION 3: momentumTransport.water
echo "🔍 VÉRIFICATION 3: momentumTransport.water"
echo "----------------------------------------"
FILE="$TEMPLATES_DIR/momentumTransport.water"

if [ ! -f "$FILE" ]; then
    echo "❌ ERREUR: Fichier non trouvé: $FILE"
    ERRORS=$((ERRORS + 1))
else
    # Vérifier nu0 = 5.0e-04
    if grep -q "nu0.*5\.0e-04;" "$FILE"; then
        echo "✅ nu0 = 5.0e-04 (CORRECT)"
    else
        echo "❌ nu0 ≠ 5.0e-04 (INCORRECT)"
        grep "nu0" "$FILE"
        ERRORS=$((ERRORS + 1))
    fi
    
    # Vérifier nuInf = 3.33e-07
    if grep -q "nuInf.*3\.33e-07;" "$FILE"; then
        echo "✅ nuInf = 3.33e-07 (CORRECT)"
    else
        echo "❌ nuInf ≠ 3.33e-07 (INCORRECT)"
        grep "nuInf" "$FILE"
        ERRORS=$((ERRORS + 1))
    fi
    
    # Vérifier k = 0.1
    if grep -q "k.*0\.1;" "$FILE"; then
        echo "✅ k = 0.1 (CORRECT)"
    else
        echo "❌ k ≠ 0.1 (INCORRECT)"
        grep "^[[:space:]]*k[[:space:]]" "$FILE"
        ERRORS=$((ERRORS + 1))
    fi
    
    # Vérifier n = 0.5
    if grep -q "n.*0\.5;" "$FILE"; then
        echo "✅ n = 0.5 (CORRECT)"
    else
        echo "❌ n ≠ 0.5 (INCORRECT)"
        grep "^[[:space:]]*n[[:space:]]" "$FILE"
        ERRORS=$((ERRORS + 1))
    fi
fi
echo ""

# RÉSUMÉ
echo "=========================================="
echo "RÉSUMÉ DE LA VALIDATION"
echo "=========================================="
if [ $ERRORS -eq 0 ]; then
    echo "✅ ✅ ✅ TOUS LES TESTS PASSENT ! ✅ ✅ ✅"
    echo ""
    echo "Les templates sont cohérents avec base_parameters.yaml"
    echo "Vous pouvez lancer l'interface Streamlit en toute confiance."
    exit 0
else
    echo "❌ ❌ ❌ $ERRORS ERREUR(S) DÉTECTÉE(S) ! ❌ ❌ ❌"
    echo ""
    echo "Certains templates ne correspondent pas à base_parameters.yaml"
    echo "Vérifiez les corrections ci-dessus."
    exit 1
fi
