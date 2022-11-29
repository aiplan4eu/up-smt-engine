import unified_planning as up
from up_SMT_engine.helper_functions.IOHelperFunctions import (
    PDDLToProblem,
    writeSolutionToFile,
    deleteFile,
)
from api_tests.CustomAPITests import CustomAPITests
from up_SMT_engine.SMTPlanner import SMTPlanner
import sys

# Install commands required:
# pip install z3-solver
# pip install unified-planning

# expected_shape is an array of integers, describing the expected action_sequence dimensions
def run_one(
    env,
    options,
    problem,
    expected_shape,
    TIMEOUT=-1,
    problem_name="Unknown problem",
):
    failure_string = (
        "\n"
        + problem_name
        + " using "
        + options["parallelism"]
        + ". use_incremental_solving: "
        + str(options["use_incremental_solving"])
        + ". Failed"
    )
    with env.factory.OneshotPlanner(name="SMTPlanner", params=options) as p:
        action_sequence = p.solve(problem, None, TIMEOUT)
        print(action_sequence)
        if action_sequence is not None and not isinstance(
            action_sequence, up.engines.PlanGenerationResult
        ):
            if len(action_sequence) == expected_shape[0]:
                if options["parallelism"] == "sequential":
                    return None
                else:
                    # For parallel plans, if there are actions which are irrelevant to the goal state, a parallel planner may decide to include or exclude these
                    # pointless actions arbitrarily. As such it is useful to set bounds for expected number of actions to account for this
                    # Maximum possible actions to still reach a valid plan
                    max_actions = expected_shape[1]
                    # Minimum possible actions to still reach a valid plan
                    min_actions = expected_shape[0]
                    counted_actions = 0
                    for action_set in action_sequence:
                        counted_actions += len(action_set)
                    if (min_actions <= counted_actions) and (
                        max_actions >= counted_actions
                    ):
                        return None
        return failure_string


def run_russian_dolls(env):
    failed_string = ""
    # Russian dolls test
    problem = CustomAPITests(env, 4)

    timeout = 10
    options = {
        "parallelism": "sequential",
        "use_incremental_solving": False,
        "unit_test": True,
    }

    options["parallelism"] = "sequential"
    options["use_incremental_solving"] = True
    expected_shape = [3]
    result = run_one(env, options, problem, expected_shape, timeout, "russian dolls")
    if result is not None:
        failed_string = failed_string + result

    options["use_incremental_solving"] = True
    result = run_one(env, options, problem, expected_shape, timeout, "russian dolls")
    if result is not None:
        failed_string = failed_string + result

    options["parallelism"] = "ForAll"
    options["use_incremental_solving"] = True
    expected_shape = [3, 3, 3]
    result = run_one(env, options, problem, expected_shape, timeout, "russian dolls")
    if result is not None:
        failed_string = failed_string + result

    options["use_incremental_solving"] = False
    result = run_one(env, options, problem, expected_shape, timeout, "russian dolls")
    if result is not None:
        failed_string = failed_string + result

    options["parallelism"] = "ThereExists"
    options["use_incremental_solving"] = True
    expected_shape = [1, 3, 3]
    result = run_one(env, options, problem, expected_shape, timeout, "russian dolls")
    if result is not None:
        failed_string = failed_string + result

    options["use_incremental_solving"] = False
    result = run_one(env, options, problem, expected_shape, timeout, "russian dolls")
    if result is not None:
        failed_string = failed_string + result

    options["parallelism"] = "relaxed_relaxed_ThereExists"
    options["use_incremental_solving"] = True
    expected_shape = [1, 3, 3]
    result = run_one(env, options, problem, expected_shape, timeout, "russian dolls")
    if result is not None:
        failed_string = failed_string + result

    options["use_incremental_solving"] = False
    result = run_one(env, options, problem, expected_shape, timeout, "russian dolls")
    if result is not None:
        failed_string = failed_string + result

    return failed_string


def run_simple_robot(env):
    failed_string = ""
    # Simple robot problem test
    problem = CustomAPITests(env, 5)

    timeout = 10
    options = {
        "parallelism": "sequential",
        "use_incremental_solving": False,
        "unit_test": True,
    }

    options["parallelism"] = "sequential"
    options["use_incremental_solving"] = True
    expected_shape = [3, 3, 3]
    result = run_one(env, options, problem, expected_shape, timeout, "simple robot")
    if result is not None:
        failed_string = failed_string + result

    options["use_incremental_solving"] = True
    result = run_one(env, options, problem, expected_shape, timeout, "simple robot")
    if result is not None:
        failed_string = failed_string + result

    options["parallelism"] = "ForAll"
    options["use_incremental_solving"] = True
    result = run_one(env, options, problem, expected_shape, timeout, "simple robot")
    if result is not None:
        failed_string = failed_string + result

    options["use_incremental_solving"] = False
    result = run_one(env, options, problem, expected_shape, timeout, "simple robot")
    if result is not None:
        failed_string = failed_string + result

    options["parallelism"] = "ThereExists"
    options["use_incremental_solving"] = True
    result = run_one(env, options, problem, expected_shape, timeout, "simple robot")
    if result is not None:
        failed_string = failed_string + result

    options["use_incremental_solving"] = False
    result = run_one(env, options, problem, expected_shape, timeout, "simple robot")
    if result is not None:
        failed_string = failed_string + result

    options["parallelism"] = "relaxed_relaxed_ThereExists"
    options["use_incremental_solving"] = True
    # Increased parallelism allows one fewer steps
    expected_shape = [2, 3, 3]
    result = run_one(env, options, problem, expected_shape, timeout, "simple robot")
    if result is not None:
        failed_string = failed_string + result

    options["use_incremental_solving"] = False
    result = run_one(env, options, problem, expected_shape, timeout, "simple robot")
    if result is not None:
        failed_string = failed_string + result

    return failed_string


def run_stacking_blocks(env):
    failed_string = ""
    # Simple robot problem test
    problem = CustomAPITests(env, 2)

    timeout = 10
    options = {
        "parallelism": "sequential",
        "use_incremental_solving": False,
        "unit_test": True,
    }

    options["parallelism"] = "sequential"
    options["use_incremental_solving"] = True
    expected_shape = [10]
    result = run_one(env, options, problem, expected_shape, timeout, "simple robot")
    if result is not None:
        failed_string = failed_string + result

    options["use_incremental_solving"] = True
    result = run_one(env, options, problem, expected_shape, timeout, "simple robot")
    if result is not None:
        failed_string = failed_string + result

    options["parallelism"] = "ForAll"
    options["use_incremental_solving"] = True
    expected_shape = [5, 10, 10]
    result = run_one(env, options, problem, expected_shape, timeout, "simple robot")
    if result is not None:
        failed_string = failed_string + result

    options["use_incremental_solving"] = False
    result = run_one(env, options, problem, expected_shape, timeout, "simple robot")
    if result is not None:
        failed_string = failed_string + result

    options["parallelism"] = "ThereExists"
    options["use_incremental_solving"] = True
    result = run_one(env, options, problem, expected_shape, timeout, "simple robot")
    if result is not None:
        failed_string = failed_string + result

    options["use_incremental_solving"] = False
    result = run_one(env, options, problem, expected_shape, timeout, "simple robot")
    if result is not None:
        failed_string = failed_string + result

    options["parallelism"] = "relaxed_relaxed_ThereExists"
    options["use_incremental_solving"] = True
    result = run_one(env, options, problem, expected_shape, timeout, "simple robot")
    if result is not None:
        failed_string = failed_string + result

    options["use_incremental_solving"] = False
    result = run_one(env, options, problem, expected_shape, timeout, "simple robot")
    if result is not None:
        failed_string = failed_string + result

    return failed_string


# These tests simply look at the shape of action sets in order to decide whether each parallel implementation is behaving correctly, and specifically distinctly from other implementations
# We use a separate bash script with VAL to test whether plans are valid, as part of performance testing.
if __name__ == "__main__":
    failed_string = ""
    env = up.environment.get_env()
    env.factory.add_engine("SMTPlanner", __name__, "SMTPlanner")
    # Test that ForAll and Sequential use three timesteps to solve, while ThereExists and relaxed relaxed ThereExists are capable of more parallelism, and therefore only need one step in this case
    # This demonstrates the increased parallelism expected
    failed_string = failed_string + run_russian_dolls(env)
    # Test that all bar relaxed relaxed ThereExists require 3 steps
    # This demonstrates that relaxed relaxed ThereExists parallelism is capable of the most parallelism
    failed_string = failed_string + run_simple_robot(env)
    # This demonstrates that non-sequential forms of parallelism are capable of using fewer steps, and proves ForAll is distinct from sequential
    failed_string = failed_string + run_stacking_blocks(env)

    if len(failed_string) > 0:
        print("Runs failed:")
        print(failed_string)
    else:
        print("All tests passed")
