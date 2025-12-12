# /run-study - Lancer une étude paramétrique

Quand l'utilisateur tape `/run-study [nom_étude]`:

1. **Vérifier que l'étude existe**:
```bash
ls config/studies/[nom_étude].yaml
```

2. **Afficher la configuration**:
```bash
cat config/studies/[nom_étude].yaml
```

3. **Demander confirmation** avec résumé:
- Paramètre varié
- Nombre de simulations
- Temps estimé (si connu)

4. **Lancer l'étude**:
```bash
python3 scripts/parametric_runner.py run --study [nom_étude]
```

5. **Suivre la progression**:
```bash
python3 scripts/parametric_runner.py status --study [nom_étude]
```

---

**Exemples**:
- `/run-study viscosity_sweep`
- `/run-study contact_angle_effect`
