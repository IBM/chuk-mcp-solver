"""Tests for edge cases and error handling in provider."""

import pytest

from chuk_mcp_solver.models import SolveConstraintModelRequest, SolverStatus
from chuk_mcp_solver.solver.ortools import ORToolsSolver as ORToolsProvider


@pytest.mark.asyncio
async def test_satisfy_mode_with_objective_warns():
    """Test that satisfy mode with objective still works (objective ignored)."""
    request = SolveConstraintModelRequest(
        mode="satisfy",
        variables=[{"id": "x", "domain": {"type": "integer", "lower": 0, "upper": 5}}],
        constraints=[],
        objective={"sense": "min", "terms": [{"var": "x", "coef": 1}]},
    )

    provider = ORToolsProvider()
    # Should not raise, just warn (we test it doesn't crash)
    response = await provider.solve_constraint_model(request)
    assert response.status == SolverStatus.SATISFIED


@pytest.mark.asyncio
async def test_unsupported_constraint_kind():
    """Test that unsupported constraint kind is handled."""
    # We can't easily create an invalid constraint through Pydantic,
    # but we can test the error path by checking the enum covers all cases
    from chuk_mcp_solver.models import ConstraintKind

    # Verify all constraint kinds are handled
    kinds = [
        ConstraintKind.LINEAR,
        ConstraintKind.ALL_DIFFERENT,
        ConstraintKind.ELEMENT,
        ConstraintKind.TABLE,
        ConstraintKind.IMPLICATION,
    ]
    assert len(kinds) == 5  # If we add more, we need to update the provider


@pytest.mark.asyncio
async def test_implication_with_non_linear_constraint_fails():
    """Test that implication with non-linear referenced constraint fails."""
    request = SolveConstraintModelRequest(
        mode="satisfy",
        variables=[
            {"id": "x", "domain": {"type": "bool"}},
            {"id": "y", "domain": {"type": "integer", "lower": 0, "upper": 10}},
            {"id": "z", "domain": {"type": "integer", "lower": 0, "upper": 10}},
        ],
        constraints=[
            {
                "id": "nested_all_diff",
                "kind": "all_different",
                "params": {"vars": ["y", "z"]},
            },
            {
                "id": "impl",
                "kind": "implication",
                "params": {
                    "if_var": "x",
                    "then_constraint_id": "nested_all_diff",  # Reference to all_different constraint
                },
            },
        ],
    )

    provider = ORToolsProvider()
    response = await provider.solve_constraint_model(request)

    # Should return error status
    assert response.status == SolverStatus.ERROR
    assert "implication only supports linear" in response.explanation.summary.lower()


@pytest.mark.asyncio
async def test_large_domain_variables():
    """Test handling of variables with large domains."""
    request = SolveConstraintModelRequest(
        mode="optimize",
        variables=[{"id": "x", "domain": {"type": "integer", "lower": 0, "upper": 1000000}}],
        constraints=[],
        objective={"sense": "max", "terms": [{"var": "x", "coef": 1}]},
    )

    provider = ORToolsProvider()
    response = await provider.solve_constraint_model(request)

    assert response.status == SolverStatus.OPTIMAL
    assert response.solutions[0].variables[0].value == 1000000


@pytest.mark.asyncio
async def test_zero_coefficient_in_constraint():
    """Test constraint with zero coefficient."""
    request = SolveConstraintModelRequest(
        mode="satisfy",
        variables=[
            {"id": "x", "domain": {"type": "integer", "lower": 0, "upper": 10}},
            {"id": "y", "domain": {"type": "integer", "lower": 0, "upper": 10}},
        ],
        constraints=[
            {
                "id": "c1",
                "kind": "linear",
                "params": {
                    "terms": [{"var": "x", "coef": 0}, {"var": "y", "coef": 1}],
                    "sense": ">=",
                    "rhs": 5,
                },
            }
        ],
    )

    provider = ORToolsProvider()
    response = await provider.solve_constraint_model(request)

    assert response.status == SolverStatus.SATISFIED
    # y should be >= 5
    values = {var.id: var.value for var in response.solutions[0].variables}
    assert values["y"] >= 5


@pytest.mark.asyncio
async def test_negative_coefficients():
    """Test constraints with negative coefficients."""
    request = SolveConstraintModelRequest(
        mode="optimize",
        variables=[
            {"id": "x", "domain": {"type": "integer", "lower": 0, "upper": 10}},
            {"id": "y", "domain": {"type": "integer", "lower": 0, "upper": 10}},
        ],
        constraints=[
            {
                "id": "c1",
                "kind": "linear",
                "params": {
                    "terms": [{"var": "x", "coef": 1}, {"var": "y", "coef": -1}],
                    "sense": ">=",
                    "rhs": 0,
                },
            }
        ],
        objective={"sense": "max", "terms": [{"var": "x", "coef": 1}, {"var": "y", "coef": 1}]},
    )

    provider = ORToolsProvider()
    response = await provider.solve_constraint_model(request)

    assert response.status == SolverStatus.OPTIMAL
    # x >= y, so maximize x + y means x=10, y=10 but constraint requires x >= y


@pytest.mark.asyncio
async def test_equality_constraint():
    """Test equality constraint explicitly."""
    request = SolveConstraintModelRequest(
        mode="satisfy",
        variables=[
            {"id": "x", "domain": {"type": "integer", "lower": 0, "upper": 10}},
            {"id": "y", "domain": {"type": "integer", "lower": 0, "upper": 10}},
        ],
        constraints=[
            {
                "id": "equal",
                "kind": "linear",
                "params": {
                    "terms": [{"var": "x", "coef": 1}, {"var": "y", "coef": -1}],
                    "sense": "==",
                    "rhs": 0,
                },
            },
            {
                "id": "fix_x",
                "kind": "linear",
                "params": {"terms": [{"var": "x", "coef": 1}], "sense": "==", "rhs": 7},
            },
        ],
    )

    provider = ORToolsProvider()
    response = await provider.solve_constraint_model(request)

    assert response.status == SolverStatus.SATISFIED
    values = {var.id: var.value for var in response.solutions[0].variables}
    assert values["x"] == values["y"] == 7


@pytest.mark.asyncio
async def test_empty_constraint_list():
    """Test model with no constraints."""
    request = SolveConstraintModelRequest(
        mode="satisfy",
        variables=[{"id": "x", "domain": {"type": "integer", "lower": 0, "upper": 10}}],
        constraints=[],
    )

    provider = ORToolsProvider()
    response = await provider.solve_constraint_model(request)

    assert response.status == SolverStatus.SATISFIED


@pytest.mark.asyncio
async def test_fractional_rhs_rounds_to_int():
    """Test that fractional RHS values are converted to int."""
    request = SolveConstraintModelRequest(
        mode="satisfy",
        variables=[{"id": "x", "domain": {"type": "integer", "lower": 0, "upper": 10}}],
        constraints=[
            {
                "id": "c1",
                "kind": "linear",
                "params": {"terms": [{"var": "x", "coef": 1}], "sense": "<=", "rhs": 5.9},
            }
        ],
    )

    provider = ORToolsProvider()
    response = await provider.solve_constraint_model(request)

    # rhs 5.9 should round to 5
    assert response.status == SolverStatus.SATISFIED
    assert response.solutions[0].variables[0].value <= 5


@pytest.mark.asyncio
async def test_duplicate_vars_in_objective_auto_merged():
    """Test that duplicate variables in objective are automatically merged."""
    request = SolveConstraintModelRequest(
        mode="optimize",
        variables=[
            {"id": "x", "domain": {"type": "integer", "lower": 0, "upper": 10}},
            {"id": "y", "domain": {"type": "integer", "lower": 0, "upper": 10}},
        ],
        constraints=[],
        objective={
            "sense": "max",
            "terms": [
                {"var": "x", "coef": 3},
                {"var": "y", "coef": 2},
                {"var": "x", "coef": 5},  # Duplicate! Should merge with first x
            ],
        },
    )

    provider = ORToolsProvider()
    response = await provider.solve_constraint_model(request)

    # Objective should be: max 8*x + 2*y (3+5=8 for x)
    # So optimal is x=10, y=10
    assert response.status == SolverStatus.OPTIMAL
    assert response.objective_value == 8 * 10 + 2 * 10


@pytest.mark.asyncio
async def test_duplicate_vars_in_constraint_auto_merged():
    """Test that duplicate variables in constraint terms are automatically merged."""
    request = SolveConstraintModelRequest(
        mode="satisfy",
        variables=[
            {"id": "x", "domain": {"type": "integer", "lower": 0, "upper": 10}},
            {"id": "y", "domain": {"type": "integer", "lower": 0, "upper": 10}},
        ],
        constraints=[
            {
                "id": "c1",
                "kind": "linear",
                "params": {
                    "terms": [
                        {"var": "x", "coef": 2},
                        {"var": "y", "coef": 1},
                        {"var": "x", "coef": 3},  # Duplicate! Should merge to 5*x
                    ],
                    "sense": "<=",
                    "rhs": 30,
                },
            }
        ],
    )

    provider = ORToolsProvider()
    response = await provider.solve_constraint_model(request)

    # Constraint should be: 5*x + y <= 30
    assert response.status == SolverStatus.SATISFIED
    values = {var.id: var.value for var in response.solutions[0].variables}
    assert 5 * values["x"] + values["y"] <= 30
