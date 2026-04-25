from typing import Dict

import numpy as np

from netparams import AlgoState, NetParams


def summary_stats(states: Dict[str, AlgoState]) -> Dict[str, dict]:
    """Compute summary statistics for each algorithm."""

    stats = {}
    for name, state in states.items():
        throughput = np.array(state.ts_throughput)
        queue = np.array(state.ts_queue_pkts)
        delay = np.array(state.ts_delay_ms)
        fairness = np.array(state.ts_jain)
        burst = np.array(state.ts_b_l)
        stats[name] = {
            "avg_throughput_mbps": float(np.mean(throughput)),
            "std_throughput_mbps": float(np.std(throughput)),
            "avg_queue_pkts": float(np.mean(queue)),
            "max_queue_pkts": float(np.max(queue)),
            "avg_delay_ms": float(np.mean(delay)),
            "max_delay_ms": float(np.max(delay)),
            "avg_jain": float(np.mean(fairness)),
            "avg_burst_gradient": float(np.mean(np.maximum(0.0, burst))),
            "pct_time_congested": float(100.0 * np.mean(burst > 0.0)),
        }
    return stats


def print_summary(
    stats: Dict[str, dict],
    params: NetParams,
    scenario: str,
    duration: float,
) -> None:
    """Print a compact comparison table."""

    separator = "-" * 76
    print()
    print("=" * 76)
    print("TCP Congestion Control Simulator Results")
    print("=" * 76)
    print(f"Scenario : {scenario}")
    print(f"Capacity : {params.C} Mbps   Flows/algo : {params.n_flows}")
    print(f"RTT_min  : {params.RTT_min * 1000:.0f} ms   Duration : {duration} s")
    print(
        f"kappa={params.kappa}  xi={params.xi}  gamma={params.gamma}  "
        f"tau={params.tau}  mu={params.mu}"
    )
    print(separator)

    headers = ["Metric"] + list(stats.keys())
    col_width = max(20, (76 - 20) // len(stats))
    fmt = f"{{:<20}}" + (f"  {{:>{col_width}}}" * len(stats))
    print(fmt.format(*headers))
    print(separator)

    rows = [
        ("Avg throughput", "avg_throughput_mbps", ".2f"),
        ("Std throughput", "std_throughput_mbps", ".2f"),
        ("Avg queue", "avg_queue_pkts", ".1f"),
        ("Max queue", "max_queue_pkts", ".1f"),
        ("Avg delay", "avg_delay_ms", ".2f"),
        ("Max delay", "max_delay_ms", ".2f"),
        ("Avg Jain", "avg_jain", ".4f"),
        ("Avg burst grad", "avg_burst_gradient", ".4f"),
        ("% congested", "pct_time_congested", ".1f"),
    ]
    for label, key, spec in rows:
        values = [f"{stats[name][key]:{spec}}" for name in stats]
        print(fmt.format(label, *values))

    best_throughput = max(stats, key=lambda name: stats[name]["avg_throughput_mbps"])
    lowest_queue = min(stats, key=lambda name: stats[name]["avg_queue_pkts"])
    lowest_delay = min(stats, key=lambda name: stats[name]["avg_delay_ms"])
    best_fairness = max(stats, key=lambda name: stats[name]["avg_jain"])
    least_bursty = min(stats, key=lambda name: stats[name]["avg_burst_gradient"])

    print(separator)
    print(f"Best throughput : {best_throughput}")
    print(f"Lowest queue    : {lowest_queue}")
    print(f"Lowest delay    : {lowest_delay}")
    print(f"Best fairness   : {best_fairness}")
    print(f"Least bursty    : {least_bursty}")
    print("=" * 76)
    print()
