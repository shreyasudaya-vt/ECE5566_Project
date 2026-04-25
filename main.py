import argparse
from pathlib import Path

from netparams import NetParams
from plotting import plot_metric_images, plot_penalty_illustration
from reporting import print_summary, summary_stats
from scenarios import VALID_SCENARIOS
from simulation import simulate

DEFAULT_DURATION = 120.0
DEFAULT_OUTPUT_DIR = "results"
DEFAULT_OUTPUT_PREFIX = "tcp_sim"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TCP congestion control simulator")
    parser.add_argument(
        "--scenario",
        default="burst",
        choices=[*VALID_SCENARIOS, "all"],
        help="Traffic scenario to simulate",
    )
    parser.add_argument("--C", type=float, default=20.0, help="Link capacity in Mbps")
    parser.add_argument("--flows", type=int, default=3, help="Flows per algorithm")
    parser.add_argument("--rtt", type=float, default=20.0, help="RTT_min in milliseconds")
    parser.add_argument("--kappa", type=float, default=1.5, help="Burst penalty weight")
    parser.add_argument("--xi", type=float, default=1.0, help="Delay penalty weight")
    parser.add_argument("--gamma", type=float, default=0.8, help="Outer penalty weight")
    parser.add_argument("--duration", type=float, default=DEFAULT_DURATION, help="Simulation length")
    parser.add_argument("--dt", type=float, default=0.5, help="Time step")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Directory for result images")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PREFIX, help="Output file prefix")
    return parser.parse_args()


def build_params(args: argparse.Namespace) -> NetParams:
    return NetParams(
        C=args.C,
        n_flows=args.flows,
        RTT_min=args.rtt / 1000.0,
        kappa=args.kappa,
        xi=args.xi,
        gamma=args.gamma,
    )


def main() -> None:
    args = parse_args()
    params = build_params(args)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\nTCP Congestion Control Simulator")
    print(
        f"Parameters: C={params.C} Mbps, {params.n_flows} flows, "
        f"RTT_min={params.RTT_min * 1000:.0f} ms, "
        f"kappa={params.kappa}, xi={params.xi}, gamma={params.gamma}, "
        f"duration={args.duration} s"
    )

    if args.scenario == "all":
        print("\nRunning all scenarios...")
        for scenario in VALID_SCENARIOS:
            print(f"\nRunning scenario: {scenario}...")
            times, states = simulate(params, scenario, args.duration, args.dt)
            stats = summary_stats(states)
            print_summary(stats, params, scenario, args.duration)
            plot_metric_images(times, states, params, scenario, output_dir, args.output)
    else:
        print(f"\nRunning scenario: {args.scenario}...")
        times, states = simulate(params, args.scenario, args.duration, args.dt)
        stats = summary_stats(states)
        print_summary(stats, params, args.scenario, args.duration)
        plot_metric_images(times, states, params, args.scenario, output_dir, args.output)

    plot_penalty_illustration(params, output_dir, args.output)
    print("Done.\n")


if __name__ == "__main__":
    main()
