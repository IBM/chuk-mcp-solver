"""Diagnostics and health checks for constraint solver.

Provides tools for analyzing solver behavior, detecting issues,
and explaining infeasibility.
"""

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum

from chuk_mcp_solver.models import SolveConstraintModelRequest, SolverStatus
from chuk_mcp_solver.observability import get_global_statistics


class HealthStatus(StrEnum):
    """Health status of solver."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class SolverHealth:
    """Health check result for solver."""

    status: HealthStatus
    message: str
    details: dict

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
        }


def check_solver_health() -> SolverHealth:
    """Check solver health based on recent performance.

    Returns:
        SolverHealth with status and diagnostics
    """
    stats = get_global_statistics()

    # If no solves yet, assume healthy
    if stats.total_solves == 0:
        return SolverHealth(
            status=HealthStatus.HEALTHY,
            message="Solver initialized, no solves yet",
            details={"total_solves": 0},
        )

    # Check error rate
    error_rate = (stats.error_solves / stats.total_solves * 100) if stats.total_solves > 0 else 0

    # Check timeout rate
    timeout_rate = stats.timeout_rate

    # Determine health status
    if error_rate > 20:  # More than 20% errors
        status = HealthStatus.UNHEALTHY
        message = f"High error rate: {error_rate:.1f}%"
    elif timeout_rate > 50:  # More than 50% timeouts
        status = HealthStatus.DEGRADED
        message = f"High timeout rate: {timeout_rate:.1f}%"
    elif error_rate > 5:  # More than 5% errors
        status = HealthStatus.DEGRADED
        message = f"Elevated error rate: {error_rate:.1f}%"
    else:
        status = HealthStatus.HEALTHY
        message = "Solver performing normally"

    return SolverHealth(
        status=status,
        message=message,
        details=stats.to_dict(),
    )


def compute_problem_hash(request: SolveConstraintModelRequest) -> str:
    """Compute deterministic hash of problem for caching/deduplication.

    Args:
        request: Solver request

    Returns:
        SHA256 hash of normalized problem representation
    """
    # Create canonical representation
    problem_dict = {
        "mode": request.mode.value,
        "variables": sorted(
            [
                {
                    "id": v.id,
                    "domain": {
                        "type": v.domain.type.value,
                        "lower": getattr(v.domain, "lower", None),
                        "upper": getattr(v.domain, "upper", None),
                    },
                }
                for v in request.variables
            ],
            key=lambda x: str(x["id"]),
        ),
        "constraints": sorted(
            [
                {
                    "id": c.id,
                    "kind": c.kind.value,
                    # params would need custom serialization per constraint type
                }
                for c in request.constraints
            ],
            key=lambda x: str(x["id"]),
        ),
        # Simplified for now - full implementation would serialize all params
    }

    # Compute hash
    problem_json = json.dumps(problem_dict, sort_keys=True)
    return hashlib.sha256(problem_json.encode()).hexdigest()


@dataclass
class InfeasibilityDiagnosis:
    """Diagnosis of why a problem is infeasible."""

    status: SolverStatus
    summary: str
    conflicting_constraints: list[str]
    suggestions: list[str]
    variable_bounds_conflicts: list[dict]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "summary": self.summary,
            "conflicting_constraints": self.conflicting_constraints,
            "suggestions": self.suggestions,
            "variable_bounds_conflicts": self.variable_bounds_conflicts,
        }


def diagnose_infeasibility(request: SolveConstraintModelRequest) -> InfeasibilityDiagnosis:
    """Analyze infeasible problem to identify likely causes.

    Args:
        request: The infeasible solver request

    Returns:
        Diagnosis with potential conflicts and suggestions
    """
    conflicting_constraints = []
    suggestions = []
    bounds_conflicts = []

    # Check for obvious variable domain conflicts
    for var in request.variables:
        if var.domain.type.value == "integer":
            if var.domain.lower > var.domain.upper:
                bounds_conflicts.append(
                    {
                        "variable": var.id,
                        "issue": "lower_bound > upper_bound",
                        "lower": var.domain.lower,
                        "upper": var.domain.upper,
                    }
                )
                suggestions.append(
                    f"Variable '{var.id}' has invalid bounds: "
                    f"lower ({var.domain.lower}) > upper ({var.domain.upper})"
                )

            if var.domain.lower == var.domain.upper:
                suggestions.append(
                    f"Variable '{var.id}' is fixed to {var.domain.lower} "
                    "(lower == upper), which may over-constrain the problem"
                )

    # Analyze constraints for potential conflicts
    # Look for multiple equality constraints on same variable
    equality_constraints: dict[str, list[str]] = {}
    for constraint in request.constraints:
        if constraint.kind.value == "linear":
            params = constraint.params
            if hasattr(params, "sense") and params.sense == "==":
                # Extract variables involved
                if hasattr(params, "terms"):
                    for term in params.terms:
                        var_id = term.var
                        if var_id not in equality_constraints:
                            equality_constraints[var_id] = []
                        equality_constraints[var_id].append(constraint.id)

    # Check for multiple equalities on same variable
    for var_id, constraint_ids in equality_constraints.items():
        if len(constraint_ids) > 1:
            conflicting_constraints.extend(constraint_ids)
            suggestions.append(
                f"Variable '{var_id}' appears in {len(constraint_ids)} equality constraints: "
                f"{', '.join(constraint_ids)}. These may be conflicting."
            )

    # Check for contradictory bounds
    if request.mode.value == "optimize" and not request.objective:
        suggestions.append(
            "Optimization mode requires an objective function, but none was provided"
        )

    # Generic suggestions
    if not suggestions:
        suggestions.extend(
            [
                "Try relaxing some constraints (e.g., <= instead of ==)",
                "Check if variable domains are too restrictive",
                "Verify that precedence/dependency constraints form a valid DAG",
                "Consider increasing search time limit if using timeout",
            ]
        )

    summary = "Problem is infeasible. "
    if bounds_conflicts:
        summary += f"Found {len(bounds_conflicts)} variable bound conflicts. "
    if conflicting_constraints:
        summary += (
            f"Identified {len(conflicting_constraints)} potentially conflicting constraints. "
        )
    if not bounds_conflicts and not conflicting_constraints:
        summary += (
            "No obvious conflicts detected. Problem may be inherently infeasible "
            "due to combination of constraints."
        )

    return InfeasibilityDiagnosis(
        status=SolverStatus.INFEASIBLE,
        summary=summary,
        conflicting_constraints=conflicting_constraints,
        suggestions=suggestions,
        variable_bounds_conflicts=bounds_conflicts,
    )


def get_solver_diagnostics() -> dict:
    """Get comprehensive solver diagnostics.

    Returns:
        Dictionary with health, stats, and recent performance
    """
    health = check_solver_health()
    stats = get_global_statistics()

    # Get recent solve outcomes
    recent_outcomes = [m.outcome.value for m in stats.recent_metrics[-10:]]

    # Get recent solve times
    recent_times = [
        {"problem_id": m.problem_id, "solve_time_ms": round(m.solve_time_ms, 2)}
        for m in stats.recent_metrics[-5:]
    ]

    return {
        "health": health.to_dict(),
        "statistics": stats.to_dict(),
        "recent_outcomes": recent_outcomes,
        "recent_solve_times": recent_times,
        "version": "1.0.0",  # TODO: Get from package metadata
    }
