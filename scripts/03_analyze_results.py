"""
analyze_results.py
---------------------------------------------------------------------
Parses NS-3 FlowMonitor XML + energy CSV output for both protocol runs
and produces the comparison graphs a final-year MANET project needs:

  1. Packet Delivery Ratio (PDR) - AODV vs EE-AODV
  2. Average End-to-End Delay
  3. Throughput
  4. Network Lifetime (% alive nodes over time)
  5. Total energy consumed over time

USAGE:
  Run your simulations first to generate these files in the same folder:
    aodv-flowmon.xml     aodv-energy.csv
    eeaodv-flowmon.xml   eeaodv-energy.csv

  Then:
    pip install matplotlib pandas --break-system-packages
    python3 analyze_results.py

Outputs PNGs into ./results/
---------------------------------------------------------------------
"""

import os
import xml.etree.ElementTree as ET
import pandas as pd
import matplotlib.pyplot as plt

OUT_DIR = "results"
os.makedirs(OUT_DIR, exist_ok=True)

PROTOCOLS = {
    "aodv": {"label": "Standard AODV", "color": "#d94f4f"},
    "eeaodv": {"label": "EE-AODV (Proposed)", "color": "#2f8f5b"},
}


def parse_flowmon(path):
    """Returns dict: pdr(%), avg_delay(ms), throughput(kbps), overhead(pkts)"""
    tree = ET.parse(path)
    root = tree.getroot()

    tx_packets = rx_packets = 0
    delay_sum = 0.0
    rx_bytes = 0
    last_rx_time = 0.0
    first_tx_time = None

    for flow in root.find("FlowStats").findall("Flow"):
        tx_packets += int(flow.get("txPackets"))
        rx = int(flow.get("rxPackets"))
        rx_packets += rx
        rx_bytes += int(flow.get("rxBytes"))
        if rx > 0:
            delay_str = flow.get("delaySum")  # e.g. "+1234000000.0ns"
            delay_ns = float(delay_str.replace("+", "").replace("ns", ""))
            delay_sum += delay_ns

    pdr = (rx_packets / tx_packets * 100.0) if tx_packets else 0.0
    avg_delay_ms = (delay_sum / rx_packets / 1e6) if rx_packets else 0.0

    return {
        "pdr": pdr,
        "avg_delay_ms": avg_delay_ms,
        "rx_packets": rx_packets,
        "tx_packets": tx_packets,
        "rx_bytes": rx_bytes,
    }


def parse_energy(path):
    df = pd.read_csv(path)
    node_cols = [c for c in df.columns if c.endswith("_J")]
    df["total_energy_J"] = df[node_cols].sum(axis=1)
    return df


def main():
    flow_results = {}
    energy_results = {}

    for proto in PROTOCOLS:
        fm_path = f"{proto}-flowmon.xml"
        en_path = f"{proto}-energy.csv"
        if os.path.exists(fm_path):
            flow_results[proto] = parse_flowmon(fm_path)
        else:
            print(f"[skip] {fm_path} not found")
        if os.path.exists(en_path):
            energy_results[proto] = parse_energy(en_path)
        else:
            print(f"[skip] {en_path} not found")

    # ---------------- PDR + Delay bar charts ----------------
    if flow_results:
        protos = list(flow_results.keys())
        labels = [PROTOCOLS[p]["label"] for p in protos]
        colors = [PROTOCOLS[p]["color"] for p in protos]

        fig, ax = plt.subplots(figsize=(5, 4))
        ax.bar(labels, [flow_results[p]["pdr"] for p in protos], color=colors)
        ax.set_ylabel("Packet Delivery Ratio (%)")
        ax.set_title("PDR Comparison")
        plt.tight_layout()
        plt.savefig(f"{OUT_DIR}/pdr_comparison.png", dpi=150)
        plt.close()

        fig, ax = plt.subplots(figsize=(5, 4))
        ax.bar(labels, [flow_results[p]["avg_delay_ms"] for p in protos], color=colors)
        ax.set_ylabel("Avg End-to-End Delay (ms)")
        ax.set_title("Delay Comparison")
        plt.tight_layout()
        plt.savefig(f"{OUT_DIR}/delay_comparison.png", dpi=150)
        plt.close()

    # ---------------- Network lifetime (alive nodes over time) ----------------
    if energy_results:
        fig, ax = plt.subplots(figsize=(6, 4))
        for proto, df in energy_results.items():
            ax.plot(df["time_s"], df["aliveNodes"],
                    label=PROTOCOLS[proto]["label"], color=PROTOCOLS[proto]["color"])
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Number of Alive Nodes")
        ax.set_title("Network Lifetime")
        ax.legend()
        plt.tight_layout()
        plt.savefig(f"{OUT_DIR}/network_lifetime.png", dpi=150)
        plt.close()

        # ---------------- Total residual energy over time ----------------
        fig, ax = plt.subplots(figsize=(6, 4))
        for proto, df in energy_results.items():
            ax.plot(df["time_s"], df["total_energy_J"],
                    label=PROTOCOLS[proto]["label"], color=PROTOCOLS[proto]["color"])
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Total Residual Energy (J)")
        ax.set_title("Cumulative Energy Consumption")
        ax.legend()
        plt.tight_layout()
        plt.savefig(f"{OUT_DIR}/energy_consumption.png", dpi=150)
        plt.close()

        # First node death time (key final-year-project metric)
        print("\n=== Network Lifetime Summary ===")
        for proto, df in energy_results.items():
            dead = df[df["aliveNodes"] < df["aliveNodes"].iloc[0]]
            first_death = dead["time_s"].iloc[0] if len(dead) else None
            print(f"{PROTOCOLS[proto]['label']}: first node death at "
                  f"{first_death if first_death is not None else 'N/A (all survived)'} s")

    if flow_results:
        print("\n=== Flow-level Summary ===")
        for proto, r in flow_results.items():
            print(f"{PROTOCOLS[proto]['label']}: PDR={r['pdr']:.2f}%  "
                  f"AvgDelay={r['avg_delay_ms']:.2f} ms  "
                  f"Rx={r['rx_packets']}/{r['tx_packets']} packets")

    print(f"\nGraphs saved to ./{OUT_DIR}/")


if __name__ == "__main__":
    main()
