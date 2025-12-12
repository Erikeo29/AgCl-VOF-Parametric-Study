#!/usr/bin/env python3
"""
Generate alpha.water field for FULL 2D GEOMETRY with nozzle (buse).

GEOMETRY 2D COMPLETE (no symmetry):
- Domain: x: -0.8→0.8mm (mirrored)
- Puit: x: -0.4→0.4mm, y: 0→0.128mm (4 blocs)
- Air gap: y: 0.128→0.158mm (6 blocs)
- Air haut: y: 0.158→0.278mm (4 blocs)
- Buse: x: -0.15→0.15mm, y: 0.158→0.558mm (2 blocs)

Initial condition:
- Buse (cellZone "buse"): alpha = 1 (encre) - PRÉ-REMPLIE
- Tout le reste: alpha = 0 (air)

IMPORTANT: L'inlet injecte de l'AIR (alpha=0) pour POUSSER l'encre vers le bas!
"""

import sys
from pathlib import Path

def read_cell_zone_labels(case_dir, zone_name):
    """Read cell labels for a specific zone from cellZones file."""
    cellzones_file = Path(case_dir) / "constant" / "polyMesh" / "cellZones"

    with open(cellzones_file, 'r') as f:
        content = f.read()

    # Find the zone
    zone_start = content.find(f"\n{zone_name}\n")
    if zone_start < 0:
        return []

    # Find cellLabels List
    labels_start = content.find("cellLabels", zone_start)
    if labels_start < 0:
        return []

    # Find the count (number after List<label>)
    count_start = content.find("\n", labels_start) + 1
    count_end = content.find("\n", count_start)
    count = int(content[count_start:count_end].strip())

    # Find opening parenthesis
    paren_start = content.find("(", count_end) + 1
    paren_end = content.find(")", paren_start)

    # Extract cell labels
    labels_text = content[paren_start:paren_end]
    labels = [int(x) for x in labels_text.split()]

    return labels

def get_num_cells(case_dir):
    """Get number of cells from owner file"""
    owner_file = Path(case_dir) / "constant" / "polyMesh" / "owner"

    with open(owner_file, 'r') as f:
        content = f.read()

    # Find the number after FoamFile block
    lines = content.split('\n')
    foam_end = -1
    for i, line in enumerate(lines):
        if line.strip() == '}':
            foam_end = i
            break

    # Find first number after }
    for i in range(foam_end + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped and stripped.isdigit():
            return int(stripped)

    raise ValueError("Could not find number of faces in owner file")

def generate_alpha_field(case_dir, output_file):
    """Generate alpha.water field file with buse filled with ink"""

    mesh_dir = Path(case_dir) / "constant" / "polyMesh"

    print("Reading mesh info...")

    # Get number of cells from owner file
    owner_file = mesh_dir / "owner"
    with open(owner_file, 'r') as f:
        content = f.read()
    lines = content.split('\n')
    foam_end = -1
    for i, line in enumerate(lines):
        if line.strip() == '}':
            foam_end = i
            break

    # Read all owner values to find max cell index
    max_owner = -1
    in_data = False
    for i in range(foam_end + 1, len(lines)):
        stripped = lines[i].strip()
        if not stripped:
            continue
        if stripped == '(':
            in_data = True
            continue
        if stripped == ')':
            break
        if in_data:
            try:
                val = int(stripped)
                if val > max_owner:
                    max_owner = val
            except ValueError:
                continue
        elif stripped.isdigit():
            continue  # This is the count line

    num_cells = max_owner + 1
    print(f"   Found {num_cells} cells")

    # Read buse zone cell labels
    print("Reading buse cell zone...")
    buse_cells = read_cell_zone_labels(case_dir, "buse")
    print(f"   Found {len(buse_cells)} cells in buse zone")

    # Create alpha field: 0 everywhere, 1 in buse
    print("Setting initial conditions...")
    print(f"   Buse cells: alpha = 1 (ink) - PRE-REMPLIE")
    print(f"   All other cells: alpha = 0 (air)")
    print(f"   Inlet BC: alpha = 0 (AIR qui pousse l'encre)")

    buse_set = set(buse_cells)

    # Write OpenFOAM field file
    print(f"Writing {output_file}...")

    header = """/*--------------------------------*- C++ -*----------------------------------*\\
  =========                 |
  \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\\\    /   O peration     | Website:  https://openfoam.org
    \\\\  /    A nd           | Version:  13
     \\\\/     M anipulation  |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    format      ascii;
    class       volScalarField;
    location    "0";
    object      alpha.water;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

// GEOMETRIE 2D COMPLETE (sans symetrie)
// Pour permettre des angles de contact differents gauche/droite
//
// Condition initiale:
//   - Buse (cellZone "buse"): alpha = 1 (encre) - PRE-REMPLIE
//   - Puit + Air: alpha = 0 (air)
//
// IMPORTANT: L'inlet injecte de l'AIR (alpha=0) pour pousser l'encre!
//
// Angles de contact:
//   - substrate (or): 35 deg - hydrophile
//   - wall_isolant_left/right: 90 deg - neutre
//   - top_isolant_left/right: 60 deg - legerement hydrophile
//   - wall_buse_left/right: 90 deg - neutre

dimensions      [];

"""

    with open(output_file, 'w') as f:
        f.write(header)

        # Write internal field with non-uniform values
        f.write(f"internalField   nonuniform List<scalar>\n{num_cells}\n(\n")

        for cell_id in range(num_cells):
            if cell_id in buse_set:
                f.write("1\n")
            else:
                f.write("0\n")

        f.write(")\n;\n\n")

        # Boundary field - GEOMETRY 2D COMPLETE avec patches gauche/droite separes
        f.write("""boundaryField
{
    // === Faces 2D (empty) ===
    front
    {
        type            empty;
    }

    back
    {
        type            empty;
    }

    // === Substrat (fond du puit) - Or, hydrophile 35 deg ===
    substrate
    {
        type            contactAngle;
        theta0          35;
        limit           gradient;
        value           uniform 0;
    }

    // === Paroi verticale de l'isolant GAUCHE - hydrophile 15 deg ===
    wall_isolant_left
    {
        type            contactAngle;
        theta0          15;
        limit           gradient;
        value           uniform 0;
    }

    // === Paroi verticale de l'isolant DROITE - hydrophobe 160 deg ===
    wall_isolant_right
    {
        type            contactAngle;
        theta0          160;
        limit           gradient;
        value           uniform 0;
    }

    // === Surface horizontale de l'isolant GAUCHE - hydrophile 15 deg ===
    top_isolant_left
    {
        type            contactAngle;
        theta0          15;
        limit           gradient;
        value           uniform 0;
    }

    // === Surface horizontale de l'isolant DROITE - hydrophobe 160 deg ===
    top_isolant_right
    {
        type            contactAngle;
        theta0          160;
        limit           gradient;
        value           uniform 0;
    }

    // === Paroi INTERIEURE de la buse GAUCHE - neutre 90 deg ===
    wall_buse_left_int
    {
        type            contactAngle;
        theta0          90;
        limit           gradient;
        value           uniform 1;
    }

    // === Paroi EXTERIEURE de la buse GAUCHE - hydrophobe 180 deg ===
    wall_buse_left_ext
    {
        type            contactAngle;
        theta0          180;
        limit           gradient;
        value           uniform 0;
    }

    // === Paroi INTERIEURE de la buse DROITE - neutre 90 deg ===
    wall_buse_right_int
    {
        type            contactAngle;
        theta0          90;
        limit           gradient;
        value           uniform 1;
    }

    // === Paroi EXTERIEURE de la buse DROITE - hydrophobe 180 deg ===
    wall_buse_right_ext
    {
        type            contactAngle;
        theta0          180;
        limit           gradient;
        value           uniform 0;
    }

    // === Inlet (haut de la buse) - AIR qui pousse l'encre ===
    inlet
    {
        type            fixedValue;
        value           uniform 0;  // AIR (pas encre!) pour pousser l'encre vers le bas
    }

    // === Atmosphere (sortie air) ===
    atmosphere
    {
        type            inletOutlet;
        inletValue      uniform 0;  // Air pur si reflux
        value           uniform 0;
    }

    // === Outlet lateral GAUCHE ===
    outlet_left
    {
        type            inletOutlet;
        inletValue      uniform 0;
        value           uniform 0;
    }

    // === Outlet lateral DROITE ===
    outlet_right
    {
        type            inletOutlet;
        inletValue      uniform 0;
        value           uniform 0;
    }
}

// ************************************************************************* //
""")

    print(f"Generated: {output_file}")
    print(f"   Total cells: {num_cells}")
    print(f"   Buse cells (alpha=1): {len(buse_cells)}")
    print(f"   Air/Puit cells (alpha=0): {num_cells - len(buse_cells)}")

    # Calculate and print phase fraction
    phase_fraction = len(buse_cells) / num_cells * 100
    print(f"   Initial phase fraction: {phase_fraction:.2f}%")
    print("")
    print("RAPPEL: L'inlet injecte de l'AIR pour pousser l'encre pre-remplie!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: generate_alpha_field.py <case_directory> [output_file]")
        print("Example: python3 scripts/generate_alpha_field.py . 0/alpha.water")
        sys.exit(1)

    case_dir = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "0/alpha.water"

    generate_alpha_field(case_dir, output_file)
