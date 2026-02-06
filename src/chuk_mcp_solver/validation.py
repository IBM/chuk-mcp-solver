"""Model validation and pre-solve checks for constraint models.

Provides comprehensive validation with actionable suggestions to help
LLMs and users fix modeling issues before solving.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import cast

from chuk_mcp_solver.models import (
    AllDifferentParams,
    Constraint,
    ConstraintKind,
    ElementParams,
    ImplicationParams,
    LinearConstraintParams,
    SolveConstraintModelRequest,
    SolverMode,
    TableParams,
)


class ValidationSeverity(StrEnum):
    """Severity level of validation issue."""

    ERROR = "error"  # Must fix - will cause solve to fail
    WARNING = "warning"  # Should fix - may cause poor performance
    INFO = "info"  # Nice to fix - improves model quality


@dataclass
class ValidationIssue:
    """A validation issue found in the model."""

    severity: ValidationSeverity
    message: str
    suggestion: str
    location: str  # e.g., "variable 'x'", "constraint 'c1'"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "severity": self.severity.value,
            "message": self.message,
            "suggestion": self.suggestion,
            "location": self.location,
        }


@dataclass
class ValidationResult:
    """Result of model validation."""

    is_valid: bool
    issues: list[ValidationIssue]

    @property
    def errors(self) -> list[ValidationIssue]:
        """Get only error-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Get only warning-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    @property
    def infos(self) -> list[ValidationIssue]:
        """Get only info-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.INFO]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "info_count": len(self.infos),
            "issues": [issue.to_dict() for issue in self.issues],
        }


class ModelValidator:
    """Validates constraint models before solving."""

    def __init__(self) -> None:
        """Initialize validator."""
        self.issues: list[ValidationIssue] = []

    def validate(self, request: SolveConstraintModelRequest) -> ValidationResult:
        """Validate a solve request.

        Args:
            request: The request to validate

        Returns:
            ValidationResult with any issues found
        """
        self.issues = []

        # Run all validation checks
        self._validate_variables(request)
        self._validate_constraints(request)
        self._validate_objective(request)
        self._validate_model_structure(request)

        # Model is valid only if there are no errors
        is_valid = len(self.errors) == 0

        return ValidationResult(is_valid=is_valid, issues=self.issues)

    @property
    def errors(self) -> list[ValidationIssue]:
        """Get current error-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    def _validate_variables(self, request: SolveConstraintModelRequest) -> None:
        """Validate variable definitions."""
        var_ids = set()

        for var in request.variables:
            # Check for duplicate IDs
            if var.id in var_ids:
                self.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Duplicate variable ID '{var.id}'",
                        suggestion=f"Rename one of the variables with ID '{var.id}' to a unique name",
                        location=f"variable '{var.id}'",
                    )
                )
            var_ids.add(var.id)

            # Check for invalid bounds
            if var.domain.type.value == "integer":
                if var.domain.lower > var.domain.upper:
                    self.issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            message=f"Variable '{var.id}' has lower bound ({var.domain.lower}) "
                            f"greater than upper bound ({var.domain.upper})",
                            suggestion=f"Swap the bounds: set lower={var.domain.upper}, "
                            f"upper={var.domain.lower}",
                            location=f"variable '{var.id}'",
                        )
                    )

                # Check for very large domains (warning)
                domain_size = var.domain.upper - var.domain.lower
                if domain_size > 1_000_000:
                    self.issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            message=f"Variable '{var.id}' has very large domain "
                            f"[{var.domain.lower}, {var.domain.upper}] with {domain_size:,} values",
                            suggestion="Consider tightening the bounds if possible to improve "
                            "solving performance",
                            location=f"variable '{var.id}'",
                        )
                    )

    def _validate_constraints(self, request: SolveConstraintModelRequest) -> None:
        """Validate constraint definitions."""
        var_ids = {v.id for v in request.variables}
        constraint_ids = set()

        for constraint in request.constraints:
            # Check for duplicate constraint IDs
            if constraint.id in constraint_ids:
                self.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Duplicate constraint ID '{constraint.id}'",
                        suggestion=f"Rename one of the constraints with ID '{constraint.id}' "
                        "to a unique name",
                        location=f"constraint '{constraint.id}'",
                    )
                )
            constraint_ids.add(constraint.id)

            # Validate constraint-specific parameters
            self._validate_constraint_params(constraint, var_ids)

    def _validate_constraint_params(self, constraint: Constraint, var_ids: set[str]) -> None:
        """Validate constraint parameters."""
        params = constraint.params

        if constraint.kind == ConstraintKind.LINEAR:
            self._validate_linear_constraint(
                constraint, cast(LinearConstraintParams, params), var_ids
            )
        elif constraint.kind == ConstraintKind.ALL_DIFFERENT:
            self._validate_all_different_constraint(
                constraint, cast(AllDifferentParams, params), var_ids
            )
        elif constraint.kind == ConstraintKind.ELEMENT:
            self._validate_element_constraint(constraint, cast(ElementParams, params), var_ids)
        elif constraint.kind == ConstraintKind.TABLE:
            self._validate_table_constraint(constraint, cast(TableParams, params), var_ids)
        elif constraint.kind == ConstraintKind.IMPLICATION:
            self._validate_implication_constraint(
                constraint, cast(ImplicationParams, params), var_ids
            )

    def _validate_linear_constraint(
        self, constraint: Constraint, params: LinearConstraintParams, var_ids: set[str]
    ) -> None:
        """Validate linear constraint parameters."""
        # Check for undefined variables
        for term in params.terms:
            if term.var not in var_ids:
                similar = self._find_similar_var(term.var, var_ids)
                suggestion = (
                    f"Define variable '{term.var}' in the variables list"
                    if not similar
                    else f"Did you mean '{similar}'? Or define variable '{term.var}'"
                )
                self.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Variable '{term.var}' referenced in constraint '{constraint.id}' "
                        "is not defined",
                        suggestion=suggestion,
                        location=f"constraint '{constraint.id}'",
                    )
                )

        # Check for zero coefficients (warning)
        zero_coef_vars = [term.var for term in params.terms if term.coef == 0]
        if zero_coef_vars:
            self.issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"Constraint '{constraint.id}' has zero coefficients for variables: "
                    f"{', '.join(zero_coef_vars)}",
                    suggestion="Remove terms with zero coefficients - they have no effect",
                    location=f"constraint '{constraint.id}'",
                )
            )

    def _validate_all_different_constraint(
        self, constraint: Constraint, params: AllDifferentParams, var_ids: set[str]
    ) -> None:
        """Validate all_different constraint parameters."""
        for var in params.vars:
            if var not in var_ids:
                similar = self._find_similar_var(var, var_ids)
                suggestion = (
                    f"Define variable '{var}' in the variables list"
                    if not similar
                    else f"Did you mean '{similar}'? Or define variable '{var}'"
                )
                self.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Variable '{var}' in all_different constraint '{constraint.id}' "
                        "is not defined",
                        suggestion=suggestion,
                        location=f"constraint '{constraint.id}'",
                    )
                )

    def _validate_element_constraint(
        self, constraint: Constraint, params: ElementParams, var_ids: set[str]
    ) -> None:
        """Validate element constraint parameters."""
        if params.index_var not in var_ids:
            similar = self._find_similar_var(params.index_var, var_ids)
            suggestion = (
                f"Define variable '{params.index_var}' in the variables list"
                if not similar
                else f"Did you mean '{similar}'? Or define variable '{params.index_var}'"
            )
            self.issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Index variable '{params.index_var}' in element constraint "
                    f"'{constraint.id}' is not defined",
                    suggestion=suggestion,
                    location=f"constraint '{constraint.id}'",
                )
            )

        if params.target_var not in var_ids:
            similar = self._find_similar_var(params.target_var, var_ids)
            suggestion = (
                f"Define variable '{params.target_var}' in the variables list"
                if not similar
                else f"Did you mean '{similar}'? Or define variable '{params.target_var}'"
            )
            self.issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Target variable '{params.target_var}' in element constraint "
                    f"'{constraint.id}' is not defined",
                    suggestion=suggestion,
                    location=f"constraint '{constraint.id}'",
                )
            )

    def _validate_table_constraint(
        self, constraint: Constraint, params: TableParams, var_ids: set[str]
    ) -> None:
        """Validate table constraint parameters."""
        for var in params.vars:
            if var not in var_ids:
                similar = self._find_similar_var(var, var_ids)
                suggestion = (
                    f"Define variable '{var}' in the variables list"
                    if not similar
                    else f"Did you mean '{similar}'? Or define variable '{var}'"
                )
                self.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Variable '{var}' in table constraint '{constraint.id}' "
                        "is not defined",
                        suggestion=suggestion,
                        location=f"constraint '{constraint.id}'",
                    )
                )

    def _validate_implication_constraint(
        self, constraint: Constraint, params: ImplicationParams, var_ids: set[str]
    ) -> None:
        """Validate implication constraint parameters."""
        if params.if_var not in var_ids:
            similar = self._find_similar_var(params.if_var, var_ids)
            suggestion = (
                f"Define variable '{params.if_var}' in the variables list"
                if not similar
                else f"Did you mean '{similar}'? Or define variable '{params.if_var}'"
            )
            self.issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Condition variable '{params.if_var}' in implication constraint "
                    f"'{constraint.id}' is not defined",
                    suggestion=suggestion,
                    location=f"constraint '{constraint.id}'",
                )
            )

    def _validate_objective(self, request: SolveConstraintModelRequest) -> None:
        """Validate objective function."""
        if request.mode == SolverMode.OPTIMIZE and not request.objective:
            self.issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message="Optimization mode requires an objective function",
                    suggestion="Either add an objective function or change mode to 'satisfy'",
                    location="request",
                )
            )

        if request.mode == SolverMode.SATISFY and request.objective:
            self.issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message="Objective function provided in satisfy mode will be ignored",
                    suggestion="Change mode to 'optimize' to use the objective, or remove it",
                    location="request",
                )
            )

        # Validate objective variables if present
        if request.objective:
            var_ids = {v.id for v in request.variables}
            objectives = (
                request.objective if isinstance(request.objective, list) else [request.objective]
            )

            for obj in objectives:
                for term in obj.terms:
                    if term.var not in var_ids:
                        similar = self._find_similar_var(term.var, var_ids)
                        suggestion = (
                            f"Define variable '{term.var}' in the variables list"
                            if not similar
                            else f"Did you mean '{similar}'?"
                        )
                        self.issues.append(
                            ValidationIssue(
                                severity=ValidationSeverity.ERROR,
                                message=f"Variable '{term.var}' in objective is not defined",
                                suggestion=suggestion,
                                location="objective",
                            )
                        )

    def _validate_model_structure(self, request: SolveConstraintModelRequest) -> None:
        """Validate overall model structure and quality."""
        num_vars = len(request.variables)
        num_constraints = len(request.constraints)

        # Check for under-constrained models
        if num_vars > 10 and num_constraints < num_vars / 5:
            self.issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    message=f"Model has {num_vars} variables but only {num_constraints} "
                    "constraints - it may be under-constrained",
                    suggestion="Consider adding more constraints to better define the problem",
                    location="model structure",
                )
            )

        # Check for over-constrained models (many constraints per variable)
        if num_vars > 0 and num_constraints / num_vars > 10:
            self.issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    message=f"Model has {num_constraints} constraints for {num_vars} variables "
                    f"(ratio {num_constraints / num_vars:.1f}:1) - it may be over-constrained",
                    suggestion="Check if some constraints are redundant or conflicting",
                    location="model structure",
                )
            )

        # Check for no constraints at all
        if num_constraints == 0 and request.mode == SolverMode.SATISFY:
            self.issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message="Model has no constraints in satisfy mode",
                    suggestion="Any variable assignment will be valid - is this intentional?",
                    location="model structure",
                )
            )

    def _find_similar_var(self, var_id: str, var_ids: set[str]) -> str | None:
        """Find a similar variable ID using simple string matching.

        Args:
            var_id: The undefined variable ID
            var_ids: Set of defined variable IDs

        Returns:
            Most similar variable ID, or None if no good match
        """
        # Simple heuristic: find vars that differ by one character or have similar prefix
        for candidate in var_ids:
            # Check edit distance of 1 (simple version)
            if len(var_id) == len(candidate):
                diff_count = sum(1 for a, b in zip(var_id, candidate, strict=False) if a != b)
                if diff_count == 1:
                    return candidate

            # Check common prefix of at least 3 chars
            if len(var_id) >= 3 and len(candidate) >= 3:
                if var_id[:3] == candidate[:3]:
                    return candidate

        return None


def validate_model(request: SolveConstraintModelRequest) -> ValidationResult:
    """Validate a constraint model.

    Args:
        request: The solve request to validate

    Returns:
        ValidationResult with any issues found
    """
    validator = ModelValidator()
    return validator.validate(request)
