# Lid-Driven Cavity — Ghia et al. (1982) Validation

Validation of OpenFOAM against the classic **lid-driven cavity** benchmark from:

> Ghia, U. K. N. G., Ghia, K. N., & Shin, C. T. (1982). *High-Re solutions for incompressible flow using the Navier-Stokes equations and a multigrid method.* Journal of Computational Physics, 48(3), 387–411.

## Current Status

| Reynolds Number | Mesh | Solver | L₂ Error (u) | L₂ Error (v) | Status |
|:-:|:-:|:-:|:-:|:-:|:-:|
| 1000 | 257×257 | pimpleFoam (laminar) | 0.00777 | 0.00943 | ✅ Validated |

## Results

![u and v velocity profiles compared with Ghia et al. at Re=1000](postProcessing/results/ghia_comparison_Re1000.png)

## Case Setup

- **Domain**: 1m × 1m square cavity (2D — `empty` BC on front/back)
- **Lid velocity**: u = 1 m/s (top wall, moving right)
- **Other walls**: no-slip (u = 0)
- **Kinematic viscosity**: ν = 1×10⁻³ m²/s → Re = UL/ν = 1000
- **Mesh**: 257×257 uniform hexahedral cells (`blockMesh`)
- **Solver**: `pimpleFoam` with `simulationType laminar`
- **Temporal**: adaptive Δt with `maxCo 0.5`, endTime = 100s

## How to Run

### Prerequisites
- OpenFOAM 13 (Foundation version) — adjust paths for other versions

### Steps

```bash
# 1. Source OpenFOAM environment
source /opt/openfoam13/etc/bashrc

# 2. Generate mesh
blockMesh

# 3. Run solver
pimpleFoam > log &

# 4. Write cell centres (for post-processing)
foamPostProcess -latestTime -func writeCellCentres

# 5. Extract centerline profiles and compare with Ghia
python3 scripts/compare_ghia.py
```

## Post-Processing

The Python script `scripts/compare_ghia.py`:

1. Reads the latest OpenFOAM time directory
2. Extracts u-velocity along the vertical centerline (x = 0.5)
3. Extracts v-velocity along the horizontal centerline (y = 0.5)
4. Interpolates to Ghia's 17 benchmark points
5. Computes L₂ norm error
6. Plots OpenFOAM profiles against Ghia data

### Requirements
```bash
pip install numpy matplotlib
```

## Project Structure

```
├── 0/                          # Initial conditions
│   ├── U                       # Velocity field
│   └── p                       # Pressure field
├── constant/
│   ├── physicalProperties      # Kinematic viscosity
│   └── momentumTransport       # Laminar simulation
├── system/
│   ├── blockMeshDict           # Mesh definition (257×257)
│   ├── controlDict             # Time stepping, maxCo = 0.5
│   ├── fvSchemes               # Discretization schemes
│   └── fvSolution              # Linear solver settings (PIMPLE)
├── scripts/
│   └── compare_ghia.py         # Validation comparison script
├── postProcessing/results/
│   └── ghia_comparison_Re1000.png
└── README.md
```

## Roadmap

- [ ] Re = 100, 400, 1000, 3200, 5000, 7500, 10000 — automated parameter sweep
- [ ] Grid convergence study (65×65, 129×129, 257×257, 513×513)
- [ ] Automated Python pipeline for running + post-processing all cases
- [ ] Streamfunction and vorticity contours
- [ ] Corner vortex resolution analysis

## References

1. Ghia, U., Ghia, K. N., & Shin, C. T. (1982). High-Re solutions for incompressible flow using the Navier-Stokes equations and a multigrid method. *Journal of Computational Physics*, 48(3), 387–411.
2. [OpenFOAM Foundation v13](https://openfoam.org/version/13/)
