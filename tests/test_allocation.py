"""Tests for high-level budget allocation solving."""

import pytest

from chuk_mcp_solver.models import (
    AllocationObjective,
    BudgetConstraint,
    Item,
    SolveBudgetAllocationRequest,
    SolverStatus,
)
from chuk_mcp_solver.solver import get_solver
from chuk_mcp_solver.solver.ortools.allocation import (
    convert_allocation_to_cpsat,
    convert_cpsat_to_allocation_response,
)


@pytest.fixture
def solver():
    """Get solver instance."""
    return get_solver("ortools")


class TestAllocationConverters:
    """Tests for allocation <-> CP-SAT converters."""

    def test_convert_simple_knapsack(self):
        """Test converting simple knapsack to CP-SAT."""
        request = SolveBudgetAllocationRequest(
            items=[
                Item(id="item_A", cost=5000, value=12000),
                Item(id="item_B", cost=3000, value=7000),
                Item(id="item_C", cost=4000, value=9000),
            ],
            budgets=[BudgetConstraint(resource="money", limit=10000)],
            objective=AllocationObjective.MAXIMIZE_VALUE,
        )

        cpsat_request = convert_allocation_to_cpsat(request)

        # Should have selection variable for each item
        assert len(cpsat_request.variables) == 3
        assert all(v.id.startswith("select_") for v in cpsat_request.variables)

        # Should have budget constraint
        budget_constraints = [c for c in cpsat_request.constraints if c.id.startswith("budget_")]
        assert len(budget_constraints) == 1

        # Should have optimization objective
        assert cpsat_request.mode == "optimize"
        assert cpsat_request.objective is not None
        assert cpsat_request.objective.sense == "max"

    def test_convert_with_dependencies(self):
        """Test allocation with dependencies."""
        request = SolveBudgetAllocationRequest(
            items=[
                Item(id="backend", cost=8000, value=5000),
                Item(id="frontend", cost=6000, value=8000, dependencies=["backend"]),
                Item(id="mobile", cost=7000, value=6000, dependencies=["backend"]),
            ],
            budgets=[BudgetConstraint(resource="money", limit=20000)],
            objective=AllocationObjective.MAXIMIZE_VALUE,
        )

        cpsat_request = convert_allocation_to_cpsat(request)

        # Should have dependency constraints (implication constraints)
        dependency_constraints = [
            c for c in cpsat_request.constraints if c.id.startswith("dependency_")
        ]
        assert len(dependency_constraints) == 2  # frontend->backend, mobile->backend

    def test_convert_with_conflicts(self):
        """Test allocation with conflicts."""
        request = SolveBudgetAllocationRequest(
            items=[
                Item(id="option_A", cost=5000, value=10000, conflicts=["option_B"]),
                Item(id="option_B", cost=4000, value=9000, conflicts=["option_A"]),
                Item(id="option_C", cost=3000, value=7000),
            ],
            budgets=[BudgetConstraint(resource="money", limit=10000)],
            objective=AllocationObjective.MAXIMIZE_VALUE,
        )

        cpsat_request = convert_allocation_to_cpsat(request)

        # Should have conflict constraint (at most one)
        conflict_constraints = [
            c for c in cpsat_request.constraints if c.id.startswith("conflict_")
        ]
        assert len(conflict_constraints) == 1  # Only one constraint for A vs B

    def test_convert_with_multi_resource(self):
        """Test allocation with multiple resource constraints."""
        request = SolveBudgetAllocationRequest(
            items=[
                Item(
                    id="feature_A",
                    cost=5000,
                    value=10000,
                    resources_required={"headcount": 2, "time": 3},
                ),
                Item(
                    id="feature_B",
                    cost=3000,
                    value=7000,
                    resources_required={"headcount": 1, "time": 2},
                ),
            ],
            budgets=[
                BudgetConstraint(resource="money", limit=10000),
                BudgetConstraint(resource="headcount", limit=3),
                BudgetConstraint(resource="time", limit=4),
            ],
            objective=AllocationObjective.MAXIMIZE_VALUE,
        )

        cpsat_request = convert_allocation_to_cpsat(request)

        # Should have budget constraint for each resource
        budget_constraints = [c for c in cpsat_request.constraints if c.id.startswith("budget_")]
        assert len(budget_constraints) == 3  # money, headcount, time


class TestAllocationSolver:
    """Tests for end-to-end allocation solving."""

    async def test_simple_knapsack(self, solver):
        """Test simple knapsack problem."""
        request = SolveBudgetAllocationRequest(
            items=[
                Item(id="item_A", cost=5000, value=12000),
                Item(id="item_B", cost=3000, value=7000),
                Item(id="item_C", cost=4000, value=9000),
            ],
            budgets=[BudgetConstraint(resource="money", limit=10000)],
            objective=AllocationObjective.MAXIMIZE_VALUE,
        )

        cpsat_request = convert_allocation_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_allocation_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        assert len(response.selected_items) >= 1
        assert response.total_cost <= 10000  # Within budget
        assert response.total_value > 0
        # Optimal solution should select A + C (cost=9000, value=21000)
        assert set(response.selected_items) == {"item_A", "item_C"}

    async def test_maximize_count(self, solver):
        """Test maximizing number of items."""
        request = SolveBudgetAllocationRequest(
            items=[
                Item(id="item_A", cost=5000, value=10000),
                Item(id="item_B", cost=3000, value=7000),
                Item(id="item_C", cost=2000, value=5000),
                Item(id="item_D", cost=1000, value=3000),
            ],
            budgets=[BudgetConstraint(resource="money", limit=8000)],
            objective=AllocationObjective.MAXIMIZE_COUNT,
        )

        cpsat_request = convert_allocation_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_allocation_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        # Should select as many items as possible: B, C, D (6000 total)
        assert len(response.selected_items) == 3
        assert response.total_cost <= 8000

    async def test_minimize_cost(self, solver):
        """Test minimizing cost while meeting value threshold."""
        request = SolveBudgetAllocationRequest(
            items=[
                Item(id="item_A", cost=5000, value=10000),
                Item(id="item_B", cost=3000, value=7000),
                Item(id="item_C", cost=4000, value=12000),
            ],
            budgets=[BudgetConstraint(resource="money", limit=20000)],
            objective=AllocationObjective.MINIMIZE_COST,
            min_value_threshold=15000,
        )

        cpsat_request = convert_allocation_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_allocation_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        assert response.total_value >= 15000  # Meets threshold
        # Should select B + C (cost=7000, value=19000) instead of A + C (cost=9000)
        assert set(response.selected_items) == {"item_B", "item_C"}
        assert response.total_cost == 7000

    async def test_with_dependencies(self, solver):
        """Test allocation respecting dependencies."""
        request = SolveBudgetAllocationRequest(
            items=[
                Item(id="backend", cost=8000, value=5000),
                Item(id="frontend", cost=6000, value=12000, dependencies=["backend"]),
                Item(id="mobile", cost=7000, value=6000),
            ],
            budgets=[BudgetConstraint(resource="money", limit=15000)],
            objective=AllocationObjective.MAXIMIZE_VALUE,
        )

        cpsat_request = convert_allocation_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_allocation_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        # If frontend is selected, backend must also be selected
        if "frontend" in response.selected_items:
            assert "backend" in response.selected_items
        # Optimal: backend + frontend (cost=14000, value=17000)
        assert set(response.selected_items) == {"backend", "frontend"}

    async def test_with_conflicts(self, solver):
        """Test allocation respecting conflicts."""
        request = SolveBudgetAllocationRequest(
            items=[
                Item(id="option_A", cost=5000, value=10000, conflicts=["option_B"]),
                Item(id="option_B", cost=4000, value=9000, conflicts=["option_A"]),
                Item(id="option_C", cost=3000, value=7000),
            ],
            budgets=[BudgetConstraint(resource="money", limit=10000)],
            objective=AllocationObjective.MAXIMIZE_VALUE,
        )

        cpsat_request = convert_allocation_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_allocation_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        # Cannot select both A and B
        assert not ("option_A" in response.selected_items and "option_B" in response.selected_items)
        # Optimal: A + C (cost=8000, value=17000)
        assert set(response.selected_items) == {"option_A", "option_C"}

    async def test_multi_resource_constraints(self, solver):
        """Test allocation with multiple resources."""
        request = SolveBudgetAllocationRequest(
            items=[
                Item(
                    id="feature_A",
                    cost=5000,
                    value=10000,
                    resources_required={"headcount": 2, "time": 3},
                ),
                Item(
                    id="feature_B",
                    cost=3000,
                    value=7000,
                    resources_required={"headcount": 1, "time": 2},
                ),
                Item(
                    id="feature_C",
                    cost=4000,
                    value=9000,
                    resources_required={"headcount": 2, "time": 1},
                ),
            ],
            budgets=[
                BudgetConstraint(resource="money", limit=10000),
                BudgetConstraint(resource="headcount", limit=3),
                BudgetConstraint(resource="time", limit=4),
            ],
            objective=AllocationObjective.MAXIMIZE_VALUE,
        )

        cpsat_request = convert_allocation_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_allocation_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        # Should respect all resource constraints
        assert response.resource_usage.get("headcount", 0) <= 3
        assert response.resource_usage.get("time", 0) <= 4
        assert response.total_cost <= 10000


class TestAllocationFromServer:
    """Test the high-level solve_budget_allocation tool."""

    async def test_solve_budget_allocation_simple(self):
        """Test solve_budget_allocation with simple knapsack."""
        from chuk_mcp_solver.server import solve_budget_allocation

        response = await solve_budget_allocation(
            items=[
                {"id": "project_A", "cost": 5000, "value": 12000},
                {"id": "project_B", "cost": 3000, "value": 7000},
                {"id": "project_C", "cost": 4000, "value": 9000},
            ],
            budgets=[{"resource": "money", "limit": 10000}],
            objective="maximize_value",
        )

        assert response.status == SolverStatus.OPTIMAL
        assert len(response.selected_items) >= 1
        assert response.total_cost <= 10000
        assert response.total_value > 0
        assert response.explanation is not None

    async def test_solve_budget_allocation_with_dependencies(self):
        """Test solve_budget_allocation with dependencies."""
        from chuk_mcp_solver.server import solve_budget_allocation

        response = await solve_budget_allocation(
            items=[
                {"id": "backend", "cost": 8000, "value": 5000},
                {"id": "frontend", "cost": 6000, "value": 12000, "dependencies": ["backend"]},
                {"id": "mobile", "cost": 7000, "value": 6000},
            ],
            budgets=[{"resource": "money", "limit": 15000}],
            objective="maximize_value",
        )

        assert response.status == SolverStatus.OPTIMAL
        if "frontend" in response.selected_items:
            assert "backend" in response.selected_items

    async def test_solve_budget_allocation_multi_resource(self):
        """Test solve_budget_allocation with multiple resources."""
        from chuk_mcp_solver.server import solve_budget_allocation

        response = await solve_budget_allocation(
            items=[
                {
                    "id": "feature_A",
                    "cost": 5000,
                    "value": 10000,
                    "resources_required": {"headcount": 2, "time": 3},
                },
                {
                    "id": "feature_B",
                    "cost": 3000,
                    "value": 7000,
                    "resources_required": {"headcount": 1, "time": 2},
                },
            ],
            budgets=[
                {"resource": "money", "limit": 10000},
                {"resource": "headcount", "limit": 3},
                {"resource": "time", "limit": 4},
            ],
            objective="maximize_value",
        )

        assert response.status == SolverStatus.OPTIMAL
        assert response.resource_usage.get("headcount", 0) <= 3
        assert response.resource_usage.get("time", 0) <= 4


class TestAllocationEdgeCases:
    """Test edge cases and error handling."""

    async def test_single_item(self, solver):
        """Test allocation with single item."""
        request = SolveBudgetAllocationRequest(
            items=[Item(id="item_A", cost=5000, value=10000)],
            budgets=[BudgetConstraint(resource="money", limit=10000)],
            objective=AllocationObjective.MAXIMIZE_VALUE,
        )

        cpsat_request = convert_allocation_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_allocation_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        assert response.selected_items == ["item_A"]

    async def test_infeasible_dependencies(self, solver):
        """Test allocation with infeasible dependency chain."""
        request = SolveBudgetAllocationRequest(
            items=[
                Item(id="item_A", cost=5000, value=10000, dependencies=["item_B"]),
                Item(id="item_B", cost=6000, value=8000),
            ],
            budgets=[BudgetConstraint(resource="money", limit=8000)],
            objective=AllocationObjective.MAXIMIZE_VALUE,
        )

        cpsat_request = convert_allocation_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_allocation_response(cpsat_response, request)

        # Can't afford both, so should select just item_B
        assert response.status == SolverStatus.OPTIMAL
        assert "item_A" not in response.selected_items
        assert "item_B" in response.selected_items

    async def test_min_max_items_constraint(self, solver):
        """Test min/max item count constraints."""
        request = SolveBudgetAllocationRequest(
            items=[
                Item(id="item_A", cost=2000, value=5000),
                Item(id="item_B", cost=3000, value=7000),
                Item(id="item_C", cost=4000, value=9000),
            ],
            budgets=[BudgetConstraint(resource="money", limit=10000)],
            objective=AllocationObjective.MAXIMIZE_VALUE,
            min_items=2,  # Must select at least 2 items
        )

        cpsat_request = convert_allocation_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_allocation_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        assert len(response.selected_items) >= 2

    async def test_resource_slack_calculation(self):
        """Test that resource slack is calculated correctly."""
        from chuk_mcp_solver.server import solve_budget_allocation

        response = await solve_budget_allocation(
            items=[
                {"id": "item_A", "cost": 5000, "value": 10000},
            ],
            budgets=[{"resource": "money", "limit": 10000}],
            objective="maximize_value",
        )

        assert response.status == SolverStatus.OPTIMAL
        # Should have 5000 slack (10000 limit - 5000 used)
        assert response.resource_slack["money"] == 5000
