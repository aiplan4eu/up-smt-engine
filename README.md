# SMT based engine implementation for unified-planning

## Introduction
An engine using satisfiability modulo theories to solve planning problems. This engine uses z3 as an out of the box solver.

### Status
pip integration incomplete
Solver tested and functional
    Solver capable of sequential, ForAll, ThereExists and relaxed relaxed ThereExists parallelism
Solver accepts and returns the expected unified-planning problem and PlanGenerationResult

### Planning approaches of UP supported
- *Problem kind*: Numeric planning with instantaneous actions
- *Operative mode*: One shot planning


### Engine Options
#### max_length
Read known user-options and store them for using in the `solve` method
Set a maximum plan length bound
#### parallelism
Option choosing the type of parallalelism. Chooses between 'sequential', 'ForAll', 'ThereExists' and 'relaxed_relaxed_ThereExists'
'sequential' corresponds to a traditional approach, choosing one action per timestep
'ForAll' corresponds to temporal parallelism, choosing a set of non-interfering actions per timestep
'ThereExists' chooses a set of actions for each timestep such that there is at least one valid sequential ordering. This corresponds to sequential plans and aims to improve performance
'relaxed_relaxed_ThereExists' is a relaxation of ThereExists, and aims to increase the number of possible actions per step further, at the cost of individual steps becoming more expensive
#### ForAll_get_sets
Option choosing whether to output a partial order plan for ForAll parallelism to see the parallel action sets
#### use_incremental_solving
Option choosing the whether to use SMT's incremental solving or not
Incremental solving preserves learned clauses after a plan length has been found unsatisfiable, reducing search for the next step at the cost of requiring more clauses maintained
#### stats_output
If a string is provided then generate statistics, and save to file, using stats_output as filepath
#### unit_test
Get action sequence for unit tests


## Installing
TODO implement pip method

Clone from https://gitlab.com/BPat123/up-smt-engine
Dependencies: unified-planning, z3

## Usage
See 'test_runner.py' and 'unit_tests.py' for usage examples

To run all options against a PDDL file use this command:
python3 test_runner.py -timeout "$TIMEOUT_VAL" -test_all -use_PDDL -domain_path "$domain_string" -problem_path "$problem_string" -solution_path "$problem_results_path"

$TIMEOUT_VAL: timeout in seconds
$domain_string: PDDL domain file path
$problem_string: PDDL problem file path
$problem_string: PDDL problem file path
$problem_results_path: Plan output path
n.b. the plan output is in PDDL format, and can be verified using programs such as VAL

e.g.
python3 up-smt-engine/test_runner.py -timeout 100 -test_all -use_PDDL -domain_path tests/counters/domain.pddl -problem_path tests/counters/problem.pddl -solution_path counters/solution.txt

## Documentation

[Documentation generated by Docstring Hosted](https://bpat123.gitlab.io/up-smt-engine/html/)

## License

MIT

## CHANGELOG
