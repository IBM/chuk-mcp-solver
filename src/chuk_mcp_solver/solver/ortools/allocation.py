"""Budget allocation problem converters.

This module converts high-level budget allocation problems (knapsack) to/from CP-SAT models.
"""

from chuk_mcp_solver.models import (
    AllocationExplanation,
    AllocationObjective,
    ConstraintKind,
    ConstraintSense,
    ImplicationParams,
    LinearConstraintParams,
    LinearTerm,
    Objective,
    ObjectiveSense,
    SearchConfig,
    SolveBudgetAllocationRequest,
    SolveBudgetAllocationResponse,
    SolveConstraintModelRequest,
    SolveConstraintModelResponse,
    SolverMode,
    SolverStatus,
    Variable,
    VariableDomain,
    VariableDomainType,
)
from chuk_mcp_solver.models import Constraint as ConstraintModel


def convert_allocation_to_cpsat(
    request: SolveBudgetAllocationRequest,
) -> SolveConstraintModelRequest:
    """Convert high-level budget allocation problem to CP-SAT model.

    Creates a knapsack-style model with:
    - Binary selection variables for each item
    - Budget constraints (linear)
    - Dependency constraints (implications)
    - Conflict constraints (at most one)
    - Value/cost/count optimization objective

    Args:
        request: High-level allocation request

    Returns:
        CP-SAT constraint model request
    """
    variables = []
    constraints = []

    # Create binary selection variable for each item
    for item in request.items:
        variables.append(
            Variable(
                id=f"select_{item.id}",
                domain=VariableDomain(type=VariableDomainType.BOOL),
                metadata={
                    "item_id": item.id,
                    "cost": item.cost,
                    "value": item.value,
                },
            )
        )

    # Build budget constraints
    # For each budget, create linear constraint: sum(select_i * cost_i) <= limit
    for budget in request.budgets:
        terms = []

        for item in request.items:
            # Determine cost for this resource
            if budget.resource == "money" or budget.resource == "cost":
                # Use item's primary cost
                item_cost = item.cost
            elif budget.resource in item.resources_required:
                # Use resource-specific requirement
                item_cost = item.resources_required[budget.resource]
            else:
                # Fallback: if no resources_required specified, use primary cost field
                # This handles cases where LLMs send cost=weight and resource="weight"
                item_cost = item.cost

            if item_cost > 0:
                # Convert to integer (multiply by 100 for cents if money)
                coef = (
                    int(item_cost * 100) if budget.resource in ("money", "cost") else int(item_cost)
                )
                terms.append(LinearTerm(var=f"select_{item.id}", coef=coef))

        if terms:
            # Convert limit to same scale
            limit = (
                int(budget.limit * 100)
                if budget.resource in ("money", "cost")
                else int(budget.limit)
            )

            constraints.append(
                ConstraintModel(
                    id=f"budget_{budget.resource}",
                    kind=ConstraintKind.LINEAR,
                    params=LinearConstraintParams(
                        terms=terms,
                        sense=ConstraintSense.LESS_EQUAL,
                        rhs=limit,
                    ),
                    metadata={
                        "description": f"Budget constraint for {budget.resource} (limit: {budget.limit})"
                    },
                )
            )

    # Add dependency constraints
    # If item A depends on item B: select_A => select_B
    for item in request.items:
        for dep_id in item.dependencies:
            # Create the linear constraint that will be referenced by the implication
            then_constraint_id = f"then_select_{dep_id}_for_{item.id}"
            constraints.append(
                ConstraintModel(
                    id=then_constraint_id,
                    kind=ConstraintKind.LINEAR,
                    params=LinearConstraintParams(
                        terms=[LinearTerm(var=f"select_{dep_id}", coef=1)],
                        sense=ConstraintSense.EQUAL,
                        rhs=1,
                    ),
                    metadata={"description": f"Dependency target: select {dep_id}"},
                )
            )

            # Create the implication constraint that references the linear constraint
            constraints.append(
                ConstraintModel(
                    id=f"dependency_{item.id}_requires_{dep_id}",
                    kind=ConstraintKind.IMPLICATION,
                    params=ImplicationParams(
                        if_var=f"select_{item.id}",
                        then_constraint_id=then_constraint_id,  # Reference to the constraint above
                    ),
                    metadata={"description": f"Item {item.id} requires {dep_id}"},
                )
            )

    # Add conflict constraints
    # If item A conflicts with item B: select_A + select_B <= 1
    seen_conflicts = set()
    for item in request.items:
        for conflict_id in item.conflicts:
            # Avoid duplicate constraints (A conflicts B and B conflicts A)
            pair = tuple(sorted([item.id, conflict_id]))
            if pair not in seen_conflicts:
                seen_conflicts.add(pair)
                constraints.append(
                    ConstraintModel(
                        id=f"conflict_{item.id}_vs_{conflict_id}",
                        kind=ConstraintKind.LINEAR,
                        params=LinearConstraintParams(
                            terms=[
                                LinearTerm(var=f"select_{item.id}", coef=1),
                                LinearTerm(var=f"select_{conflict_id}", coef=1),
                            ],
                            sense=ConstraintSense.LESS_EQUAL,
                            rhs=1,
                        ),
                        metadata={"description": f"Items {item.id} and {conflict_id} conflict"},
                    )
                )

    # Add optional min/max value constraints
    if request.min_value_threshold is not None:
        value_terms = [
            LinearTerm(var=f"select_{item.id}", coef=int(item.value * 100))
            for item in request.items
        ]
        constraints.append(
            ConstraintModel(
                id="min_value_threshold",
                kind=ConstraintKind.LINEAR,
                params=LinearConstraintParams(
                    terms=value_terms,
                    sense=ConstraintSense.GREATER_EQUAL,
                    rhs=int(request.min_value_threshold * 100),
                ),
                metadata={"description": f"Minimum value threshold: {request.min_value_threshold}"},
            )
        )

    if request.max_cost_threshold is not None:
        cost_terms = [
            LinearTerm(var=f"select_{item.id}", coef=int(item.cost * 100)) for item in request.items
        ]
        constraints.append(
            ConstraintModel(
                id="max_cost_threshold",
                kind=ConstraintKind.LINEAR,
                params=LinearConstraintParams(
                    terms=cost_terms,
                    sense=ConstraintSense.LESS_EQUAL,
                    rhs=int(request.max_cost_threshold * 100),
                ),
                metadata={"description": f"Maximum cost threshold: {request.max_cost_threshold}"},
            )
        )

    # Add optional min/max item count constraints
    if request.min_items is not None:
        count_terms = [LinearTerm(var=f"select_{item.id}", coef=1) for item in request.items]
        constraints.append(
            ConstraintModel(
                id="min_items",
                kind=ConstraintKind.LINEAR,
                params=LinearConstraintParams(
                    terms=count_terms,
                    sense=ConstraintSense.GREATER_EQUAL,
                    rhs=request.min_items,
                ),
                metadata={"description": f"Minimum items: {request.min_items}"},
            )
        )

    if request.max_items is not None:
        count_terms = [LinearTerm(var=f"select_{item.id}", coef=1) for item in request.items]
        constraints.append(
            ConstraintModel(
                id="max_items",
                kind=ConstraintKind.LINEAR,
                params=LinearConstraintParams(
                    terms=count_terms,
                    sense=ConstraintSense.LESS_EQUAL,
                    rhs=request.max_items,
                ),
                metadata={"description": f"Maximum items: {request.max_items}"},
            )
        )

    # Create objective based on allocation objective
    objective = None
    if request.objective == AllocationObjective.MAXIMIZE_VALUE:
        # Maximize total value
        value_terms = [
            LinearTerm(var=f"select_{item.id}", coef=int(item.value * 100))
            for item in request.items
        ]
        objective = Objective(sense=ObjectiveSense.MAXIMIZE, terms=value_terms)
    elif request.objective == AllocationObjective.MAXIMIZE_COUNT:
        # Maximize number of selected items
        count_terms = [LinearTerm(var=f"select_{item.id}", coef=1) for item in request.items]
        objective = Objective(sense=ObjectiveSense.MAXIMIZE, terms=count_terms)
    elif request.objective == AllocationObjective.MINIMIZE_COST:
        # Minimize total cost
        cost_terms = [
            LinearTerm(var=f"select_{item.id}", coef=int(item.cost * 100)) for item in request.items
        ]
        objective = Objective(sense=ObjectiveSense.MINIMIZE, terms=cost_terms)

    return SolveConstraintModelRequest(
        mode=SolverMode.OPTIMIZE,
        variables=variables,
        constraints=constraints,
        objective=objective,
        search=SearchConfig(
            max_time_ms=request.max_time_ms,
            return_partial_solution=request.return_partial_solution,
        ),
    )


def convert_cpsat_to_allocation_response(
    cpsat_response: SolveConstraintModelResponse,
    original_request: SolveBudgetAllocationRequest,
) -> SolveBudgetAllocationResponse:
    """Convert CP-SAT solution back to allocation domain.

    Args:
        cpsat_response: CP-SAT solver response
        original_request: Original allocation request

    Returns:
        High-level allocation response
    """
    if cpsat_response.status in (
        SolverStatus.INFEASIBLE,
        SolverStatus.UNBOUNDED,
        SolverStatus.ERROR,
    ):
        # No solution
        return SolveBudgetAllocationResponse(
            status=cpsat_response.status,
            solve_time_ms=cpsat_response.solve_time_ms,
            explanation=AllocationExplanation(
                summary=cpsat_response.explanation.summary
                if cpsat_response.explanation
                else f"Problem is {cpsat_response.status.value}"
            ),
        )

    if cpsat_response.status == SolverStatus.TIMEOUT_NO_SOLUTION:
        return SolveBudgetAllocationResponse(
            status=cpsat_response.status,
            solve_time_ms=cpsat_response.solve_time_ms,
            explanation=AllocationExplanation(
                summary=cpsat_response.explanation.summary
                if cpsat_response.explanation
                else "Timeout with no solution found",
                recommendations=[
                    "Increase max_time_ms",
                    "Reduce number of items",
                    "Relax budget constraints",
                ],
            ),
        )

    if not cpsat_response.solutions:
        return SolveBudgetAllocationResponse(
            status=cpsat_response.status,
            solve_time_ms=cpsat_response.solve_time_ms,
            explanation=AllocationExplanation(summary="No solution available"),
        )

    # Extract solution
    solution = cpsat_response.solutions[0]

    # Determine which items are selected
    selected_items = []
    for var in solution.variables:
        if var.value == 1 and var.id.startswith("select_"):
            item_id = var.id.replace("select_", "")
            selected_items.append(item_id)

    # Calculate totals
    total_cost = 0.0
    total_value = 0.0
    resource_usage: dict[str, float] = {}

    item_map = {item.id: item for item in original_request.items}

    for item_id in selected_items:
        item = item_map[item_id]
        total_cost += item.cost
        total_value += item.value

        # Track resource usage
        for resource, amount in item.resources_required.items():
            resource_usage[resource] = resource_usage.get(resource, 0.0) + amount

    # Also track "cost" or "money" as a resource
    primary_resource = None
    for budget in original_request.budgets:
        if budget.resource in ("money", "cost"):
            primary_resource = budget.resource
            resource_usage[primary_resource] = total_cost
            break

    # Calculate resource slack
    resource_slack = {}
    for budget in original_request.budgets:
        used = resource_usage.get(budget.resource, 0.0)
        resource_slack[budget.resource] = budget.limit - used

    # Build explanation
    summary_parts = []
    if cpsat_response.status == SolverStatus.OPTIMAL:
        summary_parts.append(
            f"Optimal selection: {len(selected_items)} items with total value {total_value:.2f}"
        )
    elif cpsat_response.status in (SolverStatus.FEASIBLE, SolverStatus.TIMEOUT_BEST):
        summary_parts.append(
            f"Feasible selection: {len(selected_items)} items with total value {total_value:.2f}"
        )
        if cpsat_response.optimality_gap:
            summary_parts.append(f"(gap: {cpsat_response.optimality_gap:.2f}%)")
    else:
        summary_parts.append(f"Selection: {len(selected_items)} items")

    summary_parts.append(f"under budget of {total_cost:.2f}")

    # Identify binding constraints
    binding_constraints = []
    for budget in original_request.budgets:
        slack = resource_slack.get(budget.resource, 0.0)
        if slack < 0.01:  # Nearly fully utilized
            binding_constraints.append(f"Budget '{budget.resource}' fully utilized")
        elif slack > budget.limit * 0.2:  # More than 20% slack
            binding_constraints.append(
                f"Budget '{budget.resource}' has {slack:.2f} slack ({slack / budget.limit * 100:.1f}%)"
            )

    explanation = AllocationExplanation(
        summary=" ".join(summary_parts), binding_constraints=binding_constraints
    )

    return SolveBudgetAllocationResponse(
        status=cpsat_response.status,
        selected_items=selected_items,
        total_cost=total_cost,
        total_value=total_value,
        resource_usage=resource_usage,
        resource_slack=resource_slack,
        solve_time_ms=cpsat_response.solve_time_ms,
        optimality_gap=cpsat_response.optimality_gap,
        explanation=explanation,
    )
