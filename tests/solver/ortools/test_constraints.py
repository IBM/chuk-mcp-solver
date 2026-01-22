"""Tests for advanced constraint types (cumulative, circuit, reservoir, no-overlap)."""

import pytest

from chuk_mcp_solver.models import (
    CircuitParams,
    Constraint,
    ConstraintKind,
    CumulativeParams,
    NoOverlapParams,
    Objective,
    ObjectiveSense,
    ReservoirParams,
    SearchConfig,
    SolveConstraintModelRequest,
    SolverMode,
    SolverStatus,
    Variable,
    VariableDomain,
    VariableDomainType,
)
from chuk_mcp_solver.solver.ortools import ORToolsSolver as ORToolsProvider


@pytest.mark.asyncio
async def test_cumulative_constraint_basic():
    """Test basic cumulative constraint for resource scheduling."""
    provider = ORToolsProvider()

    # Three tasks with different start times, durations, and demands
    # Resource capacity = 5
    request = SolveConstraintModelRequest(
        mode=SolverMode.SATISFY,
        variables=[
            Variable(
                id="start_1",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            ),
            Variable(
                id="start_2",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            ),
            Variable(
                id="start_3",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            ),
        ],
        constraints=[
            Constraint(
                id="resource_limit",
                kind=ConstraintKind.CUMULATIVE,
                params=CumulativeParams(
                    start_vars=["start_1", "start_2", "start_3"],
                    duration_vars=[2, 3, 2],  # constant durations
                    demand_vars=[3, 2, 4],  # constant demands
                    capacity=5,
                ),
            )
        ],
    )

    response = await provider.solve_constraint_model(request)
    assert response.status == SolverStatus.SATISFIED
    assert len(response.solutions) == 1


@pytest.mark.asyncio
async def test_cumulative_constraint_with_optimization():
    """Test cumulative constraint with makespan minimization."""
    provider = ORToolsProvider()

    # Minimize the completion time of all tasks
    request = SolveConstraintModelRequest(
        mode=SolverMode.OPTIMIZE,
        variables=[
            Variable(
                id="start_1",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=20),
            ),
            Variable(
                id="start_2",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=20),
            ),
            Variable(
                id="makespan",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=20),
            ),
        ],
        constraints=[
            Constraint(
                id="resource_limit",
                kind=ConstraintKind.CUMULATIVE,
                params=CumulativeParams(
                    start_vars=["start_1", "start_2"],
                    duration_vars=[5, 3],
                    demand_vars=[2, 3],
                    capacity=3,
                ),
            ),
            # makespan >= start_1 + duration_1
            Constraint(
                id="makespan_1",
                kind=ConstraintKind.LINEAR,
                params={
                    "terms": [
                        {"var": "makespan", "coef": 1},
                        {"var": "start_1", "coef": -1},
                    ],
                    "sense": ">=",
                    "rhs": 5,
                },
            ),
            # makespan >= start_2 + duration_2
            Constraint(
                id="makespan_2",
                kind=ConstraintKind.LINEAR,
                params={
                    "terms": [
                        {"var": "makespan", "coef": 1},
                        {"var": "start_2", "coef": -1},
                    ],
                    "sense": ">=",
                    "rhs": 3,
                },
            ),
        ],
        objective=Objective(
            sense=ObjectiveSense.MINIMIZE,
            terms=[{"var": "makespan", "coef": 1}],
        ),
    )

    response = await provider.solve_constraint_model(request)
    assert response.status == SolverStatus.OPTIMAL
    assert response.objective_value is not None
    assert response.objective_value >= 5  # At least one task duration


@pytest.mark.asyncio
async def test_circuit_constraint_tsp():
    """Test circuit constraint for a simple TSP-like problem."""
    provider = ORToolsProvider()

    # 4-node circuit problem
    # We need one binary variable per arc
    request = SolveConstraintModelRequest(
        mode=SolverMode.SATISFY,
        variables=[
            # Arcs from node 0
            Variable(
                id="arc_0_1",
                domain=VariableDomain(type=VariableDomainType.BOOL),
            ),
            Variable(
                id="arc_0_2",
                domain=VariableDomain(type=VariableDomainType.BOOL),
            ),
            Variable(
                id="arc_0_3",
                domain=VariableDomain(type=VariableDomainType.BOOL),
            ),
            # Arcs from node 1
            Variable(
                id="arc_1_0",
                domain=VariableDomain(type=VariableDomainType.BOOL),
            ),
            Variable(
                id="arc_1_2",
                domain=VariableDomain(type=VariableDomainType.BOOL),
            ),
            Variable(
                id="arc_1_3",
                domain=VariableDomain(type=VariableDomainType.BOOL),
            ),
            # Arcs from node 2
            Variable(
                id="arc_2_0",
                domain=VariableDomain(type=VariableDomainType.BOOL),
            ),
            Variable(
                id="arc_2_1",
                domain=VariableDomain(type=VariableDomainType.BOOL),
            ),
            Variable(
                id="arc_2_3",
                domain=VariableDomain(type=VariableDomainType.BOOL),
            ),
            # Arcs from node 3
            Variable(
                id="arc_3_0",
                domain=VariableDomain(type=VariableDomainType.BOOL),
            ),
            Variable(
                id="arc_3_1",
                domain=VariableDomain(type=VariableDomainType.BOOL),
            ),
            Variable(
                id="arc_3_2",
                domain=VariableDomain(type=VariableDomainType.BOOL),
            ),
        ],
        constraints=[
            Constraint(
                id="circuit",
                kind=ConstraintKind.CIRCUIT,
                params=CircuitParams(
                    arcs=[
                        (0, 1, "arc_0_1"),
                        (0, 2, "arc_0_2"),
                        (0, 3, "arc_0_3"),
                        (1, 0, "arc_1_0"),
                        (1, 2, "arc_1_2"),
                        (1, 3, "arc_1_3"),
                        (2, 0, "arc_2_0"),
                        (2, 1, "arc_2_1"),
                        (2, 3, "arc_2_3"),
                        (3, 0, "arc_3_0"),
                        (3, 1, "arc_3_1"),
                        (3, 2, "arc_3_2"),
                    ]
                ),
            )
        ],
    )

    response = await provider.solve_constraint_model(request)
    assert response.status == SolverStatus.SATISFIED
    assert len(response.solutions) == 1

    # Verify exactly 4 arcs are selected (one hamiltonian circuit)
    solution = response.solutions[0]
    selected_arcs = sum(1 for var in solution.variables if var.value == 1)
    assert selected_arcs == 4


@pytest.mark.asyncio
async def test_reservoir_constraint_inventory():
    """Test reservoir constraint for inventory management."""
    provider = ORToolsProvider()

    # Inventory problem: production and consumption events
    # Must keep inventory between min and max levels
    request = SolveConstraintModelRequest(
        mode=SolverMode.SATISFY,
        variables=[
            Variable(
                id="production_time_1",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            ),
            Variable(
                id="production_time_2",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            ),
            Variable(
                id="consumption_time_1",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            ),
            Variable(
                id="consumption_time_2",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            ),
        ],
        constraints=[
            Constraint(
                id="inventory_levels",
                kind=ConstraintKind.RESERVOIR,
                params=ReservoirParams(
                    time_vars=[
                        "production_time_1",
                        "production_time_2",
                        "consumption_time_1",
                        "consumption_time_2",
                    ],
                    level_changes=[
                        5,
                        5,
                        -3,
                        -3,
                    ],  # +5 production, -3 consumption
                    min_level=0,
                    max_level=10,
                ),
            )
        ],
    )

    response = await provider.solve_constraint_model(request)
    assert response.status == SolverStatus.SATISFIED
    assert len(response.solutions) == 1


@pytest.mark.asyncio
async def test_no_overlap_constraint_disjunctive():
    """Test no-overlap constraint for disjunctive scheduling."""
    provider = ORToolsProvider()

    # Three tasks that cannot overlap (share same resource)
    request = SolveConstraintModelRequest(
        mode=SolverMode.SATISFY,
        variables=[
            Variable(
                id="start_1",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=20),
            ),
            Variable(
                id="start_2",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=20),
            ),
            Variable(
                id="start_3",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=20),
            ),
        ],
        constraints=[
            Constraint(
                id="no_overlap",
                kind=ConstraintKind.NO_OVERLAP,
                params=NoOverlapParams(
                    start_vars=["start_1", "start_2", "start_3"],
                    duration_vars=[3, 4, 2],  # constant durations
                ),
            )
        ],
    )

    response = await provider.solve_constraint_model(request)
    assert response.status == SolverStatus.SATISFIED
    assert len(response.solutions) == 1

    # Verify tasks don't overlap
    solution = response.solutions[0]
    starts = {var.id: int(var.value) for var in solution.variables}
    durations = {"start_1": 3, "start_2": 4, "start_3": 2}

    # Create intervals
    intervals = [
        (starts[f"start_{i}"], starts[f"start_{i}"] + durations[f"start_{i}"]) for i in range(1, 4)
    ]

    # Check no overlaps
    for i in range(len(intervals)):
        for j in range(i + 1, len(intervals)):
            start_i, end_i = intervals[i]
            start_j, end_j = intervals[j]
            # No overlap: either i ends before j starts or j ends before i starts
            assert end_i <= start_j or end_j <= start_i


@pytest.mark.asyncio
async def test_no_overlap_with_optimization():
    """Test no-overlap constraint with makespan minimization."""
    provider = ORToolsProvider()

    request = SolveConstraintModelRequest(
        mode=SolverMode.OPTIMIZE,
        variables=[
            Variable(
                id="start_1",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=20),
            ),
            Variable(
                id="start_2",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=20),
            ),
            Variable(
                id="makespan",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=20),
            ),
        ],
        constraints=[
            Constraint(
                id="no_overlap",
                kind=ConstraintKind.NO_OVERLAP,
                params=NoOverlapParams(
                    start_vars=["start_1", "start_2"],
                    duration_vars=[5, 3],
                ),
            ),
            # makespan >= start_1 + 5
            Constraint(
                id="makespan_1",
                kind=ConstraintKind.LINEAR,
                params={
                    "terms": [
                        {"var": "makespan", "coef": 1},
                        {"var": "start_1", "coef": -1},
                    ],
                    "sense": ">=",
                    "rhs": 5,
                },
            ),
            # makespan >= start_2 + 3
            Constraint(
                id="makespan_2",
                kind=ConstraintKind.LINEAR,
                params={
                    "terms": [
                        {"var": "makespan", "coef": 1},
                        {"var": "start_2", "coef": -1},
                    ],
                    "sense": ">=",
                    "rhs": 3,
                },
            ),
        ],
        objective=Objective(
            sense=ObjectiveSense.MINIMIZE,
            terms=[{"var": "makespan", "coef": 1}],
        ),
    )

    response = await provider.solve_constraint_model(request)
    assert response.status == SolverStatus.OPTIMAL
    assert response.objective_value == 8  # Sequential: 5 + 3


@pytest.mark.asyncio
async def test_multi_objective_optimization():
    """Test multi-objective optimization with priority-based lexicographic ordering."""
    provider = ORToolsProvider()

    # Two objectives: primary (high priority) and secondary (low priority)
    request = SolveConstraintModelRequest(
        mode=SolverMode.OPTIMIZE,
        variables=[
            Variable(
                id="x",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            ),
            Variable(
                id="y",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            ),
        ],
        constraints=[
            Constraint(
                id="capacity",
                kind=ConstraintKind.LINEAR,
                params={
                    "terms": [{"var": "x", "coef": 1}, {"var": "y", "coef": 1}],
                    "sense": "<=",
                    "rhs": 10,
                },
            )
        ],
        objective=[
            # Primary: maximize x
            Objective(
                sense=ObjectiveSense.MAXIMIZE,
                terms=[{"var": "x", "coef": 1}],
                priority=2,  # Higher priority
                weight=1.0,
            ),
            # Secondary: maximize y
            Objective(
                sense=ObjectiveSense.MAXIMIZE,
                terms=[{"var": "y", "coef": 1}],
                priority=1,  # Lower priority
                weight=1.0,
            ),
        ],
    )

    response = await provider.solve_constraint_model(request)
    assert response.status == SolverStatus.OPTIMAL
    assert response.objective_value is not None

    # With weighted sum approach, should maximize both but prioritize x
    solution = response.solutions[0]
    x_value = next(v.value for v in solution.variables if v.id == "x")
    y_value = next(v.value for v in solution.variables if v.id == "y")

    # Since x has higher priority and both maximize, expect x to be maximized first
    assert x_value + y_value == 10  # Capacity constraint binding
    assert x_value == 10  # x should be maximized


@pytest.mark.asyncio
async def test_warm_start_solution():
    """Test warm-start solution hints."""
    provider = ORToolsProvider()

    request = SolveConstraintModelRequest(
        mode=SolverMode.OPTIMIZE,
        variables=[
            Variable(
                id="x",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            ),
            Variable(
                id="y",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            ),
        ],
        constraints=[
            Constraint(
                id="sum",
                kind=ConstraintKind.LINEAR,
                params={
                    "terms": [{"var": "x", "coef": 1}, {"var": "y", "coef": 1}],
                    "sense": "<=",
                    "rhs": 15,
                },
            )
        ],
        objective=Objective(
            sense=ObjectiveSense.MAXIMIZE,
            terms=[{"var": "x", "coef": 5}, {"var": "y", "coef": 3}],
        ),
        search=SearchConfig(
            warm_start_solution={"x": 8, "y": 5},  # Hint: x=8, y=5 (feasible but not optimal)
        ),
    )

    response = await provider.solve_constraint_model(request)
    assert response.status == SolverStatus.OPTIMAL
    # Should still find optimal solution even with non-optimal hint
    assert response.objective_value is not None


@pytest.mark.asyncio
async def test_search_config_workers_and_logging():
    """Test search configuration with workers and logging."""
    provider = ORToolsProvider()

    request = SolveConstraintModelRequest(
        mode=SolverMode.OPTIMIZE,
        variables=[
            Variable(
                id="x",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=100),
            ),
        ],
        constraints=[],
        objective=Objective(
            sense=ObjectiveSense.MAXIMIZE,
            terms=[{"var": "x", "coef": 1}],
        ),
        search=SearchConfig(
            num_search_workers=4,
            log_search_progress=False,  # Don't spam logs in tests
        ),
    )

    response = await provider.solve_constraint_model(request)
    assert response.status == SolverStatus.OPTIMAL
    assert response.objective_value == 100


@pytest.mark.asyncio
async def test_cumulative_params_validation():
    """Test CumulativeParams model validation."""
    # Valid params
    params = CumulativeParams(
        start_vars=["s1", "s2"],
        duration_vars=[1, 2],
        demand_vars=[3, 4],
        capacity=10,
    )
    assert params.capacity == 10

    # Negative capacity should fail
    with pytest.raises(ValueError):
        CumulativeParams(
            start_vars=["s1"],
            duration_vars=[1],
            demand_vars=[1],
            capacity=-1,
        )


@pytest.mark.asyncio
async def test_reservoir_params_validation():
    """Test ReservoirParams model validation."""
    # Valid params
    params = ReservoirParams(
        time_vars=["t1", "t2"],
        level_changes=[5, -3],
        min_level=0,
        max_level=10,
    )
    assert params.max_level == 10

    # Negative max_level should fail
    with pytest.raises(ValueError):
        ReservoirParams(
            time_vars=["t1"],
            level_changes=[1],
            min_level=0,
            max_level=-1,
        )
