# CHECKPOINT - 2026-01-04 - CA_buse_int = 120 (Hydrophobe)

## Contexte

Apres les 48 simulations parametriques precedentes, observation que:
1. Peu d'overflow sur plateau gauche car buse centree
2. Goutte restait accrochee a la sortie de la buse (sticking)

## Corrections apportees

### 1. Offset de la buse
- `x_gap_buse = -0.075 mm` (decalage vers la gauche)
- Permet de favoriser l'overflow sur le plateau gauche

### 2. CA_buse_int = 120 (hydrophobe)
- Avant: `CA_buse_int = 90` (neutre) → goutte colle a la buse
- Apres: `CA_buse_int = 120` (hydrophobe) → goutte se detache proprement

### 3. eta_inf = 0.1 Pa.s
- Augmente de 0.001 a 0.1 Pa.s pour stabilite numerique
- Impact sur temps de calcul a evaluer

## Etudes realisees

### offset_buse_test (8 simulations)
```yaml
x_gap_buse: -0.075mm
ratio_surface: 0.8
eta_0: [0.5, 1.5]
CA_wall_isolant_left: [30, 60]
CA_top_isolant_left: [30, 60]
```
Resultats: `results/offset_buse_test/`

### CA_top_sweep (3 simulations)
```yaml
x_gap_buse: -0.075mm
ratio_surface: 0.8
eta_0: 0.5
CA_wall_isolant_left: 30
CA_top_isolant_left: [10, 20, 30]
CA_buse_int: 120  # NOUVEAU
```
Resultats: `results/CA_top_sweep/`

## Observations CA_top_sweep

| Run | CA_top | Comportement |
|-----|--------|--------------|
| 001 | 10 | Fort overflow gauche, encre tres etalee |
| 002 | 20 | Overflow modere, encre centree |
| 003 | 30 | Overflow limite, encre dans puit |

**Conclusion:** CA_buse_int=120 resout le probleme de sticking.

## Parametres actuels (templates/system/parameters)

```
// Geometrie
x_gap_buse      0.0;        // [mm] (modifie par runner)
ratio_surface   1.0;        // [-] (modifie par runner)

// Rheologie
eta_0           1.0;        // [Pa.s]
eta_inf         0.1;        // [Pa.s] (augmente pour stabilite)

// Angles de contact buse interieur
CA_buse_int_left   120;     // [deg] Hydrophobe
CA_buse_int_right  120;     // [deg] Hydrophobe

// Temps
endTime         0.1;        // [s] = 100 ms
```

## Prochaine etape

Ajouter `dispense_time` comme parametre pour controler le temps d'ejection:
- Actuellement: 80ms fixe dans 0/U (inlet velocity table)
- Objectif: Varier 20ms, 40ms, 80ms
- Calcul automatique de la vitesse pour volume constant

## Mecanisme ejection actuel

1. **fvOptions/pistonForce**: Force constante 1.2e6 N/m3 vers le bas
2. **0/U inlet**: Vitesse 6.83 mm/s pendant 80ms puis arret

---
*Checkpoint avant ajout dispense_time*
