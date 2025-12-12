# /startup - Restauration après compactage

Lis CLAUDE.md et affiche l'état actuel du projet:

```bash
echo "=== ÉTAT DU PROJET PARAMÉTRIQUE ==="
echo ""
echo "📁 Études disponibles:"
ls config/studies/*.yaml 2>/dev/null || echo "Aucune étude définie"
echo ""
echo "📊 Résultats existants:"
ls -d results/*/ 2>/dev/null | head -5 || echo "Aucun résultat"
echo ""
echo "📝 Dernier checkpoint:"
ls -t 02_checkpoints/CHECKPOINT_SESSION_*.md 2>/dev/null | head -1
echo ""
echo "⚙️ Paramètres de base:"
cat config/base_parameters.yaml 2>/dev/null | head -20 || echo "Non configuré"
```

Ensuite, demande à l'utilisateur: **"Quelle étude paramétrique veux-tu lancer ou analyser?"**
