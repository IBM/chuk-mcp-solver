"""Tests for high-level assignment solving."""

import pytest

from chuk_mcp_solver.models import (
    Agent,
    AssignmentObjective,
    AssignmentTask,
    SolveAssignmentProblemRequest,
    SolverStatus,
)
from chuk_mcp_solver.solver import get_solver
from chuk_mcp_solver.solver.ortools.assignment import (
    convert_assignment_to_cpsat,
    convert_cpsat_to_assignment_response,
)


@pytest.fixture
def solver():
    """Get solver instance."""
    return get_solver("ortools")


class TestAssignmentConverters:
    """Tests for assignment <-> CP-SAT converters."""

    def test_convert_simple_assignment(self):
        """Test converting simple assignment to CP-SAT."""
        request = SolveAssignmentProblemRequest(
            agents=[
                Agent(id="worker_1", capacity=2),
                Agent(id="worker_2", capacity=2),
            ],
            tasks=[
                AssignmentTask(id="task_A", duration=3),
                AssignmentTask(id="task_B", duration=2),
            ],
            objective=AssignmentObjective.MINIMIZE_COST,
        )

        cpsat_request = convert_assignment_to_cpsat(request)

        # Should have assignment variable for each (task, agent) pair
        # 2 tasks × 2 agents = 4 variables
        assert len(cpsat_request.variables) == 4

        # Should have task assignment constraints (each task to exactly one agent)
        task_constraints = [c for c in cpsat_request.constraints if "task_" in c.id]
        assert len(task_constraints) == 2

        # Should have agent capacity constraints
        capacity_constraints = [c for c in cpsat_request.constraints if "capacity" in c.id]
        assert len(capacity_constraints) == 2

    def test_convert_with_skills(self):
        """Test assignment with skill matching."""
        request = SolveAssignmentProblemRequest(
            agents=[
                Agent(id="dev_1", capacity=2, skills=["python", "docker"]),
                Agent(id="dev_2", capacity=2, skills=["python", "react"]),
            ],
            tasks=[
                AssignmentTask(id="backend", duration=5, required_skills=["python", "docker"]),
                AssignmentTask(id="frontend", duration=4, required_skills=["react"]),
            ],
            objective=AssignmentObjective.MINIMIZE_COST,
        )

        cpsat_request = convert_assignment_to_cpsat(request)

        # Should have assignment variables
        assert len(cpsat_request.variables) == 4  # 2 tasks × 2 agents


class TestAssignmentSolver:
    """Tests for end-to-end assignment solving."""

    async def test_simple_assignment(self, solver):
        """Test simple 2-task 2-agent assignment."""
        request = SolveAssignmentProblemRequest(
            agents=[
                Agent(id="worker_1", capacity=2, cost_multiplier=1.0),
                Agent(id="worker_2", capacity=2, cost_multiplier=1.5),
            ],
            tasks=[
                AssignmentTask(id="task_A", duration=3),
                AssignmentTask(id="task_B", duration=2),
            ],
            objective=AssignmentObjective.MINIMIZE_COST,
        )

        cpsat_request = convert_assignment_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_assignment_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        assert len(response.assignments) == 2  # Both tasks assigned
        assert len(response.unassigned_tasks) == 0
        # Should assign both to worker_1 (cheaper)
        assert all(a.agent_id == "worker_1" for a in response.assignments)

    async def test_with_capacity_limits(self, solver):
        """Test assignment respecting capacity constraints."""
        request = SolveAssignmentProblemRequest(
            agents=[
                Agent(id="worker_1", capacity=1, cost_multiplier=1.0),  # Can only take 1 task
                Agent(
                    id="worker_2", capacity=1, cost_multiplier=2.0
                ),  # Can only take 1 task, more expensive
            ],
            tasks=[
                AssignmentTask(id="task_A", duration=1),
                AssignmentTask(id="task_B", duration=1),
            ],
            objective=AssignmentObjective.MINIMIZE_COST,
        )

        cpsat_request = convert_assignment_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_assignment_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        assert len(response.assignments) == 2
        # Each worker should get exactly 1 task (forced by capacity)
        assert response.agent_load["worker_1"] <= 1
        assert response.agent_load["worker_2"] <= 1
        # Both workers should be utilized
        assert response.agent_load["worker_1"] + response.agent_load["worker_2"] == 2

    async def test_with_skills(self, solver):
        """Test assignment with skill matching."""
        request = SolveAssignmentProblemRequest(
            agents=[
                Agent(id="dev_1", capacity=2, skills=["python", "docker"]),
                Agent(id="dev_2", capacity=2, skills=["python", "react"]),
            ],
            tasks=[
                AssignmentTask(id="backend", duration=5, required_skills=["python", "docker"]),
                AssignmentTask(id="frontend", duration=4, required_skills=["react"]),
            ],
            objective=AssignmentObjective.MINIMIZE_COST,
        )

        cpsat_request = convert_assignment_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_assignment_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        assert len(response.assignments) == 2
        # backend must go to dev_1 (only one with docker)
        backend_assignment = next(a for a in response.assignments if a.task_id == "backend")
        assert backend_assignment.agent_id == "dev_1"
        # frontend must go to dev_2 (only one with react)
        frontend_assignment = next(a for a in response.assignments if a.task_id == "frontend")
        assert frontend_assignment.agent_id == "dev_2"

    async def test_maximize_assignments(self, solver):
        """Test maximizing number of assignments."""
        request = SolveAssignmentProblemRequest(
            agents=[
                Agent(id="worker_1", capacity=2),
            ],
            tasks=[
                AssignmentTask(id="task_A", duration=1),
                AssignmentTask(id="task_B", duration=1),
                AssignmentTask(id="task_C", duration=1),
            ],
            objective=AssignmentObjective.MAXIMIZE_ASSIGNMENTS,
            force_assign_all=False,  # Can leave some unassigned
        )

        cpsat_request = convert_assignment_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_assignment_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        # Should assign 2 tasks (capacity limit)
        assert len(response.assignments) == 2
        assert len(response.unassigned_tasks) == 1

    async def test_balance_load(self, solver):
        """Test load balancing objective."""
        request = SolveAssignmentProblemRequest(
            agents=[
                Agent(id="server_1", capacity=10),
                Agent(id="server_2", capacity=10),
                Agent(id="server_3", capacity=10),
            ],
            tasks=[AssignmentTask(id=f"job_{i}", duration=1) for i in range(6)],
            objective=AssignmentObjective.BALANCE_LOAD,
        )

        cpsat_request = convert_assignment_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_assignment_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        assert len(response.assignments) == 6
        # Should distribute evenly: 2 tasks per server
        assert response.agent_load["server_1"] == 2
        assert response.agent_load["server_2"] == 2
        assert response.agent_load["server_3"] == 2


class TestAssignmentFromServer:
    """Test the high-level solve_assignment_problem tool."""

    async def test_solve_assignment_problem_simple(self):
        """Test solve_assignment_problem with simple assignment."""
        from chuk_mcp_solver.server import solve_assignment_problem

        response = await solve_assignment_problem(
            agents=[
                {"id": "worker_1", "capacity": 2},
                {"id": "worker_2", "capacity": 2},
            ],
            tasks=[
                {"id": "task_A", "duration": 3},
                {"id": "task_B", "duration": 2},
            ],
            objective="minimize_cost",
        )

        assert response.status == SolverStatus.OPTIMAL
        assert len(response.assignments) == 2
        assert response.explanation is not None

    async def test_solve_assignment_problem_with_skills(self):
        """Test solve_assignment_problem with skill matching."""
        from chuk_mcp_solver.server import solve_assignment_problem

        response = await solve_assignment_problem(
            agents=[
                {"id": "dev_1", "capacity": 2, "skills": ["python", "docker"]},
                {"id": "dev_2", "capacity": 2, "skills": ["react"]},
            ],
            tasks=[
                {"id": "backend", "duration": 5, "required_skills": ["python", "docker"]},
                {"id": "frontend", "duration": 4, "required_skills": ["react"]},
            ],
            objective="minimize_cost",
        )

        assert response.status == SolverStatus.OPTIMAL
        assert len(response.assignments) == 2
        # Verify skill matching worked
        backend = next(a for a in response.assignments if a.task_id == "backend")
        assert backend.agent_id == "dev_1"


class TestAssignmentEdgeCases:
    """Test edge cases and error handling."""

    async def test_infeasible_capacity(self, solver):
        """Test infeasible assignment (not enough capacity)."""
        request = SolveAssignmentProblemRequest(
            agents=[
                Agent(id="worker_1", capacity=1),
            ],
            tasks=[
                AssignmentTask(id="task_A", duration=1),
                AssignmentTask(id="task_B", duration=1),
            ],
            objective=AssignmentObjective.MINIMIZE_COST,
            force_assign_all=True,  # Must assign all, but capacity is insufficient
        )

        cpsat_request = convert_assignment_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_assignment_response(cpsat_response, request)

        assert response.status == SolverStatus.INFEASIBLE

    async def test_optional_assignments(self, solver):
        """Test optional task assignment with maximize_assignments objective."""
        request = SolveAssignmentProblemRequest(
            agents=[
                Agent(id="worker_1", capacity=1),
            ],
            tasks=[
                AssignmentTask(id="task_A", duration=1),
                AssignmentTask(id="task_B", duration=1),
            ],
            objective=AssignmentObjective.MAXIMIZE_ASSIGNMENTS,  # Want to assign as many as possible
            force_assign_all=False,  # Some tasks can be unassigned
        )

        cpsat_request = convert_assignment_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_assignment_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        assert len(response.assignments) == 1  # Only one task assigned (capacity limit)
        assert len(response.unassigned_tasks) == 1

    async def test_single_task_single_agent(self, solver):
        """Test minimal assignment (1 task, 1 agent)."""
        request = SolveAssignmentProblemRequest(
            agents=[Agent(id="worker_1", capacity=1)],
            tasks=[AssignmentTask(id="task_A", duration=1)],
            objective=AssignmentObjective.MINIMIZE_COST,
        )

        cpsat_request = convert_assignment_to_cpsat(request)
        cpsat_response = await solver.solve_constraint_model(cpsat_request)
        response = convert_cpsat_to_assignment_response(cpsat_response, request)

        assert response.status == SolverStatus.OPTIMAL
        assert len(response.assignments) == 1
        assert response.assignments[0].task_id == "task_A"
        assert response.assignments[0].agent_id == "worker_1"
