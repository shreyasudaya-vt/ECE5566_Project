from dataclasses import dataclass, field
from typing import List


@dataclass
class AlgoState:
    """Mutable per-algorithm simulation state."""

    name: str
    cubic_windows: List[float] = field(default_factory=list)
    rates: List[float] = field(default_factory=list)
    W: float = 0.0
    W_hi: float = 0.0
    q: float = 0.0
    ts_throughput: List[float] = field(default_factory=list)
    ts_queue_pkts: List[float] = field(default_factory=list)
    ts_delay_ms: List[float] = field(default_factory=list)
    ts_jain: List[float] = field(default_factory=list)
    ts_b_l: List[float] = field(default_factory=list)


@dataclass
class NetParams:
    """Tunable network and penalty parameters."""

    C: float = 20.0
    n_flows: int = 3
    RTT_min: float = 0.02
    kappa: float = 1.5
    xi: float = 1.0
    gamma: float = 0.8
    tau: float = 0.15
    mu: float = 0.05
    lr_cubic: float = 0.08
    lr_bbr: float = 0.10
    alpha_cubic: float = 0.4
    cubic_queue_price: float = 0.14
    cubic_burst_price: float = 0.10
