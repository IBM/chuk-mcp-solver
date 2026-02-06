# CHUK MCP Solver

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![MCP](https://img.shields.io/badge/MCP-compatible-brightgreen.svg)](https://modelcontextprotocol.io)
[![Tests](https://img.shields.io/badge/tests-260%20passed-success.svg)](#)
[![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen.svg)](#)

🔧 **General-purpose constraint and optimization solver as an MCP server**

A powerful Model Context Protocol (MCP) server that provides constraint satisfaction and optimization capabilities to LLMs and AI agents. Built on Google OR-Tools CP-SAT solver, it enables sophisticated decision-making for scheduling, resource allocation, puzzles, and more.

## Features

✨ **General Constraint Solver**
- Integer and boolean variables
- Linear constraints
- Global constraints (all_different, element, table)
- Implication constraints (conditional logic)
- Scheduling constraints (cumulative, no_overlap)
- Routing constraints (circuit)
- Inventory constraints (reservoir)
- Satisfaction and optimization modes

🎯 **Wide Range of Use Cases**
- Project scheduling and resource allocation
- Logic puzzles (Sudoku, etc.)
- Knapsack and packing problems
- Tool/model selection under constraints
- Configuration optimization
- Budget allocation

🚀 **Quality Assured**
- Async/await native
- Type-safe with Pydantic models
- Comprehensive test coverage (95%)
- Clean architecture with provider pattern
- Configurable via environment or YAML

📊 **Rich Solutions**
- Optimal and feasible solutions
- Multi-objective optimization (priority-based)
- Warm-start from previous solutions
- Parallel search workers
- Binding constraint analysis
- Human-readable explanations
- Metadata preservation

🤖 **LLM-Optimized** (Phase 2: Developer Experience)
- Pre-solve validation with actionable error messages
- Smart typo detection ("Did you mean...?" suggestions)
- Three-level validation severity (ERROR, WARNING, INFO)
- Structured observability and diagnostics
- Detailed infeasibility analysis

⚡ **Performance & Power** (Phase 3)
- Solution caching with problem hashing (LRU + TTL)
- Partial solutions (best-so-far on timeout)
- Search strategy hints (first-fail, random, etc.)
- Deterministic solving with random seeds
- Cache hit rate tracking

✅ **Production Quality**
- 246 comprehensive tests (all passing)
- 94% test coverage
- Type-safe with mypy
- Extensive error handling

🎯 **High-Level Problem APIs** (Phase 4: LLM-Native Schemas) 🆕
- **Scheduling**: Tasks with dependencies, resources, deadlines → optimal project schedules
- **Routing**: TSP/VRP with locations and vehicles → optimal delivery routes
  - ✨ **Multi-vehicle VRP with capacity constraints** (Phase 1 - NEW!)
  - Single-vehicle TSP, minimize distance/time/cost/vehicles objectives
  - Load timeline tracking, service times, vehicle-specific costs
- **Budget Allocation**: Items with costs, values, dependencies → optimal portfolio selection
- **Assignment**: Tasks with skills to agents with capacity → optimal task-agent matching
- Automatically builds CP-SAT models from high-level specs
- Domain-specific validation and error messages
- Rich responses with critical paths, utilization, route sequences, resource usage, assignments

## Example Use Cases

### High-Level Problem APIs (🆕 Phase 4)

**📅 Project Manager**: "Schedule 15 tasks with dependencies and resource constraints to finish ASAP"
- High-level API: `solve_scheduling_problem(tasks, resources, objective="minimize_makespan")`
- No need to understand CP-SAT variables or cumulative constraints
- Returns: optimal schedule with start/end times, critical path, resource utilization
- See: [`scheduling_demo.py`](examples/scheduling_demo.py)

**🚚 Delivery Driver**: "Find the shortest route visiting 10 customers with 2 trucks, respecting vehicle capacity"
- High-level API: `solve_routing_problem(locations, vehicles, objective="minimize_distance")`
- ✨ Now supports multi-vehicle VRP with capacity constraints!
- No need to understand flow conservation, MTZ constraints, or subtour elimination
- Returns: optimal routes per vehicle, total distance, load timelines
- See: [`routing_demo.py`](examples/routing_demo.py) and [`vrp_multi_vehicle_demo.py`](examples/vrp_multi_vehicle_demo.py)

**💰 Product Manager**: "Select projects to maximize ROI under $100k budget with dependencies and conflicts"
- High-level API: `solve_budget_allocation(items, budgets, objective="maximize_value")`
- No need to understand knapsack patterns or implication constraints
- Returns: selected items, total cost/value, resource usage, slack analysis
- See: [`allocation_demo.py`](examples/allocation_demo.py)

**👥 Team Lead**: "Assign development tasks to engineers matching required skills and balancing workload"
- High-level API: `solve_assignment_problem(agents, tasks, objective="balance_load")`
- No need to understand binary assignment variables or capacity constraints
- Returns: optimal assignments, agent workload, over/underutilized agents
- See: [`assignment_demo.py`](examples/assignment_demo.py)

### Low-Level Constraint Programming

**🏗️ DevOps Team**: "Schedule 20 deployment tasks across 5 servers with CPU/memory limits while minimizing total deployment time"
- Uses cumulative constraints to manage resource capacity
- Optimizes makespan while respecting dependencies
- See: [`resource_scheduler.py`](examples/resource_scheduler.py)

**🚚 Logistics Company**: "Plan delivery routes for 10 trucks visiting 50 customers to minimize total distance"
- Uses circuit constraints for vehicle routing (TSP/VRP)
- Handles time windows and capacity constraints
- See: [`delivery_router.py`](examples/delivery_router.py)

**📦 Warehouse Manager**: "Schedule production runs and customer orders while maintaining safety stock of 500 units"
- Uses reservoir constraints to track inventory levels
- Prevents stockouts and overstock situations
- See: [`inventory_manager.py`](examples/inventory_manager.py)

**☁️ Cloud Architect**: "Select AWS instances to meet requirements while minimizing cost, then latency"
- Uses multi-objective optimization with priorities
- Balances competing objectives (cost vs performance)
- See: [`multi_objective_planner.py`](examples/multi_objective_planner.py)

**🤖 AI Platform**: "Route 100 user requests to GPT-4, GPT-3.5, or Claude to minimize cost under $50 budget"
- Uses implication constraints for conditional logic
- Selects optimal model for each task based on capabilities
- See: [`tool_selector.py`](examples/tool_selector.py)

**🎯 Project Manager**: "Schedule 10 tasks with dependencies to minimize project completion time"
- Uses linear constraints for precedence relationships
- Optimizes critical path and resource allocation
- See: [`project_scheduler.py`](examples/project_scheduler.py)

**🧩 Puzzle Solver**: "Solve a Sudoku puzzle or find valid N-Queens placement"
- Uses all_different constraints for logic puzzles
- Demonstrates pure constraint satisfaction
- See: [`sudoku_solver.py`](examples/sudoku_solver.py)

**💼 Budget Planner**: "Allocate $10,000 across 20 initiatives to maximize ROI under capacity constraints"
- Uses knapsack optimization for resource allocation
- Handles multiple constraints (budget, headcount, time)
- See: [`knapsack_optimizer.py`](examples/knapsack_optimizer.py)

### LLM/AI Agent Examples

**"Claude, I need to schedule a team meeting with 5 people. Alice is only free Mon/Wed, Bob can't do mornings, and Carol must attend before David. Find a time that works."**
- LLM extracts: 5 people, availability constraints, precedence constraint
- Solver finds: Valid meeting time satisfying all constraints
- Response: "Schedule meeting Wednesday 2-3pm: Alice, Bob, Carol attend first half; David joins after Carol confirms"

**"Help me plan a road trip visiting San Francisco, LA, Vegas, and Phoenix in the shortest route starting from Seattle."**
- LLM converts to: TSP problem with 5 cities
- Solver optimizes: Circuit constraint for minimum distance route
- Response: "Optimal route (1,247 miles): Seattle → SF (808mi) → LA (382mi) → Vegas (270mi) → Phoenix (297mi) → Seattle (1,440mi)"

**"I have $500/month for AI API costs. I need to process 10,000 text requests and 2,000 image requests. What's the cheapest mix of GPT-4, GPT-3.5, and Claude?"**
- LLM builds: Cost optimization problem with budget constraint
- Solver finds: Optimal model selection minimizing cost
- Response: "Use GPT-3.5 for 8,000 text ($40), Claude for 2,000 text ($30), GPT-4 for 2,000 images ($400). Total: $470/month"

**"I'm deploying a microservice that needs 16 CPU cores and 32GB RAM. Minimize cost but keep latency under 50ms. What AWS instances should I use?"**
- LLM creates: Multi-objective problem (cost priority 1, latency priority 2)
- Solver optimizes: Instance selection meeting requirements
- Response: "Deploy 4x c5.large instances (16 cores, 32GB total) at $340/month with 30ms latency"

**"We have 3 devs, 2 designers, 1 PM. Schedule 15 tasks over 2 weeks where: Task A needs 2 devs for 3 days, Task B needs 1 designer + 1 dev for 2 days, all tasks have dependencies."**
- LLM extracts: Resource requirements, durations, dependencies
- Solver schedules: Cumulative resource constraints + precedence
- Response: "Project completes in 12 days. Task A: Days 1-3 (Alice, Bob). Task B: Days 4-5 (Carol, David)..."

**"I need to maintain 500 units of inventory. I have supplier deliveries on days 1, 7, 14 and customer orders on days 3, 5, 10, 15. When should I schedule each delivery to never run out?"**
- LLM models: Reservoir constraint problem with stock levels
- Solver finds: Valid delivery schedule maintaining safety stock
- Response: "Schedule delivery 1 on day 0 (300 units), delivery 2 on day 6 (250 units), delivery 3 on day 12 (200 units). Stock never drops below 500."

**"Find me a valid Sudoku solution for this puzzle..."**
- LLM recognizes: Constraint satisfaction problem
- Solver finds: Valid solution using all_different constraints
- Response: Shows completed Sudoku grid

**"I have 10 research papers to review. Each needs 2-4 hours. Some must be done before others. I have 20 hours this week. Create an optimal schedule."**
- LLM extracts: Tasks, durations, precedence, time budget
- Solver optimizes: Maximize papers reviewed in 20 hours
- Response: "Can complete 7 papers in 20 hours: Paper A (2h, Mon 9-11am), Paper D (3h, Mon 11am-2pm)..."

## Installation

### ⚡ Quick Start with uvx (Recommended)

No installation required! Use `uvx` to run directly:

```bash
# Run directly without installation
uvx chuk-mcp-solver
```

Or install with `uvx`:

```bash
# Install globally
uvx install chuk-mcp-solver
```

### 🌐 Public MCP Endpoint

Use our hosted solver directly - no installation needed:

- **MCP Endpoint**: `https://solver.chukai.io/mcp`

Perfect for testing, demos, or production use without infrastructure setup.

### Install from PyPI

```bash
# With pip
pip install chuk-mcp-solver

# With uv (faster)
uv pip install chuk-mcp-solver
```

### Local Development

```bash
# Navigate to project and install
cd chuk-mcp-solver
uv pip install -e ".[dev]"
```

## Quick Start

### As an MCP Server

#### Option 1: Public Hosted Endpoint (Easiest)

Use our hosted solver at `solver.chukai.io` - no installation required!

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "solver": {
      "url": "https://solver.chukai.io/mcp"
    }
  }
}
```

#### Option 2: Local with uvx (Recommended)

Run locally using `uvx` for full control and privacy:

```json
{
  "mcpServers": {
    "solver": {
      "command": "uvx",
      "args": ["chuk-mcp-solver"]
    }
  }
}
```

#### Option 3: Development Mode

For local development from source:

```json
{
  "mcpServers": {
    "solver": {
      "command": "uv",
      "args": ["run", "chuk-mcp-solver"],
      "cwd": "/path/to/chuk-mcp-solver"
    }
  }
}
```

### With Docker

Build and run using Docker:

```bash
# Build the image
docker build -t chuk-mcp-solver .

# Run the container
docker run -p 8000:8000 chuk-mcp-solver

# Or use docker-compose
docker-compose up -d
```

The Docker container runs the MCP server in HTTP mode by default on port 8000. For stdio mode (local usage), run without arguments: `python -m chuk_mcp_solver.server`

### Programmatic Usage

```python
from chuk_mcp_solver.models import SolveConstraintModelRequest
from chuk_mcp_solver.solver import get_solver

# Define a simple optimization problem
request = SolveConstraintModelRequest(
    mode="optimize",
    variables=[
        {"id": "x", "domain": {"type": "integer", "lower": 0, "upper": 10}},
        {"id": "y", "domain": {"type": "integer", "lower": 0, "upper": 10}},
    ],
    constraints=[
        {
            "id": "capacity",
            "kind": "linear",
            "params": {
                "terms": [{"var": "x", "coef": 2}, {"var": "y", "coef": 3}],
                "sense": "<=",
                "rhs": 15,
            },
        }
    ],
    objective={
        "sense": "max",
        "terms": [{"var": "x", "coef": 5}, {"var": "y", "coef": 4}],
    },
)

# Solve
solver = get_solver("ortools")
response = await solver.solve_constraint_model(request)

print(f"Status: {response.status}")
print(f"Objective: {response.objective_value}")
for var in response.solutions[0].variables:
    print(f"  {var.id} = {var.value}")
```

## Examples

The `examples/` directory contains 16 complete examples demonstrating different constraint types and use cases:

### High-Level Problem APIs

**Scheduling Demo** (`scheduling_demo.py`) 🆕
- **API**: `solve_scheduling_problem` - High-level scheduling interface
- **Use Case**: Project scheduling, resource allocation, DevOps pipelines
- **Features**: Tasks with dependencies, resource constraints, deadlines, release times

```bash
python examples/scheduling_demo.py
```

Shows 6 scheduling scenarios:
1. Simple sequential project (build → test → deploy)
2. Parallel task execution
3. Resource-constrained scheduling with capacity limits
4. Deadlines and earliest start times
5. Infeasible problem detection
6. Complex DevOps pipeline with mixed constraints

**Routing Demo** (`routing_demo.py`) 🆕
- **API**: `solve_routing_problem` - High-level TSP/VRP interface
- **Use Case**: Delivery routing, traveling salesman, logistics optimization
- **Features**: Coordinates or distance matrix, service times, vehicle costs

```bash
python examples/routing_demo.py
```

Shows 6 routing scenarios:
1. Simple TSP with coordinates
2. TSP with asymmetric distance matrix
3. TSP with service times at locations
4. TSP with cost optimization (fixed + variable)
5. Real-world 7-location delivery route
6. Small 3-city TSP with detailed breakdown

**Budget Allocation Demo** (`allocation_demo.py`) 🆕
- **API**: `solve_budget_allocation` - High-level knapsack/portfolio interface
- **Use Case**: Project selection, feature prioritization, resource allocation
- **Features**: Dependencies, conflicts, multi-resource constraints, min/max thresholds

```bash
python examples/allocation_demo.py
```

Shows 7 allocation scenarios:
1. Simple knapsack problem (maximize value under budget)
2. Portfolio selection with dependencies (backend required for frontend)
3. Feature prioritization with conflicts (mobile vs web checkout)
4. Multi-resource allocation (budget + headcount + time)
5. Maximize item count (get as many as possible)
6. Minimize cost while meeting value threshold
7. Item count constraints (min/max selection limits)

**Assignment Demo** (`assignment_demo.py`) 🆕
- **API**: `solve_assignment_problem` - High-level task-agent assignment interface
- **Use Case**: Work assignment, task delegation, resource matching
- **Features**: Skill matching, capacity constraints, load balancing, cost optimization

```bash
python examples/assignment_demo.py
```

Shows 7 assignment scenarios:
1. Simple assignment (minimize cost with different hourly rates)
2. Skill matching (assign tasks requiring specific skills to qualified agents)
3. Load balancing (distribute tasks evenly across agents)
4. Capacity constraints (agents with limited task capacity)
5. Maximize assignments (assign as many tasks as possible)
6. Infeasible assignment (insufficient capacity)
7. Custom cost matrix (task-agent preference matching)

### Performance & Features

**Performance Metrics Demo** (`performance_metrics_demo.py`) 🆕
- **Features**: Enhanced status codes, optimality gap, solve timing
- **Use Case**: Understanding solver performance and timeout behavior

```bash
python examples/performance_metrics_demo.py
```

Demonstrates the new v0.2.0+ performance metrics: `optimality_gap`, `solve_time_ms`, `timeout_best`, and `timeout_no_solution` status codes.

### Logic & Constraint Satisfaction

**Sudoku Solver** (`sudoku_solver.py`)
- **Constraints**: all_different
- **Use Case**: Logic puzzles, constraint satisfaction

```bash
python examples/sudoku_solver.py
```

Solves a 4x4 Sudoku puzzle using all_different constraints for rows, columns, and boxes.

### Optimization Problems

**Knapsack Optimizer** (`knapsack_optimizer.py`)
- **Constraints**: Linear (capacity), binary variables
- **Use Case**: Resource allocation, packing problems

```bash
python examples/knapsack_optimizer.py
```

Classic 0/1 knapsack problem: maximize value subject to weight capacity.

**Project Scheduler** (`project_scheduler.py`)
- **Constraints**: Linear (precedence), optimization
- **Use Case**: Task scheduling with dependencies

```bash
python examples/project_scheduler.py
```

Minimizes project makespan with task precedence constraints.

### Advanced Scheduling Constraints

**Resource Scheduler** (`resource_scheduler.py`) 🆕
- **Constraints**: Cumulative (resource capacity)
- **Use Case**: CPU/memory allocation, worker scheduling

```bash
python examples/resource_scheduler.py
```

Schedules tasks with resource demand under capacity limits. Shows resource utilization timeline.

**Delivery Router** (`delivery_router.py`) 🆕
- **Constraints**: Circuit (Hamiltonian path)
- **Use Case**: TSP, vehicle routing, delivery optimization

```bash
python examples/delivery_router.py
```

Finds optimal delivery route visiting all customers with minimum distance.

**Inventory Manager** (`inventory_manager.py`) 🆕
- **Constraints**: Reservoir (stock levels)
- **Use Case**: Production/consumption scheduling, inventory management

```bash
python examples/inventory_manager.py
```

Manages inventory levels with production and consumption events, maintaining safety stock.

### Multi-Objective & AI Orchestration

**Multi-Objective Planner** (`multi_objective_planner.py`) 🆕
- **Constraints**: Multi-objective optimization
- **Use Case**: Cloud deployment, trade-off analysis

```bash
python examples/multi_objective_planner.py
```

Optimizes cloud deployment with multiple objectives: minimize cost (priority 1), minimize latency (priority 2).

**Tool/Model Selection** (`tool_selector.py`)
- **Constraints**: Implication (conditional logic)
- **Use Case**: MCP tool orchestration, model selection

```bash
python examples/tool_selector.py
```

Selects optimal AI models/tools for tasks under budget constraints using implication constraints.

### Complex Real-World Examples 🔥

**GPU Job Scheduler** (`gpu_job_scheduler.py`) 🆕
- **Constraints**: Resource assignment, memory limits, job dependencies, deadlines, budget
- **Use Case**: ML/AI workload scheduling across heterogeneous GPUs

```bash
python examples/gpu_job_scheduler.py
```

Schedules ML jobs (embedding generation, fine-tuning, inference) across different GPU types (A100, V100, T4) optimizing cost vs time with resource constraints.

**Embedding Pipeline Scheduler** (`embedding_pipeline_scheduler.py`) 🆕
- **Constraints**: Multi-stage pipeline, rate limits, throughput constraints
- **Use Case**: Document processing through embedding extraction pipeline

```bash
python examples/embedding_pipeline_scheduler.py
```

Orchestrates document batches through preprocessing → embedding → vector DB ingestion, selecting optimal providers (OpenAI, Cohere, Voyage) under rate limits.

**ML Pipeline Orchestrator** (`ml_pipeline_orchestrator.py`) 🆕
- **Constraints**: End-to-end pipeline, conditional deployment, quality gates
- **Use Case**: Multi-variant model training with A/B testing

```bash
python examples/ml_pipeline_orchestrator.py
```

Trains multiple model variants through full ML lifecycle (ingest → preprocess → train → eval → deploy), deploys only models meeting quality thresholds.

### Example Output

**Resource Scheduler Output:**
```
Status: OPTIMAL
Minimum Project Duration: 9 time units

Resource Utilization Timeline:
Time | Utilization | Running Tasks
-----|-------------|------------------
   0 | 4/4 ████    | task_B, task_C
   1 | 4/4 ████    | task_B, task_C
   2 | 3/4 ███     | task_B
   4 | 4/4 ████    | task_A, task_D
...
```

**Delivery Router Output:**
```
Status: OPTIMAL
Minimum Total Distance: 46 km

Route: Warehouse → Customer_D → Customer_C → Customer_B → Customer_A → Warehouse
```

## Tool Reference

### `solve_constraint_model`

Solve a general constraint or optimization model.

**Parameters:**

- `mode` (str): `"satisfy"` for any feasible solution, `"optimize"` for best solution
- `variables` (list): Decision variables with domains
- `constraints` (list): Constraints to satisfy
- `objective` (dict, optional): Objective function (required if mode is `"optimize"`)
- `search` (dict, optional): Search configuration (time limits, etc.)

**Variable Schema:**

```python
{
    "id": "unique_id",
    "domain": {
        "type": "bool" | "integer",
        "lower": 0,  # for integer
        "upper": 10  # for integer
    },
    "metadata": {...}  # optional
}
```

**Constraint Types:**

1. **Linear**: `sum(coef * var) sense rhs`
   ```python
   {
       "id": "c1",
       "kind": "linear",
       "params": {
           "terms": [{"var": "x", "coef": 2}, {"var": "y", "coef": 3}],
           "sense": "<=",  # "<=", ">=", or "=="
           "rhs": 10
       }
   }
   ```

2. **All Different**: Variables must have distinct values
   ```python
   {
       "id": "c2",
       "kind": "all_different",
       "params": {"vars": ["x", "y", "z"]}
   }
   ```

3. **Element**: Array indexing `target = array[index]`
   ```python
   {
       "id": "c3",
       "kind": "element",
       "params": {
           "index_var": "idx",
           "array": [10, 20, 30],
           "target_var": "result"
       }
   }
   ```

4. **Table**: Allowed tuples
   ```python
   {
       "id": "c4",
       "kind": "table",
       "params": {
           "vars": ["x", "y"],
           "allowed_tuples": [[0, 1], [1, 0]]
       }
   }
   ```

5. **Implication**: If-then constraint
   ```python
   {
       "id": "c5",
       "kind": "implication",
       "params": {
           "if_var": "use_feature",
           "then": {
               "id": "cost",
               "kind": "linear",
               "params": {...}
           }
       }
   }
   ```

6. **Cumulative**: Resource scheduling with capacity
   ```python
   {
       "id": "c6",
       "kind": "cumulative",
       "params": {
           "start_vars": ["s1", "s2", "s3"],
           "duration_vars": [3, 4, 2],  # or variable IDs
           "demand_vars": [2, 1, 3],    # or variable IDs
           "capacity": 5
       }
   }
   ```

7. **Circuit**: Routing/Hamiltonian circuit
   ```python
   {
       "id": "c7",
       "kind": "circuit",
       "params": {
           "arcs": [
               (0, 1, "arc_0_1"),  # (from_node, to_node, bool_var)
               (1, 2, "arc_1_2"),
               # ...
           ]
       }
   }
   ```

8. **Reservoir**: Inventory/stock management
   ```python
   {
       "id": "c8",
       "kind": "reservoir",
       "params": {
           "time_vars": ["t1", "t2", "t3"],
           "level_changes": [5, -3, -2],  # production/consumption
           "min_level": 0,
           "max_level": 10
       }
   }
   ```

9. **No-Overlap**: Disjunctive scheduling
   ```python
   {
       "id": "c9",
       "kind": "no_overlap",
       "params": {
           "start_vars": ["s1", "s2", "s3"],
           "duration_vars": [3, 4, 2]  # or variable IDs
       }
   }
   ```

**Multi-Objective Optimization:**

```python
{
    "mode": "optimize",
    "objective": [
        {
            "sense": "max",
            "terms": [{"var": "x", "coef": 1}],
            "priority": 2,  # Higher priority
            "weight": 1.0
        },
        {
            "sense": "max",
            "terms": [{"var": "y", "coef": 1}],
            "priority": 1,  # Lower priority
            "weight": 1.0
        }
    ]
}
```

**Search Configuration:**

```python
{
    "search": {
        "max_time_ms": 5000,
        "max_solutions": 1,
        "num_search_workers": 4,
        "log_search_progress": false,
        "random_seed": 42,  # Deterministic solving
        "strategy": "first_fail",  # Search strategy hint
        "return_partial_solution": true,  # Return best-so-far on timeout
        "enable_solution_caching": true,  # Cache solutions
        "warm_start_solution": {"x": 5, "y": 3}
    }
}
```

**Search Strategies:**

- `"auto"` (default): Let solver choose best strategy
- `"first_fail"`: Choose variables with smallest domain first
- `"largest_first"`: Choose variables with largest domain first
- `"random"`: Random variable selection
- `"cheapest_first"`: Choose least expensive variables first

**Solution Caching:**

The solver automatically caches solutions using problem hashing to avoid re-solving identical problems. Enable/disable with `enable_solution_caching` (default: true).

```python
# First solve - hits the solver
response1 = await solver.solve_constraint_model(request)

# Identical problem - returns cached solution
response2 = await solver.solve_constraint_model(request)  # Cache hit!
```

Cache uses LRU eviction (max 1000 entries) with 1-hour TTL. Access global cache stats:

```python
from chuk_mcp_solver.cache import get_global_cache

cache = get_global_cache()
stats = cache.stats()
# {'size': 42, 'max_size': 1000, 'hits': 15, 'misses': 27, 'hit_rate_pct': 35.71, 'ttl_seconds': 3600}
```

**Partial Solutions on Timeout:**

When solving complex problems with time limits, enable `return_partial_solution` to get the best solution found so far:

```python
{
    "mode": "optimize",
    "search": {
        "max_time_ms": 1000,  # 1 second limit
        "return_partial_solution": true
    },
    # ... variables, constraints, objective ...
}
```

If timeout occurs, you'll get a `FEASIBLE` solution with a note explaining it's the best found so far.

**Validation and Error Messages:**

The solver validates models before solving and provides actionable error messages to help LLMs self-correct:

```python
# Invalid model with typo
response = await solver.solve_constraint_model({
    "mode": "optimize",
    "variables": [{"id": "x", "domain": {"type": "integer", "lower": 0, "upper": 10}}],
    "constraints": [{
        "id": "c1",
        "kind": "linear",
        "params": {
            "terms": [{"var": "y", "coef": 1}],  # Typo: 'y' instead of 'x'
            "sense": "<=",
            "rhs": 5
        }
    }],
    "objective": {"sense": "max", "terms": [{"var": "x", "coef": 1}]}
})

# Response includes helpful error:
# status: ERROR
# explanation: "Model validation failed with 1 error(s):
#   1. Variable 'y' referenced in constraint 'c1' is not defined
#      Location: constraint[c1].params.terms[0].var
#      Suggestion: Did you mean 'x'? (defined variables: x)"
```

Validation checks:
- Undefined variables (with "did you mean?" suggestions)
- Duplicate IDs
- Invalid domain bounds
- Empty constraint sets
- Objective without variables
- Type mismatches

**Response Schema:**

```python
{
    "status": "optimal" | "feasible" | "satisfied" | "infeasible" | "unbounded" | "timeout_best" | "timeout_no_solution" | "error",
    "objective_value": 42.0,  # if applicable
    "optimality_gap": 0.0,  # % gap from best bound (0 = proven optimal)
    "solve_time_ms": 1234,  # actual wall-clock solve time
    "solutions": [
        {
            "variables": [
                {"id": "x", "value": 5, "metadata": {...}}
            ],
            "derived": {...}  # optional computed metrics
        }
    ],
    "explanation": {
        "summary": "Found optimal solution...",
        "binding_constraints": [...]  # tight constraints
    }
}
```

**Status Codes:**
- `optimal`: Proven optimal solution found
- `feasible`: Valid solution found, but may not be optimal
- `satisfied`: All constraints satisfied (for satisfy mode)
- `infeasible`: No solution exists
- `unbounded`: Objective can be improved infinitely
- `timeout_best`: Timeout reached, returning best solution found so far
- `timeout_no_solution`: Timeout reached before finding any solution
- `error`: Solver error occurred

**Performance Metrics:**
- `optimality_gap`: Percentage gap from best bound (0.0 for optimal solutions)
- `solve_time_ms`: Actual wall-clock time spent solving

### `solve_scheduling_problem`

🆕 **High-Level Scheduling API** - A simpler interface for task scheduling problems that automatically builds the CP-SAT model for you.

Use this instead of `solve_constraint_model` when you have tasks with durations, dependencies, and resource constraints. Perfect for project planning, job scheduling, and resource allocation.

**Parameters:**

- `tasks` (list): Tasks to schedule, each with:
  - `id` (str): Unique task identifier
  - `duration` (int): Task duration in time units
  - `resources_required` (dict, optional): `{resource_id: amount}` mapping
  - `dependencies` (list, optional): Task IDs that must complete first
  - `earliest_start` (int, optional): Release time (can't start before this)
  - `deadline` (int, optional): Due date (must finish by this)
  - `priority` (int, optional): Task priority (default 1)
  - `metadata` (dict, optional): Custom metadata preserved in response

- `resources` (list, optional): Resources with capacity limits:
  - `id` (str): Resource identifier
  - `capacity` (int): Maximum units available at any time
  - `cost_per_unit` (float, optional): Cost per unit-time
  - `metadata` (dict, optional): Custom metadata

- `objective` (str): Optimization goal
  - `"minimize_makespan"` (default): Minimize total project duration
  - `"minimize_cost"`: Minimize total resource cost
  - `"minimize_lateness"`: Minimize lateness/tardiness

- `max_time_ms` (int, optional): Maximum solver time in milliseconds (default: 60000)

**Response:**

```python
{
    "status": "optimal" | "feasible" | "infeasible" | "timeout_best" | "timeout_no_solution" | "error",
    "makespan": 42,  # Total project completion time
    "total_cost": 123.45,  # Total cost (if minimize_cost)
    "schedule": [
        {
            "task_id": "build",
            "start_time": 0,
            "end_time": 10,
            "resources_used": {"cpu": 2},
            "on_critical_path": true,
            "slack": 0,
            "metadata": {...}  # preserved from request
        },
        # ... more tasks
    ],
    "resource_utilization": [
        {
            "resource_id": "cpu",
            "peak_usage": 4,
            "average_usage": 2.5,
            "utilization_pct": 62.5
        }
    ],
    "critical_path": ["build", "test", "deploy"],
    "solve_time_ms": 234,
    "optimality_gap": 0.0,
    "explanation": {
        "summary": "Found optimal schedule completing in 42 time units with 10 tasks using 3 resources",
        "recommendations": []  # suggestions if infeasible
    }
}
```

**Example: Simple Project Schedule**

```python
response = await solve_scheduling_problem(
    tasks=[
        {"id": "build", "duration": 10},
        {"id": "test", "duration": 5, "dependencies": ["build"]},
        {"id": "deploy", "duration": 3, "dependencies": ["test"]},
    ],
    objective="minimize_makespan"
)
# Returns: makespan=18, schedule with optimal timings
```

**Example: Resource-Constrained Scheduling**

```python
response = await solve_scheduling_problem(
    tasks=[
        {"id": "task_a", "duration": 5, "resources_required": {"cpu": 2}},
        {"id": "task_b", "duration": 3, "resources_required": {"cpu": 3}},
        {"id": "task_c", "duration": 4, "resources_required": {"cpu": 1}},
    ],
    resources=[{"id": "cpu", "capacity": 4}],
    objective="minimize_makespan"
)
# Automatically handles resource capacity constraints using cumulative constraints
```

**Example: Deadlines and Release Times**

```python
response = await solve_scheduling_problem(
    tasks=[
        {"id": "prep", "duration": 2, "earliest_start": 0},
        {"id": "main", "duration": 6, "dependencies": ["prep"], "deadline": 10},
        {"id": "review", "duration": 3, "dependencies": ["main"], "earliest_start": 8},
    ],
    objective="minimize_makespan"
)
# Handles time windows and deadlines automatically
```

**When to Use This vs. solve_constraint_model:**

✅ Use `solve_scheduling_problem` when:
- You have tasks with durations and dependencies
- You need to manage resource capacities
- You want to minimize makespan/cost/lateness
- You want a simpler, domain-specific API

🔧 Use `solve_constraint_model` when:
- You need custom constraints beyond scheduling
- You're solving non-scheduling problems (puzzles, knapsack, etc.)
- You need fine-grained control over the model
- You're combining scheduling with other constraint types

**Behind the Scenes:**

This tool automatically converts your high-level scheduling problem into a CP-SAT model with:
- Start/end time variables for each task
- Duration constraints: `end = start + duration`
- Precedence constraints for dependencies
- Cumulative constraints for resource capacity
- Deadline constraints
- Makespan variable and objective

See [`scheduling_demo.py`](examples/scheduling_demo.py) for comprehensive examples.

### `solve_routing_problem`

🆕 **High-Level Routing API** - A simpler interface for TSP and VRP problems that automatically builds the CP-SAT model for you.

Use this instead of `solve_constraint_model` when you need to find optimal routes for vehicles visiting locations. Perfect for delivery routing, traveling salesman problems, and logistics optimization.

**Parameters:**

- `locations` (list): Locations to visit, each with:
  - `id` (str): Unique location identifier
  - `coordinates` (tuple, optional): (x, y) or (lat, lon) coordinates
  - `service_time` (int, optional): Time spent at location (default 0)
  - `time_window` (tuple, optional): (earliest, latest) arrival time
  - `demand` (int, optional): Demand at location for capacity constraints
  - `priority` (int, optional): Location priority (default 1)

- `vehicles` (list, optional): Vehicles (if empty, assumes single vehicle TSP):
  - `id` (str): Vehicle identifier
  - `capacity` (int, optional): Maximum load (default 999999)
  - `start_location` (str): Starting location ID
  - `end_location` (str, optional): Ending location if different from start
  - `max_distance` (int, optional): Maximum distance vehicle can travel
  - `max_time` (int, optional): Maximum time vehicle can be in use
  - `cost_per_distance` (float, optional): Cost per unit distance (default 1.0)
  - `fixed_cost` (float, optional): Fixed cost if vehicle is used (default 0.0)

- `distance_matrix` (list[list[int]], optional): Distance matrix where [i][j] = distance from location i to j. If not provided, uses Euclidean distance from coordinates.

- `objective` (str): Optimization goal
  - `"minimize_distance"` (default): Minimize total distance
  - `"minimize_time"`: Minimize total time
  - `"minimize_vehicles"`: Use fewest vehicles
  - `"minimize_cost"`: Minimize total cost

- `max_time_ms` (int, optional): Maximum solver time in milliseconds (default: 60000)

**Response:**

```python
{
    "status": "optimal" | "feasible" | "infeasible" | "timeout_best" | "timeout_no_solution" | "error",
    "routes": [
        {
            "vehicle_id": "truck_1",
            "sequence": ["depot", "customer_A", "customer_B", "depot"],
            "total_distance": 45,
            "total_time": 55,  # including service times
            "total_cost": 112.50,
            "load_timeline": []  # for capacity-constrained routing
        }
    ],
    "unvisited": [],  # locations not visited (if force_visit_all=False)
    "total_distance": 45,
    "total_time": 55,
    "total_cost": 112.50,
    "vehicles_used": 1,
    "solve_time_ms": 123,
    "optimality_gap": 0.0,
    "explanation": {
        "summary": "Found optimal route visiting 4 locations with total distance 45",
        "bottlenecks": [],
        "recommendations": []
    }
}
```

**Example: Simple TSP with Coordinates**

```python
response = await solve_routing_problem(
    locations=[
        {"id": "warehouse", "coordinates": (0, 0)},
        {"id": "customer_A", "coordinates": (10, 5)},
        {"id": "customer_B", "coordinates": (5, 10)},
        {"id": "customer_C", "coordinates": (15, 15)},
    ],
    objective="minimize_distance"
)
# Returns optimal tour visiting all locations
```

**Example: TSP with Distance Matrix**

```python
response = await solve_routing_problem(
    locations=[
        {"id": "A"},
        {"id": "B"},
        {"id": "C"},
    ],
    distance_matrix=[
        [0, 10, 20],
        [10, 0, 15],
        [20, 15, 0],
    ],
    objective="minimize_distance"
)
# Uses provided distances instead of coordinates
```

**Example: Routing with Service Times and Costs**

```python
response = await solve_routing_problem(
    locations=[
        {"id": "depot", "coordinates": (0, 0), "service_time": 0},
        {"id": "store_A", "coordinates": (10, 0), "service_time": 15},
        {"id": "store_B", "coordinates": (10, 10), "service_time": 20},
    ],
    vehicles=[
        {
            "id": "van_1",
            "start_location": "depot",
            "cost_per_distance": 2.5,
            "fixed_cost": 50.0
        }
    ],
    objective="minimize_cost"
)
# Minimizes total cost (fixed + distance * cost_per_distance)
```

**When to Use This vs. solve_constraint_model:**

✅ Use `solve_routing_problem` when:
- You need to find optimal routes for visiting locations
- You have TSP (Traveling Salesman Problem) scenarios
- You want to optimize delivery routes
- You want a simpler, domain-specific API

🔧 Use `solve_constraint_model` when:
- You need custom constraints beyond routing
- You're solving non-routing problems
- You need fine-grained control over the circuit constraint
- You're combining routing with other constraint types

**Behind the Scenes:**

This tool automatically converts your high-level routing problem into a CP-SAT model with:
- Boolean arc variables for each possible location-to-location connection
- **Multi-vehicle support** with flow conservation and MTZ subtour elimination ✨ NEW
- **Capacity constraints** for vehicle load limits ✨ NEW
- Circuit constraint for single-vehicle TSP (Hamiltonian tour)
- Distance/time/cost/vehicles objective functions
- Support for service times at locations
- Vehicle cost modeling (fixed + per-distance)
- Load timeline tracking for capacity-constrained routing ✨ NEW

**Supported Features:**

✅ Single-vehicle TSP (Traveling Salesman Problem)
✅ Multi-vehicle VRP (Vehicle Routing Problem) with capacity constraints ✨ NEW (Phase 1)
✅ Multiple optimization objectives: minimize_distance, minimize_time, minimize_cost, minimize_vehicles
✅ Service times at locations
✅ Vehicle-specific costs (fixed + per-distance)
✅ Demand/capacity constraints

**Current Limitations:**

- No time window constraints yet
- No pickup and delivery yet
- No heterogeneous fleets (different vehicle types with different capabilities)

See [`routing_demo.py`](examples/routing_demo.py) for comprehensive examples.

---

### `solve_budget_allocation` 🆕

**High-level interface for budget allocation and knapsack problems.**

Solves portfolio selection, feature prioritization, and resource allocation problems. Automatically handles dependencies, conflicts, and multiple resource constraints.

**Parameters:**
- `items` (list[dict]): Items to choose from, each with:
  - `id` (str): Unique identifier
  - `cost` (float): Cost of selecting this item
  - `value` (float): Value/benefit (ROI, utility, priority)
  - `resources_required` (dict, optional): Multi-resource requirements like `{"headcount": 2, "time": 3}`
  - `dependencies` (list, optional): Item IDs that must also be selected
  - `conflicts` (list, optional): Item IDs that cannot be selected together
- `budgets` (list[dict]): Resource constraints, each with:
  - `resource` (str): Resource name (e.g., "money", "time", "headcount")
  - `limit` (float): Maximum available
- `objective` (str): Goal - `"maximize_value"` (default), `"maximize_count"`, or `"minimize_cost"`
- `min_value_threshold` (float, optional): Minimum total value required
- `max_cost_threshold` (float, optional): Maximum total cost allowed
- `min_items` (int, optional): Minimum number of items to select
- `max_items` (int, optional): Maximum number of items to select
- `max_time_ms` (int): Maximum solver time (default: 60000)

**Response:**
```json
{
  "status": "optimal",
  "selected_items": ["project_A", "project_C"],
  "total_cost": 9000.0,
  "total_value": 21000.0,
  "resource_usage": {"money": 9000.0},
  "resource_slack": {"money": 1000.0},
  "solve_time_ms": 5,
  "optimality_gap": null,
  "explanation": {
    "summary": "Optimal selection: 2 items with total value 21000.00 under budget of 9000.00",
    "binding_constraints": ["Budget 'money' has 1000.00 slack (10.0%)"],
    "marginal_items": [],
    "recommendations": []
  }
}
```

**Example 1: Simple Knapsack**
```python
response = await solve_budget_allocation(
    items=[
        {"id": "project_A", "cost": 5000, "value": 12000},
        {"id": "project_B", "cost": 3000, "value": 7000},
        {"id": "project_C", "cost": 4000, "value": 9000},
    ],
    budgets=[
        {"resource": "money", "limit": 10000}
    ],
    objective="maximize_value"
)
# Returns: Optimal selection maximizing value under $10k budget
```

**Example 2: With Dependencies**
```python
response = await solve_budget_allocation(
    items=[
        {"id": "backend", "cost": 8000, "value": 5000},
        {"id": "frontend", "cost": 6000, "value": 12000,
         "dependencies": ["backend"]},  # Frontend requires backend
        {"id": "mobile", "cost": 7000, "value": 10000,
         "dependencies": ["backend"]},
    ],
    budgets=[{"resource": "money", "limit": 15000}],
    objective="maximize_value"
)
# Automatically ensures dependencies are satisfied
```

**Example 3: With Conflicts**
```python
response = await solve_budget_allocation(
    items=[
        {"id": "mobile_checkout", "cost": 5000, "value": 15000,
         "conflicts": ["web_redesign"]},  # Can't do both
        {"id": "web_redesign", "cost": 6000, "value": 14000,
         "conflicts": ["mobile_checkout"]},
        {"id": "analytics", "cost": 3000, "value": 8000},
    ],
    budgets=[{"resource": "money", "limit": 12000}],
    objective="maximize_value"
)
# Ensures conflicting items are not both selected
```

**Example 4: Multi-Resource**
```python
response = await solve_budget_allocation(
    items=[
        {"id": "feature_A", "cost": 5000, "value": 10000,
         "resources_required": {"headcount": 2, "time": 3}},
        {"id": "feature_B", "cost": 3000, "value": 7000,
         "resources_required": {"headcount": 1, "time": 2}},
    ],
    budgets=[
        {"resource": "money", "limit": 10000},
        {"resource": "headcount", "limit": 3},
        {"resource": "time", "limit": 4}
    ],
    objective="maximize_value"
)
# Respects all resource constraints simultaneously
```

**When to Use:**

✅ Use `solve_budget_allocation` when:
- You need to select items under budget constraints
- You have knapsack or portfolio selection problems
- You need to handle dependencies or conflicts between items
- You have multiple resource constraints (budget, time, headcount)
- You want to maximize value, minimize cost, or maximize count

🔧 Use `solve_constraint_model` when:
- You need custom constraints beyond allocation
- You're solving non-allocation problems
- You need fine-grained control over the knapsack formulation
- You're combining allocation with other constraint types

**Behind the Scenes:**

This tool automatically converts your high-level allocation problem into a CP-SAT model with:
- Binary selection variables for each item
- Linear budget constraints for each resource
- Implication constraints for dependencies (if A then B)
- Linear constraints for conflicts (A + B ≤ 1)
- Value/cost/count objective function
- Optional min/max value, cost, and item count constraints

**Current Limitations:**

- No soft budget constraints (penalty-based) yet
- No category-based selection rules yet
- No multi-period allocation yet

See [`allocation_demo.py`](examples/allocation_demo.py) for comprehensive examples.

---

### `solve_assignment_problem` 🆕

**High-level task-to-agent assignment interface** - Automatically builds CP-SAT models for assigning tasks to agents with skill matching, capacity constraints, and load balancing.

```python
response = await solve_assignment_problem(
    agents=[...],
    tasks=[...],
    objective="minimize_cost" | "maximize_assignments" | "balance_load",
    cost_matrix=None,  # Optional: Custom cost matrix
    force_assign_all=True,  # Require all tasks assigned
    max_time_ms=60000,
)
```

**Example 1: Simple Assignment (Minimize Cost)**

```python
response = await solve_assignment_problem(
    agents=[
        {"id": "alice", "capacity": 2, "cost_multiplier": 1.0},  # $50/hour
        {"id": "bob", "capacity": 2, "cost_multiplier": 1.5},  # $75/hour
    ],
    tasks=[
        {"id": "task_1", "duration": 2},  # 2 hours
        {"id": "task_2", "duration": 3},  # 3 hours
        {"id": "task_3", "duration": 1},  # 1 hour
    ],
    objective="minimize_cost",
)
# Assigns tasks to cheapest agents: alice gets task_1 + task_2, bob gets task_3
# Total cost: $325 (alice: $100 + $150, bob: $75)
```

**Example 2: Skill Matching**

```python
response = await solve_assignment_problem(
    agents=[
        {"id": "alice", "capacity": 2, "skills": ["python", "docker", "aws"]},
        {"id": "bob", "capacity": 2, "skills": ["react", "typescript", "nodejs"]},
        {"id": "charlie", "capacity": 2, "skills": ["python", "react", "postgres"]},
    ],
    tasks=[
        {"id": "backend_api", "duration": 5, "required_skills": ["python", "docker"]},
        {"id": "frontend_ui", "duration": 4, "required_skills": ["react", "typescript"]},
        {"id": "database_migration", "duration": 2, "required_skills": ["python", "postgres"]},
        {"id": "deployment", "duration": 3, "required_skills": ["docker", "aws"]},
    ],
    objective="minimize_cost",
)
# Only assigns tasks to agents with matching skills
# backend_api → alice, frontend_ui → bob, database_migration → charlie, deployment → alice
```

**Example 3: Load Balancing**

```python
response = await solve_assignment_problem(
    agents=[
        {"id": "server_1", "capacity": 5},
        {"id": "server_2", "capacity": 5},
        {"id": "server_3", "capacity": 5},
    ],
    tasks=[{"id": f"job_{i}", "duration": 1} for i in range(9)],
    objective="balance_load",
)
# Distributes tasks evenly: each server gets exactly 3 tasks
```

**Example 4: Maximize Assignments (Optional Tasks)**

```python
response = await solve_assignment_problem(
    agents=[
        {"id": "team_member_1", "capacity": 2},
        {"id": "team_member_2", "capacity": 2},
    ],
    tasks=[
        {"id": "feature_a", "duration": 1},
        {"id": "feature_b", "duration": 1},
        {"id": "feature_c", "duration": 1},
        {"id": "feature_d", "duration": 1},
        {"id": "feature_e", "duration": 1},
    ],
    objective="maximize_assignments",
    force_assign_all=False,  # Some tasks can remain unassigned
)
# Assigns 4 out of 5 tasks (capacity limit)
# Returns unassigned_tasks: ["feature_c"]
```

**When to Use:**

✅ Use `solve_assignment_problem` when:
- You need to assign tasks to agents/workers/servers
- You have skill or qualification requirements
- You need to respect capacity or workload limits
- You want to minimize cost, maximize assignments, or balance load
- You have custom task-agent costs or preferences

🔧 Use `solve_constraint_model` when:
- You need custom constraints beyond assignment
- You're solving non-assignment problems
- You need fine-grained control over the assignment formulation
- You're combining assignment with other constraint types

**Behind the Scenes:**

This tool automatically converts your high-level assignment problem into a CP-SAT model with:
- Binary assignment variables for each (task, agent) pair
- Task assignment constraints (each task to exactly one agent, or at most one if optional)
- Agent capacity constraints (max number of tasks per agent)
- Skill matching constraints (forbid incompatible assignments)
- Cost minimization, assignment maximization, or load balancing objective
- Automatic cost matrix generation from agent cost_multiplier and task duration

**Response Fields:**

```python
response.status  # SolverStatus.OPTIMAL, FEASIBLE, INFEASIBLE, etc.
response.assignments  # List[Assignment(task_id, agent_id, cost)]
response.unassigned_tasks  # List[str] - Tasks not assigned (if force_assign_all=False)
response.agent_load  # Dict[str, int] - Number of tasks per agent
response.total_cost  # float - Total assignment cost
response.solve_time_ms  # int - Solve time in milliseconds
response.optimality_gap  # Optional[float] - Gap to optimal (if timeout)
response.explanation  # AssignmentExplanation with summary and recommendations
response.explanation.overloaded_agents  # List[str] - Agents with >150% of average load
response.explanation.underutilized_agents  # List[str] - Agents with <50% of average load
```

**Current Limitations:**

- No multi-skill level support (e.g., junior vs senior) yet
- No task priority or preemption yet
- No time windows or deadlines yet
- No agent preferences or task affinity yet

See [`assignment_demo.py`](examples/assignment_demo.py) for comprehensive examples.

---

## Configuration

### Environment Variables

```bash
# Provider selection
export CHUK_SOLVER_PROVIDER=ortools

# Tool-specific provider
export CHUK_SOLVER_TOOL_PROVIDER=ortools

# Config file location
export CHUK_SOLVER_CONFIG=/path/to/config.yaml
```

### YAML Configuration

Create `~/.config/chuk-mcp-solver/config.yaml`:

```yaml
default_provider: ortools

tool_providers:
  solve_constraint_model: ortools
```

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/chuk-ai/chuk-mcp-solver.git
cd chuk-mcp-solver

# Install with dev dependencies
uv pip install -e ".[dev]"
```

### Testing

```bash
# Run tests
make test

# Run with coverage (requires 90%+)
make test-cov

# Run specific tests
pytest tests/test_models.py -v

# Current stats: 196 tests, 93% coverage ✅
```

### Code Quality

```bash
# Lint
make lint

# Format
make format

# Type check
make typecheck

# All checks
make check
```

### Running Locally

```bash
# Run server
make run

# Or directly
python -m chuk_mcp_solver.server
```

## Architecture

```
chuk-mcp-solver/
├── src/chuk_mcp_solver/
│   ├── __init__.py          # Package metadata
│   ├── server.py            # MCP server + tools
│   ├── models.py            # Pydantic models + enums
│   ├── config.py            # Configuration management
│   ├── validation.py        # 🆕 Model validation (Phase 2)
│   ├── cache.py             # 🆕 Solution caching (Phase 3)
│   ├── observability.py     # 🆕 Logging & metrics (Phase 1)
│   ├── diagnostics.py       # 🆕 Health checks & analysis (Phase 1)
│   └── solver/              # Solver implementations
│       ├── __init__.py      # Solver factory (get_solver)
│       ├── provider.py      # Abstract solver interface
│       └── ortools/         # OR-Tools implementation
│           ├── solver.py    # Main ORToolsSolver class
│           ├── constraints.py  # Constraint builders
│           ├── objectives.py   # Objective + search config
│           ├── responses.py    # Response builders
│           └── scheduling.py   # 🆕 High-level scheduling converters (Phase 4)
├── tests/                   # Comprehensive test suite (196 tests)
│   ├── test_solver.py       # Factory tests
│   ├── test_models.py       # Model validation tests
│   ├── test_validation.py   # 🆕 Validation framework tests
│   ├── test_cache.py        # 🆕 Caching tests
│   ├── test_performance.py  # 🆕 Performance feature tests
│   ├── test_observability.py  # 🆕 Observability tests
│   ├── test_diagnostics.py    # 🆕 Diagnostics tests
│   ├── test_scheduling.py   # 🆕 High-level scheduling tests (Phase 4)
│   └── solver/ortools/      # OR-Tools tests (mirrors source)
│       ├── test_solver.py
│       ├── test_constraints.py
│       ├── test_responses.py
│       └── test_edge_cases.py
├── examples/                # Example scripts (13 examples)
└── pyproject.toml           # Package configuration
```

**Key Design Patterns:**

- **Modular Architecture**: Focused modules with single responsibilities
- **Solver Pattern**: Pluggable solver backends via abstract interface
- **Factory Function**: Simple `get_solver()` for solver instantiation
- **Pydantic Models**: Type-safe throughout
- **Async Native**: Non-blocking I/O
- **No Magic Strings**: Enums for all constants
- **Mirrored Test Structure**: Tests match source organization

## Use Cases

### Scheduling & Resource Allocation
- **Project Scheduling**: Task scheduling with precedence constraints → [`project_scheduler.py`](examples/project_scheduler.py)
- **Resource-Constrained Scheduling**: CPU/memory/worker allocation with capacity limits → [`resource_scheduler.py`](examples/resource_scheduler.py)
- **Inventory Management**: Production/consumption planning with stock levels → [`inventory_manager.py`](examples/inventory_manager.py)
- **Shift Rostering**: Employee scheduling with availability and skill constraints
- **Meeting Scheduling**: Calendar optimization with participant constraints

### Routing & Logistics
- **Vehicle Routing**: Delivery route optimization (TSP/VRP) → [`delivery_router.py`](examples/delivery_router.py)
- **Circuit Planning**: Hamiltonian path/circuit problems
- **Network Design**: Optimal path selection in graphs
- **Warehouse Optimization**: Pick path optimization

### Optimization Problems
- **Knapsack Problems**: Resource allocation under weight/capacity limits → [`knapsack_optimizer.py`](examples/knapsack_optimizer.py)
- **Budget Allocation**: Optimal spending across categories
- **Portfolio Selection**: Asset selection under risk/return constraints
- **Packing Problems**: Bin packing, cutting stock

### AI/LLM Orchestration
- **Multi-Model Selection**: Choose optimal AI models under budget → [`tool_selector.py`](examples/tool_selector.py)
- **Multi-Objective Planning**: Balance cost, latency, quality trade-offs → [`multi_objective_planner.py`](examples/multi_objective_planner.py)
- **Rate-Limit Aware Scheduling**: Task scheduling respecting API limits
- **Capability-Based Routing**: Route requests to appropriate models
- **Cost-Latency Optimization**: Minimize cost while meeting SLAs

### Configuration & Selection
- **System Configuration**: Parameter optimization under constraints
- **Feature Selection**: Optimal feature subset selection
- **Bundle Recommendations**: Best product/service combinations
- **Resource Sizing**: Cloud instance selection and sizing

### Logic Puzzles
- **Sudoku**: Constraint satisfaction puzzles → [`sudoku_solver.py`](examples/sudoku_solver.py)
- **Kakuro, KenKen**: Arithmetic constraint puzzles
- **Logic Grids**: Deductive reasoning puzzles
- **N-Queens**: Placement problems

## Roadmap

### Phase 1: Trust & Foundations ✅ (Completed)

- [x] Structured observability and logging
- [x] Health checks and diagnostics
- [x] Problem hashing for deduplication
- [x] Infeasibility diagnosis
- [x] Deterministic solving (random seeds)
- [x] Solution metadata tracking

### Phase 2: Developer Experience ✅ (Completed)

- [x] Pre-solve model validation
- [x] Actionable error messages for LLMs
- [x] Smart typo detection ("Did you mean...?")
- [x] Three-level validation severity (ERROR, WARNING, INFO)
- [x] Detailed validation suggestions

### Phase 3: Power & Performance ✅ (Completed)

- [x] Solution caching with LRU + TTL
- [x] Partial solutions (best-so-far on timeout)
- [x] Search strategy hints (first-fail, random, etc.)
- [x] Cache statistics and hit rate tracking
- [x] Warm-start solution hints

### Phase 1-3 Foundation Features ✅

- [x] Cumulative constraints (resource scheduling)
- [x] Circuit constraints (routing/TSP)
- [x] Reservoir constraints (inventory management)
- [x] No-overlap constraints (disjunctive scheduling)
- [x] Multi-objective optimization (priority-based)
- [x] Parallel search workers
- [x] Search progress logging

### Phase 4: LLM-Native Problem Schemas 🚧 (In Progress)

**Completed:**
- [x] High-level scheduling API (`solve_scheduling_problem`)
- [x] Task model with dependencies, resources, deadlines
- [x] Resource model with capacity constraints
- [x] Automatic CP-SAT model generation from high-level specs
- [x] Rich scheduling responses (makespan, critical path, utilization)
- [x] Scheduling examples and documentation
- [x] High-level routing API (TSP/VRP) ✨ NEW
- [x] Multi-vehicle VRP with capacity constraints ✨ NEW (Phase 4.1)
- [x] MTZ subtour elimination for VRP ✨ NEW
- [x] Multiple optimization objectives (distance, time, cost, vehicles) ✨ NEW
- [x] Load timeline tracking ✨ NEW
- [x] VRP examples and documentation ✨ NEW
- [x] High-level budget allocation API
- [x] High-level assignment API

**In Progress:**
- [ ] Time window constraints for VRP
- [ ] Pickup and delivery for VRP
- [ ] Heterogeneous fleet support

### Phase 5-7: Planned 🔮

- [ ] Solution enumeration (find N diverse solutions)
- [ ] Solution visualization (Gantt charts, graphs)
- [ ] Enhanced debugging (conflict analysis)
- [ ] Export to MPS/LP formats
- [ ] Advanced search strategies (custom heuristics)
- [ ] Symmetry breaking
- [ ] Decomposition strategies
- [ ] Documentation generation from models

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure `make check` passes
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details.

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

> This is a demonstration project provided as-is for learning and testing purposes.

## Acknowledgments

Built with:
- [Google OR-Tools](https://developers.google.com/optimization) - CP-SAT solver
- [Pydantic](https://pydantic.dev) - Data validation
- [Model Context Protocol](https://modelcontextprotocol.io/) - Protocol specification
