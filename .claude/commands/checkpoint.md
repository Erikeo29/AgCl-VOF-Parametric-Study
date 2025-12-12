# /checkpoint - Sauvegarder l'état du projet

Quand l'utilisateur tape `/checkpoint`:

1. **Créer un fichier checkpoint** dans `02_checkpoints/` avec ce format:

```
02_checkpoints/CHECKPOINT_SESSION_YYYY-MM-DD_[description].md
```

2. **Contenu du checkpoint**:

```markdown
# Checkpoint: [Description courte]
**Date**: YYYY-MM-DD HH:MM
**Status**: COMPLETE ✅ | IN_PROGRESS 🔄 | BLOCKED 🔴

## Études paramétriques
- Études créées: ...
- Études en cours: ...
- Études terminées: ...

## Ce qui fonctionne
- ✅ ...

## Problèmes résolus
- ...

## Prochaines étapes
- ⏭️ ...

## Fichiers clés modifiés
- ...
```

3. **Demander confirmation** à l'utilisateur avant de créer le fichier.

---

**Exemple de nom de fichier**:
- `CHECKPOINT_SESSION_2025-12-12_viscosity-sweep-complete.md`
- `CHECKPOINT_SESSION_2025-12-12_contact-angle-study.md`
