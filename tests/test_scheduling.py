"""Tests for high-level scheduling problem solving."""

import pytest
from chuk_mcp_solver.models import (
    Resource,
    SchedulingObjective,
    SolverStatus,
    SolveSchedulingProblemRequest,
    Task,
)
from chuk_mcp_solver.solver import get_solver
from chuk_mcp_solver.solver.ortools.scheduling import (
    convert_cpsat_to_scheduling_response,
    convert_scheduling_to_cpsat,
)


@pytest.fixture
def solver():
    """Get solver instance."""
    return get_solver("ortools")


class TestSchedulingConverters:
    """Tests for scheduling <-> CP-SAT converters."""

    def test_convert_simple_schedule(self):
        """Test converting simple scheduling problem to CP-SAT."""
        request = SolveSchedulingProblemRequest(
            tasks=[
                Task(id="A", duration=3),
                Task(id="B", duration=2, dependencies=["A"]),
            ],
            objective=SchedulingObjective.MINIMIZE_MAKESPAN,
        )

        cpsat_request = convert_scheduling_to_cpsat(request)

        # Should have start/end variables for each task + makespan
        assert len(cpsat_request.variables) == 5  # 2 tasks * 2 (start+end) + makespan

        # Should have duration constraints + precedence + makespan bounds
        constraint_kinds = {c.kind for c in cpsat_request.constraints}
        assert "linear" in constraint_kinds

        # Should have optimization objective
        assert cpsat_request.mode == "optimize"
        assert cpsat_request.objective is not None

    def test_convert_with_resources(self):
        """Test scheduling with resource constraints."""
        request = SolveSchedulingProblemRequest(
            tasks=[
                Task(id="A", duration=3, resources_required={"cpu": 2}),
                Task(id="B", duration=2, resources_required={"cpu": 3}),
            ],
            resources=[Resource(id="cpu", capacity=4)],
            objective=SchedulingObjective.MINIMIZE_MAKESPAN,
        )

        cpsat_request = convert_scheduling_to_cpsat(request)

        # Should have cumulative constraint for CPU resource
        cumulative_constraints = [c for c in cpsat_request.constraints if c.kind == "cumulative"]
        assert len(cumulative_constraints) == 1
        assert cumulative_constraints[0].id == "capacity_cpu"

    def test_convert_with_deadlines(self):
        """Test scheduling with task deadlines."""
        request = SolveSchedulingProblemRequest(
            tasks=[
                Task(id="A", duration=5, deadline=10),
                Task(id="B", duration=3),
            ],
            objective=SchedulingObjective.MINIMIZE_MAKESPAN,
        )

        cpsat_request = convert_scheduling_to_cpsat(request)

        # Should have deadline constraint for task A
        deadline_constraints = [c for c in cpsat_request.constraints if "deadline" in c.id]
        assert len(deadline_constraints) == 1
        assert deadline_constraints[0].id == "deadline_A"


class TestSchedulingSolver:
    """Tests for end-to-end scheduling solving."""

    async def test_simple_schedule_no_dependencies(self, solver):
        """Test scheduling independent tasks."""
        request = SolveSchedulingProblemRequest(
            tasks=[
                Task(id="A", duration=3),
                Task(id="B", duration=2),
                Task(id="C", duration=1),
            ],
            objective=SchedulingObjective.MINIMIZE_MAKESPAN,
        )

        # Convert and solve
        cpsat_request = convert_scheduling_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_scheduling_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        assert response.makespan is not None
        # Independent tasks can run in parallel, so makespan = max(durations)
        assert response.makespan == 3
        assert len(response.schedule) == 3

    async def test_schedule_with_dependencies(self, solver):
        """Test scheduling with task dependencies."""
        request = SolveSchedulingProblemRequest(
            tasks=[
                Task(id="A", duration=3),
                Task(id="B", duration=2, dependencies=["A"]),
                Task(id="C", duration=1, dependencies=["A"]),
            ],
            objective=SchedulingObjective.MINIMIZE_MAKESPAN,
        )

        cpsat_request = convert_scheduling_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_scheduling_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        # A must finish before B and C start
        # Optimal: A(3) + max(B(2), C(1)) = 5
        assert response.makespan == 5
        assert len(response.schedule) == 3

        # Check precedence is respected
        schedule_dict = {t.task_id: t for t in response.schedule}
        assert schedule_dict["B"].start_time >= schedule_dict["A"].end_time
        assert schedule_dict["C"].start_time >= schedule_dict["A"].end_time

    async def test_schedule_with_resource_constraints(self, solver):
        """Test scheduling with limited resources."""
        request = SolveSchedulingProblemRequest(
            tasks=[
                Task(id="A", duration=3, resources_required={"cpu": 2}),
                Task(id="B", duration=2, resources_required={"cpu": 2}),
            ],
            resources=[Resource(id="cpu", capacity=2)],
            objective=SchedulingObjective.MINIMIZE_MAKESPAN,
        )

        cpsat_request = convert_scheduling_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_scheduling_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        # Both tasks need 2 CPUs, but only 2 available -> sequential
        assert response.makespan == 5  # 3 + 2

    async def test_schedule_infeasible_deadline(self, solver):
        """Test infeasible scheduling problem."""
        request = SolveSchedulingProblemRequest(
            tasks=[
                Task(id="A", duration=10, deadline=5),  # Impossible deadline
            ],
            objective=SchedulingObjective.MINIMIZE_MAKESPAN,
        )

        cpsat_request = convert_scheduling_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_scheduling_response(cpsat_response, request)

        assert response.status == SolverStatus.INFEASIBLE
        assert len(response.schedule) == 0

    async def test_schedule_with_earliest_start(self, solver):
        """Test scheduling with release times."""
        request = SolveSchedulingProblemRequest(
            tasks=[
                Task(id="A", duration=2, earliest_start=5),
                Task(id="B", duration=3),
            ],
            objective=SchedulingObjective.MINIMIZE_MAKESPAN,
        )

        cpsat_request = convert_scheduling_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_scheduling_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        schedule_dict = {t.task_id: t for t in response.schedule}
        # Task A can't start before time 5
        assert schedule_dict["A"].start_time >= 5


class TestSchedulingFromServer:
    """Test the high-level solve_scheduling_problem tool."""

    async def test_solve_scheduling_problem_simple(self):
        """Test solve_scheduling_problem with simple tasks."""
        from chuk_mcp_solver.server import solve_scheduling_problem

        response = await solve_scheduling_problem(
            tasks=[
                {"id": "build", "duration": 10},
                {"id": "test", "duration": 5, "dependencies": ["build"]},
                {"id": "deploy", "duration": 3, "dependencies": ["test"]},
            ],
            objective="minimize_makespan",
        )

        assert response.status == SolverStatus.OPTIMAL
        assert response.makespan == 18  # 10 + 5 + 3
        assert len(response.schedule) == 3
        assert response.explanation is not None

    async def test_solve_scheduling_problem_with_resources(self):
        """Test solve_scheduling_problem with resource constraints."""
        from chuk_mcp_solver.server import solve_scheduling_problem

        response = await solve_scheduling_problem(
            tasks=[
                {"id": "task_a", "duration": 5, "resources_required": {"cpu": 2}},
                {"id": "task_b", "duration": 3, "resources_required": {"cpu": 3}},
                {"id": "task_c", "duration": 2, "resources_required": {"cpu": 1}},
            ],
            resources=[{"id": "cpu", "capacity": 4}],
            objective="minimize_makespan",
        )

        assert response.status == SolverStatus.OPTIMAL
        assert response.makespan is not None
        assert len(response.schedule) == 3

    async def test_solve_scheduling_problem_parallel_execution(self):
        """Test that independent tasks can run in parallel."""
        from chuk_mcp_solver.server import solve_scheduling_problem

        response = await solve_scheduling_problem(
            tasks=[
                {"id": "A", "duration": 5},
                {"id": "B", "duration": 5},
                {"id": "C", "duration": 5},
            ],
            objective="minimize_makespan",
        )

        assert response.status == SolverStatus.OPTIMAL
        # All tasks independent, can run in parallel
        assert response.makespan == 5
        assert len(response.schedule) == 3


class TestSchedulingEdgeCases:
    """Test edge cases and error handling."""

    async def test_single_task(self, solver):
        """Test scheduling a single task."""
        request = SolveSchedulingProblemRequest(
            tasks=[Task(id="only", duration=7)],
            objective=SchedulingObjective.MINIMIZE_MAKESPAN,
        )

        cpsat_request = convert_scheduling_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_scheduling_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        assert response.makespan == 7
        assert len(response.schedule) == 1

    async def test_zero_duration_task(self, solver):
        """Test scheduling with zero-duration task (milestone)."""
        request = SolveSchedulingProblemRequest(
            tasks=[
                Task(id="start", duration=0),
                Task(id="work", duration=5, dependencies=["start"]),
            ],
            objective=SchedulingObjective.MINIMIZE_MAKESPAN,
        )

        cpsat_request = convert_scheduling_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_scheduling_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        assert response.makespan == 5

    async def test_response_includes_metadata(self):
        """Test that task metadata is preserved in response."""
        from chuk_mcp_solver.server import solve_scheduling_problem

        response = await solve_scheduling_problem(
            tasks=[
                {"id": "A", "duration": 3, "metadata": {"team": "backend", "priority": "high"}},
            ],
            objective="minimize_makespan",
        )

        assert response.status == SolverStatus.OPTIMAL
        assert len(response.schedule) == 1
        task_assignment = response.schedule[0]
        assert task_assignment.metadata == {"team": "backend", "priority": "high"}

    async def test_with_max_makespan(self, solver):
        """Test scheduling with max_makespan constraint."""
        request = SolveSchedulingProblemRequest(
            tasks=[
                Task(id="A", duration=5),
                Task(id="B", duration=5),
            ],
            max_makespan=8,  # Force some overlap
            objective=SchedulingObjective.MINIMIZE_MAKESPAN,
        )

        cpsat_request = convert_scheduling_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_scheduling_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        assert response.makespan <= 8

    async def test_with_no_overlap_tasks(self, solver):
        """Test scheduling with no-overlap constraint groups."""
        request = SolveSchedulingProblemRequest(
            tasks=[
                Task(id="A", duration=3),
                Task(id="B", duration=2),
                Task(id="C", duration=1),
            ],
            no_overlap_tasks=[["A", "B", "C"]],  # All three can't overlap
            objective=SchedulingObjective.MINIMIZE_MAKESPAN,
        )

        cpsat_request = convert_scheduling_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_scheduling_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        # With no overlap, should be sequential: 3 + 2 + 1 = 6
        assert response.makespan == 6

    async def test_timeout_no_solution_handling(self):
        """Test handling of TIMEOUT_NO_SOLUTION status."""
        from chuk_mcp_solver.models import (
            Explanation,
            SolveConstraintModelResponse,
        )

        # Mock CPSAT response with TIMEOUT_NO_SOLUTION
        cpsat_response = SolveConstraintModelResponse(
            status=SolverStatus.TIMEOUT_NO_SOLUTION,
            solve_time_ms=100,
            explanation=Explanation(summary="Timeout occurred"),
        )

        request = SolveSchedulingProblemRequest(
            tasks=[Task(id="A", duration=5)],
            objective=SchedulingObjective.MINIMIZE_MAKESPAN,
        )

        response = convert_cpsat_to_scheduling_response(cpsat_response, request)

        assert response.status == SolverStatus.TIMEOUT_NO_SOLUTION
        assert "Timeout" in response.explanation.summary
        assert "recommendations" in dir(response.explanation)

    async def test_empty_solutions_handling(self):
        """Test handling when cpsat_response has empty solutions list."""
        from chuk_mcp_solver.models import SolveConstraintModelResponse

        # Mock CPSAT response with FEASIBLE status but no solutions (edge case)
        cpsat_response = SolveConstraintModelResponse(
            status=SolverStatus.FEASIBLE,
            solve_time_ms=50,
            solutions=[],  # Empty solutions
        )

        request = SolveSchedulingProblemRequest(
            tasks=[Task(id="A", duration=5)],
            objective=SchedulingObjective.MINIMIZE_MAKESPAN,
        )

        response = convert_cpsat_to_scheduling_response(cpsat_response, request)

        assert response.status == SolverStatus.FEASIBLE
        assert response.explanation.summary == "No solution available"

    async def test_makespan_calculation_fallback(self):
        """Test makespan calculation when not in solution variables."""
        from chuk_mcp_solver.models import Solution, SolutionVariable, SolveConstraintModelResponse

        # Mock CPSAT response without 'makespan' variable
        cpsat_response = SolveConstraintModelResponse(
            status=SolverStatus.OPTIMAL,
            solve_time_ms=100,
            solutions=[
                Solution(
                    variables=[
                        SolutionVariable(id="start_A", value=0.0),
                        SolutionVariable(id="end_A", value=5.0),
                        # No 'makespan' variable
                    ]
                )
            ],
        )

        request = SolveSchedulingProblemRequest(
            tasks=[Task(id="A", duration=5)],
            objective=SchedulingObjective.MINIMIZE_MAKESPAN,
        )

        response = convert_cpsat_to_scheduling_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        # Should calculate makespan from max end_time
        assert response.makespan == 5

    async def test_feasible_status_with_gap(self):
        """Test FEASIBLE status message generation."""
        from chuk_mcp_solver.models import (
            Explanation,
            Solution,
            SolutionVariable,
            SolveConstraintModelResponse,
        )

        # Mock CPSAT response with FEASIBLE status and gap
        cpsat_response = SolveConstraintModelResponse(
            status=SolverStatus.FEASIBLE,
            solve_time_ms=100,
            objective_value=42.0,
            optimality_gap=15.5,
            solutions=[
                Solution(
                    variables=[
                        SolutionVariable(id="start_A", value=0.0),
                        SolutionVariable(id="end_A", value=5.0),
                        SolutionVariable(id="makespan", value=5.0),
                    ]
                )
            ],
            explanation=Explanation(summary="Found feasible solution"),
        )

        request = SolveSchedulingProblemRequest(
            tasks=[Task(id="A", duration=5)],
            objective=SchedulingObjective.MINIMIZE_MAKESPAN,
        )

        response = convert_cpsat_to_scheduling_response(cpsat_response, request)

        assert response.status == SolverStatus.FEASIBLE
        assert "feasible schedule" in response.explanation.summary
        assert "gap: 15.50%" in response.explanation.summary

    async def test_satisfied_status_message(self):
        """Test SATISFIED status message generation."""
        from chuk_mcp_solver.models import Solution, SolutionVariable, SolveConstraintModelResponse

        # Mock CPSAT response with SATISFIED status (no optimization)
        cpsat_response = SolveConstraintModelResponse(
            status=SolverStatus.SATISFIED,
            solve_time_ms=100,
            solutions=[
                Solution(
                    variables=[
                        SolutionVariable(id="start_A", value=0.0),
                        SolutionVariable(id="end_A", value=5.0),
                        SolutionVariable(id="makespan", value=5.0),
                    ]
                )
            ],
        )

        request = SolveSchedulingProblemRequest(
            tasks=[Task(id="A", duration=5)],
            objective=SchedulingObjective.MINIMIZE_MAKESPAN,
        )

        response = convert_cpsat_to_scheduling_response(cpsat_response, request)

        assert response.status == SolverStatus.SATISFIED
        assert "Schedule found" in response.explanation.summary
