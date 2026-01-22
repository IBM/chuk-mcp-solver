"""Constraint builders for OR-Tools CP-SAT solver.

This module contains all constraint-building logic, separating concerns
and making the code more maintainable and testable.
"""

from ortools.sat.python import cp_model

from chuk_mcp_solver.models import (
    AllDifferentParams,
    CircuitParams,
    Constraint,
    ConstraintKind,
    ConstraintSense,
    CumulativeParams,
    ElementParams,
    ImplicationParams,
    LinearConstraintParams,
    NoOverlapParams,
    ReservoirParams,
    TableParams,
)


def build_linear_constraint(
    model: cp_model.CpModel,
    constraint: Constraint,
    var_map: dict[str, cp_model.IntVar],
) -> None:
    """Build a linear constraint.

    Args:
        model: The CP-SAT model.
        constraint: The constraint definition.
        var_map: Mapping from variable ID to CP-SAT variable.
    """
    params: LinearConstraintParams = constraint.params  # type: ignore[assignment]

    # Build linear expression (sum of coefficient * variable)
    expr = sum(int(term.coef) * var_map[term.var] for term in params.terms)

    # Convert RHS to int (OR-Tools requires integer values)
    rhs_int = int(params.rhs)

    # Add constraint based on sense
    if params.sense == ConstraintSense.LESS_EQUAL:
        model.Add(expr <= rhs_int).WithName(constraint.id)  # type: ignore[attr-defined]
    elif params.sense == ConstraintSense.GREATER_EQUAL:
        model.Add(expr >= rhs_int).WithName(constraint.id)  # type: ignore[attr-defined]
    else:  # EQUAL
        model.Add(expr == rhs_int).WithName(constraint.id)  # type: ignore[attr-defined]


def build_all_different_constraint(
    model: cp_model.CpModel,
    constraint: Constraint,
    var_map: dict[str, cp_model.IntVar],
) -> None:
    """Build an all-different constraint.

    Args:
        model: The CP-SAT model.
        constraint: The constraint definition.
        var_map: Mapping from variable ID to CP-SAT variable.
    """
    params: AllDifferentParams = constraint.params  # type: ignore[assignment]
    vars_list = [var_map[var_id] for var_id in params.vars]
    model.AddAllDifferent(vars_list).WithName(constraint.id)  # type: ignore[attr-defined]


def build_element_constraint(
    model: cp_model.CpModel,
    constraint: Constraint,
    var_map: dict[str, cp_model.IntVar],
) -> None:
    """Build an element constraint: target = array[index].

    Args:
        model: The CP-SAT model.
        constraint: The constraint definition.
        var_map: Mapping from variable ID to CP-SAT variable.
    """
    params: ElementParams = constraint.params  # type: ignore[assignment]
    index_var = var_map[params.index_var]
    target_var = var_map[params.target_var]
    model.AddElement(index_var, params.array, target_var).WithName(constraint.id)  # type: ignore[attr-defined]


def build_table_constraint(
    model: cp_model.CpModel,
    constraint: Constraint,
    var_map: dict[str, cp_model.IntVar],
) -> None:
    """Build a table constraint: allowed tuples.

    Args:
        model: The CP-SAT model.
        constraint: The constraint definition.
        var_map: Mapping from variable ID to CP-SAT variable.
    """
    params: TableParams = constraint.params  # type: ignore[assignment]
    vars_list = [var_map[var_id] for var_id in params.vars]
    model.AddAllowedAssignments(vars_list, params.allowed_tuples).WithName(constraint.id)  # type: ignore[attr-defined]


def build_implication_constraint(
    model: cp_model.CpModel,
    constraint: Constraint,
    var_map: dict[str, cp_model.IntVar],
) -> None:
    """Build an implication constraint: if bool_var then nested_constraint.

    Args:
        model: The CP-SAT model.
        constraint: The constraint definition.
        var_map: Mapping from variable ID to CP-SAT variable.

    Raises:
        ValueError: If the nested constraint is not a linear constraint.
    """
    params: ImplicationParams = constraint.params  # type: ignore[assignment]

    # Get the boolean variable
    if_var = var_map[params.if_var]

    # For now, only support linear constraints in the "then" part
    if params.then.kind != ConstraintKind.LINEAR:
        raise ValueError(
            f"Implication only supports linear constraints in 'then' part, got: {params.then.kind}"
        )

    # For nested constraint, params.then.params might be a dict
    if isinstance(params.then.params, dict):
        linear_params = LinearConstraintParams(**params.then.params)
    else:
        linear_params = params.then.params  # type: ignore[assignment]

    expr = sum(int(term.coef) * var_map[term.var] for term in linear_params.terms)  # type: ignore[union-attr,misc]

    # Convert RHS to int
    rhs_int = int(linear_params.rhs)  # type: ignore[union-attr]

    # Add implication using OnlyEnforceIf
    # Note: WithName() must be called before OnlyEnforceIf()
    if linear_params.sense == ConstraintSense.LESS_EQUAL:  # type: ignore[union-attr]
        model.Add(expr <= rhs_int).WithName(constraint.id).OnlyEnforceIf(if_var)  # type: ignore[attr-defined]
    elif linear_params.sense == ConstraintSense.GREATER_EQUAL:  # type: ignore[union-attr]
        model.Add(expr >= rhs_int).WithName(constraint.id).OnlyEnforceIf(if_var)  # type: ignore[attr-defined]
    else:  # EQUAL
        model.Add(expr == rhs_int).WithName(constraint.id).OnlyEnforceIf(if_var)  # type: ignore[attr-defined]


def build_cumulative_constraint(
    model: cp_model.CpModel,
    constraint: Constraint,
    var_map: dict[str, cp_model.IntVar],
) -> None:
    """Build a cumulative constraint for resource scheduling.

    Args:
        model: The CP-SAT model.
        constraint: The constraint definition.
        var_map: Mapping from variable ID to CP-SAT variable.
    """
    params: CumulativeParams = constraint.params  # type: ignore[assignment]

    # Get start variables
    start_vars = [var_map[var_id] for var_id in params.start_vars]

    # Process durations (can be variables or constants)
    if isinstance(params.duration_vars[0], str):
        duration_vars = [var_map[var_id] for var_id in params.duration_vars]  # type: ignore[misc,index]
    else:
        duration_vars = params.duration_vars  # type: ignore[assignment]

    # Process demands (can be variables or constants)
    if isinstance(params.demand_vars[0], str):
        demand_vars = [var_map[var_id] for var_id in params.demand_vars]  # type: ignore[misc,index]
    else:
        demand_vars = params.demand_vars  # type: ignore[assignment]

    # Create interval variables for cumulative constraint
    intervals = []
    for i, (start, duration) in enumerate(zip(start_vars, duration_vars, strict=True)):
        interval = model.NewIntervalVar(  # type: ignore[attr-defined]
            start, duration, start + duration, f"{constraint.id}_interval_{i}"
        )
        intervals.append(interval)

    # Add cumulative constraint
    model.AddCumulative(intervals, demand_vars, params.capacity).WithName(constraint.id)  # type: ignore[attr-defined]


def build_circuit_constraint(
    model: cp_model.CpModel,
    constraint: Constraint,
    var_map: dict[str, cp_model.IntVar],
) -> None:
    """Build a circuit constraint for routing problems.

    Args:
        model: The CP-SAT model.
        constraint: The constraint definition.
        var_map: Mapping from variable ID to CP-SAT variable.
    """
    params: CircuitParams = constraint.params  # type: ignore[assignment]

    # Convert arcs from (from, to, var_id) to (from, to, literal)
    arcs = []
    for from_node, to_node, var_id in params.arcs:
        literal = var_map[var_id]
        arcs.append((from_node, to_node, literal))

    model.AddCircuit(arcs).WithName(constraint.id)  # type: ignore[attr-defined]


def build_reservoir_constraint(
    model: cp_model.CpModel,
    constraint: Constraint,
    var_map: dict[str, cp_model.IntVar],
) -> None:
    """Build a reservoir constraint for inventory management.

    Args:
        model: The CP-SAT model.
        constraint: The constraint definition.
        var_map: Mapping from variable ID to CP-SAT variable.
    """
    params: ReservoirParams = constraint.params  # type: ignore[assignment]

    # Get time variables
    time_vars = [var_map[var_id] for var_id in params.time_vars]

    # Add reservoir constraint
    model.AddReservoirConstraint(  # type: ignore[attr-defined]
        time_vars,
        params.level_changes,
        params.min_level,
        params.max_level,
    ).WithName(constraint.id)


def build_no_overlap_constraint(
    model: cp_model.CpModel,
    constraint: Constraint,
    var_map: dict[str, cp_model.IntVar],
) -> None:
    """Build a no-overlap constraint for disjunctive scheduling.

    Args:
        model: The CP-SAT model.
        constraint: The constraint definition.
        var_map: Mapping from variable ID to CP-SAT variable.
    """
    params: NoOverlapParams = constraint.params  # type: ignore[assignment]

    # Get start variables
    start_vars = [var_map[var_id] for var_id in params.start_vars]

    # Process durations (can be variables or constants)
    if isinstance(params.duration_vars[0], str):
        duration_vars = [var_map[var_id] for var_id in params.duration_vars]  # type: ignore[misc,index]
    else:
        duration_vars = params.duration_vars  # type: ignore[assignment]

    # Create interval variables
    intervals = []
    for i, (start, duration) in enumerate(zip(start_vars, duration_vars, strict=True)):
        interval = model.NewIntervalVar(  # type: ignore[attr-defined]
            start, duration, start + duration, f"{constraint.id}_interval_{i}"
        )
        intervals.append(interval)

    # Add no-overlap constraint
    model.AddNoOverlap(intervals).WithName(constraint.id)  # type: ignore[attr-defined]


# Constraint builder dispatch map
CONSTRAINT_BUILDERS = {
    ConstraintKind.LINEAR: build_linear_constraint,
    ConstraintKind.ALL_DIFFERENT: build_all_different_constraint,
    ConstraintKind.ELEMENT: build_element_constraint,
    ConstraintKind.TABLE: build_table_constraint,
    ConstraintKind.IMPLICATION: build_implication_constraint,
    ConstraintKind.CUMULATIVE: build_cumulative_constraint,
    ConstraintKind.CIRCUIT: build_circuit_constraint,
    ConstraintKind.RESERVOIR: build_reservoir_constraint,
    ConstraintKind.NO_OVERLAP: build_no_overlap_constraint,
}


def build_constraint(
    model: cp_model.CpModel,
    constraint: Constraint,
    var_map: dict[str, cp_model.IntVar],
) -> None:
    """Build a single constraint using the appropriate builder.

    Args:
        model: The CP-SAT model.
        constraint: The constraint definition.
        var_map: Mapping from variable ID to CP-SAT variable.

    Raises:
        ValueError: If constraint kind is not supported.
    """
    builder = CONSTRAINT_BUILDERS.get(constraint.kind)
    if builder is None:
        raise ValueError(f"Unsupported constraint kind: {constraint.kind}")

    builder(model, constraint, var_map)
