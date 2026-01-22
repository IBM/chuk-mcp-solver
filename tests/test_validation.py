"""Tests for model validation framework."""

from chuk_mcp_solver.models import (
    AllDifferentParams,
    Constraint,
    ConstraintKind,
    ElementParams,
    ImplicationParams,
    LinearConstraintParams,
    LinearTerm,
    Objective,
    ObjectiveSense,
    SolveConstraintModelRequest,
    SolverMode,
    TableParams,
    Variable,
    VariableDomain,
    VariableDomainType,
)
from chuk_mcp_solver.validation import (
    ModelValidator,
    validate_model,
)


def test_valid_model():
    """Test that a valid model passes validation."""
    request = SolveConstraintModelRequest(
        mode=SolverMode.SATISFY,
        variables=[
            Variable(
                id="x",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            ),
            Variable(
                id="y",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            ),
        ],
        constraints=[
            Constraint(
                id="c1",
                kind=ConstraintKind.LINEAR,
                params=LinearConstraintParams(
                    terms=[
                        LinearTerm(var="x", coef=1),
                        LinearTerm(var="y", coef=1),
                    ],
                    sense="<=",
                    rhs=15,
                ),
            )
        ],
    )

    result = validate_model(request)

    assert result.is_valid
    assert len(result.errors) == 0


def test_duplicate_variable_ids():
    """Test detection of duplicate variable IDs."""
    request = SolveConstraintModelRequest(
        mode=SolverMode.SATISFY,
        variables=[
            Variable(
                id="x",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            ),
            Variable(
                id="x",  # Duplicate
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            ),
        ],
        constraints=[],
    )

    result = validate_model(request)

    assert not result.is_valid
    assert len(result.errors) == 1
    assert "duplicate" in result.errors[0].message.lower()
    assert "rename" in result.errors[0].suggestion.lower()


def test_invalid_variable_bounds():
    """Test detection of invalid variable bounds."""
    request = SolveConstraintModelRequest(
        mode=SolverMode.SATISFY,
        variables=[
            Variable(
                id="x",
                domain=VariableDomain(
                    type=VariableDomainType.INTEGER, lower=10, upper=5
                ),  # Invalid
            )
        ],
        constraints=[],
    )

    result = validate_model(request)

    assert not result.is_valid
    assert len(result.errors) == 1
    assert "lower bound" in result.errors[0].message.lower()
    assert "greater than upper bound" in result.errors[0].message.lower()
    assert "swap" in result.errors[0].suggestion.lower()


def test_large_domain_warning():
    """Test warning for very large variable domains."""
    request = SolveConstraintModelRequest(
        mode=SolverMode.SATISFY,
        variables=[
            Variable(
                id="x",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10_000_000),
            )
        ],
        constraints=[
            # Add a constraint to avoid "no constraints" warning
            Constraint(
                id="c1",
                kind=ConstraintKind.LINEAR,
                params=LinearConstraintParams(
                    terms=[LinearTerm(var="x", coef=1)],
                    sense=">=",
                    rhs=0,
                ),
            )
        ],
    )

    result = validate_model(request)

    assert result.is_valid  # Warning, not error
    assert len(result.warnings) == 1
    assert "very large domain" in result.warnings[0].message.lower()
    assert "tighten" in result.warnings[0].suggestion.lower()


def test_undefined_variable_in_constraint():
    """Test detection of undefined variables in constraints."""
    request = SolveConstraintModelRequest(
        mode=SolverMode.SATISFY,
        variables=[
            Variable(
                id="x",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            )
        ],
        constraints=[
            Constraint(
                id="c1",
                kind=ConstraintKind.LINEAR,
                params=LinearConstraintParams(
                    terms=[
                        LinearTerm(var="x", coef=1),
                        LinearTerm(var="y", coef=1),  # Undefined
                    ],
                    sense="<=",
                    rhs=10,
                ),
            )
        ],
    )

    result = validate_model(request)

    assert not result.is_valid
    assert len(result.errors) == 1
    assert "not defined" in result.errors[0].message.lower()
    assert "define variable" in result.errors[0].suggestion.lower()


def test_similar_variable_suggestion():
    """Test that similar variable names are suggested."""
    request = SolveConstraintModelRequest(
        mode=SolverMode.SATISFY,
        variables=[
            Variable(
                id="x1",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            )
        ],
        constraints=[
            Constraint(
                id="c1",
                kind=ConstraintKind.LINEAR,
                params=LinearConstraintParams(
                    terms=[
                        LinearTerm(var="x2", coef=1),  # Typo - should be x1
                    ],
                    sense="<=",
                    rhs=10,
                ),
            )
        ],
    )

    result = validate_model(request)

    assert not result.is_valid
    assert "did you mean 'x1'" in result.errors[0].suggestion.lower()


def test_zero_coefficient_warning():
    """Test warning for zero coefficients in constraints."""
    request = SolveConstraintModelRequest(
        mode=SolverMode.SATISFY,
        variables=[
            Variable(
                id="x",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            ),
            Variable(
                id="y",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            ),
        ],
        constraints=[
            Constraint(
                id="c1",
                kind=ConstraintKind.LINEAR,
                params=LinearConstraintParams(
                    terms=[
                        LinearTerm(var="x", coef=1),
                        LinearTerm(var="y", coef=0),  # Zero coefficient
                    ],
                    sense="<=",
                    rhs=10,
                ),
            )
        ],
    )

    result = validate_model(request)

    assert result.is_valid  # Warning, not error
    assert len(result.warnings) == 1
    assert "zero coefficient" in result.warnings[0].message.lower()
    assert "remove" in result.warnings[0].suggestion.lower()


def test_duplicate_constraint_ids():
    """Test detection of duplicate constraint IDs."""
    request = SolveConstraintModelRequest(
        mode=SolverMode.SATISFY,
        variables=[
            Variable(
                id="x",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            )
        ],
        constraints=[
            Constraint(
                id="c1",
                kind=ConstraintKind.LINEAR,
                params=LinearConstraintParams(
                    terms=[LinearTerm(var="x", coef=1)],
                    sense="<=",
                    rhs=10,
                ),
            ),
            Constraint(
                id="c1",  # Duplicate
                kind=ConstraintKind.LINEAR,
                params=LinearConstraintParams(
                    terms=[LinearTerm(var="x", coef=1)],
                    sense=">=",
                    rhs=0,
                ),
            ),
        ],
    )

    result = validate_model(request)

    assert not result.is_valid
    assert len(result.errors) == 1
    assert "duplicate" in result.errors[0].message.lower()


def test_optimize_without_objective():
    """Test error for optimize mode without objective."""
    request = SolveConstraintModelRequest(
        mode=SolverMode.OPTIMIZE,
        variables=[
            Variable(
                id="x",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            )
        ],
        constraints=[],
        objective=None,  # Missing
    )

    result = validate_model(request)

    assert not result.is_valid
    assert len(result.errors) == 1
    assert "objective" in result.errors[0].message.lower()
    assert "add an objective" in result.errors[0].suggestion.lower()


def test_satisfy_with_objective_warning():
    """Test warning for satisfy mode with objective."""
    request = SolveConstraintModelRequest(
        mode=SolverMode.SATISFY,
        variables=[
            Variable(
                id="x",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            )
        ],
        constraints=[
            Constraint(
                id="c1",
                kind=ConstraintKind.LINEAR,
                params=LinearConstraintParams(
                    terms=[LinearTerm(var="x", coef=1)],
                    sense=">=",
                    rhs=0,
                ),
            )
        ],
        objective=Objective(sense=ObjectiveSense.MINIMIZE, terms=[LinearTerm(var="x", coef=1)]),
    )

    result = validate_model(request)

    assert result.is_valid  # Warning, not error
    assert len(result.warnings) == 1
    assert "ignored" in result.warnings[0].message.lower()


def test_undefined_variable_in_objective():
    """Test detection of undefined variables in objective."""
    request = SolveConstraintModelRequest(
        mode=SolverMode.OPTIMIZE,
        variables=[
            Variable(
                id="x",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            )
        ],
        constraints=[],
        objective=Objective(
            sense=ObjectiveSense.MINIMIZE,
            terms=[LinearTerm(var="y", coef=1)],  # Undefined
        ),
    )

    result = validate_model(request)

    assert not result.is_valid
    assert len(result.errors) >= 1  # At least the undefined variable error
    # Find the undefined variable error
    var_errors = [e for e in result.errors if "not defined" in e.message.lower()]
    assert len(var_errors) == 1
    assert "objective" in var_errors[0].location.lower()


def test_all_different_undefined_variable():
    """Test detection of undefined variables in all_different constraint."""
    request = SolveConstraintModelRequest(
        mode=SolverMode.SATISFY,
        variables=[
            Variable(
                id="x",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            )
        ],
        constraints=[
            Constraint(
                id="c1",
                kind=ConstraintKind.ALL_DIFFERENT,
                params=AllDifferentParams(vars=["x", "y", "z"]),  # y, z undefined
            )
        ],
    )

    result = validate_model(request)

    assert not result.is_valid
    assert len(result.errors) == 2  # y and z


def test_element_undefined_variables():
    """Test detection of undefined variables in element constraint."""
    request = SolveConstraintModelRequest(
        mode=SolverMode.SATISFY,
        variables=[
            Variable(
                id="x",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            )
        ],
        constraints=[
            Constraint(
                id="c1",
                kind=ConstraintKind.ELEMENT,
                params=ElementParams(
                    index_var="idx",  # Undefined
                    array=[1, 2, 3],
                    target_var="tgt",  # Undefined
                ),
            )
        ],
    )

    result = validate_model(request)

    assert not result.is_valid
    assert len(result.errors) == 2  # idx and tgt


def test_table_undefined_variables():
    """Test detection of undefined variables in table constraint."""
    request = SolveConstraintModelRequest(
        mode=SolverMode.SATISFY,
        variables=[
            Variable(
                id="x",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            )
        ],
        constraints=[
            Constraint(
                id="c1",
                kind=ConstraintKind.TABLE,
                params=TableParams(
                    vars=["x", "y"],  # y undefined
                    allowed_tuples=[[1, 2], [3, 4]],
                ),
            )
        ],
    )

    result = validate_model(request)

    assert not result.is_valid
    assert len(result.errors) == 1


def test_implication_undefined_variable():
    """Test detection of undefined variables in implication constraint."""
    request = SolveConstraintModelRequest(
        mode=SolverMode.SATISFY,
        variables=[
            Variable(
                id="x",
                domain=VariableDomain(type=VariableDomainType.BOOL),
            )
        ],
        constraints=[
            Constraint(
                id="c2",
                kind=ConstraintKind.LINEAR,
                params=LinearConstraintParams(
                    terms=[LinearTerm(var="x", coef=1)],
                    sense="<=",
                    rhs=5,
                ),
            ),
            Constraint(
                id="c1",
                kind=ConstraintKind.IMPLICATION,
                params=ImplicationParams(
                    if_var="b",  # Undefined
                    then_constraint_id="c2",  # Reference to constraint c2
                ),
            ),
        ],
    )

    result = validate_model(request)

    assert not result.is_valid
    assert len(result.errors) == 1
    assert "condition" in result.errors[0].message.lower()


def test_under_constrained_model_info():
    """Test info message for under-constrained models."""
    request = SolveConstraintModelRequest(
        mode=SolverMode.SATISFY,
        variables=[
            Variable(
                id=f"x{i}",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            )
            for i in range(20)  # 20 variables
        ],
        constraints=[  # Only 2 constraints
            Constraint(
                id="c1",
                kind=ConstraintKind.LINEAR,
                params=LinearConstraintParams(
                    terms=[LinearTerm(var="x0", coef=1)],
                    sense="<=",
                    rhs=5,
                ),
            )
        ],
    )

    result = validate_model(request)

    assert result.is_valid
    assert len(result.infos) >= 1
    assert any("under-constrained" in info.message.lower() for info in result.infos)


def test_over_constrained_model_info():
    """Test info message for over-constrained models."""
    request = SolveConstraintModelRequest(
        mode=SolverMode.SATISFY,
        variables=[
            Variable(
                id="x",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            )
        ],
        constraints=[
            Constraint(
                id=f"c{i}",
                kind=ConstraintKind.LINEAR,
                params=LinearConstraintParams(
                    terms=[LinearTerm(var="x", coef=1)],
                    sense="<=",
                    rhs=10,
                ),
            )
            for i in range(15)  # 15 constraints for 1 variable
        ],
    )

    result = validate_model(request)

    assert result.is_valid
    assert len(result.infos) >= 1
    assert any("over-constrained" in info.message.lower() for info in result.infos)


def test_no_constraints_warning():
    """Test warning for model with no constraints in satisfy mode."""
    request = SolveConstraintModelRequest(
        mode=SolverMode.SATISFY,
        variables=[
            Variable(
                id="x",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            )
        ],
        constraints=[],  # No constraints
    )

    result = validate_model(request)

    assert result.is_valid  # Warning, not error
    assert len(result.warnings) == 1
    assert "no constraints" in result.warnings[0].message.lower()


def test_validation_result_to_dict():
    """Test ValidationResult to_dict conversion."""
    request = SolveConstraintModelRequest(
        mode=SolverMode.SATISFY,
        variables=[
            Variable(
                id="x",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=10, upper=5),  # Error
            )
        ],
        constraints=[],
    )

    result = validate_model(request)
    result_dict = result.to_dict()

    assert result_dict["is_valid"] is False
    assert result_dict["error_count"] == 1
    assert result_dict["warning_count"] >= 0
    assert "issues" in result_dict
    assert len(result_dict["issues"]) > 0


def test_model_validator_class():
    """Test using ModelValidator class directly."""
    validator = ModelValidator()

    request = SolveConstraintModelRequest(
        mode=SolverMode.SATISFY,
        variables=[
            Variable(
                id="x",
                domain=VariableDomain(type=VariableDomainType.INTEGER, lower=0, upper=10),
            )
        ],
        constraints=[],
    )

    result = validator.validate(request)

    assert result.is_valid
    assert len(result.errors) == 0
