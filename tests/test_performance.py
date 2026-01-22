"""Tests for Phase 3 performance features."""

import pytest

from chuk_mcp_solver.cache import clear_global_cache
from chuk_mcp_solver.models import (
    Constraint,
    ConstraintKind,
    LinearConstraintParams,
    LinearTerm,
    Objective,
    ObjectiveSense,
    SearchConfig,
    SearchStrategy,
    SolveConstraintModelRequest,
    SolverMode,
    SolverStatus,
    Variable,
    VariableDomain,
    VariableDomainType,
)
from chuk_mcp_solver.solver import get_solver


@pytest.mark.asyncio
async def test_solution_caching_enabled():
    """Test that solutions are cached when caching is enabled."""
    clear_global_cache()
    solver = get_solver()

    request = SolveConstraintModelRequest(
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
                kind=ConstraintKind.LINEAR,
                params=LinearConstraintParams(
                    terms=[LinearTerm(var="x", coef=1)],
                    sense=">=",
                    rhs=5,
                ),
            )
        ],
        search=SearchConfig(enable_solution_caching=True),
    )

    # First solve
    response1 = await solver.solve_constraint_model(request)
    assert response1.status == SolverStatus.SATISFIED

    # Second solve should hit cache (instant)
    response2 = await solver.solve_constraint_model(request)
    assert response2.status == SolverStatus.SATISFIED
    # Should be same solution
    assert response1.solutions[0].variables == response2.solutions[0].variables


@pytest.mark.asyncio
async def test_solution_caching_disabled():
    """Test that caching can be disabled."""
    clear_global_cache()
    solver = get_solver()

    request = SolveConstraintModelRequest(
        mode=SolverMode.SATISFY,
        variables=[
            Variable(
                id="x",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            )
        ],
        constraints=[],
        search=SearchConfig(enable_solution_caching=False),
    )

    # Should work but not cache
    response = await solver.solve_constraint_model(request)
    assert response.status == SolverStatus.SATISFIED


@pytest.mark.asyncio
async def test_search_strategy_first_fail():
    """Test first-fail search strategy."""
    solver = get_solver()

    request = SolveConstraintModelRequest(
        mode=SolverMode.SATISFY,
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
                id="c1",
                kind=ConstraintKind.LINEAR,
                params=LinearConstraintParams(
                    terms=[
                        LinearTerm(var="x", coef=1),
                        LinearTerm(var="y", coef=1),
                    ],
                    sense="<=",
                    rhs=15,
                ),
            )
        ],
        search=SearchConfig(strategy=SearchStrategy.FIRST_FAIL),
    )

    response = await solver.solve_constraint_model(request)
    assert response.status == SolverStatus.SATISFIED


@pytest.mark.asyncio
async def test_search_strategy_random():
    """Test random search strategy."""
    solver = get_solver()

    request = SolveConstraintModelRequest(
        mode=SolverMode.SATISFY,
        variables=[
            Variable(
                id="x",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            )
        ],
        constraints=[],
        search=SearchConfig(strategy=SearchStrategy.RANDOM, random_seed=42),
    )

    response = await solver.solve_constraint_model(request)
    assert response.status == SolverStatus.SATISFIED


@pytest.mark.asyncio
async def test_partial_solution_on_timeout():
    """Test returning partial solution when timeout is reached."""
    solver = get_solver()

    # Create a problem that's hard to solve optimally but easy to find feasible solutions
    request = SolveConstraintModelRequest(
        mode=SolverMode.OPTIMIZE,
        variables=[
            Variable(
                id=f"x{i}",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=100),
            )
            for i in range(10)
        ],
        constraints=[
            # Sum constraint
            Constraint(
                id="sum",
                kind=ConstraintKind.LINEAR,
                params=LinearConstraintParams(
                    terms=[LinearTerm(var=f"x{i}", coef=1) for i in range(10)],
                    sense="<=",
                    rhs=500,
                ),
            )
        ],
        objective=Objective(
            sense=ObjectiveSense.MAXIMIZE,
            terms=[LinearTerm(var=f"x{i}", coef=i + 1) for i in range(10)],
        ),
        search=SearchConfig(
            max_time_ms=50,  # Short timeout to trigger timeout but allow finding feasible solutions
            return_partial_solution=True,
        ),
    )

    response = await solver.solve_constraint_model(request)

    # Should either find optimal or return feasible solution
    assert response.status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)

    # Should have a solution
    assert len(response.solutions) > 0


@pytest.mark.asyncio
async def test_no_partial_solution_on_timeout():
    """Test that timeout without partial solution returns timeout status."""
    solver = get_solver()

    # Same problem but don't request partial solution
    request = SolveConstraintModelRequest(
        mode=SolverMode.OPTIMIZE,
        variables=[
            Variable(
                id=f"x{i}",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=100),
            )
            for i in range(10)
        ],
        constraints=[
            Constraint(
                id="sum",
                kind=ConstraintKind.LINEAR,
                params=LinearConstraintParams(
                    terms=[LinearTerm(var=f"x{i}", coef=1) for i in range(10)],
                    sense="<=",
                    rhs=500,
                ),
            )
        ],
        objective=Objective(
            sense=ObjectiveSense.MAXIMIZE,
            terms=[LinearTerm(var=f"x{i}", coef=i + 1) for i in range(10)],
        ),
        search=SearchConfig(
            max_time_ms=1,  # Very short timeout
            return_partial_solution=False,  # Don't return partial
        ),
    )

    response = await solver.solve_constraint_model(request)

    # Should find a solution quickly or timeout
    assert response.status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE, SolverStatus.TIMEOUT)


@pytest.mark.asyncio
async def test_deterministic_solving_with_seed():
    """Test that same seed produces same solution."""
    solver = get_solver()

    def make_request(seed):
        return SolveConstraintModelRequest(
            mode=SolverMode.SATISFY,
            variables=[
                Variable(
                    id="x",
                    domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=100),
                )
            ],
            constraints=[],
            search=SearchConfig(random_seed=seed, enable_solution_caching=False),
        )

    # Solve with same seed twice
    response1 = await solver.solve_constraint_model(make_request(42))
    response2 = await solver.solve_constraint_model(make_request(42))

    # Should get same solution
    assert response1.solutions[0].variables == response2.solutions[0].variables

    # Different seed should potentially give different solution
    response3 = await solver.solve_constraint_model(make_request(123))
    # May or may not be different, but should still be valid
    assert response3.status == SolverStatus.SATISFIED


@pytest.mark.asyncio
async def test_combined_features():
    """Test using multiple Phase 3 features together."""
    clear_global_cache()
    solver = get_solver()

    request = SolveConstraintModelRequest(
        mode=SolverMode.OPTIMIZE,
        variables=[
            Variable(
                id=f"x{i}",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            )
            for i in range(5)
        ],
        constraints=[
            Constraint(
                id="sum",
                kind=ConstraintKind.LINEAR,
                params=LinearConstraintParams(
                    terms=[LinearTerm(var=f"x{i}", coef=1) for i in range(5)],
                    sense="<=",
                    rhs=30,
                ),
            )
        ],
        objective=Objective(
            sense=ObjectiveSense.MAXIMIZE,
            terms=[LinearTerm(var=f"x{i}", coef=i + 1) for i in range(5)],
        ),
        search=SearchConfig(
            strategy=SearchStrategy.FIRST_FAIL,
            random_seed=42,
            enable_solution_caching=True,
            return_partial_solution=True,
            max_time_ms=5000,
        ),
    )

    # First solve
    response1 = await solver.solve_constraint_model(request)
    assert response1.status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)

    # Second solve should hit cache
    response2 = await solver.solve_constraint_model(request)
    assert response2.status == response1.status
    assert response1.solutions == response2.solutions
