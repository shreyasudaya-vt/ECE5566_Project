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
    parser.add_argument("--duration", type=float, default=DEFAULT_DURATION, help="Simulation length")
    parser.add_argument("--dt", type=float, default=0.5, help="Time step")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Directory for result images")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PREFIX, help="Output file prefix")
    
    # Global penalty parameters (apply to both)
    parser.add_argument("--gamma", type=float, default=0.8, help="Penalty weight (applies to both)")
    parser.add_argument("--kappa", type=float, default=1.5, help="Burst penalty coefficient (applies to both)")
    parser.add_argument("--xi", type=float, default=1.0, help="Delay penalty coefficient (applies to both)")
    parser.add_argument("--tau", type=float, default=0.15, help="Burst tolerance threshold (applies to both)")
    parser.add_argument("--mu", type=float, default=0.05, help="Window reduction step size (applies to both)")
    
    # CUBIC-specific parameters
    parser.add_argument("--cubic-gamma", type=float, default=None, help="CUBIC penalty weight (overrides --gamma)")
    parser.add_argument("--cubic-kappa", type=float, default=None, help="CUBIC burst penalty coefficient")
    parser.add_argument("--cubic-xi", type=float, default=None, help="CUBIC delay penalty coefficient")
    parser.add_argument("--cubic-tau", type=float, default=None, help="CUBIC burst tolerance threshold")
    parser.add_argument("--cubic-mu", type=float, default=None, help="CUBIC window reduction step size")
    parser.add_argument("--cubic-lr", type=float, default=0.08, help="CUBIC learning rate")
    parser.add_argument("--cubic-alpha", type=float, default=0.4, help="CUBIC utility scaling factor")
    parser.add_argument("--cubic-queue-price", type=float, default=0.14, help="CUBIC base queue congestion price")
    parser.add_argument("--cubic-burst-price", type=float, default=0.10, help="CUBIC base burst congestion price")
    parser.add_argument("--cubic-burst-decrease", type=float, default=0.4, help="CUBIC max multiplicative decrease on burst")
    
    # BBR-specific parameters
    parser.add_argument("--bbr-gamma", type=float, default=None, help="BBR penalty weight (overrides --gamma)")
    parser.add_argument("--bbr-kappa", type=float, default=None, help="BBR burst penalty coefficient")
    parser.add_argument("--bbr-xi", type=float, default=None, help="BBR delay penalty coefficient")
    parser.add_argument("--bbr-tau", type=float, default=None, help="BBR burst tolerance threshold")
    parser.add_argument("--bbr-mu", type=float, default=None, help="BBR window reduction step size")
    parser.add_argument("--bbr-lr", type=float, default=0.10, help="BBR learning rate")
    
    return parser.parse_args()


def build_params(args: argparse.Namespace) -> NetParams:
    from netparams import CubicParams, BbrParams
    
    # Build CUBIC parameters
    cubic_params = CubicParams(
        gamma=args.cubic_gamma if args.cubic_gamma is not None else args.gamma,
        kappa=args.cubic_kappa if args.cubic_kappa is not None else args.kappa,
        xi=args.cubic_xi if args.cubic_xi is not None else args.xi,
        tau=args.cubic_tau if args.cubic_tau is not None else args.tau,
        mu=args.cubic_mu if args.cubic_mu is not None else args.mu,
        lr=args.cubic_lr,
        alpha=args.cubic_alpha,
        queue_price=args.cubic_queue_price,
        burst_price=args.cubic_burst_price,
        burst_decrease_factor=args.cubic_burst_decrease,
    )
    
    # Build BBR parameters
    bbr_params = BbrParams(
        gamma=args.bbr_gamma if args.bbr_gamma is not None else args.gamma,
        kappa=args.bbr_kappa if args.bbr_kappa is not None else args.kappa,
        xi=args.bbr_xi if args.bbr_xi is not None else args.xi,
        tau=args.bbr_tau if args.bbr_tau is not None else args.tau,
        mu=args.bbr_mu if args.bbr_mu is not None else args.mu,
        lr=args.bbr_lr,
    )
    
    return NetParams(
        C=args.C,
        n_flows=args.flows,
        RTT_min=args.rtt / 1000.0,
        cubic_params=cubic_params,
        bbr_params=bbr_params,
    )


def main() -> None:
    args = parse_args()
    params = build_params(args)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\nTCP Congestion Control Simulator")
    print(
        f"Network: C={params.C} Mbps, {params.n_flows} flows, "
        f"RTT_min={params.RTT_min * 1000:.0f} ms, duration={args.duration} s"
    )
    print("\nCUBIC Parameters:")
    print(
        f"  gamma={params.cubic_params.gamma}, kappa={params.cubic_params.kappa}, "
        f"xi={params.cubic_params.xi}, tau={params.cubic_params.tau}, mu={params.cubic_params.mu}, "
        f"lr={params.cubic_params.lr}"
    )
    print("\nBBR Parameters:")
    print(
        f"  gamma={params.bbr_params.gamma}, kappa={params.bbr_params.kappa}, "
        f"xi={params.bbr_params.xi}, tau={params.bbr_params.tau}, mu={params.bbr_params.mu}, "
        f"lr={params.bbr_params.lr}"
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
