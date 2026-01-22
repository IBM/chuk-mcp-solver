"""Tests for Pydantic models and enums."""

import pytest
from pydantic import ValidationError

from chuk_mcp_solver.models import (
    AllDifferentParams,
    BindingConstraint,
    Constraint,
    ConstraintKind,
    ConstraintSense,
    ElementParams,
    Explanation,
    ImplicationParams,
    LinearConstraintParams,
    LinearTerm,
    Objective,
    ObjectiveSense,
    SearchConfig,
    Solution,
    SolutionVariable,
    SolveConstraintModelRequest,
    SolveConstraintModelResponse,
    SolverMode,
    SolverStatus,
    TableParams,
    Variable,
    VariableDomain,
    VariableDomainType,
)

# ============================================================================
# Enum Tests
# ============================================================================


def test_solver_mode_enum():
    """Test SolverMode enum values."""
    assert SolverMode.SATISFY == "satisfy"
    assert SolverMode.OPTIMIZE == "optimize"
    assert len(SolverMode) == 2


def test_variable_domain_type_enum():
    """Test VariableDomainType enum values."""
    assert VariableDomainType.BOOL == "bool"
    assert VariableDomainType.INTEGER == "integer"
    assert len(VariableDomainType) == 2


def test_constraint_sense_enum():
    """Test ConstraintSense enum values."""
    assert ConstraintSense.LESS_EQUAL == "<="
    assert ConstraintSense.GREATER_EQUAL == ">="
    assert ConstraintSense.EQUAL == "=="
    assert len(ConstraintSense) == 3


def test_objective_sense_enum():
    """Test ObjectiveSense enum values."""
    assert ObjectiveSense.MINIMIZE == "min"
    assert ObjectiveSense.MAXIMIZE == "max"
    assert len(ObjectiveSense) == 2


def test_constraint_kind_enum():
    """Test ConstraintKind enum values."""
    assert ConstraintKind.LINEAR == "linear"
    assert ConstraintKind.ALL_DIFFERENT == "all_different"
    assert ConstraintKind.ELEMENT == "element"
    assert ConstraintKind.TABLE == "table"
    assert ConstraintKind.IMPLICATION == "implication"
    assert ConstraintKind.CUMULATIVE == "cumulative"
    assert ConstraintKind.CIRCUIT == "circuit"
    assert ConstraintKind.RESERVOIR == "reservoir"
    assert ConstraintKind.NO_OVERLAP == "no_overlap"
    assert len(ConstraintKind) == 9


def test_solver_status_enum():
    """Test SolverStatus enum values."""
    assert SolverStatus.OPTIMAL == "optimal"
    assert SolverStatus.FEASIBLE == "feasible"
    assert SolverStatus.SATISFIED == "satisfied"
    assert SolverStatus.INFEASIBLE == "infeasible"
    assert SolverStatus.UNBOUNDED == "unbounded"
    assert SolverStatus.TIMEOUT == "timeout"
    assert SolverStatus.TIMEOUT_BEST == "timeout_best"
    assert SolverStatus.TIMEOUT_NO_SOLUTION == "timeout_no_solution"
    assert SolverStatus.ERROR == "error"
    assert len(SolverStatus) == 9


# ============================================================================
# Variable Domain Tests
# ============================================================================


def test_variable_domain_bool():
    """Test boolean variable domain."""
    domain = VariableDomain(type=VariableDomainType.BOOL)
    assert domain.type == VariableDomainType.BOOL
    assert domain.lower == 0
    assert domain.upper == 1


def test_variable_domain_integer():
    """Test integer variable domain."""
    domain = VariableDomain(type=VariableDomainType.INTEGER, lower=10, upper=20)
    assert domain.type == VariableDomainType.INTEGER
    assert domain.lower == 10
    assert domain.upper == 20


def test_variable_domain_defaults():
    """Test variable domain default values."""
    domain = VariableDomain(type="integer")
    assert domain.lower == 0
    assert domain.upper == 1


# ============================================================================
# Variable Tests
# ============================================================================


def test_variable_minimal():
    """Test variable with minimal fields."""
    var = Variable(id="x", domain={"type": "bool"})
    assert var.id == "x"
    assert var.domain.type == VariableDomainType.BOOL
    assert var.metadata is None


def test_variable_with_metadata():
    """Test variable with metadata."""
    var = Variable(
        id="x", domain={"type": "integer", "lower": 0, "upper": 10}, metadata={"task": "A"}
    )
    assert var.id == "x"
    assert var.metadata == {"task": "A"}


def test_variable_empty_id_fails():
    """Test that empty variable ID fails validation."""
    with pytest.raises(ValidationError):
        Variable(id="", domain={"type": "bool"})


# ============================================================================
# Constraint Parameter Tests
# ============================================================================


def test_linear_term():
    """Test LinearTerm model."""
    term = LinearTerm(var="x", coef=3.5)
    assert term.var == "x"
    assert term.coef == 3.5


def test_linear_constraint_params():
    """Test LinearConstraintParams model."""
    params = LinearConstraintParams(
        terms=[{"var": "x", "coef": 2}, {"var": "y", "coef": 3}], sense="<=", rhs=10
    )
    assert len(params.terms) == 2
    assert params.sense == ConstraintSense.LESS_EQUAL
    assert params.rhs == 10


def test_linear_constraint_params_empty_terms_fails():
    """Test that empty terms list fails validation."""
    with pytest.raises(ValidationError):
        LinearConstraintParams(terms=[], sense="<=", rhs=10)


def test_all_different_params():
    """Test AllDifferentParams model."""
    params = AllDifferentParams(vars=["x", "y", "z"])
    assert params.vars == ["x", "y", "z"]


def test_all_different_params_single_var_fails():
    """Test that single variable fails validation."""
    with pytest.raises(ValidationError):
        AllDifferentParams(vars=["x"])


def test_element_params():
    """Test ElementParams model."""
    params = ElementParams(index_var="idx", array=[10, 20, 30], target_var="result")
    assert params.index_var == "idx"
    assert params.array == [10, 20, 30]
    assert params.target_var == "result"


def test_table_params():
    """Test TableParams model."""
    params = TableParams(vars=["x", "y"], allowed_tuples=[[0, 1], [1, 0]])
    assert params.vars == ["x", "y"]
    assert len(params.allowed_tuples) == 2


# ============================================================================
# Constraint Tests
# ============================================================================


def test_constraint_linear():
    """Test linear constraint."""
    constraint = Constraint(
        id="c1",
        kind="linear",
        params={"terms": [{"var": "x", "coef": 1}], "sense": "<=", "rhs": 5},
    )
    assert constraint.id == "c1"
    assert constraint.kind == ConstraintKind.LINEAR


def test_constraint_all_different():
    """Test all_different constraint."""
    constraint = Constraint(id="c1", kind="all_different", params={"vars": ["x", "y", "z"]})
    assert constraint.kind == ConstraintKind.ALL_DIFFERENT


def test_constraint_with_metadata():
    """Test constraint with metadata."""
    constraint = Constraint(
        id="c1",
        kind="linear",
        params={"terms": [{"var": "x", "coef": 1}], "sense": "<=", "rhs": 5},
        metadata={"description": "Capacity limit"},
    )
    assert constraint.metadata == {"description": "Capacity limit"}


# ============================================================================
# Objective Tests
# ============================================================================


def test_objective_minimize():
    """Test minimize objective."""
    obj = Objective(sense="min", terms=[{"var": "x", "coef": 1}, {"var": "y", "coef": 2}])
    assert obj.sense == ObjectiveSense.MINIMIZE
    assert len(obj.terms) == 2


def test_objective_maximize():
    """Test maximize objective."""
    obj = Objective(sense="max", terms=[{"var": "profit", "coef": 1}])
    assert obj.sense == ObjectiveSense.MAXIMIZE


def test_objective_empty_terms_fails():
    """Test that empty terms list fails validation."""
    with pytest.raises(ValidationError):
        Objective(sense="min", terms=[])


# ============================================================================
# Search Config Tests
# ============================================================================


def test_search_config_defaults():
    """Test SearchConfig default values."""
    config = SearchConfig()
    assert config.max_time_ms is None
    assert config.max_solutions == 1


def test_search_config_with_values():
    """Test SearchConfig with custom values."""
    config = SearchConfig(max_time_ms=5000, max_solutions=10)
    assert config.max_time_ms == 5000
    assert config.max_solutions == 10


def test_search_config_negative_time_fails():
    """Test that negative max_time_ms fails validation."""
    with pytest.raises(ValidationError):
        SearchConfig(max_time_ms=-1)


def test_search_config_zero_solutions_fails():
    """Test that zero max_solutions fails validation."""
    with pytest.raises(ValidationError):
        SearchConfig(max_solutions=0)


# ============================================================================
# Request Tests
# ============================================================================


def test_request_satisfy_mode():
    """Test request in satisfy mode."""
    request = SolveConstraintModelRequest(
        mode="satisfy",
        variables=[{"id": "x", "domain": {"type": "bool"}}],
        constraints=[],
    )
    assert request.mode == SolverMode.SATISFY
    assert len(request.variables) == 1
    assert request.objective is None


def test_request_optimize_mode():
    """Test request in optimize mode."""
    request = SolveConstraintModelRequest(
        mode="optimize",
        variables=[{"id": "x", "domain": {"type": "integer", "lower": 0, "upper": 10}}],
        constraints=[],
        objective={"sense": "min", "terms": [{"var": "x", "coef": 1}]},
    )
    assert request.mode == SolverMode.OPTIMIZE
    assert request.objective is not None


def test_request_empty_variables_fails():
    """Test that empty variables list fails validation."""
    with pytest.raises(ValidationError):
        SolveConstraintModelRequest(mode="satisfy", variables=[], constraints=[])


# ============================================================================
# Solution Tests
# ============================================================================


def test_solution_variable():
    """Test SolutionVariable model."""
    sol_var = SolutionVariable(id="x", value=5.0, metadata={"task": "A"})
    assert sol_var.id == "x"
    assert sol_var.value == 5.0
    assert sol_var.metadata == {"task": "A"}


def test_solution():
    """Test Solution model."""
    solution = Solution(
        variables=[{"id": "x", "value": 1}, {"id": "y", "value": 0}],
        derived={"makespan": 10},
    )
    assert len(solution.variables) == 2
    assert solution.derived == {"makespan": 10}


# ============================================================================
# Explanation Tests
# ============================================================================


def test_binding_constraint():
    """Test BindingConstraint model."""
    bc = BindingConstraint(id="c1", sense="<=", lhs_value=10.0, rhs=10.0)
    assert bc.id == "c1"
    assert bc.sense == ConstraintSense.LESS_EQUAL
    assert bc.lhs_value == 10.0


def test_explanation():
    """Test Explanation model."""
    explanation = Explanation(summary="Found optimal solution", binding_constraints=[])
    assert explanation.summary == "Found optimal solution"
    assert len(explanation.binding_constraints) == 0


# ============================================================================
# Response Tests
# ============================================================================


def test_response_optimal():
    """Test response with optimal status."""
    response = SolveConstraintModelResponse(
        status="optimal",
        objective_value=42.0,
        solutions=[{"variables": [{"id": "x", "value": 1}]}],
    )
    assert response.status == SolverStatus.OPTIMAL
    assert response.objective_value == 42.0


def test_response_infeasible():
    """Test response with infeasible status."""
    response = SolveConstraintModelResponse(
        status="infeasible", explanation={"summary": "No solution exists"}
    )
    assert response.status == SolverStatus.INFEASIBLE
    assert response.objective_value is None


def test_response_has_api_version():
    """Test that response includes API version."""
    response = SolveConstraintModelResponse(status="optimal")
    assert response.apiversion is not None
    assert len(response.apiversion) > 0


# ============================================================================
# Integration Tests (Complex Models)
# ============================================================================


def test_complete_optimization_request():
    """Test a complete optimization request."""
    request = SolveConstraintModelRequest(
        mode="optimize",
        variables=[
            {"id": "x1", "domain": {"type": "bool"}},
            {"id": "x2", "domain": {"type": "bool"}},
        ],
        constraints=[
            {
                "id": "capacity",
                "kind": "linear",
                "params": {
                    "terms": [{"var": "x1", "coef": 2}, {"var": "x2", "coef": 3}],
                    "sense": "<=",
                    "rhs": 4,
                },
            }
        ],
        objective={"sense": "max", "terms": [{"var": "x1", "coef": 5}, {"var": "x2", "coef": 7}]},
        search={"max_time_ms": 1000},
    )

    assert request.mode == SolverMode.OPTIMIZE
    assert len(request.variables) == 2
    assert len(request.constraints) == 1
    assert request.objective is not None
    assert request.search is not None


def test_implication_constraint():
    """Test implication constraint with referenced linear constraint."""
    constraint = Constraint(
        id="impl",
        kind="implication",
        params={
            "if_var": "use_feature",
            "then_constraint_id": "cost_constraint",  # Reference to another constraint by ID
        },
    )

    assert constraint.kind == ConstraintKind.IMPLICATION
    # constraint.params is already an ImplicationParams model
    params: ImplicationParams = constraint.params  # type: ignore
    assert params.if_var == "use_feature"
    assert params.then_constraint_id == "cost_constraint"
