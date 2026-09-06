"""
analyze_multi_run.py
---------------------------------------------------------------------
Averages results across multiple trial runs (aodv-run1..N, eeaodv-run1..N)
for a statistically defensible comparison -- use this instead of
analyze_results.py once you have multiple --run=N trials.

USAGE:
  Run your simulations first with a matching --run=N and --prefix=<proto>-runN:
    ./ns3 run "... --protocol=aodv   --run=1 --prefix=aodv-run1"
    ./ns3 run "... --protocol=eeaodv --run=1 --prefix=eeaodv-run1"
    ... (repeat for run=2,3,4,5)

  Then:
    python3 analyze_multi_run.py

Outputs averaged PNGs into ./results_multirun/ and prints a summary table.
---------------------------------------------------------------------
"""

import os
import glob
import xml.etree.ElementTree as ET
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

OUT_DIR = "results_multirun"
os.makedirs(OUT_DIR, exist_ok=True)

PROTOCOLS = {
    "aodv": {"label": "Standard AODV", "color": "#d94f4f"},
    "eeaodv": {"label": "EE-AODV (Proposed)", "color": "#2f8f5b"},
}


def parse_flowmon(path):
    tree = ET.parse(path)
    root = tree.getroot()
    tx_packets = rx_packets = 0
    delay_sum = 0.0
    for flow in root.find("FlowStats").findall("Flow"):
        tx_packets += int(flow.get("txPackets"))
        rx = int(flow.get("rxPackets"))
        rx_packets += rx
        if rx > 0:
            delay_ns = float(flow.get("delaySum").replace("+", "").replace("ns", ""))
            delay_sum += delay_ns
    pdr = (rx_packets / tx_packets * 100.0) if tx_packets else 0.0
    avg_delay_ms = (delay_sum / rx_packets / 1e6) if rx_packets else 0.0
    return pdr, avg_delay_ms, rx_packets, tx_packets


def parse_energy(path):
    df = pd.read_csv(path)
    node_cols = [c for c in df.columns if c.endswith("_J")]
    df["total_energy_J"] = df[node_cols].sum(axis=1)
    first_death_time = None
    initial_alive = df["aliveNodes"].iloc[0]
    dead = df[df["aliveNodes"] < initial_alive]
    if len(dead):
        first_death_time = dead["time_s"].iloc[0]
    return df, first_death_time


def find_runs(proto):
    """Find all flowmon files matching <proto>-runN-flowmon.xml"""
    pattern = f"{proto}-run*-flowmon.xml"
    files = sorted(glob.glob(pattern))
    runs = []
    for f in files:
        prefix = f.replace("-flowmon.xml", "")
        energy_file = f"{prefix}-energy.csv"
        if os.path.exists(energy_file):
            runs.append((f, energy_file, prefix))
        else:
            print(f"[warn] {energy_file} missing for {f}, skipping energy for this run")
            runs.append((f, None, prefix))
    return runs


def main():
    summary = {}
    energy_dfs = {}

    for proto in PROTOCOLS:
        runs = find_runs(proto)
        if not runs:
            print(f"[skip] no runs found for {proto} (expected files like {proto}-run1-flowmon.xml)")
            continue

        pdrs, delays, first_deaths = [], [], []
        run_energy_dfs = []

        for flowmon_path, energy_path, prefix in runs:
            pdr, delay, rx, tx = parse_flowmon(flowmon_path)
            pdrs.append(pdr)
            delays.append(delay)
            print(f"  {prefix}: PDR={pdr:.2f}%  delay={delay:.2f}ms  rx={rx}/{tx}")

            if energy_path:
                edf, first_death = parse_energy(energy_path)
                run_energy_dfs.append(edf)
                if first_death is not None:
                    first_deaths.append(first_death)

        summary[proto] = {
            "pdr_mean": np.mean(pdrs),
            "pdr_std": np.std(pdrs),
            "delay_mean": np.mean(delays),
            "delay_std": np.std(delays),
            "n_runs": len(pdrs),
            "first_death_mean": np.mean(first_deaths) if first_deaths else None,
            "first_death_runs": len(first_deaths),
        }
        energy_dfs[proto] = run_energy_dfs

    # ---------------- Print summary table ----------------
    print("\n" + "=" * 70)
    print(f"{'Protocol':<22}{'PDR (%)':<18}{'Delay (ms)':<18}{'Avg 1st Death (s)'}")
    print("=" * 70)
    for proto, s in summary.items():
        label = PROTOCOLS[proto]["label"]
        pdr_str = f"{s['pdr_mean']:.2f} +/- {s['pdr_std']:.2f}"
        delay_str = f"{s['delay_mean']:.2f} +/- {s['delay_std']:.2f}"
        death_str = (f"{s['first_death_mean']:.1f} ({s['first_death_runs']}/{s['n_runs']} runs)"
                     if s['first_death_mean'] is not None else "N/A (no deaths)")
        print(f"{label:<22}{pdr_str:<18}{delay_str:<18}{death_str}")
    print("=" * 70)

    # ---------------- PDR / Delay bar charts with error bars ----------------
    protos = list(summary.keys())
    if protos:
        labels = [PROTOCOLS[p]["label"] for p in protos]
        colors = [PROTOCOLS[p]["color"] for p in protos]

        fig, ax = plt.subplots(figsize=(5, 4))
        ax.bar(labels, [summary[p]["pdr_mean"] for p in protos],
               yerr=[summary[p]["pdr_std"] for p in protos], capsize=5, color=colors)
        ax.set_ylabel("Packet Delivery Ratio (%)")
        ax.set_title(f"PDR Comparison (avg of {summary[protos[0]]['n_runs']} runs)")
        plt.tight_layout()
        plt.savefig(f"{OUT_DIR}/pdr_comparison_avg.png", dpi=150)
        plt.close()

        fig, ax = plt.subplots(figsize=(5, 4))
        ax.bar(labels, [summary[p]["delay_mean"] for p in protos],
               yerr=[summary[p]["delay_std"] for p in protos], capsize=5, color=colors)
        ax.set_ylabel("Avg End-to-End Delay (ms)")
        ax.set_title(f"Delay Comparison (avg of {summary[protos[0]]['n_runs']} runs)")
        plt.tight_layout()
        plt.savefig(f"{OUT_DIR}/delay_comparison_avg.png", dpi=150)
        plt.close()

    # ---------------- Averaged network lifetime curve ----------------
    if energy_dfs:
        fig, ax = plt.subplots(figsize=(6, 4))
        for proto, dfs in energy_dfs.items():
            if not dfs:
                continue
            # Align on time_s, average aliveNodes across runs
            merged = dfs[0][["time_s"]].copy()
            for i, df in enumerate(dfs):
                merged[f"alive_{i}"] = df["aliveNodes"].reindex(merged.index, method="nearest")
            alive_cols = [c for c in merged.columns if c.startswith("alive_")]
            merged["alive_mean"] = merged[alive_cols].mean(axis=1)
            ax.plot(merged["time_s"], merged["alive_mean"],
                    label=PROTOCOLS[proto]["label"], color=PROTOCOLS[proto]["color"])
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Avg Alive Nodes")
        ax.set_title("Network Lifetime (averaged)")
        ax.legend()
        plt.tight_layout()
        plt.savefig(f"{OUT_DIR}/network_lifetime_avg.png", dpi=150)
        plt.close()

    print(f"\nGraphs saved to ./{OUT_DIR}/")


if __name__ == "__main__":
    main()
