"""Observability and monitoring for constraint solver.

Provides structured logging, metrics, and diagnostics for production deployments.
"""

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

# Configure structured logger
logger = logging.getLogger("chuk_mcp_solver")


class SolveOutcome(StrEnum):
    """Solver outcome for metrics tracking."""

    SUCCESS = "success"
    INFEASIBLE = "infeasible"
    TIMEOUT = "timeout"
    ERROR = "error"
    UNBOUNDED = "unbounded"


@dataclass
class SolverMetrics:
    """Metrics for a single solve operation."""

    problem_id: str
    timestamp: str
    num_variables: int
    num_constraints: int
    solve_time_ms: float
    outcome: SolveOutcome
    objective_value: float | None = None
    num_solutions: int = 0
    solver_type: str = "ortools"
    mode: str = "satisfy"

    # Additional context
    num_binding_constraints: int = 0
    timeout_ms: int | None = None
    max_solutions: int | None = None

    # Error details if applicable
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "problem_id": self.problem_id,
            "timestamp": self.timestamp,
            "num_variables": self.num_variables,
            "num_constraints": self.num_constraints,
            "solve_time_ms": self.solve_time_ms,
            "outcome": self.outcome.value,
            "objective_value": self.objective_value,
            "num_solutions": self.num_solutions,
            "solver_type": self.solver_type,
            "mode": self.mode,
            "num_binding_constraints": self.num_binding_constraints,
            "timeout_ms": self.timeout_ms,
            "max_solutions": self.max_solutions,
            "error_message": self.error_message,
        }


@dataclass
class SolverStatistics:
    """Aggregate statistics across multiple solves."""

    total_solves: int = 0
    successful_solves: int = 0
    infeasible_solves: int = 0
    timeout_solves: int = 0
    error_solves: int = 0

    total_solve_time_ms: float = 0.0
    min_solve_time_ms: float = float("inf")
    max_solve_time_ms: float = 0.0

    total_variables: int = 0
    total_constraints: int = 0

    recent_metrics: list[SolverMetrics] = field(default_factory=list)
    max_recent: int = 100  # Keep last 100 solves

    def record(self, metrics: SolverMetrics) -> None:
        """Record a solve operation."""
        self.total_solves += 1

        # Update outcome counters
        if metrics.outcome == SolveOutcome.SUCCESS:
            self.successful_solves += 1
        elif metrics.outcome == SolveOutcome.INFEASIBLE:
            self.infeasible_solves += 1
        elif metrics.outcome == SolveOutcome.TIMEOUT:
            self.timeout_solves += 1
        elif metrics.outcome == SolveOutcome.ERROR:
            self.error_solves += 1

        # Update timing stats
        self.total_solve_time_ms += metrics.solve_time_ms
        self.min_solve_time_ms = min(self.min_solve_time_ms, metrics.solve_time_ms)
        self.max_solve_time_ms = max(self.max_solve_time_ms, metrics.solve_time_ms)

        # Update problem size stats
        self.total_variables += metrics.num_variables
        self.total_constraints += metrics.num_constraints

        # Keep recent metrics
        self.recent_metrics.append(metrics)
        if len(self.recent_metrics) > self.max_recent:
            self.recent_metrics.pop(0)

    @property
    def avg_solve_time_ms(self) -> float:
        """Average solve time across all solves."""
        return self.total_solve_time_ms / self.total_solves if self.total_solves > 0 else 0.0

    @property
    def success_rate(self) -> float:
        """Success rate as percentage."""
        return (self.successful_solves / self.total_solves * 100) if self.total_solves > 0 else 0.0

    @property
    def infeasible_rate(self) -> float:
        """Infeasible rate as percentage."""
        return (self.infeasible_solves / self.total_solves * 100) if self.total_solves > 0 else 0.0

    @property
    def timeout_rate(self) -> float:
        """Timeout rate as percentage."""
        return (self.timeout_solves / self.total_solves * 100) if self.total_solves > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "total_solves": self.total_solves,
            "successful_solves": self.successful_solves,
            "infeasible_solves": self.infeasible_solves,
            "timeout_solves": self.timeout_solves,
            "error_solves": self.error_solves,
            "success_rate_pct": round(self.success_rate, 2),
            "infeasible_rate_pct": round(self.infeasible_rate, 2),
            "timeout_rate_pct": round(self.timeout_rate, 2),
            "avg_solve_time_ms": round(self.avg_solve_time_ms, 2),
            "min_solve_time_ms": round(self.min_solve_time_ms, 2),
            "max_solve_time_ms": round(self.max_solve_time_ms, 2),
            "avg_variables": (
                round(self.total_variables / self.total_solves, 1) if self.total_solves > 0 else 0
            ),
            "avg_constraints": (
                round(self.total_constraints / self.total_solves, 1) if self.total_solves > 0 else 0
            ),
        }


# Global statistics tracker
_global_stats = SolverStatistics()


def get_global_statistics() -> SolverStatistics:
    """Get global solver statistics."""
    return _global_stats


def reset_global_statistics() -> None:
    """Reset global statistics (useful for testing)."""
    global _global_stats
    _global_stats = SolverStatistics()


@contextmanager
def track_solve(
    problem_id: str, num_variables: int, num_constraints: int, mode: str
) -> Iterator[Any]:
    """Context manager to track solve operation with timing.

    Usage:
        with track_solve("problem_123", 10, 5, "optimize") as tracker:
            # Solve problem
            tracker.set_outcome(SolveOutcome.SUCCESS, objective_value=42.0)
    """

    class SolveTracker:
        """Tracker for current solve operation."""

        def __init__(self) -> None:
            self.start_time = time.time()
            self.outcome: SolveOutcome | None = None
            self.objective_value: float | None = None
            self.num_solutions: int = 0
            self.num_binding_constraints: int = 0
            self.error_message: str | None = None

        def set_outcome(
            self,
            outcome: SolveOutcome,
            objective_value: float | None = None,
            num_solutions: int = 0,
            num_binding_constraints: int = 0,
        ) -> None:
            """Set solve outcome and metrics."""
            self.outcome = outcome
            self.objective_value = objective_value
            self.num_solutions = num_solutions
            self.num_binding_constraints = num_binding_constraints

        def set_error(self, error_message: str) -> None:
            """Set error details."""
            self.outcome = SolveOutcome.ERROR
            self.error_message = error_message

    tracker = SolveTracker()

    try:
        logger.info(
            "solve_started",
            extra={
                "problem_id": problem_id,
                "num_variables": num_variables,
                "num_constraints": num_constraints,
                "mode": mode,
            },
        )
        yield tracker

    except Exception as e:
        tracker.set_error(str(e))
        logger.error(
            "solve_error",
            extra={
                "problem_id": problem_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise

    finally:
        # Calculate elapsed time
        elapsed_ms = (time.time() - tracker.start_time) * 1000

        # Default to error if outcome not set
        if tracker.outcome is None:
            tracker.outcome = SolveOutcome.ERROR

        # Create metrics
        metrics = SolverMetrics(
            problem_id=problem_id,
            timestamp=datetime.utcnow().isoformat(),
            num_variables=num_variables,
            num_constraints=num_constraints,
            solve_time_ms=elapsed_ms,
            outcome=tracker.outcome,
            objective_value=tracker.objective_value,
            num_solutions=tracker.num_solutions,
            mode=mode,
            num_binding_constraints=tracker.num_binding_constraints,
            error_message=tracker.error_message,
        )

        # Record in global stats
        _global_stats.record(metrics)

        # Log completion
        logger.info(
            "solve_completed",
            extra=metrics.to_dict(),
        )


def log_problem_details(
    problem_id: str, variables: list, constraints: list, objective: Any = None
) -> None:
    """Log detailed problem structure for debugging.

    Args:
        problem_id: Unique problem identifier
        variables: List of variables
        constraints: List of constraints
        objective: Optional objective specification
    """
    # Summarize constraint types
    constraint_types: dict[str, int] = {}
    for constraint in constraints:
        kind = constraint.get("kind", "unknown")
        constraint_types[kind] = constraint_types.get(kind, 0) + 1

    # Summarize variable types
    variable_types: dict[str, int] = {}
    for variable in variables:
        var_type = variable.get("domain", {}).get("type", "unknown")
        variable_types[var_type] = variable_types.get(var_type, 0) + 1

    logger.debug(
        "problem_details",
        extra={
            "problem_id": problem_id,
            "num_variables": len(variables),
            "num_constraints": len(constraints),
            "variable_types": variable_types,
            "constraint_types": constraint_types,
            "has_objective": objective is not None,
        },
    )
