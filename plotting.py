from pathlib import Path
from typing import Callable, Dict

import matplotlib
import numpy as np
from matplotlib import pyplot as plt

from netparams import AlgoState, NetParams
from util import penalty

matplotlib.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linestyle": "--",
        "figure.dpi": 130,
    }
)

PALETTE = {
    "CUBIC": "#185FA5",
    "BBRv3": "#3B6D11",
    "Burst-Aware CUBIC": "#BA7517",
    "Burst-Aware BBR": "#993556",
}

LINESTYLES = {
    "CUBIC": "-",
    "BBRv3": "--",
    "Burst-Aware CUBIC": "-.",
    "Burst-Aware BBR": ":",
}


def ensure_output_dir(base_dir: str | Path, scenario: str) -> Path:
    """Create and return the scenario-specific output directory."""

    scenario_dir = Path(base_dir) / scenario
    scenario_dir.mkdir(parents=True, exist_ok=True)
    return scenario_dir


def _format_title(params: NetParams, scenario: str, title: str) -> str:
    return (
        f"{title} - {scenario}\n"
        f"C={params.C} Mbps, flows={params.n_flows}, RTT_min={params.RTT_min * 1000:.0f} ms, "
        f"kappa={params.kappa}, xi={params.xi}, gamma={params.gamma}"
    )


def _save_figure(fig: plt.Figure, output_path: Path) -> None:
    fig.savefig(output_path, bbox_inches="tight", dpi=130)
    print(f"Figure saved -> {output_path}")
    plt.close(fig)


def _add_burst_window(ax: plt.Axes, scenario: str) -> None:
    if scenario == "burst":
        ax.axvspan(25, 35, alpha=0.07, color="red", label="Burst window")


def _plot_timeseries(
    times: np.ndarray,
    states: Dict[str, AlgoState],
    scenario: str,
    params: NetParams,
    ylabel: str,
    title: str,
    value_getter: Callable[[AlgoState], list[float]],
    output_path: Path,
    include_capacity: bool = False,
    include_zero_line: bool = False,
    y_limits: tuple[float, float] | None = None,
) -> None:
    fig, ax = plt.subplots(figsize=(10, 5.5))

    for name, state in states.items():
        ax.plot(
            times,
            value_getter(state),
            color=PALETTE[name],
            ls=LINESTYLES[name],
            lw=1.8,
            label=name,
        )

    if include_capacity:
        ax.axhline(params.C, color="gray", ls=":", lw=1.0, alpha=0.6, label="Capacity")
    if include_zero_line:
        ax.axhline(0.0, color="gray", ls=":", lw=1.0, alpha=0.5)

    _add_burst_window(ax, scenario)

    ax.set_xlabel("Time (s)", fontsize=10)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_title(_format_title(params, scenario, title), fontsize=11, pad=10)
    ax.tick_params(labelsize=9)
    if y_limits is not None:
        ax.set_ylim(*y_limits)

    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, labels, fontsize=9, framealpha=0.9)
    fig.tight_layout()
    _save_figure(fig, output_path)


def plot_metric_images(
    times: np.ndarray,
    states: Dict[str, AlgoState],
    params: NetParams,
    scenario: str,
    output_dir: str | Path,
    output_prefix: str,
) -> None:
    """Export each scenario metric as its own image."""

    scenario_dir = ensure_output_dir(output_dir, scenario)

    _plot_timeseries(
        times,
        states,
        scenario,
        params,
        ylabel="Mbps",
        title="Throughput over time",
        value_getter=lambda state: state.ts_throughput,
        output_path=scenario_dir / f"{output_prefix}_throughput.png",
        include_capacity=True,
    )
    _plot_timeseries(
        times,
        states,
        scenario,
        params,
        ylabel="Packets",
        title="Queue depth at bottleneck",
        value_getter=lambda state: state.ts_queue_pkts,
        output_path=scenario_dir / f"{output_prefix}_queue.png",
    )
    _plot_timeseries(
        times,
        states,
        scenario,
        params,
        ylabel="ms",
        title="Queuing delay",
        value_getter=lambda state: state.ts_delay_ms,
        output_path=scenario_dir / f"{output_prefix}_delay.png",
    )
    _plot_timeseries(
        times,
        states,
        scenario,
        params,
        ylabel="Jain index",
        title="Per-flow fairness",
        value_getter=lambda state: state.ts_jain,
        output_path=scenario_dir / f"{output_prefix}_fairness.png",
        y_limits=(0.0, 1.05),
    )
    _plot_timeseries(
        times,
        states,
        scenario,
        params,
        ylabel="b_l",
        title="Burst gradient",
        value_getter=lambda state: state.ts_b_l,
        output_path=scenario_dir / f"{output_prefix}_burst_gradient.png",
        include_zero_line=True,
    )

    fig, ax_throughput = plt.subplots(figsize=(8.5, 5.5))
    names = list(states.keys())
    abbreviations = ["CUBIC", "BBRv3", "BA-CUBIC", "BA-BBR"]
    x_pos = np.arange(len(names))
    width = 0.35
    avg_throughput = [np.mean(states[name].ts_throughput) for name in names]
    avg_delay = [np.mean(states[name].ts_delay_ms) for name in names]

    ax_delay = ax_throughput.twinx()
    throughput_bars = ax_throughput.bar(
        x_pos - width / 2,
        avg_throughput,
        width,
        color=[PALETTE[name] for name in names],
        alpha=0.8,
        label="Avg throughput",
    )
    delay_bars = ax_delay.bar(
        x_pos + width / 2,
        avg_delay,
        width,
        color=[PALETTE[name] for name in names],
        alpha=0.4,
        label="Avg delay",
    )

    ax_throughput.set_xticks(x_pos)
    ax_throughput.set_xticklabels(abbreviations, fontsize=9)
    ax_throughput.set_ylabel("Avg throughput (Mbps)", fontsize=10)
    ax_delay.set_ylabel("Avg queuing delay (ms)", fontsize=10)
    ax_throughput.set_title(_format_title(params, scenario, "Average throughput vs delay"), fontsize=11, pad=10)
    ax_throughput.tick_params(labelsize=9)
    ax_delay.tick_params(labelsize=9)

    for bar, value in zip(throughput_bars, avg_throughput):
        ax_throughput.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.1,
            f"{value:.1f}",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    for bar, value in zip(delay_bars, avg_delay):
        ax_delay.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.02,
            f"{value:.1f}",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    throughput_handles, throughput_labels = ax_throughput.get_legend_handles_labels()
    delay_handles, delay_labels = ax_delay.get_legend_handles_labels()
    ax_throughput.legend(
        throughput_handles + delay_handles,
        throughput_labels + delay_labels,
        fontsize=9,
        framealpha=0.9,
        loc="upper left",
    )
    fig.tight_layout()
    _save_figure(fig, scenario_dir / f"{output_prefix}_throughput_vs_delay.png")


def plot_penalty_illustration(params: NetParams, output_dir: str | Path, output_prefix: str) -> None:
    """Generate the penalty-surface illustration in the shared results directory."""

    results_dir = Path(output_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    fig.suptitle(
        "Convex penalty surface P(d_l, b_l) = xi*d_l + (kappa/2)*max(0,b_l)^2",
        fontsize=11,
    )

    d_vals = np.linspace(0, 0.1, 200)
    b_vals = np.linspace(-0.5, 1.5, 200)

    ax = axes[0]
    for delay_fixed, color in ((0.0, "#185FA5"), (0.02, "#BA7517"), (0.05, "#993556")):
        values = np.array([penalty(delay_fixed, burst, params.xi, params.kappa) for burst in b_vals])
        ax.plot(b_vals, values, color=color, lw=1.8, label=f"d_l = {delay_fixed:.2f} s")
    ax.axvline(0, color="gray", ls=":", lw=1, alpha=0.5)
    ax.set_xlabel("Burst gradient b_l", fontsize=10)
    ax.set_ylabel("Penalty P", fontsize=10)
    ax.set_title("P vs burst gradient", fontsize=10)
    ax.legend(fontsize=9)

    ax3d = fig.add_subplot(1, 2, 2, projection="3d")
    delay_mesh, burst_mesh = np.meshgrid(d_vals, b_vals)
    penalty_mesh = np.vectorize(
        lambda delay, burst: penalty(delay, burst, params.xi, params.kappa)
    )(delay_mesh, burst_mesh)
    surface = ax3d.plot_surface(delay_mesh, burst_mesh, penalty_mesh, cmap="viridis", alpha=0.85, linewidth=0)
    ax3d.set_xlabel("d_l (s)", fontsize=8)
    ax3d.set_ylabel("b_l", fontsize=8)
    ax3d.set_zlabel("P", fontsize=8)
    ax3d.set_title("P(d_l, b_l) surface", fontsize=10)
    fig.colorbar(surface, ax=ax3d, shrink=0.5, pad=0.1)

    fig.tight_layout()
    _save_figure(fig, results_dir / f"{output_prefix}_penalty_surface.png")
