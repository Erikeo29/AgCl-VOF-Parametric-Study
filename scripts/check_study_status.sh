#!/bin/bash
# Script pour surveiller l'avancement d'une étude paramétrique

STUDY=${1:-full_parametric_32}
RESULTS_DIR="results/$STUDY"

echo "=== STATUS: $STUDY ==="
echo ""

if [ ! -d "$RESULTS_DIR" ]; then
    echo "Étude non trouvée: $RESULTS_DIR"
    exit 1
fi

# Compter les runs
total=$(ls -d $RESULTS_DIR/run_* 2>/dev/null | wc -l)
completed=0
running=0
error=0

for run in $RESULTS_DIR/run_*/; do
    if [ -f "${run}run.log" ]; then
        if grep -q "^End$" "${run}run.log" 2>/dev/null; then
            ((completed++))
        elif grep -q "FOAM FATAL" "${run}run.log" 2>/dev/null; then
            ((error++))
        else
            ((running++))
            # Afficher le temps actuel de la simulation en cours
            current_time=$(grep "^Time = " "${run}run.log" 2>/dev/null | tail -1 | awk '{print $3}')
            run_name=$(basename "$run")
            if [ -n "$current_time" ]; then
                echo "  En cours: $run_name (t=${current_time}s)"
            fi
        fi
    fi
done

pending=$((total > 0 ? 32 - total : 32))

echo ""
echo "Résumé:"
echo "  ✅ Terminées:   $completed / 32"
echo "  🔄 En cours:    $running"
echo "  ❌ Erreurs:     $error"
echo "  ⏳ En attente:  $pending"
echo ""
echo "Dossier: $RESULTS_DIR"
