"""Pydantic models for constraint solver.

This module defines all data models, enums, and types used throughout the solver.
No magic strings - all constants are defined as enums or module-level constants.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ============================================================================
# Constants
# ============================================================================

# API versioning
API_VERSION = "1.0.0"

# Constraint kinds
CONSTRAINT_KIND_LINEAR = "linear"
CONSTRAINT_KIND_ALL_DIFFERENT = "all_different"
CONSTRAINT_KIND_ELEMENT = "element"
CONSTRAINT_KIND_TABLE = "table"
CONSTRAINT_KIND_IMPLICATION = "implication"
CONSTRAINT_KIND_CUMULATIVE = "cumulative"
CONSTRAINT_KIND_CIRCUIT = "circuit"
CONSTRAINT_KIND_RESERVOIR = "reservoir"
CONSTRAINT_KIND_NO_OVERLAP = "no_overlap"


# ============================================================================
# Enums - No Magic Strings
# ============================================================================


class SolverMode(str, Enum):
    """Solver execution mode."""

    SATISFY = "satisfy"
    OPTIMIZE = "optimize"


class VariableDomainType(str, Enum):
    """Variable domain types supported by the solver."""

    BOOL = "bool"
    INTEGER = "integer"


class ConstraintSense(str, Enum):
    """Comparison operators for linear constraints."""

    LESS_EQUAL = "<="
    GREATER_EQUAL = ">="
    EQUAL = "=="


class ObjectiveSense(str, Enum):
    """Optimization direction."""

    MINIMIZE = "min"
    MAXIMIZE = "max"


class ConstraintKind(str, Enum):
    """Types of constraints supported by the solver."""

    LINEAR = CONSTRAINT_KIND_LINEAR
    ALL_DIFFERENT = CONSTRAINT_KIND_ALL_DIFFERENT
    ELEMENT = CONSTRAINT_KIND_ELEMENT
    TABLE = CONSTRAINT_KIND_TABLE
    IMPLICATION = CONSTRAINT_KIND_IMPLICATION
    CUMULATIVE = CONSTRAINT_KIND_CUMULATIVE
    CIRCUIT = CONSTRAINT_KIND_CIRCUIT
    RESERVOIR = CONSTRAINT_KIND_RESERVOIR
    NO_OVERLAP = CONSTRAINT_KIND_NO_OVERLAP


class SolverStatus(str, Enum):
    """Solution status returned by the solver."""

    OPTIMAL = "optimal"
    FEASIBLE = "feasible"
    SATISFIED = "satisfied"
    INFEASIBLE = "infeasible"
    UNBOUNDED = "unbounded"
    TIMEOUT = "timeout"  # Deprecated: use TIMEOUT_BEST or TIMEOUT_NO_SOLUTION
    TIMEOUT_BEST = "timeout_best"  # Timeout reached but best-so-far solution available
    TIMEOUT_NO_SOLUTION = "timeout_no_solution"  # Timeout reached with no solution found
    ERROR = "error"


# ============================================================================
# Variable Domain Models
# ============================================================================


class VariableDomain(BaseModel):
    """Domain specification for a decision variable.

    Defines the type and bounds for a variable in the constraint model.
    """

    type: VariableDomainType = Field(
        ...,
        description="Variable domain type: 'bool' for binary variables, 'integer' for integer variables",
    )
    lower: int = Field(
        default=0,
        description="Lower bound (inclusive) for integer variables; ignored for bool variables",
    )
    upper: int = Field(
        default=1,
        description="Upper bound (inclusive) for integer variables; ignored for bool variables",
    )


# ============================================================================
# Variable Models
# ============================================================================


class Variable(BaseModel):
    """Decision variable in the constraint model.

    Each variable represents a choice to be made by the solver.
    """

    id: str = Field(
        ...,
        description="Unique identifier for this variable",
        min_length=1,
    )
    domain: VariableDomain = Field(
        ...,
        description="Domain specification (type and bounds)",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional metadata for explanations and context; echoed in solutions",
    )


# ============================================================================
# Constraint Parameter Models
# ============================================================================


class LinearTerm(BaseModel):
    """A term in a linear expression: coefficient * variable."""

    var: str = Field(
        ...,
        description="Variable identifier",
        min_length=1,
    )
    coef: float = Field(
        ...,
        description="Coefficient multiplying the variable",
    )


class LinearConstraintParams(BaseModel):
    """Parameters for a linear constraint: sum(terms) sense rhs."""

    terms: list[LinearTerm] = Field(
        ...,
        description="List of linear terms forming the left-hand side",
        min_length=1,
    )
    sense: ConstraintSense = Field(
        ...,
        description="Comparison operator: '<=', '>=', or '=='",
    )
    rhs: float = Field(
        ...,
        description="Right-hand side constant value",
    )


class AllDifferentParams(BaseModel):
    """Parameters for an all-different constraint."""

    vars: list[str] = Field(
        ...,
        description="List of variable identifiers that must all take different values",
        min_length=2,
    )


class ElementParams(BaseModel):
    """Parameters for an element constraint: target = array[index]."""

    index_var: str = Field(
        ...,
        description="Integer variable used as index into the array",
        min_length=1,
    )
    array: list[int] = Field(
        ...,
        description="Constant integer array to index into",
        min_length=1,
    )
    target_var: str = Field(
        ...,
        description="Variable that equals array[index_var]",
        min_length=1,
    )


class TableParams(BaseModel):
    """Parameters for a table constraint: allowed tuples."""

    vars: list[str] = Field(
        ...,
        description="List of variable identifiers forming the tuple",
        min_length=1,
    )
    allowed_tuples: list[list[int]] = Field(
        ...,
        description="List of allowed integer tuples for the variables",
        min_length=1,
    )


class CumulativeParams(BaseModel):
    """Parameters for a cumulative constraint: resource capacity over time."""

    start_vars: list[str] = Field(
        ...,
        description="List of start time variable identifiers",
        min_length=1,
    )
    duration_vars: list[str] | list[int] = Field(
        ...,
        description="List of duration variable identifiers or constant durations",
        min_length=1,
    )
    demand_vars: list[str] | list[int] = Field(
        ...,
        description="List of demand variable identifiers or constant demands",
        min_length=1,
    )
    capacity: int = Field(
        ...,
        description="Maximum cumulative resource capacity",
        ge=0,
    )


class CircuitParams(BaseModel):
    """Parameters for a circuit constraint: routing/tour problem."""

    arcs: list[tuple[int, int, str]] = Field(
        ...,
        description="List of (from_node, to_node, arc_var) tuples forming possible connections",
        min_length=1,
    )


class ReservoirParams(BaseModel):
    """Parameters for a reservoir constraint: inventory/stock management."""

    time_vars: list[str] = Field(
        ...,
        description="List of time variable identifiers when events occur",
        min_length=1,
    )
    level_changes: list[int] = Field(
        ...,
        description="Change in level at each time point (positive=production, negative=consumption)",
        min_length=1,
    )
    min_level: int = Field(
        default=0,
        description="Minimum reservoir level (default 0)",
    )
    max_level: int = Field(
        ...,
        description="Maximum reservoir level (capacity)",
        ge=0,
    )


class NoOverlapParams(BaseModel):
    """Parameters for a no-overlap constraint: disjunctive scheduling."""

    start_vars: list[str] = Field(
        ...,
        description="List of start time variable identifiers",
        min_length=1,
    )
    duration_vars: list[str] | list[int] = Field(
        ...,
        description="List of duration variable identifiers or constant durations",
        min_length=1,
    )


class ImplicationParams(BaseModel):
    """Parameters for an implication constraint: if bool_var then nested_constraint."""

    if_var: str = Field(
        ...,
        description="Boolean variable: when true, the nested constraint must hold",
        min_length=1,
    )
    then: Constraint = Field(
        ...,
        description="Nested constraint that becomes active when if_var is true",
    )


# ============================================================================
# Constraint Models
# ============================================================================


class Constraint(BaseModel):
    """Constraint in the constraint model.

    Each constraint restricts the values that variables can take.
    """

    id: str = Field(
        ...,
        description="Unique identifier for this constraint",
        min_length=1,
    )
    kind: ConstraintKind = Field(
        ...,
        description="Type of constraint: linear, all_different, element, table, implication, cumulative, circuit, reservoir, or no_overlap",
    )
    params: (
        LinearConstraintParams
        | AllDifferentParams
        | ElementParams
        | TableParams
        | ImplicationParams
        | CumulativeParams
        | CircuitParams
        | ReservoirParams
        | NoOverlapParams
    ) = Field(
        ...,
        description="Parameters specific to the constraint kind",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional metadata for explanations (e.g., human description)",
    )


# ============================================================================
# Objective Models
# ============================================================================


class Objective(BaseModel):
    """Objective function for optimization.

    Defines a linear objective to minimize or maximize.
    Supports multi-objective via lexicographic ordering.
    """

    sense: ObjectiveSense = Field(
        ...,
        description="Optimization direction: 'min' to minimize, 'max' to maximize",
    )
    terms: list[LinearTerm] = Field(
        ...,
        description="Linear terms forming the objective function",
        min_length=1,
    )
    priority: int = Field(
        default=1,
        description="Priority level for lexicographic multi-objective (higher = more important)",
        ge=1,
    )
    weight: float = Field(
        default=1.0,
        description="Weight for weighted-sum multi-objective optimization",
        gt=0.0,
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional explanation/label for the objective",
    )


# ============================================================================
# Search Configuration
# ============================================================================


class SearchStrategy(str, Enum):
    """Search strategy hint for the solver."""

    AUTO = "auto"  # Let solver decide
    FIRST_FAIL = "first_fail"  # Choose variable with smallest domain first
    LARGEST_FIRST = "largest_first"  # Choose variable with largest domain first
    RANDOM = "random"  # Random variable selection
    CHEAPEST_FIRST = "cheapest_first"  # Choose variable with smallest impact


class SearchConfig(BaseModel):
    """Solver search configuration and limits."""

    max_time_ms: int | None = Field(
        default=None,
        description="Maximum solver time in milliseconds",
        ge=1,
    )
    max_solutions: int = Field(
        default=1,
        description="Maximum number of solutions to return",
        ge=1,
    )
    num_search_workers: int | None = Field(
        default=None,
        description="Number of parallel search workers (default: auto)",
        ge=1,
    )
    log_search_progress: bool = Field(
        default=False,
        description="Enable search progress logging",
    )
    warm_start_solution: dict[str, int] | None = Field(
        default=None,
        description="Optional warm-start solution hint (variable_id -> value mapping)",
    )
    random_seed: int | None = Field(
        default=None,
        description="Random seed for deterministic solving (enables reproducible results)",
        ge=0,
    )
    strategy: SearchStrategy = Field(
        default=SearchStrategy.AUTO,
        description="Search strategy hint for variable selection",
    )
    return_partial_solution: bool = Field(
        default=False,
        description="Return best solution found so far if timeout is reached",
    )
    enable_solution_caching: bool = Field(
        default=True,
        description="Cache solutions to avoid re-solving identical problems",
    )


# ============================================================================
# Request Model
# ============================================================================


class SolveConstraintModelRequest(BaseModel):
    """Request to solve a constraint/optimization model.

    This is the main input to the solve_constraint_model tool.
    """

    mode: SolverMode = Field(
        ...,
        description="Solver mode: 'satisfy' to find any feasible solution, 'optimize' to find optimal solution",
    )
    variables: list[Variable] = Field(
        ...,
        description="List of decision variables",
        min_length=1,
    )
    constraints: list[Constraint] = Field(
        ...,
        description="List of constraints",
    )
    objective: Objective | list[Objective] | None = Field(
        default=None,
        description="Objective function(s); required when mode is 'optimize'. Can be single objective or list for multi-objective optimization",
    )
    search: SearchConfig | None = Field(
        default=None,
        description="Optional solver search/limits configuration",
    )


# ============================================================================
# Solution Models
# ============================================================================


class SolutionVariable(BaseModel):
    """Variable value in a solution."""

    id: str = Field(
        ...,
        description="Variable identifier",
    )
    value: float = Field(
        ...,
        description="Assigned value in this solution",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Original metadata from the variable definition",
    )


class Solution(BaseModel):
    """A single solution to the constraint model."""

    variables: list[SolutionVariable] = Field(
        ...,
        description="Variable assignments in this solution",
    )
    derived: dict[str, Any] | None = Field(
        default=None,
        description="Optional derived metrics computed from the solution (e.g., makespan, counts)",
    )


class BindingConstraint(BaseModel):
    """Information about a constraint that is tight/critical in the solution."""

    id: str = Field(
        ...,
        description="Constraint identifier",
    )
    sense: ConstraintSense | None = Field(
        default=None,
        description="Constraint sense (for linear constraints)",
    )
    lhs_value: float = Field(
        ...,
        description="Evaluated left-hand side under the solution",
    )
    rhs: float = Field(
        ...,
        description="Right-hand side value",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional constraint metadata",
    )


class Explanation(BaseModel):
    """Human-readable explanation of the solution."""

    summary: str = Field(
        ...,
        description="High-level textual summary of the result",
    )
    binding_constraints: list[BindingConstraint] = Field(
        default_factory=list,
        description="Constraints that are tight/critical in the solution",
    )


# ============================================================================
# Response Model
# ============================================================================


class SolveConstraintModelResponse(BaseModel):
    """Response from solving a constraint/optimization model."""

    apiversion: str = Field(
        default=API_VERSION,
        description="API version",
    )
    status: SolverStatus = Field(
        ...,
        description="Solution status: optimal, feasible, satisfied, infeasible, unbounded, timeout_best, timeout_no_solution, or error",
    )
    objective_value: float | None = Field(
        default=None,
        description="Objective value for the best solution, if applicable",
    )
    optimality_gap: float | None = Field(
        default=None,
        description="Optimality gap as percentage (0-100) from best bound; only for optimization problems. Lower is better, 0 means proven optimal",
    )
    solve_time_ms: int = Field(
        default=0,
        description="Actual wall-clock solve time in milliseconds",
        ge=0,
    )
    solutions: list[Solution] = Field(
        default_factory=list,
        description="List of solutions; usually length 1 unless max_solutions > 1",
    )
    explanation: Explanation | None = Field(
        default=None,
        description="Optional human-readable explanation of the result",
    )


# ============================================================================
# High-Level Scheduling Models (Phase 4)
# ============================================================================


class Task(BaseModel):
    """A task to be scheduled with duration, dependencies, and resource requirements."""

    id: str = Field(
        ...,
        description="Unique task identifier",
        min_length=1,
    )
    duration: int = Field(
        ...,
        description="Task duration in time units (hours, minutes, etc.)",
        ge=0,
    )
    resources_required: dict[str, int] = Field(
        default_factory=dict,
        description="Resource requirements as {resource_id: amount}",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="List of task IDs that must complete before this task starts",
    )
    earliest_start: int | None = Field(
        default=None,
        description="Optional earliest start time (release time)",
        ge=0,
    )
    deadline: int | None = Field(
        default=None,
        description="Optional deadline (due date)",
        ge=0,
    )
    priority: int = Field(
        default=1,
        description="Task priority (higher = more important)",
        ge=1,
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata for explanations",
    )


class Resource(BaseModel):
    """A resource with capacity constraints."""

    id: str = Field(
        ...,
        description="Unique resource identifier",
        min_length=1,
    )
    capacity: int = Field(
        ...,
        description="Maximum units available at any time",
        ge=0,
    )
    cost_per_unit: float = Field(
        default=0.0,
        description="Optional cost per unit-time for cost optimization",
        ge=0.0,
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata",
    )


class SchedulingObjective(str, Enum):
    """Scheduling optimization objectives."""

    MINIMIZE_MAKESPAN = "minimize_makespan"  # Finish ASAP
    MINIMIZE_COST = "minimize_cost"  # Minimize resource costs
    MINIMIZE_LATENESS = "minimize_lateness"  # Minimize deadline violations


class SolveSchedulingProblemRequest(BaseModel):
    """High-level scheduling problem definition.

    Use this instead of solve_constraint_model when you have tasks with
    durations, dependencies, and resource constraints. The solver will
    automatically build the appropriate CP-SAT model.
    """

    tasks: list[Task] = Field(
        ...,
        description="List of tasks to schedule",
        min_length=1,
    )
    resources: list[Resource] = Field(
        default_factory=list,
        description="Optional list of resources with capacity constraints",
    )
    objective: SchedulingObjective = Field(
        default=SchedulingObjective.MINIMIZE_MAKESPAN,
        description="Optimization objective",
    )
    max_makespan: int | None = Field(
        default=None,
        description="Optional hard deadline for project completion",
        ge=1,
    )
    no_overlap_tasks: list[list[str]] = Field(
        default_factory=list,
        description="Optional groups of tasks that cannot run concurrently",
    )
    max_time_ms: int = Field(
        default=60000,
        description="Maximum solver time in milliseconds",
        ge=1,
    )
    return_partial_solution: bool = Field(
        default=True,
        description="Return best solution found if timeout occurs",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata",
    )


class TaskAssignment(BaseModel):
    """A scheduled task with timing information."""

    task_id: str = Field(
        ...,
        description="Task identifier",
    )
    start_time: int = Field(
        ...,
        description="Task start time",
        ge=0,
    )
    end_time: int = Field(
        ...,
        description="Task end time",
        ge=0,
    )
    resources_used: dict[str, int] = Field(
        default_factory=dict,
        description="Resources allocated to this task",
    )
    on_critical_path: bool = Field(
        default=False,
        description="Whether this task is on the critical path",
    )
    slack: int = Field(
        default=0,
        description="Slack time (how much task can be delayed without affecting makespan)",
        ge=0,
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Original task metadata",
    )


class ResourceUtilization(BaseModel):
    """Resource usage over time."""

    resource_id: str = Field(
        ...,
        description="Resource identifier",
    )
    peak_usage: int = Field(
        ...,
        description="Peak utilization",
        ge=0,
    )
    avg_usage: float = Field(
        ...,
        description="Average utilization",
        ge=0.0,
    )
    capacity: int = Field(
        ...,
        description="Resource capacity",
        ge=0,
    )
    total_cost: float = Field(
        default=0.0,
        description="Total cost (if cost_per_unit defined)",
        ge=0.0,
    )


class SchedulingExplanation(BaseModel):
    """Human-readable explanation of the schedule."""

    summary: str = Field(
        ...,
        description="High-level summary of the result",
    )
    bottlenecks: list[str] = Field(
        default_factory=list,
        description="Identified bottlenecks (e.g., 'Task Deploy limited by available GPUs')",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Suggestions for improvement",
    )
    binding_constraints: list[str] = Field(
        default_factory=list,
        description="Constraints that are tight/critical",
    )


class SolveSchedulingProblemResponse(BaseModel):
    """Scheduling solution with domain-specific details."""

    status: SolverStatus = Field(
        ...,
        description="Solution status",
    )
    makespan: int | None = Field(
        default=None,
        description="Project completion time (max end time of all tasks)",
        ge=0,
    )
    total_cost: float | None = Field(
        default=None,
        description="Total resource cost if applicable",
        ge=0.0,
    )
    schedule: list[TaskAssignment] = Field(
        default_factory=list,
        description="Scheduled tasks with timing",
    )
    resource_utilization: list[ResourceUtilization] = Field(
        default_factory=list,
        description="Resource usage summary",
    )
    critical_path: list[str] = Field(
        default_factory=list,
        description="Task IDs on the critical path",
    )
    solve_time_ms: int = Field(
        default=0,
        description="Actual solve time in milliseconds",
        ge=0,
    )
    optimality_gap: float | None = Field(
        default=None,
        description="Optimality gap percentage",
    )
    explanation: SchedulingExplanation = Field(
        ...,
        description="Human-readable explanation",
    )


# ============================================================================
# Routing Models (Phase 4.1.2)
# ============================================================================


class Location(BaseModel):
    """A location to visit in a routing problem."""

    id: str = Field(
        ...,
        description="Unique location identifier",
        min_length=1,
    )
    coordinates: tuple[float, float] | None = Field(
        default=None,
        description="Optional (latitude, longitude) or (x, y) coordinates",
    )
    service_time: int = Field(
        default=0,
        description="Time spent servicing this location",
        ge=0,
    )
    time_window: tuple[int, int] | None = Field(
        default=None,
        description="Optional (earliest, latest) arrival time window",
    )
    demand: int = Field(
        default=0,
        description="Demand at this location (for capacity-constrained routing)",
        ge=0,
    )
    priority: int = Field(
        default=1,
        description="Location priority (higher = more important)",
        ge=0,
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata",
    )

    @field_validator("coordinates", mode="before")
    @classmethod
    def coerce_coordinates(cls, v: Any) -> Any:
        """Coerce list to tuple for LLM compatibility."""
        if isinstance(v, list) and len(v) == 2:
            return tuple(v)
        return v

    @field_validator("time_window", mode="before")
    @classmethod
    def coerce_time_window(cls, v: Any) -> Any:
        """Coerce list to tuple for LLM compatibility."""
        if isinstance(v, list) and len(v) == 2:
            return tuple(v)
        return v


class Vehicle(BaseModel):
    """A vehicle for routing problems."""

    id: str = Field(
        ...,
        description="Unique vehicle identifier",
        min_length=1,
    )
    capacity: int = Field(
        default=999999,
        description="Maximum load capacity",
        ge=0,
    )
    start_location: str = Field(
        ...,
        description="Starting location ID",
        min_length=1,
    )
    end_location: str | None = Field(
        default=None,
        description="Ending location ID (if different from start for open tours)",
    )
    max_distance: int | None = Field(
        default=None,
        description="Maximum distance this vehicle can travel",
        ge=0,
    )
    max_time: int | None = Field(
        default=None,
        description="Maximum time this vehicle can be in use",
        ge=0,
    )
    cost_per_distance: float = Field(
        default=1.0,
        description="Cost per unit distance",
        ge=0.0,
    )
    fixed_cost: float = Field(
        default=0.0,
        description="Fixed cost if vehicle is used",
        ge=0.0,
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata",
    )


class RoutingObjective(str, Enum):
    """Routing optimization objectives."""

    MINIMIZE_DISTANCE = "minimize_distance"  # Minimize total distance
    MINIMIZE_TIME = "minimize_time"  # Minimize total time
    MINIMIZE_VEHICLES = "minimize_vehicles"  # Use fewest vehicles
    MINIMIZE_COST = "minimize_cost"  # Minimize total cost


class SolveRoutingProblemRequest(BaseModel):
    """High-level routing problem definition.

    Use this for TSP (Traveling Salesman Problem), VRP (Vehicle Routing Problem),
    and delivery route optimization. The solver will automatically build the
    appropriate CP-SAT model using circuit constraints.
    """

    locations: list[Location] = Field(
        ...,
        description="List of locations to visit",
        min_length=2,
    )
    vehicles: list[Vehicle] = Field(
        default_factory=list,
        description="List of vehicles (if empty, assumes single vehicle TSP)",
    )
    distance_matrix: list[list[int]] | None = Field(
        default=None,
        description="Distance matrix where [i][j] = distance from location i to j. If not provided, uses Euclidean distance from coordinates.",
    )
    objective: RoutingObjective = Field(
        default=RoutingObjective.MINIMIZE_DISTANCE,
        description="Optimization objective",
    )
    force_visit_all: bool = Field(
        default=True,
        description="If True, all locations must be visited. If False, some can be skipped.",
    )
    max_route_distance: int | None = Field(
        default=None,
        description="Optional maximum distance for any single route",
        ge=0,
    )
    max_time_ms: int = Field(
        default=60000,
        description="Maximum solver time in milliseconds",
        ge=1,
    )
    return_partial_solution: bool = Field(
        default=True,
        description="Return best solution found if timeout occurs",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata",
    )


class Route(BaseModel):
    """A vehicle route through locations."""

    vehicle_id: str = Field(
        ...,
        description="Vehicle identifier",
    )
    sequence: list[str] = Field(
        ...,
        description="Location IDs in visit order",
    )
    total_distance: int = Field(
        ...,
        description="Total route distance",
        ge=0,
    )
    total_time: int = Field(
        ...,
        description="Total route time including service times",
        ge=0,
    )
    total_cost: float = Field(
        ...,
        description="Total route cost",
        ge=0.0,
    )
    load_timeline: list[tuple[str, int]] = Field(
        default_factory=list,
        description="Load after visiting each location: [(location_id, load), ...]",
    )


class RoutingExplanation(BaseModel):
    """Human-readable explanation of the routing solution."""

    summary: str = Field(
        ...,
        description="High-level summary of the result",
    )
    bottlenecks: list[str] = Field(
        default_factory=list,
        description="Identified bottlenecks (e.g., 'Vehicle capacity constraint forces 2 trips')",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Suggestions for improvement",
    )


class SolveRoutingProblemResponse(BaseModel):
    """Routing solution with domain-specific details."""

    status: SolverStatus = Field(
        ...,
        description="Solution status",
    )
    routes: list[Route] = Field(
        default_factory=list,
        description="Vehicle routes",
    )
    unvisited: list[str] = Field(
        default_factory=list,
        description="Location IDs not visited (if force_visit_all=False)",
    )
    total_distance: int = Field(
        default=0,
        description="Total distance across all routes",
        ge=0,
    )
    total_time: int = Field(
        default=0,
        description="Total time across all routes",
        ge=0,
    )
    total_cost: float = Field(
        default=0.0,
        description="Total cost across all routes",
        ge=0.0,
    )
    vehicles_used: int = Field(
        default=0,
        description="Number of vehicles actually used",
        ge=0,
    )
    solve_time_ms: int = Field(
        default=0,
        description="Actual solve time in milliseconds",
        ge=0,
    )
    optimality_gap: float | None = Field(
        default=None,
        description="Optimality gap percentage",
    )
    explanation: RoutingExplanation = Field(
        ...,
        description="Human-readable explanation",
    )


# ============================================================================
# Budget Allocation Models (Phase 4.1.3)
# ============================================================================


class Item(BaseModel):
    """An item to potentially select in budget allocation."""

    id: str = Field(
        ...,
        description="Unique item identifier",
    )
    cost: float = Field(
        ...,
        description="Cost of selecting this item",
        ge=0.0,
    )
    value: float = Field(
        ...,
        description="Value/benefit of selecting this item (ROI, utility, priority score)",
        ge=0.0,
    )
    resources_required: dict[str, float] = Field(
        default_factory=dict,
        description="Additional resources required (e.g., {'headcount': 2.5, 'servers': 1})",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Item IDs that must also be selected if this item is selected",
    )
    conflicts: list[str] = Field(
        default_factory=list,
        description="Item IDs that cannot be selected together with this item",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for explanations",
    )


class BudgetConstraint(BaseModel):
    """A budget or resource limit."""

    resource: str = Field(
        ...,
        description="Resource name (e.g., 'money', 'time', 'headcount')",
    )
    limit: float = Field(
        ...,
        description="Maximum amount available",
        ge=0.0,
    )
    penalty_per_unit_over: float = Field(
        default=0.0,
        description="Penalty for exceeding limit (0 = hard constraint)",
        ge=0.0,
    )


class AllocationObjective(str, Enum):
    """Budget allocation optimization objectives."""

    MAXIMIZE_VALUE = "maximize_value"
    MAXIMIZE_COUNT = "maximize_count"  # Select as many items as possible
    MINIMIZE_COST = "minimize_cost"  # While meeting value threshold


class SolveBudgetAllocationRequest(BaseModel):
    """High-level budget allocation / knapsack problem definition."""

    items: list[Item] = Field(
        ...,
        min_length=1,
        description="Items to choose from",
    )
    budgets: list[BudgetConstraint] = Field(
        ...,
        min_length=1,
        description="Budget and resource constraints",
    )
    objective: AllocationObjective = Field(
        default=AllocationObjective.MAXIMIZE_VALUE,
        description="Optimization goal",
    )
    min_value_threshold: float | None = Field(
        default=None,
        description="Minimum total value required (optional constraint)",
        ge=0.0,
    )
    max_cost_threshold: float | None = Field(
        default=None,
        description="Maximum total cost allowed (optional constraint)",
        ge=0.0,
    )
    min_items: int | None = Field(
        default=None,
        description="Minimum number of items to select",
        ge=0,
    )
    max_items: int | None = Field(
        default=None,
        description="Maximum number of items to select",
        ge=0,
    )
    max_time_ms: int = Field(
        default=60000,
        description="Maximum solver time in milliseconds",
        ge=1,
    )
    return_partial_solution: bool = Field(
        default=True,
        description="Return best solution found if timeout occurs",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context",
    )


class AllocationExplanation(BaseModel):
    """Human-readable explanation of the allocation solution."""

    summary: str = Field(
        ...,
        description="High-level summary of the result",
    )
    binding_constraints: list[str] = Field(
        default_factory=list,
        description="Constraints that are fully utilized",
    )
    marginal_items: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Items almost selected but excluded",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Suggestions for improvement",
    )


class SolveBudgetAllocationResponse(BaseModel):
    """Budget allocation solution with domain-specific details."""

    status: SolverStatus = Field(
        ...,
        description="Solution status",
    )
    selected_items: list[str] = Field(
        default_factory=list,
        description="IDs of selected items",
    )
    total_cost: float = Field(
        default=0.0,
        description="Total cost of selected items",
        ge=0.0,
    )
    total_value: float = Field(
        default=0.0,
        description="Total value of selected items",
        ge=0.0,
    )
    resource_usage: dict[str, float] = Field(
        default_factory=dict,
        description="Resource consumption by resource name",
    )
    resource_slack: dict[str, float] = Field(
        default_factory=dict,
        description="Unused capacity by resource name",
    )
    solve_time_ms: int = Field(
        default=0,
        description="Actual solve time in milliseconds",
        ge=0,
    )
    optimality_gap: float | None = Field(
        default=None,
        description="Optimality gap percentage",
    )
    explanation: AllocationExplanation = Field(
        ...,
        description="Human-readable explanation",
    )


# ============================================================================
# Assignment Models (Phase 4.1.4)
# ============================================================================


class Agent(BaseModel):
    """An agent that can be assigned tasks."""

    id: str = Field(
        ...,
        description="Unique agent identifier",
    )
    capacity: int = Field(
        default=1,
        description="Maximum number of tasks this agent can handle",
        ge=0,
    )
    skills: list[str] = Field(
        default_factory=list,
        description="Skills this agent possesses",
    )
    cost_multiplier: float = Field(
        default=1.0,
        description="Cost multiplier for this agent",
        ge=0.0,
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for explanations",
    )


class AssignmentTask(BaseModel):
    """A task to be assigned to an agent."""

    id: str = Field(
        ...,
        description="Unique task identifier",
    )
    required_skills: list[str] = Field(
        default_factory=list,
        description="Skills required to perform this task",
    )
    duration: int = Field(
        default=1,
        description="Task duration or workload",
        ge=0,
    )
    priority: int = Field(
        default=1,
        description="Task priority (higher = more important)",
        ge=0,
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for explanations",
    )


class AssignmentObjective(str, Enum):
    """Assignment optimization objectives."""

    MINIMIZE_COST = "minimize_cost"
    MAXIMIZE_ASSIGNMENTS = "maximize_assignments"  # Assign as many tasks as possible
    BALANCE_LOAD = "balance_load"  # Distribute tasks evenly across agents


class SolveAssignmentProblemRequest(BaseModel):
    """High-level assignment problem definition."""

    agents: list[Agent] = Field(
        ...,
        min_length=1,
        description="Agents available to perform tasks",
    )
    tasks: list[AssignmentTask] = Field(
        ...,
        min_length=1,
        description="Tasks to be assigned",
    )
    cost_matrix: list[list[float]] | None = Field(
        default=None,
        description="Cost matrix where [i][j] = cost to assign task i to agent j. "
        "If not provided, uses agent.cost_multiplier * task.duration",
    )
    objective: AssignmentObjective = Field(
        default=AssignmentObjective.MINIMIZE_COST,
        description="Optimization goal",
    )
    force_assign_all: bool = Field(
        default=True,
        description="If True, all tasks must be assigned (problem is infeasible if not possible). "
        "If False, some tasks can remain unassigned.",
    )
    max_time_ms: int = Field(
        default=60000,
        description="Maximum solver time in milliseconds",
        ge=1,
    )
    return_partial_solution: bool = Field(
        default=True,
        description="Return best solution found if timeout occurs",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context",
    )


class Assignment(BaseModel):
    """A task assigned to an agent."""

    task_id: str = Field(
        ...,
        description="ID of the assigned task",
    )
    agent_id: str = Field(
        ...,
        description="ID of the agent assigned to the task",
    )
    cost: float = Field(
        ...,
        description="Cost of this assignment",
        ge=0.0,
    )


class AssignmentExplanation(BaseModel):
    """Human-readable explanation of the assignment solution."""

    summary: str = Field(
        ...,
        description="High-level summary of the result",
    )
    overloaded_agents: list[str] = Field(
        default_factory=list,
        description="Agents assigned more tasks than typical",
    )
    underutilized_agents: list[str] = Field(
        default_factory=list,
        description="Agents with capacity but few/no assignments",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Suggestions for improvement",
    )


class SolveAssignmentProblemResponse(BaseModel):
    """Assignment solution with domain-specific details."""

    status: SolverStatus = Field(
        ...,
        description="Solution status",
    )
    assignments: list[Assignment] = Field(
        default_factory=list,
        description="Task-to-agent assignments",
    )
    unassigned_tasks: list[str] = Field(
        default_factory=list,
        description="Tasks that could not be assigned",
    )
    agent_load: dict[str, int] = Field(
        default_factory=dict,
        description="Number of tasks assigned to each agent",
    )
    total_cost: float = Field(
        default=0.0,
        description="Total cost of all assignments",
        ge=0.0,
    )
    solve_time_ms: int = Field(
        default=0,
        description="Actual solve time in milliseconds",
        ge=0,
    )
    optimality_gap: float | None = Field(
        default=None,
        description="Optimality gap percentage",
    )
    explanation: AssignmentExplanation = Field(
        ...,
        description="Human-readable explanation",
    )


# ============================================================================
# Rebuild Models for Forward References
# ============================================================================

# Rebuild models with circular/forward references after all models are defined
# This is required for ImplicationParams which contains a Constraint field,
# creating a circular reference: Constraint → ImplicationParams → Constraint
Constraint.model_rebuild()
ImplicationParams.model_rebuild()
