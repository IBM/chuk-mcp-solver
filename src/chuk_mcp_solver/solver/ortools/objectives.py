"""Objective and solver configuration for OR-Tools CP-SAT solver.

This module handles objective function building and solver parameter configuration.
"""

from ortools.sat.python import cp_model

from chuk_mcp_solver.models import (
    Objective,
    ObjectiveSense,
    SearchStrategy,
    SolveConstraintModelRequest,
)


def build_objective(
    model: cp_model.CpModel,
    objective: Objective | list[Objective],
    var_map: dict[str, cp_model.IntVar],
) -> None:
    """Build the objective function.

    Supports both single and multi-objective optimization.
    For multi-objective, uses lexicographic ordering by priority.

    Args:
        model: The CP-SAT model.
        objective: Single objective or list of objectives.
        var_map: Mapping from variable ID to CP-SAT variable.
    """
    # Handle single objective
    if isinstance(objective, Objective):
        expr = sum(int(term.coef) * var_map[term.var] for term in objective.terms)
        if objective.sense == ObjectiveSense.MINIMIZE:
            model.Minimize(expr)  # type: ignore[attr-defined]
        else:  # MAXIMIZE
            model.Maximize(expr)  # type: ignore[attr-defined]
        return

    # Handle multi-objective
    # Sort by priority (higher = more important)
    sorted_objectives = sorted(objective, key=lambda o: o.priority, reverse=True)

    # For OR-Tools CP-SAT, we use weighted sum approach for multi-objective
    # since lexicographic is not directly supported
    # Higher priority objectives get much larger weights
    total_expr = 0
    weight_multiplier = 1000000  # Scale factor between priority levels

    for obj in sorted_objectives:
        expr = sum(int(term.coef) * var_map[term.var] for term in obj.terms)
        # Apply priority scaling and user-defined weight
        scaled_weight = (weight_multiplier**obj.priority) * obj.weight
        total_expr += scaled_weight * expr

    # Use the sense of the highest priority objective
    if sorted_objectives[0].sense == ObjectiveSense.MINIMIZE:
        model.Minimize(total_expr)  # type: ignore[attr-defined]
    else:
        model.Maximize(total_expr)  # type: ignore[attr-defined]


def configure_solver(solver: cp_model.CpSolver, request: SolveConstraintModelRequest) -> None:
    """Configure solver parameters.

    Args:
        solver: The CP-SAT solver.
        request: The request containing search configuration.
    """
    if not request.search:
        return

    # Time limit
    if request.search.max_time_ms:
        solver.parameters.max_time_in_seconds = request.search.max_time_ms / 1000.0

    # Number of parallel search workers
    if request.search.num_search_workers:
        solver.parameters.num_search_workers = request.search.num_search_workers

    # Search progress logging
    if request.search.log_search_progress:
        solver.parameters.log_search_progress = True

    # Random seed for deterministic solving
    if request.search.random_seed is not None:
        solver.parameters.random_seed = request.search.random_seed

    # Search strategy
    if request.search.strategy != SearchStrategy.AUTO:
        # Map our strategy enum to OR-Tools parameters
        if request.search.strategy == SearchStrategy.FIRST_FAIL:
            solver.parameters.search_branching = cp_model.FIXED_SEARCH
            # Note: Variable order is determined by the order variables are added to the model
        elif request.search.strategy == SearchStrategy.RANDOM:
            solver.parameters.randomize_search = True

    # Note: Warm start solution hints are handled separately in solve_constraint_model
    # via solver.AddHint() after model construction
