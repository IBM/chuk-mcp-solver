"""Quick test for multi-vehicle VRP implementation."""

import pytest

from chuk_mcp_solver.server import solve_routing_problem


@pytest.mark.asyncio
async def test_basic_2_vehicle_vrp():
    """Test basic 2-vehicle VRP with capacity constraints."""
    locations = [
        {"id": "depot", "coordinates": (0, 0), "demand": 0},
        {"id": "c1", "coordinates": (10, 0), "demand": 30},
        {"id": "c2", "coordinates": (0, 10), "demand": 25},
        {"id": "c3", "coordinates": (10, 10), "demand": 20},
    ]

    vehicles = [
        {"id": "v1", "capacity": 50, "start_location": "depot"},
        {"id": "v2", "capacity": 50, "start_location": "depot"},
    ]

    response = await solve_routing_problem(
        locations=locations,
        vehicles=vehicles,
        objective="minimize_distance",
        max_time_ms=10000,
    )

    print(f"\nStatus: {response.status}")
    print(f"Vehicles used: {response.vehicles_used}")
    print(f"Total distance: {response.total_distance}")

    assert response.status in ("optimal", "feasible")
    assert response.vehicles_used <= 2
    assert response.total_distance > 0
    assert len(response.routes) == response.vehicles_used

    # Verify all customers visited exactly once
    visited_customers = set()
    for route in response.routes:
        print(f"\nRoute for {route.vehicle_id}:")
        print(f"  Sequence: {' → '.join(route.sequence)}")
        print(f"  Distance: {route.total_distance}")
        print(f"  Load timeline: {route.load_timeline}")

        for loc_id in route.sequence:
            if loc_id != "depot":
                assert loc_id not in visited_customers, f"Customer {loc_id} visited multiple times"
                visited_customers.add(loc_id)

    assert len(visited_customers) == 3, "Not all customers visited"
    print("\n✓ All customers visited exactly once")


@pytest.mark.asyncio
async def test_minimize_vehicles():
    """Test that minimize_vehicles uses fewest vehicles possible."""
    locations = [
        {"id": "depot", "coordinates": (0, 0), "demand": 0},
        {"id": "c1", "coordinates": (5, 0), "demand": 10},
        {"id": "c2", "coordinates": (10, 0), "demand": 10},
    ]

    vehicles = [
        {"id": "v1", "capacity": 100, "start_location": "depot", "fixed_cost": 50.0},
        {"id": "v2", "capacity": 100, "start_location": "depot", "fixed_cost": 50.0},
        {"id": "v3", "capacity": 100, "start_location": "depot", "fixed_cost": 50.0},
    ]

    response = await solve_routing_problem(
        locations=locations,
        vehicles=vehicles,
        objective="minimize_vehicles",
        max_time_ms=10000,
    )

    print(f"\nStatus: {response.status}")
    print(f"Vehicles used: {response.vehicles_used} of {len(vehicles)}")

    assert response.status in ("optimal", "feasible")
    # Should use only 1 vehicle since total demand (20) fits in one vehicle (capacity 100)
    assert response.vehicles_used == 1
    print(f"✓ Minimized to {response.vehicles_used} vehicle")


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_basic_2_vehicle_vrp())
    asyncio.run(test_minimize_vehicles())
