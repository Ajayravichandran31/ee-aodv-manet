# EE-AODV: Energy-Efficient Routing Optimization in MANETs for Battery-Constrained Devices

An energy-threshold and delay-weighted route selection extension to the AODV routing protocol, implemented and evaluated in NS-3.41.

## Overview

Standard AODV selects routes purely by hop count and has no awareness of a node's remaining battery energy. In a MANET made up entirely of battery-powered devices, this causes the same energy-rich and energy-poor nodes to be used as relays with equal likelihood — draining weak nodes prematurely, breaking active routes, and triggering costly route rediscovery.

**EE-AODV** addresses this with two lightweight mechanisms added directly into AODV's existing Route Request (RREQ) handling, with **zero new control packets**:

1. **Critical energy threshold** — a node whose residual energy falls below 5% of its initial capacity drops incoming RREQs instead of forwarding them, protecting its last reserve.
2. **Energy-proportional delayed rebroadcast** — a node forwards RREQs with a delay inversely proportional to its residual energy. Since AODV's destination always accepts the *first* RREP it receives, this implicitly biases route selection toward higher-energy paths — without any node ever comparing energy values explicitly.

## Base Paper

This project is benchmarked against:
> T. Legesse, D. W. Girmaw, E. Yitayal, E. Admassu, "Energy aware stable path ad hoc on-demand distance vector algorithm for extending network lifetime of mobile ad hoc networks," *PLOS ONE*, vol. 20, no. 4, 2025.

## Results Summary

Evaluated in NS-3.41 with 30 nodes, IEEE 802.11b ad-hoc, Random Waypoint mobility, 5 trials per configuration:

| Condition | Metric | Standard AODV | EE-AODV (Proposed) |
|---|---|---|---|
| Energy-scarce (5 J) | Packet Delivery Ratio | 41.85% | **64.04%** |
| Energy-scarce (5 J) | Avg. End-to-End Delay | 317.9 ms | **90.1 ms** |
| Energy-abundant (100 J) | Packet Delivery Ratio | 88.93% | 88.45% |
| Energy-abundant (100 J) | Avg. End-to-End Delay | 86.4 ms | 79.3 ms |

EE-AODV shows a substantial improvement under energy-constrained conditions and converges to standard AODV-like behaviour when energy is abundant — confirming the mechanism activates proportionally to actual need, with no added overhead when it isn't required.

See `results/` for full comparison graphs.

## Repository Structure

```
ee-aodv-manet/
├── src/eeaodv/              # Modified AODV module (cloned from ns-3's aodv module)
│   ├── model/               # Core protocol logic — see model/eeaodv-routing-protocol.cc
│   └── helper/
├── scratch/
│   └── manet-energy-sim.cc  # Simulation scenario: mobility, energy model, traffic, FlowMonitor
├── scripts/
│   ├── 03_analyze_results.py      # Single-run analysis + graphs
│   └── 05_analyze_multi_run.py    # Multi-trial averaging + statistics + lifetime projection
├── results/                 # Output graphs (PDR, delay, energy consumption comparisons)
├── docs/                    # Project report / presentation (if included)
└── README.md
```

## Requirements

- [NS-3.41](https://www.nsnam.org/) (or compatible version)
- Python 3 with `matplotlib`, `pandas`, `numpy`

## Setup & Build

1. Clone this repo's `src/eeaodv` folder into your NS-3 installation's `src/` directory:
   ```bash
   cp -r src/eeaodv /path/to/ns-3.41/src/
   cp scratch/manet-energy-sim.cc /path/to/ns-3.41/scratch/
   ```
2. Rebuild NS-3:
   ```bash
   cd /path/to/ns-3.41
   ./ns3 build
   ```

## Running Simulations

```bash
# Standard AODV baseline
./ns3 run "scratch/manet-energy-sim --protocol=aodv --nNodes=30 --simTime=200 --areaX=400 --areaY=400 --run=1 --prefix=aodv-run1"

# Proposed EE-AODV
./ns3 run "scratch/manet-energy-sim --protocol=eeaodv --nNodes=30 --simTime=200 --areaX=400 --areaY=400 --run=1 --prefix=eeaodv-run1"
```

Repeat with `--run=2` through `--run=5` (different random seeds) for each protocol to gather multi-trial statistics.

## Analyzing Results

```bash
pip install matplotlib pandas numpy --break-system-packages
python3 scripts/05_analyze_multi_run.py
```

This prints a PDR/delay/lifetime summary table and saves comparison graphs to `results_multirun/`.

## Key Parameters

| Parameter | Value |
|---|---|
| Critical energy threshold | 5% of initial energy |
| Max added rebroadcast delay (k) | 25 ms |
| Simulation area | 400 m × 400 m |
| Mobility model | Random Waypoint (1–5 m/s, 2s pause) |
| MAC/PHY | IEEE 802.11b, ad-hoc mode |
| Traffic | CBR over UDP, 512-byte packets |

## Status

This is an active final-year academic project (Phase I complete). Phase II will add extended trials, a NetAnim visual demonstration, and a full statistical writeup.

## License

Academic project — add a license here if you intend to make this reusable (MIT is a common permissive choice for student projects: https://choosealicense.com/licenses/mit/).

## Authors

Ajay R(8208E23ITR012), Aakash N(8208E23ITR002), Mohamed Faheem S(8208E23ITR072)
Department of B.Tech Information Technology, E.G.S. Pillay Engineering College
