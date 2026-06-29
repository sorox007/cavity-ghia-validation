#!/usr/bin/env python3
"""
Compare OpenFOAM cavity results with Ghia et al. (1982) benchmark data.
Extracts u-velocity along vertical centerline and v-velocity along horizontal centerline.

Usage:
    python3 compare_ghia.py [--case /path/to/cavity]

If --case is not provided, assumes the script is run from the case directory.
"""

import re
import os
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')  # non-interactive backend — saves PNG without display
import matplotlib.pyplot as plt


# ============================================================================
# Ghia et al. (1982) Re=1000 benchmark data
# Source: Table I & II, J. Comp. Physics, 48(3), 387-411
# ============================================================================

# u-velocity along vertical centerline (x = 0.5)
GHIA_Y = np.array([1.0000, 0.9766, 0.9688, 0.9609, 0.9531, 0.8516, 0.7344,
                    0.6172, 0.5000, 0.4531, 0.2813, 0.1719, 0.1016, 0.0703,
                    0.0625, 0.0547, 0.0000])

GHIA_U = np.array([1.00000, 0.65928, 0.57492, 0.51117, 0.46604, 0.33304, 0.18719,
                    0.05702, -0.06080, -0.10648, -0.27805, -0.38289, -0.29730,
                    -0.22220, -0.20196, -0.18109, 0.00000])

# v-velocity along horizontal centerline (y = 0.5)
GHIA_X = np.array([1.0000, 0.9688, 0.9609, 0.9531, 0.9453, 0.9063, 0.8594,
                    0.8047, 0.5000, 0.2344, 0.2266, 0.1563, 0.0938, 0.0781,
                    0.0703, 0.0625, 0.0000])

GHIA_V = np.array([0.00000, -0.21388, -0.27669, -0.33714, -0.39188, -0.51500,
                    -0.42665, -0.31966, 0.02526, 0.32235, 0.33075, 0.37095,
                    0.32627, 0.30353, 0.29012, 0.27485, 0.00000])


# ============================================================================
# OpenFOAM file readers
# ============================================================================

def read_of_scalar_field(filepath):
    """
    Read an OpenFOAM volScalarField and return numpy array of internal field values.
    
    Handles two formats:
      - nonuniform List<scalar>: one value per cell
      - uniform <value>: single scalar for all cells
    """
    with open(filepath, 'r') as f:
        content = f.read()

    # Nonuniform: internalField nonuniform List<scalar> \n N \n ( v1 v2 ... )
    match = re.search(
        r'internalField\s+nonuniform\s+List<scalar>\s*\n(\d+)\s*\n\(([\s\S]*?)\)',
        content
    )
    if match:
        n = int(match.group(1))
        values = np.array([float(x) for x in match.group(2).split()])
        assert len(values) == n, f"Expected {n} values, got {len(values)}"
        return values

    # Uniform: internalField uniform <value>
    match = re.search(r'internalField\s+uniform\s+([\d.eE+-]+)', content)
    if match:
        return float(match.group(1))

    raise ValueError(f"Could not parse scalar field from {filepath}")


def read_of_vector_field(filepath):
    """
    Read an OpenFOAM volVectorField and return separate numpy arrays for (ux, uy, uz).
    
    Parses the internal field section which contains entries like:
      (1.58631e-07 -1.48567e-07 0)
    
    Uses the count from the header to exclude boundary field values.
    """
    with open(filepath, 'r') as f:
        content = f.read()

    # Find all (ux uy uz) patterns — captures signed scientific notation and integers
    vectors = re.findall(
        r'\((-?[\d.eE+-]+)\s+(-?[\d.eE+-]+)\s+(-?[\d.eE+-]+)\)',
        content
    )

    if not vectors:
        raise ValueError(f"Could not parse vector field from {filepath}")

    # Get expected count from header to exclude boundary field entries
    count_match = re.search(
        r'internalField\s+nonuniform\s+List<vector>\s*\n(\d+)',
        content
    )
    if count_match:
        n = int(count_match.group(1))
        vectors = vectors[:n]

    vectors = np.array(vectors, dtype=float)
    return vectors[:, 0], vectors[:, 1], vectors[:, 2]


# ============================================================================
# Centerline extraction
# ============================================================================

def extract_centerline(cc_coord, cc_other, field_vals, center_val, tolerance):
    """
    Extract a 1D profile along a centerline from 2D cell-centre data.
    
    Parameters
    ----------
    cc_coord : ndarray — coordinate along the profile direction (e.g. y for vertical)
    cc_other : ndarray — coordinate perpendicular to profile (e.g. x for vertical)
    field_vals : ndarray — field values (e.g. ux) at each cell
    center_val : float — centerline position (e.g. 0.5 for x=0.5)
    tolerance : float — how close a cell must be to the centerline
    
    Returns
    -------
    coord, values : sorted 1D arrays along the centerline
    """
    mask = np.abs(cc_other - center_val) < tolerance
    coord = cc_coord[mask]
    values = field_vals[mask]
    sort_idx = np.argsort(coord)
    return coord[sort_idx], values[sort_idx]


# ============================================================================
# Error computation
# ============================================================================

def compute_l2_error(of_coord, of_values, ghia_coord, ghia_values):
    """
    Compute L2 (RMS) error between OpenFOAM and Ghia benchmark.
    
    Interpolates the higher-resolution OF data onto the 17 Ghia y/x points,
    then computes the root-mean-square of the differences.
    
    L2 = sqrt( mean( (u_OF - u_Ghia)^2 ) )
    """
    of_at_ghia = np.interp(ghia_coord, of_coord, of_values)
    error = np.sqrt(np.mean((of_at_ghia - ghia_values) ** 2))
    return error, of_at_ghia


# ============================================================================
# Main
# ============================================================================

def main():
    # Parse command-line arguments
    case_dir = "."
    if "--case" in sys.argv:
        idx = sys.argv.index("--case")
        case_dir = sys.argv[idx + 1]

    # Find latest time directory
    time_dirs = []
    for d in os.listdir(case_dir):
        full_path = os.path.join(case_dir, d)
        if os.path.isdir(full_path):
            try:
                float(d)
                time_dirs.append(d)
            except ValueError:
                pass

    if not time_dirs:
        print("ERROR: No time directories found. Run pimpleFoam first.")
        sys.exit(1)

    time_dir = max(time_dirs, key=lambda x: float(x))
    base = os.path.join(case_dir, time_dir)
    print(f"Using time directory: {time_dir}")

    # Check for cell centre files
    ccx_path = os.path.join(base, "Ccx")
    ccy_path = os.path.join(base, "Ccy")
    u_path = os.path.join(base, "U")

    if not os.path.exists(ccx_path):
        print(f"ERROR: {ccx_path} not found.")
        print("Run: foamPostProcess -latestTime -func writeCellCentres")
        sys.exit(1)

    # Read data
    ccx = read_of_scalar_field(ccx_path)
    ccy = read_of_scalar_field(ccy_path)
    ux, uy, uz = read_of_vector_field(u_path)

    n_cells = len(ux)
    nx = int(round(1.0 / (ccx[1] - ccx[0]))) + 1 if n_cells > 1 else 1
    cell_size = 1.0 / max(nx - 1, 1)
    tolerance = cell_size * 0.6  # slightly more than half cell width

    print(f"Mesh: {n_cells} cells, estimated {nx}×{n_cells // nx}×1")
    print(f"Cell size: {cell_size:.6f} m, tolerance: {tolerance:.6f} m")

    # Extract centerlines
    vert_y, vert_u = extract_centerline(ccy, ccx, ux, 0.5, tolerance)
    horiz_x, horiz_v = extract_centerline(ccx, ccy, uy, 0.5, tolerance)

    print(f"Vertical centerline: {len(vert_y)} points")
    print(f"Horizontal centerline: {len(horiz_x)} points")

    # Compute errors
    u_error, _ = compute_l2_error(vert_y, vert_u, GHIA_Y, GHIA_U)
    v_error, _ = compute_l2_error(horiz_x, horiz_v, GHIA_X, GHIA_V)

    print(f"\nL2 error (u along x=0.5): {u_error:.6f}")
    print(f"L2 error (v along y=0.5): {v_error:.6f}")

    # ---- Plot ----
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # u-velocity along vertical centerline
    axes[0].plot(vert_u, vert_y, 'b-', linewidth=1.5, label='OpenFOAM')
    axes[0].plot(GHIA_U, GHIA_Y, 'ro', markersize=6, label='Ghia et al. (1982)')
    axes[0].set_xlabel('u-velocity', fontsize=12)
    axes[0].set_ylabel('y', fontsize=12)
    axes[0].set_title(f'u along vertical centerline (Re=1000)\nL₂ error = {u_error:.6f}', fontsize=12)
    axes[0].legend(fontsize=10)
    axes[0].grid(True, alpha=0.3)

    # v-velocity along horizontal centerline
    axes[1].plot(horiz_x, horiz_v, 'b-', linewidth=1.5, label='OpenFOAM')
    axes[1].plot(GHIA_X, GHIA_V, 'ro', markersize=6, label='Ghia et al. (1982)')
    axes[1].set_xlabel('x', fontsize=12)
    axes[1].set_ylabel('v-velocity', fontsize=12)
    axes[1].set_title(f'v along horizontal centerline (Re=1000)\nL₂ error = {v_error:.6f}', fontsize=12)
    axes[1].legend(fontsize=10)
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()

    output_dir = os.path.join(case_dir, "postProcessing", "results")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "ghia_comparison_Re1000.png")
    plt.savefig(output_path, dpi=150)
    print(f"\nPlot saved to: {output_path}")


if __name__ == "__main__":
    main()
