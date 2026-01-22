"""Tests for response.py edge cases to increase coverage."""

import pytest


@pytest.mark.asyncio
class TestResponseEdgeCases:
    """Test edge cases in response building."""

    async def test_zero_objective_value_gap_calculation(self):
        """Test optimality gap calculation when objective value is zero."""
        from chuk_mcp_solver.models import (
            LinearTerm,
            Objective,
            ObjectiveSense,
            SearchConfig,
            SolveConstraintModelRequest,
            SolverMode,
            Variable,
            VariableDomain,
            VariableDomainType,
        )
        from chuk_mcp_solver.solver.ortools import ORToolsSolver

        # Problem where objective is zero: minimize x where x = 0
        request = SolveConstraintModelRequest(
            mode=SolverMode.OPTIMIZE,
            variables=[
                Variable(
                    id="x",
                    domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=0),
                )
            ],
            constraints=[],
            objective=Objective(sense=ObjectiveSense.MINIMIZE, terms=[LinearTerm(var="x", coef=1)]),
            search=SearchConfig(max_time_ms=1000),
        )

        solver = ORToolsSolver()
        response = await solver.solve_constraint_model(request)

        assert response.status == "optimal"
        assert response.objective_value == 0

    async def test_feasible_solution_without_objective(self):
        """Test feasible solution summary when no objective is present."""
        from chuk_mcp_solver.models import (
            Constraint,
            ConstraintKind,
            ConstraintSense,
            LinearConstraintParams,
            LinearTerm,
            SearchConfig,
            SolveConstraintModelRequest,
            SolverMode,
            Variable,
            VariableDomain,
            VariableDomainType,
        )
        from chuk_mcp_solver.solver.ortools import ORToolsSolver

        # Satisfiability problem with timeout to get FEASIBLE status
        request = SolveConstraintModelRequest(
            mode=SolverMode.SATISFY,
            variables=[
                Variable(
                    id="x",
                    domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=1000),
                )
            ],
            constraints=[
                Constraint(
                    id="c1",
                    kind=ConstraintKind.LINEAR,
                    params=LinearConstraintParams(
                        terms=[LinearTerm(var="x", coef=1)],
                        sense=ConstraintSense.GREATER_EQUAL,
                        rhs=5,
                    ),
                )
            ],
            search=SearchConfig(max_time_ms=1),  # Very short timeout
        )

        solver = ORToolsSolver()
        response = await solver.solve_constraint_model(request)

        # Should get either optimal or feasible (or timeout)
        assert response.status in (
            "optimal",
            "feasible",
            "timeout_best",
            "satisfied",
            "timeout_no_solution",
        )

    async def test_feasible_with_objective_and_gap(self):
        """Test feasible solution with objective value and optimality gap."""
        from chuk_mcp_solver.models import (
            LinearTerm,
            Objective,
            ObjectiveSense,
            SearchConfig,
            SolveConstraintModelRequest,
            SolverMode,
            Variable,
            VariableDomain,
            VariableDomainType,
        )
        from chuk_mcp_solver.solver.ortools import ORToolsSolver

        # Large problem with short timeout to get non-optimal solution
        variables = [
            Variable(
                id=f"x{i}",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=100),
            )
            for i in range(20)
        ]

        request = SolveConstraintModelRequest(
            mode=SolverMode.OPTIMIZE,
            variables=variables,
            constraints=[],
            objective=Objective(
                sense=ObjectiveSense.MAXIMIZE,
                terms=[LinearTerm(var=f"x{i}", coef=1) for i in range(20)],
            ),
            search=SearchConfig(max_time_ms=1),  # Very short timeout
        )

        solver = ORToolsSolver()
        response = await solver.solve_constraint_model(request)

        # Should get a solution (optimal or feasible)
        assert response.status in ("optimal", "feasible", "timeout_best", "timeout_no_solution")
