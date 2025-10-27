# CSI-4130 Final Project — MCTS Playground with UCT/PUCT

## Problem Statement
Game trees explode combinatorially, making exhaustive search impractical. I will build a Monte Carlo Tree Search (MCTS) playground to study how exploration–exploitation trade-offs (UCT vs. PUCT) affect decision quality in large search spaces.

## Proposed Method
Implement MCTS from scratch (selection/expansion/simulation/backpropagation) with pluggable policies:
- UCT and PUCT selection; epsilon-greedy rollouts vs. heuristic rollouts.
- Domains: 2048 and Connect-Four (deterministic), plus a stochastic gridworld.
- Metrics: win rate vs. time, nodes expanded, depth, regret.
- Visualizations: UCB curves, visit counts, and rollout outcome histograms.

## Data Sources
Self-contained environments (no external data). Optional: open Connect-Four benchmarks.

## Milestones (Draft)
- Week 1: Minimal MCTS + 2048 adapter, CLI demo
- Week 2: Add PUCT + rollout variants + logging
- Week 3: Experiments & plots; ablate C value and rollout depth
- Final: Report + slides + live demo

## Tech
Python, NumPy, matplotlib; optional Streamlit UI.
