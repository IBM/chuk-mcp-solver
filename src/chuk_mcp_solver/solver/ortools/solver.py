"""OR-Tools CP-SAT solver implementation.

Main solver class that orchestrates constraint solving using Google OR-Tools.
"""

import time

from ortools.sat.python import cp_model

from chuk_mcp_solver.cache import get_global_cache
from chuk_mcp_solver.diagnostics import diagnose_infeasibility
from chuk_mcp_solver.models import (
    Explanation,
    SolveConstraintModelRequest,
    SolveConstraintModelResponse,
    SolverMode,
    SolverStatus,
    VariableDomainType,
)
from chuk_mcp_solver.observability import SolveOutcome, logger, track_solve
from chuk_mcp_solver.solver.ortools.constraints import build_constraint
from chuk_mcp_solver.solver.ortools.objectives import build_objective, configure_solver
from chuk_mcp_solver.solver.ortools.responses import build_failure_response, build_success_response
from chuk_mcp_solver.solver.provider import SolverProvider
from chuk_mcp_solver.validation import validate_model


class ORToolsSolver(SolverProvider):
    """Google OR-Tools CP-SAT constraint solver.

    High-performance constraint programming solver supporting:
    - Integer and boolean variables
    - Linear constraints
    - Global constraints (all_different, element, table)
    - Scheduling constraints (cumulative, no_overlap)
    - Routing constraints (circuit)
    - Inventory constraints (reservoir)
    - Multi-objective optimization
    """

    async def solve_constraint_model(
        self, request: SolveConstraintModelRequest
    ) -> SolveConstraintModelResponse:
        """Solve a constraint/optimization model using OR-Tools CP-SAT.

        Args:
            request: The constraint model to solve.

        Returns:
            SolveConstraintModelResponse with solution status and results.

        Raises:
            ValueError: If the request is invalid or contains unsupported features.
        """
        # Validate model first
        validation_result = validate_model(request)
        if not validation_result.is_valid:
            # Format validation errors into explanation
            error_summary = (
                f"Model validation failed with {len(validation_result.errors)} error(s):\n"
            )
            for i, error in enumerate(validation_result.errors, 1):
                error_summary += f"\n{i}. {error.message}"
                error_summary += f"\n   Location: {error.location}"
                error_summary += f"\n   Suggestion: {error.suggestion}\n"

            return SolveConstraintModelResponse(
                status=SolverStatus.ERROR,
                explanation=Explanation(summary=error_summary),
            )

        # Validate request (legacy validation)
        self._validate_request(request)

        # Check cache if enabled
        cache = get_global_cache()
        if request.search and request.search.enable_solution_caching:
            cached_response = cache.get(request)
            if cached_response is not None:
                logger.info("Returning cached solution")
                return cached_response

        # Generate problem ID for tracking
        problem_id = f"{request.mode.value}_{len(request.variables)}v_{len(request.constraints)}c"

        # Track solve operation with observability
        with track_solve(
            problem_id=problem_id,
            num_variables=len(request.variables),
            num_constraints=len(request.constraints),
            mode=request.mode.value,
        ) as tracker:
            try:
                # Build CP-SAT model
                model = cp_model.CpModel()
                var_map = self._build_variables(model, request)
                self._build_constraints(model, request, var_map)

                # Set objective if optimizing
                if request.mode == SolverMode.OPTIMIZE and request.objective:
                    build_objective(model, request.objective, var_map)

                # Solve
                solver = cp_model.CpSolver()
                configure_solver(solver, request)

                # Add warm-start solution hints if provided
                if request.search and request.search.warm_start_solution:
                    for var_id, value in request.search.warm_start_solution.items():
                        if var_id in var_map:
                            model.AddHint(var_map[var_id], value)  # type: ignore[attr-defined]

                # Track solve time
                start_time = time.time()
                status = solver.Solve(model)
                solve_time_ms = int((time.time() - start_time) * 1000)

                # Convert status
                solver_status = self._convert_status(status, request.mode)  # type: ignore[arg-type]

                # Build response and track outcome
                if solver_status in (
                    SolverStatus.OPTIMAL,
                    SolverStatus.FEASIBLE,
                    SolverStatus.SATISFIED,
                ):
                    # Track successful solve
                    outcome = SolveOutcome.SUCCESS
                    objective_value = (
                        solver.ObjectiveValue() if solver.ObjectiveValue() != 0 else None
                    )
                    tracker.set_outcome(
                        outcome=outcome,
                        objective_value=objective_value,
                        num_solutions=1,
                    )
                    response = build_success_response(
                        solver_status, solver, var_map, request, solve_time_ms
                    )

                    # Cache successful solution
                    if request.search and request.search.enable_solution_caching:
                        cache.put(request, response)

                    return response
                else:
                    # Track failure and provide diagnosis
                    if solver_status == SolverStatus.INFEASIBLE:
                        tracker.set_outcome(outcome=SolveOutcome.INFEASIBLE)
                        # Generate detailed infeasibility diagnosis
                        diagnosis = diagnose_infeasibility(request)

                        # Format diagnosis into summary
                        summary_parts = [diagnosis.summary]
                        if diagnosis.suggestions:
                            summary_parts.append("\n\nSuggestions:")
                            for suggestion in diagnosis.suggestions:
                                summary_parts.append(f"- {suggestion}")

                        return SolveConstraintModelResponse(
                            status=solver_status,
                            explanation=Explanation(summary="\n".join(summary_parts)),
                        )
                    elif solver_status == SolverStatus.TIMEOUT:
                        tracker.set_outcome(outcome=SolveOutcome.TIMEOUT)

                        # Check if solver found any solution
                        has_solution = status in (cp_model.FEASIBLE, cp_model.OPTIMAL)

                        # Return partial solution if requested and available
                        if (
                            request.search
                            and request.search.return_partial_solution
                            and has_solution
                        ):
                            # Return best solution found so far with TIMEOUT_BEST status
                            response = build_success_response(
                                SolverStatus.TIMEOUT_BEST, solver, var_map, request, solve_time_ms
                            )
                            # Add note about timeout
                            if response.explanation:
                                response.explanation.summary += (
                                    "\n\nNote: Solver timed out. "
                                    "This is the best solution found so far (not proven optimal)."
                                )
                            else:
                                response.explanation = Explanation(
                                    summary="Solver timed out. "
                                    "This is the best solution found so far (not proven optimal)."
                                )
                            return response
                        else:
                            # No solution found before timeout
                            return SolveConstraintModelResponse(
                                status=SolverStatus.TIMEOUT_NO_SOLUTION,
                                solve_time_ms=solve_time_ms,
                                explanation=Explanation(
                                    summary="Solver timed out before finding any solution. "
                                    "Try increasing max_time_ms, simplifying the problem, "
                                    "or providing a warm-start solution hint."
                                ),
                            )
                    else:
                        tracker.set_outcome(outcome=SolveOutcome.ERROR)

                    return build_failure_response(solver_status)

            except Exception as e:
                logger.error(f"Error solving model: {e}", exc_info=True)
                tracker.set_error(str(e))
                return SolveConstraintModelResponse(
                    status=SolverStatus.ERROR,
                    explanation=Explanation(summary=f"Solver error: {str(e)}"),
                )

    def _validate_request(self, request: SolveConstraintModelRequest) -> None:
        """Validate the solve request.

        Args:
            request: The request to validate.

        Raises:
            ValueError: If the request is invalid.
        """
        if request.mode == SolverMode.OPTIMIZE and not request.objective:
            raise ValueError("Objective required when mode is 'optimize'")

        if request.mode == SolverMode.SATISFY and request.objective:
            logger.warning(
                "Objective provided in 'satisfy' mode will be ignored. "
                "Use mode='optimize' to optimize the objective."
            )

    def _build_variables(
        self, model: cp_model.CpModel, request: SolveConstraintModelRequest
    ) -> dict[str, cp_model.IntVar]:
        """Build CP-SAT variables from request.

        Args:
            model: The CP-SAT model.
            request: The request containing variable definitions.

        Returns:
            Mapping from variable ID to CP-SAT variable.
        """
        var_map = {}

        for var_def in request.variables:
            if var_def.domain.type == VariableDomainType.BOOL:
                # Boolean variables are [0, 1] integer variables
                cp_var = model.NewIntVar(0, 1, var_def.id)  # type: ignore[attr-defined]
            else:  # INTEGER
                cp_var = model.NewIntVar(var_def.domain.lower, var_def.domain.upper, var_def.id)  # type: ignore[attr-defined]

            var_map[var_def.id] = cp_var

        return var_map

    def _build_constraints(
        self,
        model: cp_model.CpModel,
        request: SolveConstraintModelRequest,
        var_map: dict[str, cp_model.IntVar],
    ) -> None:
        """Build all constraints.

        Args:
            model: The CP-SAT model.
            request: The request containing constraint definitions.
            var_map: Mapping from variable ID to CP-SAT variable.
        """
        # Build a constraints map for implication constraint lookups
        constraints_map = {c.id: c for c in request.constraints}

        # Find constraints that are referenced by implications (to avoid building them twice)
        referenced_by_implications = set()
        for constraint in request.constraints:
            if constraint.kind == "implication":
                from chuk_mcp_solver.models import ImplicationParams

                params: ImplicationParams = constraint.params  # type: ignore[assignment]
                referenced_by_implications.add(params.then_constraint_id)

        for constraint in request.constraints:
            # Skip constraints that are only referenced by implications
            # (they will be built with OnlyEnforceIf by the implication)
            if constraint.id in referenced_by_implications:
                continue

            build_constraint(model, constraint, var_map, constraints_map)

    def _convert_status(self, cp_status: int, mode: SolverMode) -> SolverStatus:
        """Convert CP-SAT status to SolverStatus.

        Args:
            cp_status: The CP-SAT status code.
            mode: The solver mode (satisfy or optimize).

        Returns:
            The corresponding SolverStatus.
        """
        if cp_status == cp_model.OPTIMAL:
            # In satisfy mode, treat OPTIMAL as SATISFIED
            if mode == SolverMode.SATISFY:
                return SolverStatus.SATISFIED
            else:
                return SolverStatus.OPTIMAL
        elif cp_status == cp_model.FEASIBLE:
            if mode == SolverMode.SATISFY:
                return SolverStatus.SATISFIED
            else:
                return SolverStatus.FEASIBLE
        elif cp_status == cp_model.INFEASIBLE:
            return SolverStatus.INFEASIBLE
        elif cp_status == cp_model.UNKNOWN:
            return SolverStatus.TIMEOUT
        elif cp_status == cp_model.MODEL_INVALID:
            return SolverStatus.ERROR
        else:
            return SolverStatus.ERROR
