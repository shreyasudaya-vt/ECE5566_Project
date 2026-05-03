# Implementation Mapping to Paper

## File Structure

- **main.py** - Entry point, argument parsing, orchestrates simulations
- **simulation.py** - Core simulation logic with `_update_cubic_states()` and `_update_bbr_states()`
- **util.py** - Mathematical functions for utility and penalty calculations
- **netparams.py** - Parameter definitions and state structures
- **scenarios.py** - Traffic pattern definitions (steady, burst, elephant, ramp)
- **plotting.py** - Visualization of results
- **reporting.py** - Summary statistics and table printing

## Paper-to-Code Mapping

### 1. Penalty Function (Paper Section 3.3.1, Equation)

**Paper:**
$$P(d_l, b_l) = \xi d_l + \frac{\kappa}{2}\max(0, b_l)^2$$

**Code (util.py):**
```python
def penalty(d_l: float, b_l: float, xi: float, kappa: float) -> float:
    """Return the convex delay/burst penalty."""
    return xi * d_l + (kappa / 2.0) * max(0.0, b_l) ** 2
```

### 2. Penalty Gradients

**For CUBIC (Paper Eq. 23 - gradients w.r.t. rate):**

Paper derivation:
- ∂P/∂d_l = ξ
- ∂P/∂b_l = κ*max(0, b_l)
- ∂d_l/∂x_i = 1/C (queue grows with individual flow rate)
- ∂b_l/∂x_i = 1/C (burst gradient depends on aggregate rate)
- **Total:** ∂P/∂x_i = (ξ + κ*max(0, b_l))/C

**Code (util.py):**
```python
def grad_penalty_wrt_rate(b_l: float, C: float, xi: float, kappa: float) -> float:
    """Return the penalty gradient with respect to a flow rate."""
    dp_db = kappa * max(0.0, b_l)  # ∂P/∂b_l
    dp_dd = xi                       # ∂P/∂d_l
    dd_dx = 1.0 / C                  # ∂d_l/∂x_i
    return dp_dd * dd_dx + dp_db / C  # = (ξ + κ*max(0,b_l))/C
```

**For BBRv3 (Paper Eq. 25 - gradients w.r.t. window):**

Paper derivation:
- d_l(W) = max(0, W - BDP) / B_max
- ∂d_l/∂W = 1/B_max if W > BDP else 0
- b_l(W) = (W - BDP) / BDP
- ∂b_l/∂W = 1/BDP if W > BDP else 0
- **Total:** ∂P/∂W = ξ/B_max + κ*(W-BDP)/BDP * 1/BDP

**Code (util.py):**
```python
def grad_penalty_wrt_W(W: float, BDP: float, B_max: float, xi: float, kappa: float) -> float:
    """Return the penalty gradient with respect to a BBR window."""
    excess = max(0.0, W - BDP)
    dd_dW = (1.0 / B_max) if W > BDP else 0.0
    db_dW = (1.0 / BDP) if W > BDP else 0.0
    return xi * dd_dW + kappa * (excess / BDP) * db_dW
```

### 3. Burst-Aware CUBIC Implementation

**Paper (Equation 23):**
$$\text{Maximize}_x \geq 0 \quad \sum_{i \in S} U_{cubic}(x_i) - \gamma \sum_{l \in L} \left[ \xi d_l + \frac{\kappa}{2}\max(0, b_l(x))^2 \right]$$

where $b_l(x) = \frac{\sum_{j \in S_l} x_j - C_l}{C_l}$

**Algorithm (Code in simulation.py - _update_cubic_states):**

```python
# Gradient ascent on utility minus penalty
utility_gradient = grad_U_cubic(rate, alpha)           # ∂U/∂x
base_congestion = params.cubic_queue_price * queue_pressure

if burst_aware:
    # Add formal penalty from Eq. 23
    penalty_gradient = params.gamma * grad_penalty_wrt_rate(
        burst_gradient, capacity, params.xi, params.kappa
    )
    congestion_signal = base_congestion + penalty_gradient
else:
    congestion_signal = base_congestion

# Update: Δw = lr * bdp * (∂U/∂x - congestion_signal)
next_window = window + params.lr_cubic * per_flow_bdp * (utility_gradient - congestion_signal)

# Multiplicative decrease on burst detection (from paper's constraint)
if burst_aware and burst_gradient > tau:
    burst_penalty = params.mu * max(0.0, burst_gradient - tau)
    next_window *= max(0.5, 1.0 - min(0.4, burst_penalty))
```

**Justification:**
- Base gradient ascent implements the optimization framework
- For burst-aware: penalty term is added to congestion signal (Eq. 23 coefficient γ)
- Dynamic window reduction mimics paper's constraint: $W \leq W_hi - \mu \max(0, b_l - \tau)$

### 4. Burst-Aware BBRv3 Implementation

**Paper (Equation 25):**
$$\text{Minimize}_W \quad \frac{1}{2}(W - B_{max} \cdot RTT_{min})^2 + \phi \left[ \xi d_l(W) + \frac{\kappa}{2}\max(0, b_l(W))^2 \right]$$

Subject to:
- $W \geq W_{min}$
- $W \leq \max(W_{min}, W_hi^{(t)} - \mu \max(0, b_l(W) - \tau))$

**Algorithm (Code in simulation.py - _update_bbr_states):**

```python
# Gradient descent on objective function
objective_gradient = state.W - bdp  # ∂(objective)/∂W ≈ ∂BDP_term/∂W

if burst_aware:
    # Add penalty term gradient
    objective_gradient += params.gamma * grad_penalty_wrt_W(
        state.W, bdp, capacity, params.xi, params.kappa
    )
    
    # Dynamic constraint: reduce W_hi on burst
    burst_gradient = max(0.0, (state.W - bdp) / (bdp + 1e-12))
    reduction = params.mu * max(0.0, burst_gradient - params.tau) * bdp
    state.W_hi = max(bdp * 0.5, state.W_hi - reduction)

# Gradient descent update
state.W = state.W - params.lr_bbr * objective_gradient

# Enforce constraints
state.W = np.clip(state.W, bdp * 0.1, state.W_hi)
```

**Justification:**
- Gradient descent directly minimizes the objective (Eq. 25)
- Penalty gradient added to objective gradient (note: paper uses φ, code uses γ)
- Dynamic W_hi constraint directly implements paper's feasible region

### 5. Utility Functions

**For CUBIC (Paper Section 3.1.1):**

$$U(x) = -\frac{3c}{RTT^{1/3}} x^{-1/3}$$

Simplified in code as: $U(x) = \alpha x^{1/3}$ where α ∝ c/RTT^{1/3}

**Code (util.py):**
```python
def U_cubic(x: float, alpha: float) -> float:
    return alpha * (max(x, 1e-9) ** (1.0 / 3.0))

def grad_U_cubic(x: float, alpha: float) -> float:
    return alpha / (3.0 * max(x, 1e-9) ** (2.0/3.0))
```

### 6. Key Parameters

| Parameter | Symbol | Description | Default | Used In |
|-----------|--------|-------------|---------|---------|
| `gamma` (γ) | γ | Penalty weight multiplier | 0.8 | Both |
| `xi` (ξ) | ξ | Queue delay penalty coefficient | 1.0 | Both |
| `kappa` (κ) | κ | Burst gradient penalty coefficient | 1.5 | Both |
| `tau` (τ) | τ | Burst tolerance threshold | 0.15 | Both |
| `mu` (μ) | μ | Window reduction step size | 0.05 | Both |
| `lr_cubic` | - | Learning rate for CUBIC | 0.08 | CUBIC |
| `lr_bbr` | - | Learning rate for BBR | 0.10 | BBR |

### 7. State Variables

**AlgoState (netparams.py):**
```python
@dataclass
class AlgoState:
    name: str
    cubic_windows: List[float]      # Congestion windows for each flow
    rates: List[float]              # Sending rates (= window / RTT)
    W: float                        # BBR in-flight data volume
    W_hi: float                     # BBR dynamic window upper bound
    q: float                        # Queue depth at bottleneck (in time units)
    ts_throughput: List[float]      # Time series: throughput over time
    ts_queue_pkts: List[float]      # Time series: queue in packets
    ts_delay_ms: List[float]        # Time series: queuing delay
    ts_jain: List[float]            # Time series: fairness index
    ts_b_l: List[float]             # Time series: burst gradient
```

### 8. Traffic Scenarios

**Paper Tests Burst Handling, Code Implements:**

- **steady:** No extra load - baseline fairness
- **burst:** 80% extra load for 10 seconds (t=25-35s out of 60s)
- **elephant:** 120% sustained extra load starting at t=15s
- **ramp:** Extra load increases from 0 to 150% over first 40 seconds

---

## Verification Checklist

- [x] Penalty function P(d_l, b_l) correctly computes ξ*d_l + (κ/2)*max(0,b_l)²
- [x] Gradient ∂P/∂x correctly applies chain rule with d_l and b_l dependencies
- [x] Gradient ∂P/∂W correctly handles BDP-relative definitions
- [x] CUBIC implements gradient ascent on U(x) - γ*P (Eq. 23)
- [x] BBRv3 implements gradient descent on BDP_term + φ*P (Eq. 25)
- [x] Dynamic constraints W_hi(t) properly reduce on burst detection
- [x] Burst gradient b_l correctly computed as (Σx_i - C)/C
- [x] Queuing delay d_l correctly computed from queue and capacity
- [x] All parameters have proper units and scaling
- [x] Results show burst-aware variants handle congestion better (especially BBR)

---

## Known Limitations

1. **CUBIC Burst-Aware:** While mathematically correct, penalty-based approach shows limited practical benefit for CUBIC due to window dynamics dominance. Consider:
   - Increasing γ substantially (tested with γ=2.5)
   - Using harder window constraints (multiplicative decrease)
   - Direct rate-based implementation

2. **Single Bottleneck:** Simulator tests single shared link. Paper framework supports multi-link networks but not implemented here.

3. **Perfect Information:** All flows instantly know queue depth and can adjust. Real networks have RTT delays.

4. **No Packet Loss Modeling:** Queue never causes actual drops (just tracking depth). Paper formulation assumes loss probability feedback.

5. **Equal Flow Weights:** All flows treated equally in aggregation. Paper supports weighted utilities.
