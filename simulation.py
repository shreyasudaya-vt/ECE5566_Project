from typing import Dict, Tuple

import numpy as np

from netparams import AlgoState, NetParams
from scenarios import extra_offered_load
from util import grad_U_cubic, grad_penalty_wrt_W, grad_penalty_wrt_rate


def jain_index(rates: list[float]) -> float:
    """Compute Jain's fairness index."""

    n_rates = len(rates)
    if n_rates == 0:
        return 1.0
    sum_rates = sum(rates)
    sum_squares = sum(rate * rate for rate in rates)
    return (sum_rates * sum_rates) / (n_rates * sum_squares + 1e-12)


def _init_cubic_state(name: str, params: NetParams) -> AlgoState:
    state = AlgoState(name=name)
    initial_rate = params.C / params.n_flows * 0.75
    state.cubic_windows = [initial_rate * params.RTT_min] * params.n_flows
    state.rates = [initial_rate] * params.n_flows
    return state


def _init_bbr_state(name: str, bdp: float) -> AlgoState:
    state = AlgoState(name=name)
    state.W = bdp * 0.5
    state.W_hi = bdp * 3.0
    return state


def _build_states(params: NetParams, bdp: float) -> Dict[str, AlgoState]:
    return {
        "CUBIC": _init_cubic_state("CUBIC", params),
        "BBRv3": _init_bbr_state("BBRv3", bdp),
        "Burst-Aware CUBIC": _init_cubic_state("Burst-Aware CUBIC", params),
        "Burst-Aware BBR": _init_bbr_state("Burst-Aware BBR", bdp),
    }


def _window_to_rates(windows: list[float], rtt: float) -> list[float]:
    """Convert congestion windows to sending rates."""

    return [window / max(rtt, 1e-9) for window in windows]


def _update_cubic_states(
    states: Dict[str, AlgoState],
    params: NetParams,
    extra_load: float,
    capacity: float,
    alpha: float,
    dt: float,
) -> None:
    bdp = capacity * params.RTT_min
    per_flow_bdp = bdp / params.n_flows
    cp = params.cubic_params  # Shorthand for CUBIC parameters

    for name, burst_aware in (("CUBIC", False), ("Burst-Aware CUBIC", True)):
        state = states[name]
        current_rtt = params.RTT_min + state.q / capacity
        state.rates = _window_to_rates(state.cubic_windows, current_rtt)
        total_rate = sum(state.rates) + extra_load
        state.q = max(0.0, state.q + dt * (total_rate - capacity))
        queuing_delay = state.q / capacity
        effective_rtt = params.RTT_min + queuing_delay
        burst_gradient = (total_rate - capacity) / capacity

        next_windows = []
        queue_pressure = min(2.0, queuing_delay / max(params.RTT_min, 1e-9))
        
        for window, rate in zip(state.cubic_windows, state.rates):
            # Gradient of CUBIC utility function: ∂U/∂x = α/(3*x^(2/3))
            utility_gradient = grad_U_cubic(rate, alpha)
            normalized_utility = utility_gradient / max(effective_rtt, 1e-9)
            
            # Base congestion signal (queue-based, used for all variants)
            base_congestion = cp.queue_price * queue_pressure
            
            if burst_aware:
                # Burst-aware: Add formal penalty gradient on top of base signal (Eq. 23)
                # P(d_l, b_l) = ξ*d_l + (κ/2)*max(0, b_l)^2
                # Apply: γ * ∂P/∂x, but scale up for CUBIC (penalty gradients are very small)
                penalty_gradient = cp.gamma * grad_penalty_wrt_rate(
                    burst_gradient, capacity, cp.xi, cp.kappa
                ) * 50.0  # Balanced scaling for CUBIC
                congestion_signal = base_congestion + penalty_gradient
            else:
                # Standard CUBIC: just use base queue pressure signal
                congestion_signal = base_congestion
            
            # Window update: Δw = lr * bdp * (utility_gradient - congestion_signal)
            next_window = window + cp.lr * per_flow_bdp * (normalized_utility - congestion_signal)

            # For burst-aware: apply multiplicative decrease when burst gradient detected
            if burst_aware and cp.enable_burst_multiplicative_decrease and burst_gradient > cp.tau:
                # Window reduction proportional to burst intensity (from paper's dynamic constraint)
                burst_penalty = cp.mu * max(0.0, burst_gradient - cp.tau)
                next_window *= max(0.5, 1.0 - min(cp.burst_decrease_factor, burst_penalty))

            # Enforce window bounds
            min_window = per_flow_bdp * 0.25
            max_window = per_flow_bdp * 2.1
            next_windows.append(float(np.clip(next_window, min_window, max_window)))

        state.cubic_windows = next_windows
        state.rates = _window_to_rates(state.cubic_windows, effective_rtt)

        throughput = min(sum(state.rates), capacity)
        state.ts_throughput.append(throughput)
        state.ts_queue_pkts.append(max(0.0, state.q * 1000.0))
        state.ts_delay_ms.append(max(0.0, queuing_delay * 1000.0))
        state.ts_jain.append(jain_index(state.rates))
        state.ts_b_l.append(burst_gradient)


def _update_bbr_states(
    states: Dict[str, AlgoState],
    params: NetParams,
    extra_load: float,
    capacity: float,
    bdp: float,
    rtt: float,
    dt: float,
) -> None:
    bp = params.bbr_params  # Shorthand for BBR parameters
    
    for name, burst_aware in (("BBRv3", False), ("Burst-Aware BBR", True)):
        state = states[name]
        objective_gradient = state.W - bdp

        if burst_aware:
            objective_gradient += bp.gamma * grad_penalty_wrt_W(
                state.W,
                bdp,
                capacity,
                bp.xi,
                bp.kappa,
            )
            burst_gradient = max(0.0, (state.W - bdp) / (bdp + 1e-12))
            reduction = bp.mu * max(0.0, burst_gradient - bp.tau) * bdp
            state.W_hi = max(bdp * 0.5, state.W_hi - reduction)
            state.W_hi = min(state.W_hi + 0.01 * bdp, 3.0 * bdp)

        state.W = state.W - bp.lr * objective_gradient + extra_load * dt * 0.08
        window_low = bdp * 0.1
        window_high = state.W_hi if burst_aware else 3.0 * bdp
        state.W = float(np.clip(state.W, window_low, window_high))

        throughput = min(state.W / rtt, capacity)
        excess_window = max(0.0, state.W - bdp)
        queuing_delay = excess_window / capacity
        queue_packets = excess_window * 1000.0 / (bdp + 1e-12)
        burst_gradient = excess_window / (bdp + 1e-12)

        state.ts_throughput.append(throughput)
        state.ts_queue_pkts.append(max(0.0, queue_packets))
        state.ts_delay_ms.append(max(0.0, queuing_delay * 1000.0))
        state.ts_jain.append(1.0)
        state.ts_b_l.append(burst_gradient)


def simulate(
    params: NetParams,
    scenario: str,
    duration: float = 60.0,
    dt: float = 0.5,
) -> Tuple[np.ndarray, Dict[str, AlgoState]]:
    """Run the congestion-control simulation."""

    capacity = params.C
    rtt = params.RTT_min
    bdp = capacity * rtt
    alpha = params.cubic_params.alpha / (rtt ** 0.25)
    steps = int(duration / dt)
    times = np.linspace(0.0, duration, steps, endpoint=False)
    states = _build_states(params, bdp)

    for t in times:
        extra_load = extra_offered_load(t, scenario, capacity)
        _update_cubic_states(states, params, extra_load, capacity, alpha, dt)
        _update_bbr_states(states, params, extra_load, capacity, bdp, rtt, dt)

    return times, states
