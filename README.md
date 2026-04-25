"""
TCP Congestion Control Simulator
=================================
Implements and compares four algorithms from the paper:
  "Tentatively creating a TCP congestion control algorithm
   through convex optimization" (Udaya & Ellwood)

Algorithms:
  1. CUBIC        — NUM framework, alpha-fairness utility
  2. BBRv3        — BDP distance minimisation
  3. Burst-Aware CUBIC — CUBIC + convex penalty P(d_l, b_l)
  4. Burst-Aware BBR   — BBR  + convex penalty P(d_l, b_l)

Scenarios:
  steady    — constant background traffic
  burst     — sudden spike in offered load (t=25-35s)
  elephant  — persistent heavy flow joins at t=15s
  ramp      — offered load increases linearly

Usage:
  python main.py [--scenario SCENARIO] [--C C] [--flows N]
                 [--rtt RTT_MS] [--kappa K] [--xi X]
                 [--gamma G] [--duration T] [--dt DT]
                 [--output-dir RESULTS_DIR] [--output OUTPUT_PREFIX]

Results:
  Individual graphs are written to results/<scenario>/ by default.
  Running with --scenario all exports the full set of graphs for every scenario.
  The penalty surface image is written once to the top-level results directory.
"""
