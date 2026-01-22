"""Tests for solver factory and interface."""

import pytest

from chuk_mcp_solver.solver import ORToolsSolver, SolverProvider, get_solver


def test_get_solver_ortools():
    """Test get_solver returns OR-Tools solver."""
    solver = get_solver("ortools")
    assert isinstance(solver, ORToolsSolver)
    assert isinstance(solver, SolverProvider)


def test_get_solver_unknown_type():
    """Test that unknown solver type raises ValueError."""
    with pytest.raises(ValueError, match="Unknown solver type: nonexistent"):
        get_solver("nonexistent")


def test_ortools_solver_instance():
    """Test ORToolsSolver can be instantiated directly."""
    solver = ORToolsSolver()
    assert isinstance(solver, SolverProvider)
    assert hasattr(solver, "solve_constraint_model")
