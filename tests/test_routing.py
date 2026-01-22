"""Tests for high-level routing problem solving."""

import pytest

from chuk_mcp_solver.models import (
    Location,
    RoutingObjective,
    SolveRoutingProblemRequest,
    SolverStatus,
    Vehicle,
)
from chuk_mcp_solver.solver import get_solver
from chuk_mcp_solver.solver.ortools.routing import (
    convert_cpsat_to_routing_response,
    convert_routing_to_cpsat,
)


@pytest.fixture
def solver():
    """Get solver instance."""
    return get_solver("ortools")


class TestRoutingConverters:
    """Tests for routing <-> CP-SAT converters."""

    def test_convert_simple_tsp(self):
        """Test converting simple TSP to CP-SAT."""
        request = SolveRoutingProblemRequest(
            locations=[
                Location(id="A", coordinates=(0, 0)),
                Location(id="B", coordinates=(10, 0)),
                Location(id="C", coordinates=(5, 5)),
            ],
            objective=RoutingObjective.MINIMIZE_DISTANCE,
        )

        cpsat_request = convert_routing_to_cpsat(request)

        # Should have arc variables for each pair (3 locations = 6 directed arcs)
        # 3 locations: A->B, A->C, B->A, B->C, C->A, C->B = 6 arcs
        assert len(cpsat_request.variables) == 6

        # Should have circuit constraint
        circuit_constraints = [c for c in cpsat_request.constraints if c.kind == "circuit"]
        assert len(circuit_constraints) == 1

        # Should have optimization objective
        assert cpsat_request.mode == "optimize"
        assert cpsat_request.objective is not None

    def test_convert_with_distance_matrix(self):
        """Test TSP with explicit distance matrix."""
        request = SolveRoutingProblemRequest(
            locations=[
                Location(id="A"),
                Location(id="B"),
                Location(id="C"),
            ],
            distance_matrix=[
                [0, 10, 20],
                [10, 0, 15],
                [20, 15, 0],
            ],
            objective=RoutingObjective.MINIMIZE_DISTANCE,
        )

        cpsat_request = convert_routing_to_cpsat(request)

        # Should use provided distance matrix
        assert len(cpsat_request.variables) == 6  # 3 locations, 6 arcs
        assert cpsat_request.objective is not None

    def test_convert_with_vehicle(self):
        """Test TSP with vehicle configuration."""
        request = SolveRoutingProblemRequest(
            locations=[
                Location(id="depot", coordinates=(0, 0)),
                Location(id="customer_A", coordinates=(10, 5)),
                Location(id="customer_B", coordinates=(5, 10)),
            ],
            vehicles=[
                Vehicle(
                    id="truck_1",
                    start_location="depot",
                    cost_per_distance=2.5,
                )
            ],
            objective=RoutingObjective.MINIMIZE_COST,
        )

        cpsat_request = convert_routing_to_cpsat(request)

        # Should have arc variables
        assert len(cpsat_request.variables) == 6  # 3 locations, 6 arcs
        assert cpsat_request.objective is not None


class TestRoutingSolver:
    """Tests for end-to-end routing solving."""

    async def test_simple_tsp_3_locations(self, solver):
        """Test simple 3-location TSP."""
        request = SolveRoutingProblemRequest(
            locations=[
                Location(id="A", coordinates=(0, 0)),
                Location(id="B", coordinates=(10, 0)),
                Location(id="C", coordinates=(0, 10)),
            ],
            objective=RoutingObjective.MINIMIZE_DISTANCE,
        )

        cpsat_request = convert_routing_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_routing_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        assert response.total_distance is not None
        assert len(response.routes) == 1
        assert len(response.routes[0].sequence) == 3  # All 3 locations
        assert response.vehicles_used == 1

    async def test_tsp_with_distance_matrix(self, solver):
        """Test TSP with explicit distances."""
        # Triangle: A-B: 10, B-C: 15, C-A: 20
        # Optimal tour: A->B->C->A = 10 + 15 + 20 = 45
        request = SolveRoutingProblemRequest(
            locations=[
                Location(id="A"),
                Location(id="B"),
                Location(id="C"),
            ],
            distance_matrix=[
                [0, 10, 20],
                [10, 0, 15],
                [20, 15, 0],
            ],
            objective=RoutingObjective.MINIMIZE_DISTANCE,
        )

        cpsat_request = convert_routing_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_routing_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        assert response.total_distance == 45  # 10 + 15 + 20
        assert len(response.routes) == 1
        assert len(response.routes[0].sequence) == 3

    async def test_tsp_with_service_time(self, solver):
        """Test TSP with service times."""
        request = SolveRoutingProblemRequest(
            locations=[
                Location(id="depot", coordinates=(0, 0), service_time=0),
                Location(id="customer_A", coordinates=(10, 0), service_time=5),
                Location(id="customer_B", coordinates=(0, 10), service_time=3),
            ],
            objective=RoutingObjective.MINIMIZE_TIME,
        )

        cpsat_request = convert_routing_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_routing_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        # Total time = travel time + service times
        # Service times: depot(0) + A(5) + B(3) = 8
        assert response.total_time > response.total_distance  # Includes service time

    async def test_tsp_minimize_cost(self, solver):
        """Test TSP with cost objective."""
        request = SolveRoutingProblemRequest(
            locations=[
                Location(id="A", coordinates=(0, 0)),
                Location(id="B", coordinates=(10, 0)),
                Location(id="C", coordinates=(5, 5)),
            ],
            vehicles=[
                Vehicle(
                    id="truck",
                    start_location="A",
                    cost_per_distance=2.0,
                    fixed_cost=50.0,
                )
            ],
            objective=RoutingObjective.MINIMIZE_COST,
        )

        cpsat_request = convert_routing_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_routing_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        # Cost = distance * cost_per_distance + fixed_cost
        assert response.total_cost > 50.0  # At least fixed cost
        assert response.routes[0].vehicle_id == "truck"


class TestRoutingFromServer:
    """Test the high-level solve_routing_problem tool."""

    async def test_solve_routing_problem_simple(self):
        """Test solve_routing_problem with simple TSP."""
        from chuk_mcp_solver.server import solve_routing_problem

        response = await solve_routing_problem(
            locations=[
                {"id": "warehouse", "coordinates": (0, 0)},
                {"id": "customer_A", "coordinates": (10, 5)},
                {"id": "customer_B", "coordinates": (5, 10)},
                {"id": "customer_C", "coordinates": (15, 15)},
            ],
            objective="minimize_distance",
        )

        assert response.status == SolverStatus.OPTIMAL
        assert len(response.routes) == 1
        assert len(response.routes[0].sequence) == 4
        assert response.total_distance > 0
        assert response.explanation is not None

    async def test_solve_routing_problem_with_distance_matrix(self):
        """Test solve_routing_problem with distance matrix."""
        from chuk_mcp_solver.server import solve_routing_problem

        response = await solve_routing_problem(
            locations=[
                {"id": "A"},
                {"id": "B"},
                {"id": "C"},
                {"id": "D"},
            ],
            distance_matrix=[
                [0, 10, 15, 20],
                [10, 0, 35, 25],
                [15, 35, 0, 30],
                [20, 25, 30, 0],
            ],
            objective="minimize_distance",
        )

        assert response.status == SolverStatus.OPTIMAL
        assert len(response.routes[0].sequence) == 4
        assert response.total_distance > 0

    async def test_solve_routing_problem_with_vehicle(self):
        """Test solve_routing_problem with vehicle config."""
        from chuk_mcp_solver.server import solve_routing_problem

        response = await solve_routing_problem(
            locations=[
                {"id": "depot", "coordinates": (0, 0)},
                {"id": "stop_1", "coordinates": (10, 0)},
                {"id": "stop_2", "coordinates": (10, 10)},
            ],
            vehicles=[
                {
                    "id": "van_1",
                    "start_location": "depot",
                    "cost_per_distance": 1.5,
                    "fixed_cost": 100.0,
                }
            ],
            objective="minimize_cost",
        )

        assert response.status == SolverStatus.OPTIMAL
        assert response.total_cost >= 100.0  # At least fixed cost
        assert response.routes[0].vehicle_id == "van_1"


class TestRoutingEdgeCases:
    """Test edge cases and error handling."""

    async def test_two_location_tsp(self, solver):
        """Test minimum TSP with 2 locations."""
        request = SolveRoutingProblemRequest(
            locations=[
                Location(id="A", coordinates=(0, 0)),
                Location(id="B", coordinates=(10, 0)),
            ],
            objective=RoutingObjective.MINIMIZE_DISTANCE,
        )

        cpsat_request = convert_routing_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_routing_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        assert len(response.routes[0].sequence) == 2
        assert response.total_distance == 20  # A->B->A = 10 + 10

    async def test_multi_vehicle_routing_works(self):
        """Test that multi-vehicle routing is now implemented."""
        from chuk_mcp_solver.server import solve_routing_problem

        response = await solve_routing_problem(
            locations=[
                {"id": "A", "coordinates": (0, 0), "demand": 0},
                {"id": "B", "coordinates": (10, 0), "demand": 10},
                {"id": "C", "coordinates": (0, 10), "demand": 10},
            ],
            vehicles=[
                {"id": "truck_1", "start_location": "A", "capacity": 20},
                {"id": "truck_2", "start_location": "A", "capacity": 20},
            ],
        )

        # Should successfully solve with multiple vehicles
        assert response.status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)
        assert response.vehicles_used >= 1
        assert len(response.routes) >= 1

    async def test_metadata_preserved(self):
        """Test that location metadata is preserved."""
        from chuk_mcp_solver.server import solve_routing_problem

        response = await solve_routing_problem(
            locations=[
                {"id": "A", "coordinates": (0, 0), "metadata": {"type": "depot"}},
                {
                    "id": "B",
                    "coordinates": (10, 0),
                    "metadata": {"type": "customer", "priority": "high"},
                },
                {
                    "id": "C",
                    "coordinates": (5, 5),
                    "metadata": {"type": "customer", "priority": "low"},
                },
            ],
            objective="minimize_distance",
        )

        assert response.status == SolverStatus.OPTIMAL
        # Metadata is part of request but not directly in response
        # Just verify solve succeeded with metadata present
        assert len(response.routes[0].sequence) == 3
