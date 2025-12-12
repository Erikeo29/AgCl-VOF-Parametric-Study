#!/usr/bin/env python3
"""
Comprehensive Post-Processor for OpenFOAM VOF Simulation Results
Extracts phase field evolution, mass conservation, spreading metrics, and solver quality
"""

import os
import re
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

class VOFPostProcessor:
    def __init__(self, results_dir):
        self.results_dir = Path(results_dir)
        self.timesteps = []
        self.alpha_data = {}
        self.solver_metrics = {}
        self.mesh_volume = None

    def find_timesteps(self):
        """Find all timestep directories"""
        timestep_dirs = sorted([d for d in self.results_dir.iterdir()
                               if d.is_dir() and d.name.replace('.', '').replace('-', '').isdigit()])
        self.timesteps = [float(d.name) for d in timestep_dirs]
        print(f"Found {len(self.timesteps)} timesteps: {self.timesteps}")
        return self.timesteps

    def read_alpha_field(self, timestep):
        """Read alpha.water field for a given timestep"""
        alpha_file = self.results_dir / str(timestep) / "alpha.water"

        if not alpha_file.exists():
            print(f"WARNING: {alpha_file} not found")
            return None

        with open(alpha_file, 'r') as f:
            lines = f.readlines()

        # Find where data starts (after "internalField nonuniform List<scalar>")
        data_start = None
        num_cells = None

        for i, line in enumerate(lines):
            if 'internalField' in line and 'nonuniform' in line:
                # Next line should have number of cells
                num_cells = int(lines[i+1].strip())
                data_start = i + 3  # Skip "(" line
                break

        if data_start is None:
            print(f"ERROR: Could not find data start in {alpha_file}")
            return None

        # Extract numeric data
        alpha_values = []
        for line in lines[data_start:]:
            line = line.strip()
            if line == ')':
                break
            try:
                alpha_values.append(float(line))
            except ValueError:
                continue

        alpha_array = np.array(alpha_values)

        if len(alpha_array) != num_cells:
            print(f"WARNING: Expected {num_cells} cells, got {len(alpha_array)} values")

        return alpha_array

    def read_cell_volumes(self):
        """Read cell volumes from mesh (for mass conservation)"""
        # Try to read from cellVolumes or calculate from mesh
        vol_file = self.results_dir / "constant" / "polyMesh" / "V"

        if vol_file.exists():
            with open(vol_file, 'r') as f:
                lines = f.readlines()

            # Parse similar to alpha.water
            data_start = None
            for i, line in enumerate(lines):
                if 'internalField' in line:
                    num_cells = int(lines[i+1].strip())
                    data_start = i + 3
                    break

            volumes = []
            for line in lines[data_start:]:
                line = line.strip()
                if line == ')':
                    break
                try:
                    volumes.append(float(line))
                except ValueError:
                    continue

            return np.array(volumes)
        else:
            # Estimate uniform cell volume
            print("WARNING: Cell volumes file not found, using uniform estimate")
            return None

    def analyze_timestep(self, timestep):
        """Complete analysis for a single timestep"""
        alpha = self.read_alpha_field(timestep)

        if alpha is None:
            return None

        analysis = {
            'time': timestep,
            'min_alpha': np.min(alpha),
            'max_alpha': np.max(alpha),
            'mean_alpha': np.mean(alpha),
            'interface_cells': np.sum((alpha > 0.01) & (alpha < 0.99)),
            'ink_cells': np.sum(alpha > 0.5),
            'total_cells': len(alpha),
            'alpha_array': alpha  # Keep for spreading analysis
        }

        return analysis

    def calculate_mass_conservation(self):
        """Calculate mass conservation across simulation"""
        if not self.alpha_data:
            return None

        # Get initial and final timesteps
        times = sorted(self.alpha_data.keys())
        t0 = times[0]
        tf = times[-1]

        # Calculate total ink volume (sum of alpha values)
        # In VOF, alpha represents volume fraction, so sum(alpha) ~ total ink volume
        initial_volume = np.sum(self.alpha_data[t0]['alpha_array'])
        final_volume = np.sum(self.alpha_data[tf]['alpha_array'])

        # Conservation error
        error_abs = final_volume - initial_volume
        error_rel = (error_abs / initial_volume) * 100 if initial_volume > 0 else 0

        return {
            'initial_volume': initial_volume,
            'final_volume': final_volume,
            'absolute_error': error_abs,
            'relative_error_pct': error_rel,
            'status': 'EXCELLENT' if abs(error_rel) < 0.1 else ('ACCEPTABLE' if abs(error_rel) < 0.5 else 'POOR')
        }

    def calculate_spreading_radius(self, alpha, threshold=0.5):
        """Estimate spreading radius from phase field"""
        # Simple metric: count cells with alpha > threshold
        # More sophisticated: calculate center of mass and max extent

        ink_cells = np.sum(alpha > threshold)

        # Assuming roughly spherical/circular spreading
        # Radius ~ sqrt(volume / pi) in 2D or cube_root(volume) in 3D
        # For simplicity, use ink_cells as a proxy for spread area

        return ink_cells

    def analyze_spreading(self):
        """Analyze spreading behavior over time"""
        times = sorted(self.alpha_data.keys())
        spreading_data = []

        for t in times:
            radius_proxy = self.calculate_spreading_radius(self.alpha_data[t]['alpha_array'])
            spreading_data.append({
                'time': t,
                'radius_proxy': radius_proxy,
                'ink_cells': self.alpha_data[t]['ink_cells']
            })

        # Calculate spreading rate
        if len(spreading_data) > 1:
            initial_radius = spreading_data[0]['radius_proxy']
            final_radius = spreading_data[-1]['radius_proxy']
            time_span = spreading_data[-1]['time'] - spreading_data[0]['time']

            spreading_rate = (final_radius - initial_radius) / time_span if time_span > 0 else 0
        else:
            initial_radius = final_radius = spreading_rate = 0

        return {
            'timeseries': spreading_data,
            'initial_radius': initial_radius,
            'final_radius': final_radius,
            'total_spreading': final_radius - initial_radius,
            'spreading_rate': spreading_rate,
            'is_spreading': final_radius > initial_radius
        }

    def parse_solver_log(self):
        """Extract solver quality metrics from run.log"""
        log_file = self.results_dir / "run.log"

        if not log_file.exists():
            print(f"WARNING: run.log not found at {log_file}")
            return None

        with open(log_file, 'r') as f:
            log_content = f.read()

        # Extract Courant numbers
        courant_pattern = r'Courant Number mean: ([\d.e+-]+) max: ([\d.e+-]+)'
        courant_matches = re.findall(courant_pattern, log_content)

        if courant_matches:
            courant_means = [float(m[0]) for m in courant_matches]
            courant_maxs = [float(m[1]) for m in courant_matches]
        else:
            courant_means = courant_maxs = []

        # Extract residuals (p_rgh, alpha.water)
        prgh_pattern = r'Solving for p_rgh.*Final residual = ([\d.e+-]+)'
        alpha_pattern = r'Phase-1 volume fraction = ([\d.e+-]+)'

        prgh_residuals = [float(r) for r in re.findall(prgh_pattern, log_content)]

        # Check for divergence indicators
        divergence_keywords = ['FOAM FATAL', 'floating point exception', 'SIGFPE', 'nan', 'inf']
        divergence_detected = any(keyword in log_content.lower() for keyword in divergence_keywords)

        return {
            'courant_mean': np.mean(courant_means) if courant_means else 0,
            'courant_max': np.max(courant_maxs) if courant_maxs else 0,
            'prgh_residual_mean': np.mean(prgh_residuals) if prgh_residuals else 0,
            'prgh_residual_max': np.max(prgh_residuals) if prgh_residuals else 0,
            'num_timesteps': len(courant_means),
            'divergence_detected': divergence_detected
        }

    def create_phase_snapshots(self, output_file, times_to_plot=None):
        """Create 2D phase field snapshots at key times"""
        if times_to_plot is None:
            # Default: start, middle, end
            times = sorted(self.alpha_data.keys())
            if len(times) >= 3:
                times_to_plot = [times[0], times[len(times)//2], times[-1]]
            else:
                times_to_plot = times

        fig, axes = plt.subplots(1, len(times_to_plot), figsize=(15, 4))

        if len(times_to_plot) == 1:
            axes = [axes]

        for i, t in enumerate(times_to_plot):
            alpha = self.alpha_data[t]['alpha_array']

            # Reshape to approximate 2D grid (assuming mesh is roughly structured)
            # For unstructured mesh, this is a simplified visualization
            # Just show histogram or 1D representation

            ax = axes[i]

            # Create histogram to show phase distribution
            ax.hist(alpha, bins=50, range=(0, 1), color='blue', alpha=0.7, edgecolor='black')
            ax.set_xlabel('Alpha (volume fraction)')
            ax.set_ylabel('Number of cells')
            ax.set_title(f't = {t:.3f} s')
            ax.grid(True, alpha=0.3)
            ax.set_xlim(0, 1)

            # Add statistics text
            stats_text = f'Mean: {self.alpha_data[t]["mean_alpha"]:.4f}\n'
            stats_text += f'Ink cells: {self.alpha_data[t]["ink_cells"]}'
            ax.text(0.98, 0.97, stats_text, transform=ax.transAxes,
                   verticalalignment='top', horizontalalignment='right',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                   fontsize=9)

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Created phase snapshots: {output_file}")
        plt.close()

    def create_spreading_plot(self, output_file, spreading_data):
        """Create spreading radius vs time plot"""
        times = [d['time'] for d in spreading_data['timeseries']]
        radii = [d['radius_proxy'] for d in spreading_data['timeseries']]

        fig, ax = plt.subplots(figsize=(10, 6))

        ax.plot(times, radii, 'o-', linewidth=2, markersize=8, color='darkblue', label='Ink spread (cells)')
        ax.set_xlabel('Time (s)', fontsize=12)
        ax.set_ylabel('Spreading proxy (cells with α > 0.5)', fontsize=12)
        ax.set_title('Droplet Spreading Evolution - Simulation #27', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)

        # Add trend line
        z = np.polyfit(times, radii, 1)
        p = np.poly1d(z)
        ax.plot(times, p(times), '--', color='red', alpha=0.5, label=f'Linear fit (slope={z[0]:.1f} cells/s)')
        ax.legend(fontsize=10)

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Created spreading plot: {output_file}")
        plt.close()

    def generate_report(self, output_file, mass_cons, spreading, solver_metrics):
        """Generate comprehensive markdown report"""

        report = f"""# Post-Processor Analysis - Simulation #27

**Generated**: {Path(output_file).stat().st_mtime if Path(output_file).exists() else 'N/A'}
**Results Directory**: `{self.results_dir}`
**Timesteps Analyzed**: {len(self.alpha_data)}

---

## 1. Phase Field Evolution (Data Table)

| Time (s) | Min(α) | Max(α) | Mean(α) | Interface Cells | Ink Cells (α>0.5) | Total Cells |
|----------|--------|--------|---------|----------------|------------------|-------------|
"""

        for t in sorted(self.alpha_data.keys()):
            data = self.alpha_data[t]
            report += f"| {data['time']:.4f} | {data['min_alpha']:.6f} | {data['max_alpha']:.6f} | {data['mean_alpha']:.6f} | {data['interface_cells']} | {data['ink_cells']} | {data['total_cells']} |\n"

        report += f"""
**Key Observations**:
- Initial mean alpha: {self.alpha_data[sorted(self.alpha_data.keys())[0]]['mean_alpha']:.6f}
- Final mean alpha: {self.alpha_data[sorted(self.alpha_data.keys())[-1]]['mean_alpha']:.6f}
- Interface cells (0.01 < α < 0.99): Average {np.mean([d['interface_cells'] for d in self.alpha_data.values()]):.0f} cells
- Phase field integrity: {'✅ VALID' if all(d['max_alpha'] <= 1.0 and d['min_alpha'] >= 0.0 for d in self.alpha_data.values()) else '❌ INVALID (out of bounds)'}

---

## 2. Mass Conservation Analysis

**Initial State** (t={sorted(self.alpha_data.keys())[0]:.4f} s):
- Total volume (sum of α): {mass_cons['initial_volume']:.4f} (volume units)
- Number of ink cells: {self.alpha_data[sorted(self.alpha_data.keys())[0]]['ink_cells']}

**Final State** (t={sorted(self.alpha_data.keys())[-1]:.4f} s):
- Total volume (sum of α): {mass_cons['final_volume']:.4f} (volume units)
- Number of ink cells: {self.alpha_data[sorted(self.alpha_data.keys())[-1]]['ink_cells']}

**Conservation Error**:
- Absolute error: {mass_cons['absolute_error']:.6f} volume units
- Relative error: {mass_cons['relative_error_pct']:.4f}%
- **Assessment**: {'✅ EXCELLENT' if abs(mass_cons['relative_error_pct']) < 0.1 else ('✅ ACCEPTABLE' if abs(mass_cons['relative_error_pct']) < 0.5 else '⚠️ POOR')} (<0.1% = excellent, <0.5% = acceptable)

**Status**: {mass_cons['status']}

---

## 3. Spreading Detection & Analysis

**Spreading Metrics**:
- Initial spreading proxy: {spreading['initial_radius']} cells
- Final spreading proxy: {spreading['final_radius']} cells
- Total spreading: {spreading['total_spreading']} cells
- Spreading rate: {spreading['spreading_rate']:.2f} cells/s
- Time duration: {sorted(self.alpha_data.keys())[-1] - sorted(self.alpha_data.keys())[0]:.4f} s

**Assessment**: {'✅ SPREADING DETECTED' if spreading['is_spreading'] else '⚠️ NO SPREADING DETECTED'}

**Interpretation**:
"""

        if spreading['is_spreading']:
            report += f"- Droplet is spreading over time (ink cells increased by {spreading['total_spreading']} cells)\n"
            report += f"- Spreading appears {'rapid' if spreading['spreading_rate'] > 100 else 'moderate' if spreading['spreading_rate'] > 10 else 'slow'} (rate: {spreading['spreading_rate']:.1f} cells/s)\n"
        else:
            report += "- ⚠️ No significant spreading detected - droplet may be stationary or retracting\n"
            report += "- Possible causes: Surface tension dominates, contact angle issues, or mesh resolution\n"

        report += f"""
---

## 4. Solver Quality Metrics

**Courant Numbers** (from run.log):
- Mean Courant: {solver_metrics['courant_mean']:.6f}
- Max Courant: {solver_metrics['courant_max']:.6f}
- Status: {'✅ STABLE' if solver_metrics['courant_max'] < 0.3 else '⚠️ HIGH' if solver_metrics['courant_max'] < 1.0 else '❌ UNSTABLE'} (limit: 0.3)

**Pressure Residuals** (p_rgh):
- Mean residual: {solver_metrics['prgh_residual_mean']:.2e}
- Max residual: {solver_metrics['prgh_residual_max']:.2e}
- Status: {'✅ CONVERGED' if solver_metrics['prgh_residual_max'] < 1e-5 else '⚠️ MARGINAL' if solver_metrics['prgh_residual_max'] < 1e-3 else '❌ POOR'}

**Timesteps Completed**: {solver_metrics['num_timesteps']}

**Divergence Check**: {'❌ DIVERGENCE DETECTED' if solver_metrics['divergence_detected'] else '✅ NO DIVERGENCE'}

---

## 5. Visualizations

### Phase Field Distribution Snapshots
![Phase Snapshots](phase_snapshots_sim27.png)

**Description**: Histograms showing distribution of alpha values (volume fraction) at start, middle, and end of simulation. Peaks at α≈0 represent air, peaks at α≈1 represent ink.

### Spreading Evolution
![Spreading Plot](spreading_radius_sim27.png)

**Description**: Number of cells with α > 0.5 (ink cells) over time. Increasing trend indicates spreading behavior.

---

## 6. Data Files Generated

1. **phase_evolution_timeseries.txt** - Raw tabular data (time, alpha stats, spreading metrics)
2. **phase_snapshots_sim27.png** - Phase distribution histograms
3. **spreading_radius_sim27.png** - Spreading evolution plot
4. **POSTPROCESSOR_ANALYSIS_SIM27.md** - This report

---

## 7. Conclusion & Quality Assessment

**Overall Simulation Quality**:
"""

        # Determine overall status
        issues = []
        if mass_cons['relative_error_pct'] > 0.5:
            issues.append("Poor mass conservation")
        if solver_metrics['courant_max'] > 0.3:
            issues.append("High Courant numbers")
        if solver_metrics['divergence_detected']:
            issues.append("Solver divergence detected")
        if not spreading['is_spreading']:
            issues.append("No spreading detected (physics issue?)")

        if len(issues) == 0:
            report += "✅ **EXCELLENT** - All quality checks passed\n\n"
            report += "**Recommendations**:\n"
            report += "- Simulation completed successfully with good mass conservation\n"
            report += "- Spreading behavior captured\n"
            report += "- Results ready for validation against experimental/COMSOL data\n"
        elif len(issues) <= 2:
            report += "⚠️ **ACCEPTABLE WITH CONCERNS** - Minor issues detected\n\n"
            report += "**Issues Found**:\n"
            for issue in issues:
                report += f"- {issue}\n"
            report += "\n**Recommendations**:\n"
            report += "- Review solver settings if Courant numbers are high\n"
            report += "- Check boundary conditions if spreading is unexpected\n"
            report += "- Consider mesh refinement if mass conservation is borderline\n"
        else:
            report += "❌ **POOR QUALITY** - Multiple serious issues\n\n"
            report += "**Issues Found**:\n"
            for issue in issues:
                report += f"- {issue}\n"
            report += "\n**Recommendations**:\n"
            report += "- ⚠️ Results may not be physically accurate\n"
            report += "- Review solver configuration (fvSchemes, fvSolution)\n"
            report += "- Check initial conditions and boundary conditions\n"
            report += "- Consider reducing time step or improving mesh quality\n"

        report += f"""
---

**Analysis completed successfully**
**Next steps**: Validate against COMSOL reference data or experimental measurements
"""

        with open(output_file, 'w') as f:
            f.write(report)

        print(f"Generated comprehensive report: {output_file}")

    def save_timeseries_data(self, output_file, spreading):
        """Save raw timeseries data to text file"""
        with open(output_file, 'w') as f:
            f.write("# Phase Evolution Time Series - Simulation #27\n")
            f.write("# Time(s)\tMin(alpha)\tMax(alpha)\tMean(alpha)\tInterface_Cells\tInk_Cells\tSpreading_Proxy\n")

            for data in spreading['timeseries']:
                t = data['time']
                alpha_stats = self.alpha_data[t]
                f.write(f"{t:.6f}\t{alpha_stats['min_alpha']:.6f}\t{alpha_stats['max_alpha']:.6f}\t")
                f.write(f"{alpha_stats['mean_alpha']:.6f}\t{alpha_stats['interface_cells']}\t")
                f.write(f"{alpha_stats['ink_cells']}\t{data['radius_proxy']}\n")

        print(f"Saved timeseries data: {output_file}")

    def run_complete_analysis(self, validation_dir):
        """Execute complete post-processing workflow"""
        print("\n" + "="*80)
        print("COMPREHENSIVE VOF POST-PROCESSOR - SIMULATION #27")
        print("="*80 + "\n")

        # Step 1: Find all timesteps
        print("Step 1: Finding timesteps...")
        self.find_timesteps()

        # Step 2: Extract phase field data for all timesteps
        print("\nStep 2: Extracting phase field data...")
        for t in self.timesteps:
            print(f"  Processing t={t:.4f} s...", end=' ')
            analysis = self.analyze_timestep(t)
            if analysis:
                self.alpha_data[t] = analysis
                print(f"✅ (mean α={analysis['mean_alpha']:.4f}, ink cells={analysis['ink_cells']})")
            else:
                print("❌ FAILED")

        # Step 3: Calculate mass conservation
        print("\nStep 3: Analyzing mass conservation...")
        mass_cons = self.calculate_mass_conservation()
        if mass_cons:
            print(f"  Initial volume: {mass_cons['initial_volume']:.4f}")
            print(f"  Final volume: {mass_cons['final_volume']:.4f}")
            print(f"  Relative error: {mass_cons['relative_error_pct']:.4f}% ({mass_cons['status']})")

        # Step 4: Analyze spreading
        print("\nStep 4: Analyzing spreading behavior...")
        spreading = self.analyze_spreading()
        print(f"  Initial: {spreading['initial_radius']} cells")
        print(f"  Final: {spreading['final_radius']} cells")
        print(f"  Spreading: {'YES' if spreading['is_spreading'] else 'NO'} (Δ={spreading['total_spreading']} cells)")

        # Step 5: Parse solver log
        print("\nStep 5: Extracting solver metrics from run.log...")
        solver_metrics = self.parse_solver_log()
        if solver_metrics:
            print(f"  Max Courant: {solver_metrics['courant_max']:.6f}")
            print(f"  Timesteps: {solver_metrics['num_timesteps']}")
            print(f"  Divergence: {'DETECTED' if solver_metrics['divergence_detected'] else 'NONE'}")

        # Step 6: Create visualizations
        print("\nStep 6: Creating visualizations...")
        validation_path = Path(validation_dir)
        validation_path.mkdir(parents=True, exist_ok=True)

        snapshots_file = validation_path / "phase_snapshots_sim27.png"
        self.create_phase_snapshots(snapshots_file)

        spreading_file = validation_path / "spreading_radius_sim27.png"
        self.create_spreading_plot(spreading_file, spreading)

        # Step 7: Save timeseries data
        print("\nStep 7: Saving timeseries data...")
        timeseries_file = validation_path / "phase_evolution_timeseries.txt"
        self.save_timeseries_data(timeseries_file, spreading)

        # Step 8: Generate report
        print("\nStep 8: Generating comprehensive report...")
        report_file = validation_path / "POSTPROCESSOR_ANALYSIS_SIM27.md"
        self.generate_report(report_file, mass_cons, spreading, solver_metrics)

        print("\n" + "="*80)
        print("ANALYSIS COMPLETE")
        print("="*80)
        print(f"\nOutput files created in: {validation_path}")
        print(f"  1. {timeseries_file.name}")
        print(f"  2. {snapshots_file.name}")
        print(f"  3. {spreading_file.name}")
        print(f"  4. {report_file.name}")
        print("\n")

        return {
            'mass_conservation': mass_cons,
            'spreading': spreading,
            'solver_metrics': solver_metrics,
            'output_files': [timeseries_file, snapshots_file, spreading_file, report_file]
        }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 comprehensive_postprocessor.py <results_directory>")
        print("Example: python3 comprehensive_postprocessor.py results/27/")
        sys.exit(1)

    results_dir = sys.argv[1]
    validation_dir = "validation"

    processor = VOFPostProcessor(results_dir)
    results = processor.run_complete_analysis(validation_dir)

    print("Post-processing completed successfully!")
