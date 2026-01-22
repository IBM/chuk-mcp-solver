"""Tests for server.py tool functions to increase coverage."""

import pytest


@pytest.mark.asyncio
class TestConstraintModelTool:
    """Test solve_constraint_model tool from server.py."""

    async def test_solve_constraint_model_simple(self):
        """Test solve_constraint_model tool directly."""
        from chuk_mcp_solver.server import solve_constraint_model

        # Simple problem: x + y = 10, x >= 0, y >= 0
        response = await solve_constraint_model(
            mode="satisfy",
            variables=[
                {"id": "x", "domain": {"type": "integer", "lower": 0, "upper": 10}},
                {"id": "y", "domain": {"type": "integer", "lower": 0, "upper": 10}},
            ],
            constraints=[
                {
                    "id": "sum_to_10",
                    "kind": "linear",
                    "params": {
                        "terms": [{"var": "x", "coef": 1}, {"var": "y", "coef": 1}],
                        "sense": "==",
                        "rhs": 10,
                    },
                }
            ],
        )

        assert response["status"] in ("optimal", "feasible", "satisfied")
        assert len(response["solutions"]) > 0
        # Verify x + y = 10
        sol = response["solutions"][0]
        x_val = next(v["value"] for v in sol["variables"] if v["id"] == "x")
        y_val = next(v["value"] for v in sol["variables"] if v["id"] == "y")
        assert x_val + y_val == 10

    async def test_solve_constraint_model_with_objective(self):
        """Test solve_constraint_model with optimization."""
        from chuk_mcp_solver.server import solve_constraint_model

        response = await solve_constraint_model(
            mode="optimize",
            variables=[
                {"id": "x", "domain": {"type": "integer", "lower": 0, "upper": 100}},
            ],
            constraints=[],
            objective={"sense": "max", "terms": [{"var": "x", "coef": 1}]},
        )

        assert response["status"] == "optimal"
        sol = response["solutions"][0]
        x_val = next(v["value"] for v in sol["variables"] if v["id"] == "x")
        assert x_val == 100  # Should maximize to upper bound

    async def test_solve_constraint_model_with_search_config(self):
        """Test solve_constraint_model with search configuration."""
        from chuk_mcp_solver.server import solve_constraint_model

        response = await solve_constraint_model(
            mode="satisfy",
            variables=[
                {"id": "x", "domain": {"type": "integer", "lower": 0, "upper": 10}},
            ],
            constraints=[],
            search={
                "max_time_ms": 1000,
                "num_workers": 2,
                "strategy": "first_fail",
            },
        )

        assert response["status"] in ("optimal", "feasible", "satisfied")
        assert response["solve_time_ms"] <= 1000 + 100  # Allow 100ms tolerance
