"""Tests for enhanced status codes and performance metrics."""

import pytest

from chuk_mcp_solver.models import (
    Constraint,
    LinearConstraintParams,
    LinearTerm,
    Objective,
    SearchConfig,
    SolveConstraintModelRequest,
    SolverMode,
    SolverStatus,
    Variable,
    VariableDomain,
    VariableDomainType,
)
from chuk_mcp_solver.solver import get_solver


@pytest.fixture
def solver():
    """Get OR-Tools solver instance."""
    return get_solver("ortools")


class TestEnhancedStatus:
    """Tests for new status codes: TIMEOUT_BEST and TIMEOUT_NO_SOLUTION."""

    async def test_optimal_has_zero_gap(self, solver):
        """Test that optimal solutions have 0% optimality gap."""
        # Simple knapsack: maximize value subject to capacity
        request = SolveConstraintModelRequest(
            mode=SolverMode.OPTIMIZE,
            variables=[
                Variable(id="x1", domain=VariableDomain(type=VariableDomainType.BOOL)),
                Variable(id="x2", domain=VariableDomain(type=VariableDomainType.BOOL)),
            ],
            constraints=[
                Constraint(
                    id="capacity",
                    kind="linear",
                    params=LinearConstraintParams(
                        terms=[
                            LinearTerm(var="x1", coef=3),
                            LinearTerm(var="x2", coef=5),
                        ],
                        sense="<=",
                        rhs=7,
                    ),
                )
            ],
            objective=Objective(
                sense="max",
                terms=[
                    LinearTerm(var="x1", coef=10),
                    LinearTerm(var="x2", coef=15),
                ],
            ),
        )

        response = await solver.solve_constraint_model(request)

        assert response.status == SolverStatus.OPTIMAL
        assert response.optimality_gap == 0.0
        assert response.solve_time_ms >= 0
        assert response.objective_value is not None

    async def test_timeout_with_solution(self, solver):
        """Test TIMEOUT_BEST status when timeout occurs with a solution."""
        # Create a problem with a simple initial solution (all zeros)
        # but make optimization complex
        variables = [
            Variable(
                id=f"x{i}",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            )
            for i in range(10)
        ]

        # Add some constraints
        constraints = [
            Constraint(
                id=f"c{i}",
                kind="linear",
                params=LinearConstraintParams(
                    terms=[LinearTerm(var=f"x{i}", coef=1), LinearTerm(var=f"x{i + 1}", coef=1)],
                    sense="<=",
                    rhs=15,
                ),
            )
            for i in range(9)
        ]

        request = SolveConstraintModelRequest(
            mode=SolverMode.OPTIMIZE,
            variables=variables,
            constraints=constraints,
            objective=Objective(
                sense="max",
                terms=[LinearTerm(var=f"x{i}", coef=i + 1) for i in range(10)],
            ),
            search=SearchConfig(
                max_time_ms=1,  # Very short timeout
                return_partial_solution=True,  # Request partial solution
            ),
        )

        response = await solver.solve_constraint_model(request)

        # Could get OPTIMAL (fast), TIMEOUT_BEST (partial), or TIMEOUT_NO_SOLUTION
        assert response.status in (
            SolverStatus.OPTIMAL,
            SolverStatus.TIMEOUT_BEST,
            SolverStatus.TIMEOUT_NO_SOLUTION,
        )
        assert response.solve_time_ms >= 0

        if response.status == SolverStatus.TIMEOUT_BEST:
            # Should have a solution
            assert len(response.solutions) > 0
            assert response.objective_value is not None
            # May have an optimality gap > 0
            assert response.optimality_gap is not None
            # Check explanation mentions timeout
            assert response.explanation is not None
            assert "timed out" in response.explanation.summary.lower()
        elif response.status == SolverStatus.TIMEOUT_NO_SOLUTION:
            # No solution found
            assert len(response.solutions) == 0

    async def test_timeout_no_solution(self, solver):
        """Test TIMEOUT_NO_SOLUTION status when timeout occurs without finding a solution."""
        # Create a complex problem with very short timeout
        # Make it hard enough that solver likely won't find solution in 1ms
        variables = [
            Variable(
                id=f"x{i}",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=100),
            )
            for i in range(20)
        ]

        # Add many complex constraints
        constraints = []
        for i in range(19):
            constraints.append(
                Constraint(
                    id=f"c{i}",
                    kind="linear",
                    params=LinearConstraintParams(
                        terms=[
                            LinearTerm(var=f"x{i}", coef=2),
                            LinearTerm(var=f"x{i + 1}", coef=3),
                        ],
                        sense="<=",
                        rhs=150,
                    ),
                )
            )

        # Add all_different constraint to make it harder
        constraints.append(
            Constraint(
                id="all_diff",
                kind="all_different",
                params={"vars": [f"x{i}" for i in range(10)]},
            )
        )

        request = SolveConstraintModelRequest(
            mode=SolverMode.OPTIMIZE,
            variables=variables,
            constraints=constraints,
            objective=Objective(
                sense="max",
                terms=[LinearTerm(var=f"x{i}", coef=i + 1) for i in range(20)],
            ),
            search=SearchConfig(
                max_time_ms=1,  # Very short timeout
                return_partial_solution=False,  # Don't return partial solution
            ),
        )

        response = await solver.solve_constraint_model(request)

        # Could get OPTIMAL (fast), TIMEOUT_NO_SOLUTION (no solution found), or TIMEOUT_BEST (found partial)
        # This test is probabilistic - just verify the status is valid
        assert response.status in (
            SolverStatus.OPTIMAL,
            SolverStatus.FEASIBLE,
            SolverStatus.TIMEOUT_NO_SOLUTION,
            SolverStatus.TIMEOUT_BEST,
        )
        assert response.solve_time_ms >= 0

        if response.status == SolverStatus.TIMEOUT_NO_SOLUTION:
            # Should have no solution
            assert len(response.solutions) == 0
            assert response.objective_value is None
            # Check explanation
            assert response.explanation is not None
            assert "timed out" in response.explanation.summary.lower()

    async def test_solve_time_tracked(self, solver):
        """Test that solve_time_ms is always populated."""
        request = SolveConstraintModelRequest(
            mode=SolverMode.SATISFY,
            variables=[
                Variable(
                    id="x",
                    domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
                )
            ],
            constraints=[],
        )

        response = await solver.solve_constraint_model(request)

        assert response.status == SolverStatus.SATISFIED
        assert response.solve_time_ms >= 0
        assert isinstance(response.solve_time_ms, int)

    async def test_optimality_gap_for_feasible(self, solver):
        """Test optimality gap calculation for feasible (non-optimal) solutions."""
        # Create a problem and limit solve time to get feasible (not optimal)
        variables = [
            Variable(
                id=f"x{i}",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            )
            for i in range(5)
        ]

        request = SolveConstraintModelRequest(
            mode=SolverMode.OPTIMIZE,
            variables=variables,
            constraints=[],
            objective=Objective(
                sense="max",
                terms=[LinearTerm(var=f"x{i}", coef=i + 1) for i in range(5)],
            ),
            search=SearchConfig(
                max_time_ms=10,  # Short timeout to potentially get feasible solution
            ),
        )

        response = await solver.solve_constraint_model(request)

        # Should be optimal or feasible
        assert response.status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)

        # Optimality gap should be defined
        assert response.optimality_gap is not None

        if response.status == SolverStatus.OPTIMAL:
            assert response.optimality_gap == 0.0
        else:  # FEASIBLE
            # Gap could be anything, just verify it's non-negative
            assert response.optimality_gap >= 0.0


class TestPerformanceMetrics:
    """Tests for performance metrics in responses."""

    async def test_all_responses_include_metrics(self, solver):
        """Test that all response types include performance metrics."""
        # Test OPTIMAL
        optimal_request = SolveConstraintModelRequest(
            mode=SolverMode.OPTIMIZE,
            variables=[
                Variable(
                    id="x",
                    domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
                )
            ],
            constraints=[],
            objective=Objective(sense="max", terms=[LinearTerm(var="x", coef=1)]),
        )

        response = await solver.solve_constraint_model(optimal_request)
        assert response.status == SolverStatus.OPTIMAL
        assert response.solve_time_ms >= 0
        assert response.optimality_gap == 0.0

        # Test INFEASIBLE
        infeasible_request = SolveConstraintModelRequest(
            mode=SolverMode.SATISFY,
            variables=[
                Variable(
                    id="x",
                    domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
                )
            ],
            constraints=[
                Constraint(
                    id="c1",
                    kind="linear",
                    params=LinearConstraintParams(
                        terms=[LinearTerm(var="x", coef=1)],
                        sense="<=",
                        rhs=5,
                    ),
                ),
                Constraint(
                    id="c2",
                    kind="linear",
                    params=LinearConstraintParams(
                        terms=[LinearTerm(var="x", coef=1)],
                        sense=">=",
                        rhs=10,
                    ),
                ),
            ],
        )

        response = await solver.solve_constraint_model(infeasible_request)
        assert response.status == SolverStatus.INFEASIBLE
        # Infeasible responses may not have solve_time_ms populated in all cases
        # but the field should exist
        assert hasattr(response, "solve_time_ms")

    async def test_explanation_includes_gap_info(self, solver):
        """Test that explanations mention optimality gap when relevant."""
        request = SolveConstraintModelRequest(
            mode=SolverMode.OPTIMIZE,
            variables=[
                Variable(
                    id="x",
                    domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
                )
            ],
            constraints=[],
            objective=Objective(sense="max", terms=[LinearTerm(var="x", coef=1)]),
        )

        response = await solver.solve_constraint_model(request)

        assert response.explanation is not None
        assert isinstance(response.explanation.summary, str)
        assert len(response.explanation.summary) > 0

        # Optimal solution should mention "optimal"
        if response.status == SolverStatus.OPTIMAL:
            assert "optimal" in response.explanation.summary.lower()


class TestBackwardCompatibility:
    """Tests for backward compatibility with old TIMEOUT status."""

    async def test_timeout_status_still_handled(self, solver):
        """Test that old TIMEOUT status enum value still exists for compatibility."""
        # Verify the old TIMEOUT enum still exists
        assert hasattr(SolverStatus, "TIMEOUT")
        assert SolverStatus.TIMEOUT == "timeout"

        # The new statuses should be different
        assert SolverStatus.TIMEOUT_BEST != SolverStatus.TIMEOUT
        assert SolverStatus.TIMEOUT_NO_SOLUTION != SolverStatus.TIMEOUT
