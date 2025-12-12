# scripts/ - Automation & Analysis Scripts

**Location**: `/scripts/` directory in v3_ref project

This directory contains all executable scripts for simulation automation and post-processing analysis.

---

## 📋 Script Organization

### Bash Scripts (Simulation Automation)
- `run_simulation.sh` - **Main wrapper** to launch interFoam simulations
  - Creates sequential `results/N/` directories
  - Copies case files from root templates
  - Captures logs to `results/N/run.log`
  - Also available at ROOT as convenience: `../run_simulation.sh`

- `setup_case.sh` (future) - Initial case setup from geometry
- `postprocess.sh` (future) - Run post-processing pipeline
- `validate.sh` (future) - Mesh & case validation checks

### Python Scripts (Analysis & Utilities)

#### `post_processor.py`
**Purpose**: Extract VOF phase field data from OpenFOAM results
- Input: `results/N/0.XXXX/alpha.water`
- Output: Phase evolution plots & metrics (to `validation/`)
- Creates: `phase_field_t0.png`, `phase_evolution_timeseries.png`, `phase_data_timeseries.txt`

#### `mesh_analyzer.py`
**Purpose**: Analyze mesh quality from OpenFOAM checkMesh output
- Input: `constant/polyMesh/`
- Output: Mesh metrics & quality assessment
- Parses: Non-orthogonality, skewness, aspect ratio

#### `field_extractor.py`
**Purpose**: Extract physics metrics from simulation fields
- Input: `results/N/0.XXXX/` (U, p_rgh, alpha.water, etc.)
- Output: Velocity profiles, pressure distribution, contact angle
- Metrics: Max velocity, pressure gradients, spreading radius

#### `visualizer.py`
**Purpose**: Create publication-quality phase field visualizations
- Input: `results/N/0.XXXX/alpha.water`
- Output: Phase distribution plots at t=0, t=mid, t=final
- Features: Color maps, boundary annotations, time evolution

#### `comsol_comparator.py`
**Purpose**: Validate OpenFOAM results against COMSOL reference
- Input: OpenFOAM results + COMSOL reference data
- Output: Validation report (to `validation/report.md`)
- Metrics: Spreading radius comparison, max velocity diff, error analysis

### Python Dependencies
**File**: `requirements.txt`
```
numpy>=1.20
matplotlib>=3.3
scipy>=1.7
h5py>=3.0
paraview-python  # Optional: for advanced visualization
```

Install with:
```bash
pip3 install -r scripts/requirements.txt
```

---

## 🚀 Quick Start

### Run a simulation
```bash
./run_simulation.sh
# Creates results/1/, results/2/, etc. automatically
```

### Post-process results (after simulation)
```bash
# Extract phase field data
python3 scripts/post_processor.py results/1/

# Analyze mesh quality
python3 scripts/mesh_analyzer.py constant/polyMesh/

# Extract physics metrics
python3 scripts/field_extractor.py results/1/

# Create visualizations
python3 scripts/visualizer.py results/1/

# Compare against COMSOL
python3 scripts/comsol_comparator.py results/1/ --reference path/to/comsol_data.csv
```

### Full workflow
```bash
# 1. Run simulation
./run_simulation.sh

# 2. Wait for completion (monitor with: tail -f results/1/run.log)

# 3. Post-process all at once
python3 scripts/post_processor.py results/1/
python3 scripts/visualizer.py results/1/
python3 scripts/comsol_comparator.py results/1/

# 4. Check results
ls -la validation/  # See generated reports & plots
```

---

## 🔧 Development Notes

### Python Style
- Follow PEP 8 style guide
- Use type hints for function parameters
- Include docstrings for all functions
- Example:
  ```python
  def extract_phase_field(results_dir: str, output_dir: str) -> dict:
      """Extract phase field evolution from OpenFOAM results.

      Args:
          results_dir: Path to results/N/ directory
          output_dir: Where to save extracted data

      Returns:
          Dictionary with phase metrics (time, radius, volume, etc.)
      """
  ```

### OpenFOAM Data Access
- Use `OF_CASE` environment variable or command-line argument
- Parse binary OpenFOAM files with `h5py` or `numpy`
- Alternative: Use `foamListBoundary`, `foamDictionary` commands
- Example:
  ```python
  import os
  results_dir = "results/1/"
  timestep_dir = os.path.join(results_dir, "0.0001")
  alpha_file = os.path.join(timestep_dir, "alpha.water")
  ```

### Output Organization
- All generated files go to `validation/` directory
- Naming convention: `{script}_{description}_{YYYY-MM-DD}.{ext}`
  - `post_processor_phase_evolution_2025-11-22.md`
  - `visualizer_phase_field_2025-11-22.png`
  - `comsol_comparator_report_2025-11-22.md`

### Testing
- Test scripts on `results/1/` after first simulation
- Keep test data small (use coarse mesh for development)
- Log all operations to `logs/` directory

---

## 📁 File Structure After Full Workflow

```
scripts/
├── run_simulation.sh ................ Executable
├── post_processor.py ............... Executable
├── mesh_analyzer.py ................ Executable
├── field_extractor.py .............. Executable
├── visualizer.py ................... Executable
├── comsol_comparator.py ............ Executable
├── requirements.txt ................ Python dependencies
└── README.md ........................ This file

Outputs:
├── logs/
│   ├── agent_execution_*.log ....... Script execution logs
│   └── *.md ........................ Analysis reports
│
└── validation/
    ├── phase_field_*.png ........... Phase field plots
    ├── phase_data_*.txt ............ Raw phase data
    ├── results_phase_evolution_*.md  Analysis reports
    └── report.md ................... Final validation report
```

---

## 🔐 Permissions

All scripts should be executable:
```bash
chmod +x scripts/*.sh
```

Python scripts can be run directly or via `python3 scripts/name.py`.

---

## 📚 Related Documentation

- **CLAUDE.md** - Project overview & OpenFOAM case structure
- **PARAMETERS_AgCl.md** - Physics parameters & boundary conditions
- **TRACKING_COMPLETE.md** - File organization reference
- **COMSOL reference** - `documentation/Rapport_Complet_Physique_COMSOL.md`

---

**Last updated**: 2025-11-22
**Status**: Framework ready, scripts to be implemented
**Next**: Create individual script templates based on this spec

