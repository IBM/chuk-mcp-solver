"""Tests for observability and metrics tracking."""

import pytest

from chuk_mcp_solver.observability import (
    SolveOutcome,
    SolverMetrics,
    SolverStatistics,
    get_global_statistics,
    reset_global_statistics,
    track_solve,
)


def test_solver_metrics_to_dict():
    """Test SolverMetrics to_dict conversion."""
    metrics = SolverMetrics(
        problem_id="test_123",
        timestamp="2025-01-01T00:00:00",
        num_variables=10,
        num_constraints=5,
        solve_time_ms=42.5,
        outcome=SolveOutcome.SUCCESS,
        objective_value=100.0,
        num_solutions=1,
        solver_type="ortools",
        mode="optimize",
    )

    result = metrics.to_dict()

    assert result["problem_id"] == "test_123"
    assert result["num_variables"] == 10
    assert result["num_constraints"] == 5
    assert result["solve_time_ms"] == 42.5
    assert result["outcome"] == "success"
    assert result["objective_value"] == 100.0


def test_solver_statistics_record():
    """Test recording metrics in statistics."""
    stats = SolverStatistics()

    # Record successful solve
    metrics1 = SolverMetrics(
        problem_id="p1",
        timestamp="2025-01-01T00:00:00",
        num_variables=10,
        num_constraints=5,
        solve_time_ms=42.5,
        outcome=SolveOutcome.SUCCESS,
    )
    stats.record(metrics1)

    assert stats.total_solves == 1
    assert stats.successful_solves == 1
    assert stats.infeasible_solves == 0
    assert stats.total_solve_time_ms == 42.5
    assert stats.min_solve_time_ms == 42.5
    assert stats.max_solve_time_ms == 42.5

    # Record infeasible solve
    metrics2 = SolverMetrics(
        problem_id="p2",
        timestamp="2025-01-01T00:01:00",
        num_variables=15,
        num_constraints=8,
        solve_time_ms=100.0,
        outcome=SolveOutcome.INFEASIBLE,
    )
    stats.record(metrics2)

    assert stats.total_solves == 2
    assert stats.successful_solves == 1
    assert stats.infeasible_solves == 1
    assert stats.total_solve_time_ms == 142.5
    assert stats.min_solve_time_ms == 42.5
    assert stats.max_solve_time_ms == 100.0


def test_solver_statistics_rates():
    """Test computed rate properties."""
    stats = SolverStatistics()

    # All successful
    for i in range(10):
        stats.record(
            SolverMetrics(
                problem_id=f"p{i}",
                timestamp="2025-01-01T00:00:00",
                num_variables=10,
                num_constraints=5,
                solve_time_ms=50.0,
                outcome=SolveOutcome.SUCCESS,
            )
        )

    assert stats.success_rate == 100.0
    assert stats.infeasible_rate == 0.0
    assert stats.timeout_rate == 0.0

    # Add some failures
    stats.record(
        SolverMetrics(
            problem_id="p_inf",
            timestamp="2025-01-01T00:01:00",
            num_variables=10,
            num_constraints=5,
            solve_time_ms=50.0,
            outcome=SolveOutcome.INFEASIBLE,
        )
    )
    stats.record(
        SolverMetrics(
            problem_id="p_timeout",
            timestamp="2025-01-01T00:02:00",
            num_variables=10,
            num_constraints=5,
            solve_time_ms=5000.0,
            outcome=SolveOutcome.TIMEOUT,
        )
    )

    assert stats.total_solves == 12
    assert stats.success_rate == pytest.approx(83.33, abs=0.01)
    assert stats.infeasible_rate == pytest.approx(8.33, abs=0.01)
    assert stats.timeout_rate == pytest.approx(8.33, abs=0.01)


def test_solver_statistics_avg_solve_time():
    """Test average solve time calculation."""
    stats = SolverStatistics()

    stats.record(
        SolverMetrics(
            problem_id="p1",
            timestamp="2025-01-01T00:00:00",
            num_variables=10,
            num_constraints=5,
            solve_time_ms=100.0,
            outcome=SolveOutcome.SUCCESS,
        )
    )
    stats.record(
        SolverMetrics(
            problem_id="p2",
            timestamp="2025-01-01T00:01:00",
            num_variables=10,
            num_constraints=5,
            solve_time_ms=200.0,
            outcome=SolveOutcome.SUCCESS,
        )
    )

    assert stats.avg_solve_time_ms == 150.0


def test_solver_statistics_to_dict():
    """Test statistics to_dict conversion."""
    stats = SolverStatistics()

    stats.record(
        SolverMetrics(
            problem_id="p1",
            timestamp="2025-01-01T00:00:00",
            num_variables=10,
            num_constraints=5,
            solve_time_ms=100.0,
            outcome=SolveOutcome.SUCCESS,
        )
    )

    result = stats.to_dict()

    assert result["total_solves"] == 1
    assert result["successful_solves"] == 1
    assert result["success_rate_pct"] == 100.0
    assert result["avg_solve_time_ms"] == 100.0


def test_track_solve_success():
    """Test track_solve context manager for successful solve."""
    reset_global_statistics()

    with track_solve("test_problem", 10, 5, "optimize") as tracker:
        tracker.set_outcome(outcome=SolveOutcome.SUCCESS, objective_value=42.0, num_solutions=1)

    stats = get_global_statistics()
    assert stats.total_solves == 1
    assert stats.successful_solves == 1
    assert stats.recent_metrics[0].problem_id == "test_problem"
    assert stats.recent_metrics[0].outcome == SolveOutcome.SUCCESS
    assert stats.recent_metrics[0].objective_value == 42.0


def test_track_solve_infeasible():
    """Test track_solve for infeasible problem."""
    reset_global_statistics()

    with track_solve("infeasible_problem", 5, 3, "satisfy") as tracker:
        tracker.set_outcome(outcome=SolveOutcome.INFEASIBLE)

    stats = get_global_statistics()
    assert stats.total_solves == 1
    assert stats.infeasible_solves == 1
    assert stats.recent_metrics[0].outcome == SolveOutcome.INFEASIBLE


def test_track_solve_error():
    """Test track_solve with explicit error."""
    reset_global_statistics()

    with track_solve("error_problem", 5, 3, "satisfy") as tracker:
        tracker.set_error("Something went wrong")

    stats = get_global_statistics()
    assert stats.total_solves == 1
    assert stats.error_solves == 1
    assert stats.recent_metrics[0].outcome == SolveOutcome.ERROR
    assert stats.recent_metrics[0].error_message == "Something went wrong"


def test_track_solve_exception():
    """Test track_solve with unhandled exception."""
    reset_global_statistics()

    with pytest.raises(ValueError):
        with track_solve("exception_problem", 5, 3, "satisfy"):
            raise ValueError("Test error")

    stats = get_global_statistics()
    assert stats.total_solves == 1
    assert stats.error_solves == 1
    assert stats.recent_metrics[0].outcome == SolveOutcome.ERROR


def test_track_solve_no_outcome_set():
    """Test track_solve defaults to ERROR if outcome not set."""
    reset_global_statistics()

    with track_solve("no_outcome_problem", 5, 3, "satisfy"):
        # Don't set outcome
        pass

    stats = get_global_statistics()
    assert stats.total_solves == 1
    assert stats.error_solves == 1
    assert stats.recent_metrics[0].outcome == SolveOutcome.ERROR


def test_recent_metrics_limit():
    """Test that recent_metrics list is limited to max_recent."""
    stats = SolverStatistics(max_recent=5)

    # Record 10 solves
    for i in range(10):
        stats.record(
            SolverMetrics(
                problem_id=f"p{i}",
                timestamp="2025-01-01T00:00:00",
                num_variables=10,
                num_constraints=5,
                solve_time_ms=50.0,
                outcome=SolveOutcome.SUCCESS,
            )
        )

    # Should only keep last 5
    assert len(stats.recent_metrics) == 5
    assert stats.recent_metrics[0].problem_id == "p5"
    assert stats.recent_metrics[4].problem_id == "p9"


def test_global_statistics_reset():
    """Test resetting global statistics."""
    # Reset first to ensure clean state
    reset_global_statistics()

    # Record some data
    with track_solve("test_problem", 10, 5, "optimize") as tracker:
        tracker.set_outcome(outcome=SolveOutcome.SUCCESS)

    stats = get_global_statistics()
    assert stats.total_solves == 1

    # Reset
    reset_global_statistics()

    stats = get_global_statistics()
    assert stats.total_solves == 0
    assert len(stats.recent_metrics) == 0
