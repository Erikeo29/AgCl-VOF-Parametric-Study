---
name: openfoam-mesh-expert
description: Guide mesh generation and quality validation for OpenFOAM CFD simulations using gmsh and checkMesh, with focus on VOF multiphase and contact angle boundaries
version: "1.0.0"
---

# OpenFOAM Mesh Expert Skill

## When to use this skill

Invoke when:
- Converting NASTRAN (NAS) mesh files to OpenFOAM polyMesh format
- Comparing multiple mesh variants (coarse vs fine refinement)
- Checking mesh quality against project specifications
- Diagnosing mesh-related convergence issues
- Evaluating mesh resolution for multiphase flow (VOF) with contact angles
- Planning mesh refinement strategy for droplet spreading simulation

## ⚠️ CRITICAL: Parameter Philosophy

**NEVER hardcode geometry or quality threshold values in this skill.**

All geometry dimensions and mesh quality thresholds are defined in:
- **Single source of truth**: `documentation/PARAMETERS_AgCl.md`
- Read from file to validate mesh against actual project specs

This skill explains **HOW** to evaluate meshes, not **WHAT** the limits are.

## Key quality thresholds (source: PARAMETERS_AgCl.md)

**Read from file** → Critical Validation Criteria section:
- Max non-orthogonality: [value from file]
- Max skewness: [value from file]
- Aspect ratio limits: [value from file]
- No negative volumes: MANDATORY (always true)

**Other constraints** (from PARAMETERS_AgCl.md → Geometry):
- Well diameter: [read from file]
- Domain height: [read from file]
- Other geometric bounds: [read from file]

**Mesh requirements** (from PARAMETERS_AgCl.md → Interface Properties):
- Interface resolution: [read from file - typically "3-5 cells across droplet diameter"]
- Y+ at walls: [read from file - typically "<1 for wall-resolved VOF"]

**Axisymmetric specifics** (from PARAMETERS_AgCl.md → Geometry):
- Wedge angle (if 2D axisymmetric): [read from file - typically 5°]

## Workflow procedures

### NAS to OpenFOAM conversion sequence

1. **Validate NAS file structure**:
   - Location: `01_Data_Comsol/01_Geometry_Mesh/`
   - Check file is readable (text format NASTRAN)
   - Extract: node count, element count, element types

2. **Assess all available variants**:
   - Find all `mesh_nozzle_*.nas` files
   - For each file:
     - Count GRID cards (nodes)
     - Count element cards (CQUAD4, CTRIA3, CPENTA6, CHEXA8, etc.)
     - Estimate OpenFOAM cell count (typically 1.5-3× NAS element count)
   - **Rank by element count, NOT by filename** (no assumptions about numbering)

3. **Recommend conversion order**:
   - Coarsest variant first (fastest test, smallest cell count)
   - Fallback order: progressively finer meshes
   - Justification: Verified by actual element counts

4. **Convert NAS → gmsh format**:
   - Input: NASTRAN file from 01_Data_Comsol/01_Geometry_Mesh/
   - Tool: gmsh or Python script for NAS parsing
   - Output: `constant/polyMesh/mesh.msh` (v2.2 format required)
   - Command: `gmshToFoam constant/polyMesh/mesh.msh`

5. **Generate OpenFOAM polyMesh**:
   - Result: `constant/polyMesh/` directory containing:
     - points, faces, cells, boundary
   - Verify: All files present and non-empty

6. **Validate mesh quality**:
   - Run: `checkMesh -verbose`
   - Extract metrics:
     - Max non-orthogonality: Compare vs threshold from PARAMETERS_AgCl.md
     - Max skewness: Compare vs threshold from PARAMETERS_AgCl.md
     - Any negative volumes: Must be ZERO
     - Any boundary issues: Report if found
   - Decision: PASS (all thresholds met) / FAIL (any threshold exceeded) / PARTIAL

7. **Decision logic**:
   - **PASS**: Proceed to Case Configurator
   - **FAIL on first variant**: Try next fallback mesh (Step 4 with different .nas file)
   - **FAIL on all variants**: Invoke Hunter agent for NAS format or conversion issues

### Quality issue diagnosis

**IF max non-orthogonality exceeds threshold from PARAMETERS_AgCl.md**:
- Run checkMesh to identify problem location
- Likely issues: Sharp corners (nozzle inlet) or contact region
- Solutions: Try next mesh variant OR request mesh refinement

**IF max skewness exceeds threshold**:
- Indicates highly distorted elements
- Solutions: Try next mesh variant OR request COMSOL mesh regeneration

**IF negative volumes detected**:
- **CRITICAL**: Mesh is invalid, do NOT use
- Cause: NAS file corruption or format incompatibility
- Action: Try different mesh variant or request COMSOL re-export

**IF conversion tool error** (gmshToFoam fails):
- Check gmsh version (must be compatible)
- Check file path (spaces can cause issues)
- Try next mesh variant

### Microfluidics-specific considerations

**Contact angle boundaries** (from PARAMETERS_AgCl.md → Boundary Conditions):
- Require fine resolution at wall
- Read target spacing from PARAMETERS_AgCl.md (if specified)
- Typical: cells <1 mm at contact line

**Y+ (wall distance scaling)** (from PARAMETERS_AgCl.md → Interface Properties or Mesh requirements):
- Read specification from file
- Typical for VOF: Y+ < 1 (wall-resolved)
- Verify: Mesh spacing at walls satisfies this

**Interface capturing** (from PARAMETERS_AgCl.md → Interface Properties):
- Read required cell count across droplet
- Typical: 3-5 cells across nozzle or initial droplet diameter
- Verify: Mesh is fine enough to capture interface

**Gradual grading** (from PARAMETERS_AgCl.md → Mesh requirements if specified):
- Avoid sudden cell size jumps
- Typical: Growth ratio <1.2 from fine to coarse regions
- Inspect if checkMesh reports aspect ratio issues

**Surface tension criterion** (from PARAMETERS_AgCl.md → Interface Properties or Geometry):
- Read required resolution from file
- May specify: dx/3 < σ/ΔP (surface tension vs pressure effects)
- Mesh must be fine enough to resolve capillary forces

## Common prompts this skill handles

- "Compare all 4 mesh variants (mesh_nozzle_1 through 4)"
- "Which mesh is coarsest? Which is finest?"
- "Check mesh quality against PARAMETERS_AgCl.md"
- "Validate polyMesh generation from NAS file"
- "Why is mesh quality failing checkMesh?"
- "Estimate cell count for interFoam simulation"
- "Is mesh fine enough for VOF interface capturing?"
- "Diagnose NAS conversion issues"

## Key commands

```bash
# List all available NAS files
ls -lh 01_Data_Comsol/01_Geometry_Mesh/mesh_nozzle_*.nas

# Inspect NAS file structure
head -100 01_Data_Comsol/01_Geometry_Mesh/mesh_nozzle_1.nas

# Count nodes (GRID cards)
grep "^GRID" 01_Data_Comsol/01_Geometry_Mesh/mesh_nozzle_1.nas | wc -l

# Count elements
grep "^CQUAD4\|^CTRIA3\|^CPENTA6\|^CHEXA8" 01_Data_Comsol/01_Geometry_Mesh/mesh_nozzle_1.nas | wc -l

# Convert NAS to gmsh (command depends on gmsh support)
gmsh 01_Data_Comsol/01_Geometry_Mesh/mesh_nozzle_1.nas -o constant/polyMesh/mesh.msh

# Convert gmsh to OpenFOAM polyMesh
gmshToFoam constant/polyMesh/mesh.msh

# Validate mesh quality
checkMesh -verbose > agent_state/mesh_quality.log 2>&1
```

## Output expectations

**Mesh Validator agent** uses this skill to:
- Rank all available NAS variants by element count (no assumptions)
- Recommend starting variant (usually coarsest for fastest first test)
- Document fallback order for if conversion/quality fails
- Output: `agent_state/mesh_validation.md` with comparison table

**Mesh Generator agent** uses this skill to:
- Execute conversion (NAS → gmsh → polyMesh) for approved variant
- Run checkMesh and extract quality metrics
- Compare against thresholds from PARAMETERS_AgCl.md
- Output: `agent_state/mesh_generator_report.md` with PASS/FAIL decision

## Validation checklist

✅ All mesh variants assessed (actual element counts, not assumed order)
✅ Quality thresholds compared against PARAMETERS_AgCl.md (with sources cited)
✅ Geometry bounds validated against PARAMETERS_AgCl.md dimensions
✅ Recommended variant justified by measured refinement level
✅ Fallback mesh order prepared
✅ All assumptions documented

## Related documentation

- **Geometry/quality specs**: `documentation/PARAMETERS_AgCl.md`
- **OpenFOAM docs**: User Guide - Mesh section, checkMesh reference
- **gmsh docs**: NASTRAN format support, mesh quality
- **Agent reference**: `.claude/agents/1-mesh-validator.md`, `.claude/agents/2-mesh-generator.md`

---

## 🎯 Golden Rule

> **Compare meshes by actual metrics (element count), read all thresholds from PARAMETERS_AgCl.md.**
>
> This skill explains HOW to evaluate, not WHAT the limits are.
