---
name: solver-configuration
description: Configure interFoam solver with VOF multiphase method and Carreau non-Newtonian rheology for droplet spreading simulations
version: "1.0.0"
---

# Solver Configuration Skill

## When to use this skill

Invoke when:
- Setting up OpenFOAM case (0/, constant/, system/ directories)
- Configuring interFoam with VOF and Carreau model
- Defining boundary conditions (inlet, walls, outlets)
- Setting time stepping (deltaT, Courant number constraints)
- Implementing contact angle boundary conditions (hydrophobic surfaces)
- Verifying physical parameters match PARAMETERS_AgCl.md

## ⚠️ CRITICAL: Parameter Philosophy

**NEVER hardcode parameter values in this skill.**

All numerical values (viscosities, densities, surface tension, contact angles, velocities) are defined in:
- **Single source of truth**: `documentation/PARAMETERS_AgCl.md`
- Read from file at runtime, do NOT memorize or guess

This skill explains **HOW** to use parameters, not **WHAT** the values are.

## Key configuration principles

### Carreau Rheology (Non-Newtonian)

**What it is**: Mathematical model for shear-thinning fluids (viscosity decreases with shear rate)

**Parameters to read from `documentation/PARAMETERS_AgCl.md` → Fluid Properties: Ink**:
- Zero-shear viscosity (η₀)
- Infinite-shear viscosity (η∞)
- Relaxation time (λ)
- Power-law index (n)

**Validation**: Ensure n < 1 for shear-thinning behavior (typical for inks)

**OpenFOAM implementation**: All 4 values must appear in `constant/transportProperties`

### VOF Method (Volume of Fluid)

**What it is**: Multiphase flow method tracking sharp interface between ink and air

**Phase field (alpha)**:
- α = 0: Pure air
- α = 1: Pure ink
- 0 < α < 1: Interface region

**Discretization requirement**: Read from `documentation/PARAMETERS_AgCl.md` → Interface Properties
- Should specify: Use Gauss upwind for alpha field (CRITICAL for mass conservation)

**Contact angle**: Read from `documentation/PARAMETERS_AgCl.md` → Boundary Conditions
- Apply contactAngleFvPatchScalarField at hydrophobic walls
- Value: [Read from file, likely 145° but may vary by substrate treatment]

**Surface tension**: Read from `documentation/PARAMETERS_AgCl.md` → Interface Properties
- Implemented in transportProperties as `sigma` parameter
- Units: N/m

### Stability Constraints

**Courant number**:
- Definition: Co = U × Δt / Δx
- Requirement: Maintain Co < 0.3 (mandatory for VOF stability)
- How to achieve: Reduce Δt if Courant exceeds 0.3

**Density ratio**:
- Read densities from `documentation/PARAMETERS_AgCl.md` → Fluid Properties: Ink and Air
- Calculate ratio: ρ_ink / ρ_air
- Large ratios (>100) demand careful initialization and time stepping

**Interface resolution**:
- Target: 3-5 computational cells across expected droplet diameter
- Check from PARAMETERS_AgCl.md → Geometry → nozzle/well dimensions
- Mesh must be fine enough to resolve interface

## Workflow procedures

### Case setup sequence

1. **Read all parameters** from `documentation/PARAMETERS_AgCl.md`
   - Extract: Fluid properties (Carreau, densities), boundary conditions, simulation parameters, interface properties
   - Verify all required sections present

2. **Create 0/ directory** with initial conditions:
   - **U (velocity field)**:
     - Inlet BC: Fixed velocity (calculate from PARAMETERS_AgCl.md → Simulation Parameters → velocity)
     - Walls: No-slip boundary (0 velocity) - unless PARAMETERS_AgCl.md specifies otherwise
     - Outlet: Zero-gradient
   - **p_rgh (pressure field)**:
     - Standard practice: Reference pressure = 0 Pa
     - Inlet: Zero-gradient
     - Outlet: Fixed value (0 Pa)
     - Walls: Zero-gradient
   - **alpha.water (phase fraction)**:
     - Contact angle BC at walls: Read specified angle from PARAMETERS_AgCl.md → Boundary Conditions
     - Inlet: Fixed value (1.0 = pure ink, or ramp for smooth startup)
     - Outlet: Zero-gradient

3. **Create constant/ directory** with properties:
   - **transportProperties**:
     - Carreau model: η₀, η∞, λ, n (from PARAMETERS_AgCl.md → Fluid Properties: Ink)
     - Densities: ρ_ink, ρ_air (from PARAMETERS_AgCl.md → Fluid Properties)
     - Surface tension: σ (from PARAMETERS_AgCl.md → Interface Properties)
   - All values read directly from PARAMETERS_AgCl.md sections

4. **Create system/ configuration**:
   - **controlDict**:
     - endTime: From PARAMETERS_AgCl.md → Simulation Parameters
     - deltaT: Calculate to maintain Courant <0.3
     - writeInterval: Frequency for output (suggest every 0.001 s or similar)
   - **fvSchemes**:
     - Alpha field: **CRITICAL** → Gauss upwind (from PARAMETERS_AgCl.md → Interface Properties specification)
     - Velocity: Gauss linearUpwind
     - Laplacian: Gauss linear corrected
   - **fvSolution**:
     - Solver tolerances: p (1e-7), U (1e-6), alpha (1e-8)
     - PIMPLE: nOuterCorrectors=2, nCorrectors=2

5. **Verify all BCs and physics**:
   - All parameters match PARAMETERS_AgCl.md values (with sources cited)
   - No hardcoded project-specific values
   - Courant number achievable: Co = U × Δt / dx < 0.3

### Boundary conditions setup

**Inlet patch**:
- Velocity: Fixed value from PARAMETERS_AgCl.md → Simulation Parameters (inlet velocity v₀)
- Pressure: Zero-gradient
- Alpha: Fixed value 1.0 (pure ink) or ramped (smooth startup)

**Wall patches** (hydrophobic surfaces):
- Velocity: No-slip (0) - unless PARAMETERS_AgCl.md specifies slip
- Pressure: Zero-gradient
- Alpha: Contact angle BC with angle from PARAMETERS_AgCl.md → Boundary Conditions

**Outlet patches**:
- Velocity: Zero-gradient or pressureInletOutlet (domain-dependent)
- Pressure: Fixed value 0 Pa (reference)
- Alpha: Zero-gradient

### Courant number control

**Formula**:
```
Courant number Co = (velocity) × (time step) / (cell size)

For VOF stability: Co < 0.3 (hard constraint)

Given:
  - Max velocity U (from inlet BC in PARAMETERS_AgCl.md)
  - Min cell size Δx (from mesh)
Then:
  Δt = 0.3 × Δx / U  (maximum safe time step)
```

**Verification**:
- Calculate Δt to achieve Co < 0.3
- Set controlDict deltaT to this value
- Solver will monitor Courant number during simulation

## Common prompts this skill handles

- "Set up interFoam case for droplet spreading"
- "Create initial conditions with correct inlet velocity"
- "Configure transportProperties with Carreau model"
- "Implement contact angle boundary condition"
- "Verify Courant number stability"
- "Set VOF discretization to Gauss upwind"
- "Create system/ configuration for VOF"
- "Estimate time step for Courant < 0.3"

## Key files to create/modify

```
0/
├── U (velocity field - inlet BC from parameters)
├── p_rgh (pressure field)
└── alpha.water (phase fraction with contact angle BC)

constant/
├── transportProperties (Carreau, densities, surface tension FROM PARAMETERS_AgCl.md)
└── turbulenceProperties (not typically needed for VOF-only simulations)

system/
├── controlDict (time stepping, output frequency)
├── fvSchemes (discretization: MUST include Gauss upwind for alpha)
├── fvSolution (solver tolerances)
└── decomposeParDict (if parallel—not needed for serial runs)
```

## Critical constraints (source: PARAMETERS_AgCl.md)

**Read these from file, do NOT assume**:
- Carreau model parameters (4 values)
- Densities (ink and air)
- Surface tension value
- Contact angle(s) at walls
- Inlet velocity
- Simulation endTime
- Any wall slip conditions (if not standard no-slip)

**Standard OpenFOAM conventions** (OK if not in PARAMETERS_AgCl.md):
- Pressure reference = 0 Pa
- No-slip walls (unless specified otherwise)
- Zero-gradient outlets

## Validation checklist

✅ All parameters sourced from `documentation/PARAMETERS_AgCl.md` (with citations)
✅ Carreau model complete (all 4 parameters specified)
✅ Contact angle value applied to hydrophobic walls (from file)
✅ Surface tension included in transportProperties (from file)
✅ Discretization scheme: alpha = Gauss upwind (VOF requirement)
✅ Courant number <0.3 achievable with chosen Δt
✅ NO hardcoded numerical values in configuration
✅ All assumptions (wall BC type if not specified) documented with flags

## Output expectations

**Case Configurator agent** uses this skill to:
- Create 0/, constant/, system/ directories
- Populate with physics settings read from PARAMETERS_AgCl.md
- Generate setup report showing parameter sources and validation
- Flag any assumptions with ⚠️ warnings for user review

## Related documentation

- **Parameter source**: `documentation/PARAMETERS_AgCl.md` (single source of truth)
- **OpenFOAM guides**: User Guide - interFoam, VOF method, transportProperties
- **Agent reference**: `.claude/agents/3-case-configurator.md`
- **Validation**: Check agent_state/case_setup_report.md for detailed configuration

---

## 🎯 Golden Rule

> **Read parameters from PARAMETERS_AgCl.md, never assume or hardcode.**
>
> This skill explains HOW to configure, not WHAT the values are.
