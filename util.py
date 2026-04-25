def U_cubic(x: float, alpha: float) -> float:
    """Return the CUBIC-style utility value."""

    return alpha * (max(x, 1e-9) ** (1.0 / 3.0))


def grad_U_cubic(x: float, alpha: float) -> float:
    """Return the utility gradient with respect to rate."""

    return alpha / (3.0 * max(x, 1e-9) ** (1.0 / 3.0))


def penalty(d_l: float, b_l: float, xi: float, kappa: float) -> float:
    """Return the convex delay/burst penalty."""

    return xi * d_l + (kappa / 2.0) * max(0.0, b_l) ** 2


def grad_penalty_wrt_rate(b_l: float, C: float, xi: float, kappa: float) -> float:
    """Return the penalty gradient with respect to a flow rate."""

    dp_db = kappa * max(0.0, b_l)
    dp_dd = xi
    dd_dx = 1.0 / C
    return dp_dd * dd_dx + dp_db / C


def grad_penalty_wrt_W(W: float, BDP: float, B_max: float, xi: float, kappa: float) -> float:
    """Return the penalty gradient with respect to a BBR window."""

    excess = max(0.0, W - BDP)
    dd_dW = (1.0 / B_max) if W > BDP else 0.0
    db_dW = (1.0 / BDP) if W > BDP else 0.0
    return xi * dd_dW + kappa * (excess / BDP) * db_dW
