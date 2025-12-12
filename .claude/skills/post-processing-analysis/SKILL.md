---
name: post-processing-analysis
description: Extract and visualize phase field evolution, spreading metrics, and validation data from OpenFOAM interFoam VOF simulations
version: "1.0.0"
---

# Post-Processing Analysis Skill

## When to use this skill

Invoke when:
- Extracting results from completed interFoam simulation
- Visualizing phase field (ink vs air) evolution over entire simulation
- Measuring droplet spreading radius, contact angle, interface location
- Computing mass conservation error
- Preparing validation data for comparison against specifications
- Analyzing VOF interface quality and numerical diffusion

## ⚠️ CRITICAL: Parameter Philosophy

**NEVER hardcode specification values (mass tolerance, contact angle, etc.) in this skill.**

All validation thresholds and expected values are defined in:
- **Single source of truth**: `documentation/PARAMETERS_AgCl.md`
- Read from file for comparison, do NOT assume values

This skill explains **HOW** to extract and visualize data, not **WHAT** the success criteria are.

## Key responsibilities

### 1. Phase Field Extraction (PRIMARY)

**What to extract**: Alpha field (phase fraction) from every timestep

**Procedure**:
- List all time-step directories: `0/`, `0.001/`, `0.002/`, ... (final/)
- For each timestep:
  - Read `alpha.water` field (VOF phase fraction)
  - Store spatial distribution (grid + alpha values)
  - Record timestep time value
- Preserve complete time evolution (0 to final)

**Output format**:
- Raw data: `validation/phase_data_timeseries.txt` (tabular or structured)
- Accessible for visualization and analysis

### 2. Phase Field Visualization

**Visual outputs** (user's primary interest):
- **Snapshots**: Phase field at t=0, t=mid, t=final
  - Files: `validation/phase_field_t0.png`, `phase_field_tmid.png`, `phase_field_tfinal.png`
  - Show: Ink (α=1) vs Air (α=0) distribution
  - Labels: Time stamp, axis labels, color bar
- **Time evolution plot**: Complete progression from start to end
  - File: `validation/phase_evolution_timeseries.png`
  - Show: How phase field changes over entire simulation
  - Format: Time series plot showing spreading progression

**Color scheme**:
- Clear distinction between ink (α≈1) and air (α≈0)
- Interface region (0<α<1) shown distinctly
- Easy to see spreading pattern visually

### 3. Secondary Metrics (Derived from Phase)

**Mass conservation** (from alpha integration):
- **Calculation**: Integrate alpha field over entire domain at each timestep
  - Initial: V₀ = ∫∫∫ α(t=0) dV
  - Final: Vf = ∫∫∫ α(t=final) dV
  - Error = (Vf - V₀) / V₀ (in %)
- **Interpretation**: <0.1% = excellent, 0.1-0.5% = acceptable
- **Source**: Read acceptable threshold from PARAMETERS_AgCl.md → Critical Validation Criteria

**Spreading radius** (from interface location):
- **Calculation**: Find alpha=0.5 contour (interface)
- **Measurement**: Distance from axis (axisymmetric) or furthest ink location
- **Time series**: Radius vs time for entire simulation
- **Comparison**: Later compared with PARAMETERS_AgCl.md specifications

**Contact angle** (from phase gradient at wall):
- **Calculation**: Extract alpha gradient at substrate/wall
  - Method: ∂α/∂n (normal derivative at contact line)
  - Convert to angle: θ = arctan(slope)
- **Time series**: Track how contact angle evolves
- **Later compared**: Against value specified in PARAMETERS_AgCl.md → Boundary Conditions

**Solver metrics** (from simulation log):
- **Courant number**: Max and min values achieved
- **Continuity errors**: Max and min per timestep
- **Solver convergence**: Any warnings or divergence

### 4. Report Generation

**Output file**: `validation/results_phase_evolution.md`

**Structure**:
1. **AGENT SIGNATURE** (mandatory): Agent name, date, status
2. **Phase field visualization** (PRIMARY): Snapshots + time evolution plots
3. **Phase data tables**: Time-series numerical data
4. **Secondary metrics**: Mass, spreading radius, contact angle, solver performance
5. **Raw data links**: References to data files for further analysis

## Workflow procedures

### Data extraction sequence

1. **Verify simulation complete**:
   - Check if final time-step directory exists
   - Confirm alpha.water fields present in all timesteps

2. **Extract phase field from all timesteps**:
   - FOR each time directory (in chronological order):
     - Read alpha.water scalar field
     - Extract spatial data (node coordinates, alpha values)
     - Record timestep number and time value

3. **Integrate alpha for mass conservation**:
   - Initial volume: V₀ = sum(alpha × cell_volume) at t=0
   - Final volume: Vf = sum(alpha × cell_volume) at t=final
   - Error = |Vf - V₀| / V₀ × 100%

4. **Find interface location**:
   - Identify alpha=0.5 contour (interface between ink and air)
   - For each timestep:
     - Locate interface position
     - Measure radius (distance from axis if axisymmetric)

5. **Extract contact angle at wall**:
   - For each timestep:
     - Find alpha field at wall patch (substrate)
     - Calculate gradient ∂α/∂normal
     - Convert to contact angle in degrees

6. **Extract solver metrics** from simulation.log:
   - Max/min Courant number across all steps
   - Max/min continuity error across all steps
   - Any solver warnings or divergence indicators

7. **Generate visualizations**:
   - Create snapshot plots: t=0, t=mid, t=final
   - Create time-series evolution plot
   - Create data table with all time steps

8. **Generate report**:
   - Compile all visualizations and data
   - Write to validation/results_phase_evolution.md
   - Include agent signature header
   - Cite data sources (which timesteps, calculation methods)

## Common prompts this skill handles

- "Extract phase field evolution from simulation results"
- "Visualize how ink spreads over time"
- "Create phase field snapshots at key times"
- "Calculate mass conservation error"
- "Measure spreading radius from alpha field"
- "Extract contact angle dynamics"
- "Generate time-series plot of phase evolution"
- "Prepare validation data for comparison with COMSOL"

## Key data sources

**Input** (from completed Solver Executor):
- All time-step directories: `0/`, `0.001/`, `0.002/`, ... (final time)
- Each contains: `alpha.water`, `U`, `p_rgh`, etc.
- Solver log: `agent_state/simulation.log` (for residuals, Courant, etc.)

**Output**:
- `validation/phase_field_t0.png` (initial phase snapshot)
- `validation/phase_field_tmid.png` (mid-simulation snapshot)
- `validation/phase_field_tfinal.png` (final phase snapshot)
- `validation/phase_evolution_timeseries.png` (complete time evolution)
- `validation/phase_data_timeseries.txt` (numerical data for all timesteps)
- `validation/results_phase_evolution.md` (comprehensive report with visualizations)

## Validation checklist

✅ Alpha field extracted from **ALL timesteps** (complete time evolution)
✅ Phase field visualized clearly (ink vs air distinction obvious)
✅ Time-series showing progression from t=0 to t=final
✅ Mass conservation error calculated (with interpretation)
✅ Spreading radius tracked over time
✅ Contact angle extracted and documented
✅ Solver performance metrics included
✅ All data sources cited in report
✅ AGENT SIGNATURE included in output
✅ Report ready for Validator to compare against PARAMETERS_AgCl.md

## Output expectations

**Post-Processor agent** uses this skill to:
- Extract phase field from all simulation timesteps
- Create visual snapshots and time-series plots
- Calculate mass conservation, spreading radius, contact angle
- Generate comprehensive results report with visualizations
- Output: `validation/results_phase_evolution.md` with embedded plots and data

**Next agent (Validator)** uses output to:
- Compare measured values against specifications in PARAMETERS_AgCl.md
- Assess phase field quality (sharpness, no spurious currents)
- Generate final PASS/FAIL validation report

## Related documentation

- **Specifications**: `documentation/PARAMETERS_AgCl.md` (used by Validator for comparison)
- **OpenFOAM**: Post-processing guides, VOF field output formats
- **Agent reference**: `.claude/agents/5-post-processor.md`, `.claude/agents/6-validator.md`
- **Solver output**: Time-step directories from `.claude/agents/4-solver-executor.md`

---

## 🎯 Golden Rule

> **Extract ALL timesteps, visualize phase evolution clearly, calculate metrics, but defer success criteria to PARAMETERS_AgCl.md.**
>
> This skill explains HOW to extract and visualize, not WHAT the limits are.
