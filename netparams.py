from dataclasses import dataclass, field
from typing import List, Optional


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
class CubicParams:
    """CUBIC-specific tunable parameters."""

    gamma: float = 0.8  # Penalty weight multiplier
    kappa: float = 1.5  # Burst gradient penalty coefficient
    xi: float = 1.0  # Queue delay penalty coefficient
    tau: float = 0.15  # Burst tolerance threshold
    mu: float = 0.05  # Window reduction step size
    lr: float = 0.08  # Learning rate
    alpha: float = 0.4  # Utility scaling factor
    queue_price: float = 0.14  # Base queue congestion price
    burst_price: float = 0.10  # Base burst congestion price
    enable_burst_multiplicative_decrease: bool = True  # Apply multiplicative window reduction on burst
    burst_decrease_factor: float = 0.4  # Max multiplicative decrease (0-1)


@dataclass
class BbrParams:
    """BBR-specific tunable parameters."""

    gamma: float = 0.8  # Penalty weight multiplier
    kappa: float = 1.5  # Burst gradient penalty coefficient
    xi: float = 1.0  # Queue delay penalty coefficient
    tau: float = 0.15  # Burst tolerance threshold
    mu: float = 0.05  # Window reduction step size
    lr: float = 0.10  # Learning rate
    pacing_margin: float = 0.01  # Pacing margin (1% below capacity)


@dataclass
class NetParams:
    """Network and algorithm-specific parameters."""

    # Network parameters
    C: float = 20.0  # Link capacity in Mbps
    n_flows: int = 3  # Number of flows per algorithm
    RTT_min: float = 0.02  # Base RTT in seconds
    
    # Algorithm-specific parameters
    cubic_params: CubicParams = field(default_factory=CubicParams)
    bbr_params: BbrParams = field(default_factory=BbrParams)
    
    # Shared legacy parameters (for backward compatibility)
    kappa: Optional[float] = None  # Will override cubic/bbr kappa if set
    xi: Optional[float] = None  # Will override cubic/bbr xi if set
    gamma: Optional[float] = None  # Will override cubic/bbr gamma if set
    tau: Optional[float] = None  # Will override cubic/bbr tau if set
    mu: Optional[float] = None  # Will override cubic/bbr mu if set
    lr_cubic: Optional[float] = None  # Will override cubic lr if set
    lr_bbr: Optional[float] = None  # Will override bbr lr if set
    alpha_cubic: Optional[float] = None  # Will override cubic alpha if set
    cubic_queue_price: Optional[float] = None  # Will override cubic queue_price if set
    cubic_burst_price: Optional[float] = None  # Will override cubic burst_price if set
    
    def __post_init__(self):
        """Apply legacy parameters as overrides if provided."""
        if self.gamma is not None:
            self.cubic_params.gamma = self.gamma
            self.bbr_params.gamma = self.gamma
        if self.kappa is not None:
            self.cubic_params.kappa = self.kappa
            self.bbr_params.kappa = self.kappa
        if self.xi is not None:
            self.cubic_params.xi = self.xi
            self.bbr_params.xi = self.xi
        if self.tau is not None:
            self.cubic_params.tau = self.tau
            self.bbr_params.tau = self.tau
        if self.mu is not None:
            self.cubic_params.mu = self.mu
            self.bbr_params.mu = self.mu
        if self.lr_cubic is not None:
            self.cubic_params.lr = self.lr_cubic
        if self.lr_bbr is not None:
            self.bbr_params.lr = self.lr_bbr
        if self.alpha_cubic is not None:
            self.cubic_params.alpha = self.alpha_cubic
        if self.cubic_queue_price is not None:
            self.cubic_params.queue_price = self.cubic_queue_price
        if self.cubic_burst_price is not None:
            self.cubic_params.burst_price = self.cubic_burst_price
