"""MCP server for constraint and optimization solving.

Exposes constraint solving and optimization capabilities via MCP tools.
"""

import logging
import sys

from chuk_mcp_server import ChukMCPServer, tool

from chuk_mcp_solver.models import (
    Agent,
    AllocationObjective,
    AssignmentObjective,
    AssignmentTask,
    BudgetConstraint,
    Item,
    Location,
    Resource,
    RoutingObjective,
    SchedulingObjective,
    SolveAssignmentProblemRequest,
    SolveAssignmentProblemResponse,
    SolveBudgetAllocationRequest,
    SolveBudgetAllocationResponse,
    SolveConstraintModelRequest,
    SolveRoutingProblemRequest,
    SolveRoutingProblemResponse,
    SolveSchedulingProblemRequest,
    SolveSchedulingProblemResponse,
    Task,
    Vehicle,
)
from chuk_mcp_solver.providers import get_provider_for_tool
from chuk_mcp_solver.solver.ortools.allocation import (
    convert_allocation_to_cpsat,
    convert_cpsat_to_allocation_response,
)
from chuk_mcp_solver.solver.ortools.assignment import (
    convert_assignment_to_cpsat,
    convert_cpsat_to_assignment_response,
)
from chuk_mcp_solver.solver.ortools.routing import (
    convert_cpsat_to_routing_response,
    convert_routing_to_cpsat,
)
from chuk_mcp_solver.solver.ortools.scheduling import (
    convert_cpsat_to_scheduling_response,
    convert_scheduling_to_cpsat,
)

logger = logging.getLogger(__name__)


@tool  # type: ignore[arg-type]
async def solve_constraint_model(
    mode: str,
    variables: list[dict],
    constraints: list[dict],
    objective: dict | None = None,
    search: dict | None = None,
) -> dict:
    """Solve a general constraint or optimization model.

    This tool solves discrete optimization and constraint satisfaction problems.
    It supports integer and boolean variables, linear constraints, global constraints
    (all_different, element, table), implications, and linear objectives.

    Use cases include:
    - Project scheduling and resource allocation
    - Sudoku and logic puzzles
    - Configuration optimization
    - Tool/model selection under constraints
    - Routing and assignment problems
    - Budget allocation

    Args:
        mode: Solver mode - 'satisfy' to find any feasible solution,
              'optimize' to find the best solution according to the objective.
        variables: List of decision variables, each with:
            - id (str): Unique identifier
            - domain (dict): Domain specification with:
                - type (str): 'bool' or 'integer'
                - lower (int): Lower bound for integers (default 0)
                - upper (int): Upper bound for integers (default 1)
            - metadata (dict, optional): Context for explanations
        constraints: List of constraints, each with:
            - id (str): Unique identifier
            - kind (str): Constraint type - 'linear', 'all_different', 'element',
                         'table', or 'implication'
            - params (dict): Constraint-specific parameters:
                For 'linear': terms (list of {var, coef}), sense ('<=', '>=', '=='), rhs (number)
                For 'all_different': vars (list of variable ids)
                For 'element': index_var (str), array (list of int), target_var (str)
                For 'table': vars (list of str), allowed_tuples (list of lists)
                For 'implication': if_var (str), then (nested constraint dict)
            - metadata (dict, optional): Description and context
        objective: Optional objective function (required if mode='optimize'):
            - sense (str): 'min' or 'max'
            - terms (list): Linear terms as {var, coef}
            - metadata (dict, optional): Description
        search: Optional search configuration:
            - max_time_ms (int): Maximum solver time in milliseconds
            - max_solutions (int): Maximum solutions to return (default 1)

    Returns:
        SolveConstraintModelResponse containing:
            - status: 'optimal', 'feasible', 'satisfied', 'infeasible', 'unbounded',
                     'timeout', or 'error'
            - objective_value: Objective value if applicable
            - solutions: List of solutions with variable assignments
            - explanation: Human-readable summary and binding constraints

    Tips for LLMs:
        - Start with a small model to test; gradually add complexity.
        - For Sudoku: use 'all_different' constraints for rows, columns, and blocks.
        - For scheduling: use linear constraints for precedence and capacity.
        - Variable metadata is useful for building readable explanations.
        - Constraint metadata helps identify which constraints are tight.
        - If infeasible, check constraint metadata to diagnose conflicts.
        - Use 'satisfy' mode for puzzles; 'optimize' mode for cost/time minimization.

    Example (simple knapsack):
        ```python
        response = await solve_constraint_model(
            mode="optimize",
            variables=[
                {"id": "take_item_1", "domain": {"type": "bool"}},
                {"id": "take_item_2", "domain": {"type": "bool"}},
            ],
            constraints=[
                {
                    "id": "capacity",
                    "kind": "linear",
                    "params": {
                        "terms": [
                            {"var": "take_item_1", "coef": 3},
                            {"var": "take_item_2", "coef": 5},
                        ],
                        "sense": "<=",
                        "rhs": 7,
                    },
                }
            ],
            objective={
                "sense": "max",
                "terms": [
                    {"var": "take_item_1", "coef": 10},
                    {"var": "take_item_2", "coef": 15},
                ],
            },
        )
        ```
    """
    # Construct request model from dict params (Pydantic will validate)
    request = SolveConstraintModelRequest(
        mode=mode,  # type: ignore[arg-type]
        variables=variables,  # type: ignore[arg-type]
        constraints=constraints,  # type: ignore[arg-type]
        objective=objective,  # type: ignore[arg-type]
        search=search,  # type: ignore[arg-type]
    )

    # Get provider and solve
    provider = get_provider_for_tool("solve_constraint_model")
    response = await provider.solve_constraint_model(request)

    # Convert response to dict for MCP (mode='json' ensures enums are strings)
    return response.model_dump(mode="json")


@tool  # type: ignore[arg-type]
async def solve_scheduling_problem(
    tasks: list[Task],
    resources: list[Resource] | None = None,
    objective: SchedulingObjective = SchedulingObjective.MINIMIZE_MAKESPAN,
    max_time_ms: int = 60000,
) -> SolveSchedulingProblemResponse:
    """Solve a task scheduling problem with dependencies and resource constraints.

    This is a high-level interface for scheduling problems. Use this instead of
    solve_constraint_model when you have tasks with durations, dependencies,
    and resource constraints. The solver automatically builds the appropriate
    CP-SAT model.

    Args:
        tasks: List of Task objects to schedule (id, duration required; dependencies, resources, etc. optional)
        resources: Optional list of Resource objects with capacity constraints
        objective: SchedulingObjective enum (MINIMIZE_MAKESPAN, MINIMIZE_COST, or MINIMIZE_LATENESS)
        max_time_ms: Maximum solver time in milliseconds (default 60000)

    Returns:
        SolveSchedulingProblemResponse containing:
            - status: Solution status
            - makespan: Project completion time
            - schedule: List of task assignments with start/end times
            - resource_utilization: Resource usage summary
            - critical_path: Task IDs on critical path
            - solve_time_ms: Actual solve time
            - optimality_gap: Gap from best bound
            - explanation: Human-readable summary

    Tips for LLMs:
        - Extract task durations from natural language (e.g., "takes 2 hours" -> duration: 2)
        - Parse dependencies carefully (e.g., "A before B" -> B depends on A)
        - Default resource capacity to system constraints if not specified
        - If user says "as fast as possible", use minimize_makespan
        - Check for circular dependencies before solving
        - If infeasible, check for conflicting deadlines or impossible dependencies

    Example (simple project schedule):
        ```python
        response = await solve_scheduling_problem(
            tasks=[
                {"id": "build", "duration": 10, "dependencies": []},
                {"id": "test", "duration": 5, "dependencies": ["build"]},
                {"id": "deploy", "duration": 3, "dependencies": ["test"]}
            ],
            objective="minimize_makespan"
        )
        # Returns optimal schedule with makespan = 18
        ```

    Example (with resource constraints):
        ```python
        response = await solve_scheduling_problem(
            tasks=[
                {"id": "task_a", "duration": 5, "resources_required": {"cpu": 2}},
                {"id": "task_b", "duration": 3, "resources_required": {"cpu": 3}},
            ],
            resources=[{"id": "cpu", "capacity": 4}],
            objective="minimize_makespan"
        )
        # Returns schedule respecting CPU capacity
        ```
    """
    # Construct request model (params are already validated Pydantic models)
    request = SolveSchedulingProblemRequest(
        tasks=tasks,
        resources=resources or [],
        objective=objective,
        max_time_ms=max_time_ms,
    )

    # Convert to CP-SAT model
    cpsat_request = convert_scheduling_to_cpsat(request)

    # Solve using CP-SAT
    provider = get_provider_for_tool("solve_constraint_model")
    cpsat_response = await provider.solve_constraint_model(cpsat_request)

    # Convert response back to scheduling domain
    response = convert_cpsat_to_scheduling_response(cpsat_response, request)

    return response


@tool  # type: ignore[arg-type]
async def solve_routing_problem(
    locations: list[Location],
    vehicles: list[Vehicle] | None = None,
    distance_matrix: list[list[int]] | None = None,
    objective: RoutingObjective = RoutingObjective.MINIMIZE_DISTANCE,
    max_time_ms: int = 60000,
) -> SolveRoutingProblemResponse:
    """Solve vehicle routing problems (TSP/VRP) with optimal route planning.

    Find optimal routes for vehicles visiting locations. Supports single-vehicle TSP,
    multi-vehicle VRP with capacity constraints, and multiple optimization objectives.

    Args:
        locations: List of locations to visit, each with:
            - id: Unique identifier (required)
            - coordinates: (x, y) tuple for Euclidean distance (optional if distance_matrix provided)
            - demand: Load to pick up at this location (default 0)
            - service_time: Time spent at location in minutes (default 0)
        vehicles: List of vehicles (optional, defaults to single vehicle if omitted):
            - id: Vehicle identifier (required)
            - capacity: Maximum load capacity (default unlimited)
            - start_location: Starting location ID (required)
            - cost_per_distance: Cost per unit distance (default 1.0)
            - fixed_cost: Fixed cost if vehicle is used (default 0.0)
        distance_matrix: Optional distance matrix [i][j] = distance from location i to j.
            If omitted, uses Euclidean distance from coordinates.
        objective: Optimization goal (default "minimize_distance"):
            - "minimize_distance": Shortest total route length
            - "minimize_time": Shortest total time (distance + service times)
            - "minimize_cost": Lowest total cost (fixed + distance costs)
            - "minimize_vehicles": Use fewest vehicles possible
        max_time_ms: Solver time limit in milliseconds (default 60000)

    Returns:
        SolveRoutingProblemResponse with:
            - status: OPTIMAL, FEASIBLE, or INFEASIBLE
            - routes: List of routes, each with vehicle_id, sequence of location IDs, total_distance, load_timeline
            - total_distance: Sum of all route distances
            - total_cost: Total cost across all routes
            - vehicles_used: Number of vehicles actually used
            - explanation: Human-readable summary

    Tips for LLMs:
        - **TSP (single vehicle)**: Omit vehicles parameter or provide one vehicle
        - **VRP (multiple vehicles)**: Provide multiple vehicles with capacity limits
        - **Capacity constraints**: Set demand per location and capacity per vehicle
        - **Use coordinates** for geographic routing (automatically calculates distances)
        - **Use distance_matrix** when you have pre-computed distances or non-Euclidean metrics
        - **minimize_vehicles**: When you want to use as few vehicles as possible
        - **minimize_cost**: When vehicles have different costs (e.g., small truck vs large truck)
        - First location in route sequence is always the start location
        - Routes automatically return to start location (depot)

    Example - Simple TSP:
        response = await solve_routing_problem(
            locations=[
                {"id": "warehouse", "coordinates": (0, 0)},
                {"id": "store_A", "coordinates": (10, 5)},
                {"id": "store_B", "coordinates": (5, 10)},
            ]
        )
        # Single vehicle visits all locations, returns to warehouse

    Example - Multi-Vehicle VRP:
        response = await solve_routing_problem(
            locations=[
                {"id": "depot", "coordinates": (0, 0), "demand": 0},
                {"id": "customer_1", "coordinates": (10, 5), "demand": 15},
                {"id": "customer_2", "coordinates": (5, 10), "demand": 20},
                {"id": "customer_3", "coordinates": (15, 15), "demand": 25},
            ],
            vehicles=[
                {"id": "truck_1", "capacity": 50, "start_location": "depot"},
                {"id": "truck_2", "capacity": 40, "start_location": "depot"},
            ],
            objective="minimize_distance"
        )
        # Returns optimal routes respecting capacity limits

    Example - Minimize Fleet Size:
        response = await solve_routing_problem(
            locations=[...],  # 10 customers
            vehicles=[
                {"id": "truck_1", "capacity": 100, "start_location": "depot"},
                {"id": "truck_2", "capacity": 100, "start_location": "depot"},
                {"id": "truck_3", "capacity": 100, "start_location": "depot"},
            ],
            objective="minimize_vehicles"
        )
        # Uses minimum number of trucks needed to serve all customers
    """
    # Construct request model (params are already validated Pydantic models)
    request = SolveRoutingProblemRequest(
        locations=locations,
        vehicles=vehicles or [],
        distance_matrix=distance_matrix,
        objective=objective,
        max_time_ms=max_time_ms,
    )

    # Convert to CP-SAT model
    cpsat_request = convert_routing_to_cpsat(request)

    # Solve using CP-SAT
    provider = get_provider_for_tool("solve_constraint_model")
    cpsat_response = await provider.solve_constraint_model(cpsat_request)

    # Convert response back to routing domain
    response = convert_cpsat_to_routing_response(cpsat_response, request)

    return response


@tool  # type: ignore[arg-type]
async def solve_budget_allocation(
    items: list[Item],
    budgets: list[BudgetConstraint],
    objective: AllocationObjective = AllocationObjective.MAXIMIZE_VALUE,
    min_value_threshold: float | None = None,
    max_cost_threshold: float | None = None,
    min_items: int | None = None,
    max_items: int | None = None,
    max_time_ms: int = 60000,
) -> SolveBudgetAllocationResponse:
    """Solve a budget allocation or knapsack problem.

    This is a high-level interface for budget allocation and portfolio selection problems.
    Use this instead of solve_constraint_model when you need to select items under
    budget constraints with dependencies and conflicts.

    Args:
        items: List of items to choose from, each with:
            - id (str): Unique item identifier
            - cost (float): Cost of selecting this item
            - value (float): Value/benefit of this item (ROI, utility, priority score)
            - resources_required (dict, optional): {resource_name: amount} dict for multi-resource constraints
            - dependencies (list, optional): Item IDs that must also be selected if this item is selected
            - conflicts (list, optional): Item IDs that cannot be selected together with this item
            - metadata (dict, optional): Additional context
        budgets: List of budget constraints, each with:
            - resource (str): Resource name (e.g., "money", "time", "headcount")
            - limit (float): Maximum amount available
            - penalty_per_unit_over (float, optional): Penalty for exceeding (default 0 = hard constraint)
        objective: Optimization goal - 'maximize_value', 'maximize_count', or 'minimize_cost'
        min_value_threshold: Optional minimum total value required
        max_cost_threshold: Optional maximum total cost allowed
        min_items: Optional minimum number of items to select
        max_items: Optional maximum number of items to select
        max_time_ms: Maximum solver time in milliseconds (default 60000)

    Returns:
        SolveBudgetAllocationResponse containing:
            - status: Solution status
            - selected_items: List of selected item IDs
            - total_cost: Total cost of selected items
            - total_value: Total value of selected items
            - resource_usage: Resource consumption by resource name
            - resource_slack: Unused capacity by resource name
            - solve_time_ms: Actual solve time
            - optimality_gap: Gap from best bound
            - explanation: Human-readable summary

    Tips for LLMs:
        - For portfolio selection: items are projects/investments, budgets are capital/resources
        - For feature prioritization: items are features, value is business value, cost is effort
        - For campaign allocation: items are campaigns, budgets are ad spend across channels
        - Dependencies model "must have both or neither" relationships
        - Conflicts model "can only choose one" relationships
        - Use maximize_value for ROI optimization
        - Use maximize_count to get as many items as possible under budget

    Example (Simple Knapsack)::

        response = await solve_budget_allocation(
            items=[
                {"id": "project_A", "cost": 5000, "value": 12000},
                {"id": "project_B", "cost": 3000, "value": 7000},
                {"id": "project_C", "cost": 4000, "value": 9000},
            ],
            budgets=[
                {"resource": "money", "limit": 10000}
            ],
            objective="maximize_value"
        )
        # Returns optimal selection maximizing value under $10k budget

    Example (With Dependencies)::

        response = await solve_budget_allocation(
            items=[
                {"id": "backend", "cost": 8000, "value": 5000},
                {"id": "frontend", "cost": 6000, "value": 8000, "dependencies": ["backend"]},
                {"id": "mobile", "cost": 7000, "value": 6000, "dependencies": ["backend"]},
            ],
            budgets=[
                {"resource": "money", "limit": 15000}
            ],
            objective="maximize_value"
        )
        # Frontend requires backend, so solver considers dependencies

    Example (Multi-Resource)::

        response = await solve_budget_allocation(
            items=[
                {"id": "feature_A", "cost": 5000, "value": 10000,
                 "resources_required": {"headcount": 2, "time": 3}},
                {"id": "feature_B", "cost": 3000, "value": 7000,
                 "resources_required": {"headcount": 1, "time": 2}},
            ],
            budgets=[
                {"resource": "money", "limit": 10000},
                {"resource": "headcount", "limit": 3},
                {"resource": "time", "limit": 4}
            ],
            objective="maximize_value"
        )
        # Respects multiple resource constraints simultaneously
    """
    # Construct request model (params are already validated Pydantic models)
    request = SolveBudgetAllocationRequest(
        items=items,
        budgets=budgets,
        objective=objective,
        min_value_threshold=min_value_threshold,
        max_cost_threshold=max_cost_threshold,
        min_items=min_items,
        max_items=max_items,
        max_time_ms=max_time_ms,
    )

    # Convert to CP-SAT model
    cpsat_request = convert_allocation_to_cpsat(request)

    # Solve using CP-SAT
    provider = get_provider_for_tool("solve_constraint_model")
    cpsat_response = await provider.solve_constraint_model(cpsat_request)

    # Convert response back to allocation domain
    response = convert_cpsat_to_allocation_response(cpsat_response, request)

    return response


@tool  # type: ignore[arg-type]
async def solve_assignment_problem(
    agents: list[Agent],
    tasks: list[AssignmentTask],
    cost_matrix: list[list[float]] | None = None,
    objective: AssignmentObjective = AssignmentObjective.MINIMIZE_COST,
    force_assign_all: bool = True,
    max_time_ms: int = 60000,
) -> SolveAssignmentProblemResponse:
    """Solve a task assignment problem.

    This is a high-level interface for assignment and matching problems. Use this instead
    of solve_constraint_model when you need to assign tasks to agents/workers with
    capacity and skill constraints.

    Args:
        agents: List of agents available to perform tasks, each with:
            - id (str): Unique agent identifier
            - capacity (int, optional): Maximum number of tasks (default 1)
            - skills (list, optional): Skills this agent possesses
            - cost_multiplier (float, optional): Cost multiplier (default 1.0)
            - metadata (dict, optional): Additional context
        tasks: List of tasks to be assigned, each with:
            - id (str): Unique task identifier
            - required_skills (list, optional): Skills required for this task
            - duration (int, optional): Task duration/workload (default 1)
            - priority (int, optional): Task priority (default 1)
            - metadata (dict, optional): Additional context
        cost_matrix: Optional cost matrix where [i][j] = cost to assign task i to agent j.
                    If not provided, uses agent.cost_multiplier * task.duration
        objective: Optimization goal - 'minimize_cost', 'maximize_assignments', or 'balance_load'
        force_assign_all: If True, all tasks must be assigned (infeasible if not possible).
                         If False, some tasks can remain unassigned.
        max_time_ms: Maximum solver time in milliseconds (default 60000)

    Returns:
        SolveAssignmentProblemResponse containing:
            - status: Solution status
            - assignments: List of task-to-agent assignments
            - unassigned_tasks: Tasks that could not be assigned
            - agent_load: Number of tasks assigned to each agent
            - total_cost: Total cost of all assignments
            - solve_time_ms: Actual solve time
            - optimality_gap: Gap from best bound
            - explanation: Human-readable summary

    Tips for LLMs:
        - For task assignment: agents are workers/machines, tasks are jobs/work items
        - For matching: agents are resources, tasks are requests to match
        - Skills create hard constraints (incompatible if skills don't match)
        - Use minimize_cost for cost-optimal assignments
        - Use maximize_assignments when some tasks are optional
        - Use balance_load to distribute work evenly across agents

    Example (Simple Assignment)::

        response = await solve_assignment_problem(
            agents=[
                {"id": "worker_1", "capacity": 2, "cost_multiplier": 1.0},
                {"id": "worker_2", "capacity": 2, "cost_multiplier": 1.5},
            ],
            tasks=[
                {"id": "task_A", "duration": 3},
                {"id": "task_B", "duration": 2},
                {"id": "task_C", "duration": 1},
            ],
            objective="minimize_cost"
        )
        # Returns cost-optimal assignment respecting capacity

    Example (With Skills)::

        response = await solve_assignment_problem(
            agents=[
                {"id": "dev_1", "capacity": 3, "skills": ["python", "docker"]},
                {"id": "dev_2", "capacity": 2, "skills": ["python", "react"]},
            ],
            tasks=[
                {"id": "backend", "duration": 5, "required_skills": ["python", "docker"]},
                {"id": "frontend", "duration": 4, "required_skills": ["react"]},
            ],
            objective="minimize_cost"
        )
        # Only assigns tasks to agents with matching skills

    Example (Balance Load)::

        response = await solve_assignment_problem(
            agents=[
                {"id": "server_1", "capacity": 10},
                {"id": "server_2", "capacity": 10},
                {"id": "server_3", "capacity": 10},
            ],
            tasks=[
                {"id": f"job_{i}", "duration": 1} for i in range(15)
            ],
            objective="balance_load"
        )
        # Distributes tasks evenly across servers (5 per server)
    """
    # Construct request model (params are already validated Pydantic models)
    request = SolveAssignmentProblemRequest(
        agents=agents,
        tasks=tasks,
        cost_matrix=cost_matrix,
        objective=objective,
        force_assign_all=force_assign_all,
        max_time_ms=max_time_ms,
    )

    # Convert to CP-SAT model
    cpsat_request = convert_assignment_to_cpsat(request)

    # Solve using CP-SAT
    provider = get_provider_for_tool("solve_constraint_model")
    cpsat_response = await provider.solve_constraint_model(cpsat_request)

    # Convert response back to assignment domain
    response = convert_cpsat_to_assignment_response(cpsat_response, request)

    return response


def main() -> None:
    """Main entry point for the MCP server."""
    # Default to stdio for MCP compatibility (Claude Desktop, mcp-cli)
    transport = "stdio"

    # Allow HTTP mode via command line
    if len(sys.argv) > 1 and sys.argv[1] in ["http", "--http"]:
        transport = "http"
        logger.warning("Starting CHUK MCP Solver in HTTP mode")

    # Suppress logging in STDIO mode
    if transport == "stdio":
        # Set chuk_mcp_server loggers to ERROR only
        logging.getLogger("chuk_mcp_server").setLevel(logging.ERROR)
        logging.getLogger("chuk_mcp_server.core").setLevel(logging.ERROR)
        logging.getLogger("chuk_mcp_server.stdio_transport").setLevel(logging.ERROR)
        # Suppress httpx logging
        logging.getLogger("httpx").setLevel(logging.ERROR)

    # Create and run server
    server = ChukMCPServer("chuk-mcp-solver")

    if transport == "stdio":
        server.run(stdio=True)
    else:
        # Bind to all interfaces for Docker containers
        server.run(host="0.0.0.0", port=8000)  # nosec B104


if __name__ == "__main__":
    main()
