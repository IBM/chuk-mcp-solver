"""Tests for OR-Tools solver implementation."""

import pytest
from chuk_mcp_solver.models import SolveConstraintModelRequest, SolverStatus
from chuk_mcp_solver.solver.ortools import ORToolsSolver

# ============================================================================
# OR-Tools Provider Tests - Simple Cases
# ============================================================================


@pytest.mark.asyncio
async def test_simple_satisfy():
    """Test simple satisfaction problem."""
    request = SolveConstraintModelRequest(
        mode="satisfy",
        variables=[{"id": "x", "domain": {"type": "integer", "lower": 0, "upper": 10}}],
        constraints=[
            {
                "id": "bound",
                "kind": "linear",
                "params": {"terms": [{"var": "x", "coef": 1}], "sense": ">=", "rhs": 5},
            }
        ],
    )

    solver = ORToolsSolver()
    response = await solver.solve_constraint_model(request)

    assert response.status == SolverStatus.SATISFIED
    assert len(response.solutions) == 1
    assert len(response.solutions[0].variables) == 1
    assert response.solutions[0].variables[0].value >= 5


@pytest.mark.asyncio
async def test_simple_optimize():
    """Test simple optimization problem."""
    request = SolveConstraintModelRequest(
        mode="optimize",
        variables=[{"id": "x", "domain": {"type": "integer", "lower": 0, "upper": 10}}],
        constraints=[],
        objective={"sense": "min", "terms": [{"var": "x", "coef": 1}]},
    )

    solver = ORToolsSolver()
    response = await solver.solve_constraint_model(request)

    assert response.status == SolverStatus.OPTIMAL
    assert response.objective_value == 0.0
    assert response.solutions[0].variables[0].value == 0


@pytest.mark.asyncio
async def test_knapsack_problem(simple_knapsack_request):
    """Test knapsack optimization."""
    request = SolveConstraintModelRequest(**simple_knapsack_request)

    solver = ORToolsSolver()
    response = await solver.solve_constraint_model(request)

    assert response.status == SolverStatus.OPTIMAL
    assert response.objective_value is not None
    # Should take item_2 (weight 5, value 15) and item_3 (weight 2, value 8)
    # Total weight: 7 <= 7, Total value: 23
    assert response.objective_value == 23.0


@pytest.mark.asyncio
async def test_all_different_constraint(simple_sudoku_cell_request):
    """Test all_different constraint."""
    request = SolveConstraintModelRequest(**simple_sudoku_cell_request)

    solver = ORToolsSolver()
    response = await solver.solve_constraint_model(request)

    assert response.status == SolverStatus.SATISFIED

    # Extract values
    values = {var.id: int(var.value) for var in response.solutions[0].variables}

    # cell_0 should be 1 (fixed)
    assert values["cell_0"] == 1

    # All should be different and in range [1, 4]
    assert len(set(values.values())) == 4
    assert all(1 <= v <= 4 for v in values.values())


@pytest.mark.asyncio
async def test_infeasible_problem(infeasible_request):
    """Test infeasible problem."""
    request = SolveConstraintModelRequest(**infeasible_request)

    solver = ORToolsSolver()
    response = await solver.solve_constraint_model(request)

    assert response.status == SolverStatus.INFEASIBLE
    assert len(response.solutions) == 0
    assert response.explanation is not None
    assert "infeasible" in response.explanation.summary.lower()


# ============================================================================
# Advanced Constraint Tests
# ============================================================================


@pytest.mark.asyncio
async def test_element_constraint():
    """Test element constraint."""
    request = SolveConstraintModelRequest(
        mode="satisfy",
        variables=[
            {"id": "index", "domain": {"type": "integer", "lower": 0, "upper": 2}},
            {"id": "result", "domain": {"type": "integer", "lower": 0, "upper": 100}},
        ],
        constraints=[
            {
                "id": "elem",
                "kind": "element",
                "params": {"index_var": "index", "array": [10, 20, 30], "target_var": "result"},
            },
            {
                "id": "index_fixed",
                "kind": "linear",
                "params": {"terms": [{"var": "index", "coef": 1}], "sense": "==", "rhs": 1},
            },
        ],
    )

    solver = ORToolsSolver()
    response = await solver.solve_constraint_model(request)

    assert response.status == SolverStatus.SATISFIED
    values = {var.id: int(var.value) for var in response.solutions[0].variables}
    assert values["index"] == 1
    assert values["result"] == 20  # array[1]


@pytest.mark.asyncio
async def test_table_constraint():
    """Test table constraint."""
    request = SolveConstraintModelRequest(
        mode="satisfy",
        variables=[
            {"id": "x", "domain": {"type": "integer", "lower": 0, "upper": 2}},
            {"id": "y", "domain": {"type": "integer", "lower": 0, "upper": 2}},
        ],
        constraints=[
            {
                "id": "table",
                "kind": "table",
                "params": {"vars": ["x", "y"], "allowed_tuples": [[0, 1], [1, 0], [2, 2]]},
            }
        ],
    )

    solver = ORToolsSolver()
    response = await solver.solve_constraint_model(request)

    assert response.status == SolverStatus.SATISFIED
    values = {var.id: int(var.value) for var in response.solutions[0].variables}
    assert (values["x"], values["y"]) in [(0, 1), (1, 0), (2, 2)]


@pytest.mark.asyncio
async def test_implication_constraint():
    """Test implication constraint."""
    request = SolveConstraintModelRequest(
        mode="optimize",
        variables=[
            {"id": "use_feature", "domain": {"type": "bool"}},
            {"id": "cost", "domain": {"type": "integer", "lower": 0, "upper": 20}},
        ],
        constraints=[
            {
                "id": "cost_req",
                "kind": "linear",
                "params": {
                    "terms": [{"var": "cost", "coef": 1}],
                    "sense": ">=",
                    "rhs": 10,
                },
            },
            {
                "id": "impl",
                "kind": "implication",
                "params": {
                    "if_var": "use_feature",
                    "then_constraint_id": "cost_req",  # Reference to cost_req constraint
                },
            },
        ],
        objective={"sense": "min", "terms": [{"var": "cost", "coef": 1}]},
    )

    solver = ORToolsSolver()
    response = await solver.solve_constraint_model(request)

    assert response.status == SolverStatus.OPTIMAL
    # Should set use_feature=0 to avoid cost requirement
    values = {var.id: var.value for var in response.solutions[0].variables}
    assert values["use_feature"] == 0
    assert values["cost"] == 0


# ============================================================================
# Boolean Variable Tests
# ============================================================================


@pytest.mark.asyncio
async def test_boolean_variables():
    """Test boolean variable handling."""
    request = SolveConstraintModelRequest(
        mode="optimize",
        variables=[
            {"id": "x", "domain": {"type": "bool"}},
            {"id": "y", "domain": {"type": "bool"}},
        ],
        constraints=[
            {
                "id": "at_least_one",
                "kind": "linear",
                "params": {
                    "terms": [{"var": "x", "coef": 1}, {"var": "y", "coef": 1}],
                    "sense": ">=",
                    "rhs": 1,
                },
            }
        ],
        objective={"sense": "min", "terms": [{"var": "x", "coef": 1}, {"var": "y", "coef": 1}]},
    )

    solver = ORToolsSolver()
    response = await solver.solve_constraint_model(request)

    assert response.status == SolverStatus.OPTIMAL
    # Should set exactly one to 1
    values = {var.id: var.value for var in response.solutions[0].variables}
    assert sum(values.values()) == 1


# ============================================================================
# Metadata and Explanation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_variable_metadata_preserved():
    """Test that variable metadata is preserved in solution."""
    request = SolveConstraintModelRequest(
        mode="satisfy",
        variables=[
            {
                "id": "task_A",
                "domain": {"type": "bool"},
                "metadata": {"task_name": "Task A", "priority": 1},
            }
        ],
        constraints=[],
    )

    solver = ORToolsSolver()
    response = await solver.solve_constraint_model(request)

    assert response.status == SolverStatus.SATISFIED
    sol_var = response.solutions[0].variables[0]
    assert sol_var.metadata == {"task_name": "Task A", "priority": 1}


@pytest.mark.asyncio
async def test_binding_constraints_identified():
    """Test that binding constraints are identified."""
    request = SolveConstraintModelRequest(
        mode="optimize",
        variables=[{"id": "x", "domain": {"type": "integer", "lower": 0, "upper": 10}}],
        constraints=[
            {
                "id": "upper_limit",
                "kind": "linear",
                "params": {"terms": [{"var": "x", "coef": 1}], "sense": "<=", "rhs": 5},
                "metadata": {"description": "Maximum capacity"},
            }
        ],
        objective={"sense": "max", "terms": [{"var": "x", "coef": 1}]},
    )

    solver = ORToolsSolver()
    response = await solver.solve_constraint_model(request)

    assert response.status == SolverStatus.OPTIMAL
    assert response.explanation is not None
    assert len(response.explanation.binding_constraints) > 0
    assert response.explanation.binding_constraints[0].id == "upper_limit"


# ============================================================================
# Search Configuration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_search_config_timeout():
    """Test search configuration with timeout."""
    # Create a problem that would take time to solve optimally
    request = SolveConstraintModelRequest(
        mode="optimize",
        variables=[
            {"id": f"x{i}", "domain": {"type": "integer", "lower": 0, "upper": 100}}
            for i in range(10)
        ],
        constraints=[],
        objective={
            "sense": "max",
            "terms": [{"var": f"x{i}", "coef": i + 1} for i in range(10)],
        },
        search={"max_time_ms": 1},  # Very short timeout
    )

    solver = ORToolsSolver()
    response = await solver.solve_constraint_model(request)

    # Should complete quickly, status may be optimal or timeout depending on speed
    assert response.status in (
        SolverStatus.OPTIMAL,
        SolverStatus.TIMEOUT,
        SolverStatus.FEASIBLE,
        SolverStatus.TIMEOUT_NO_SOLUTION,
        SolverStatus.TIMEOUT_BEST,
    )


# ============================================================================
# Validation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_optimize_without_objective_fails():
    """Test that optimize mode without objective fails validation."""
    request = SolveConstraintModelRequest(
        mode="optimize",
        variables=[{"id": "x", "domain": {"type": "bool"}}],
        constraints=[],
    )

    solver = ORToolsSolver()

    # Now handled by validation framework, returns error response instead of raising
    response = await solver.solve_constraint_model(request)
    assert response.status == SolverStatus.ERROR
    assert "objective" in response.explanation.summary.lower()


# ============================================================================
# Edge Cases
# ============================================================================


@pytest.mark.asyncio
async def test_no_constraints():
    """Test problem with no constraints."""
    request = SolveConstraintModelRequest(
        mode="optimize",
        variables=[{"id": "x", "domain": {"type": "integer", "lower": 0, "upper": 10}}],
        constraints=[],
        objective={"sense": "max", "terms": [{"var": "x", "coef": 1}]},
    )

    solver = ORToolsSolver()
    response = await solver.solve_constraint_model(request)

    assert response.status == SolverStatus.OPTIMAL
    assert response.solutions[0].variables[0].value == 10  # Maximum value


@pytest.mark.asyncio
async def test_single_variable_single_constraint():
    """Test minimal problem."""
    request = SolveConstraintModelRequest(
        mode="satisfy",
        variables=[{"id": "x", "domain": {"type": "integer", "lower": 0, "upper": 5}}],
        constraints=[
            {
                "id": "fixed",
                "kind": "linear",
                "params": {"terms": [{"var": "x", "coef": 1}], "sense": "==", "rhs": 3},
            }
        ],
    )

    solver = ORToolsSolver()
    response = await solver.solve_constraint_model(request)

    assert response.status == SolverStatus.SATISFIED
    assert response.solutions[0].variables[0].value == 3
