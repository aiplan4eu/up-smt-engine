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
# pip install --pre unified-planning


def run_one(
    env,
    options,
    problem,
    verbose=False,
    write_solution=False,
    solution_path="",
    TIMEOUT=-1,
):
    print(
        "\nParallelism is: "
        + options["parallelism"]
        + ". use_incremental_solving: "
        + str(options["use_incremental_solving"])
    )
    with env.factory.OneshotPlanner(name="SMTPlanner", params=options) as p:
        result = p.solve(problem, None, TIMEOUT)
        if (
            result.status
            == up.engines.results.PlanGenerationResultStatus.SOLVED_SATISFICING
        ):
            print("Solution found")
            if verbose:
                print("\n".join(str(x) for x in result.plan.actions))
            if write_solution and len(solution_path) > 0:
                solution_path = (
                    solution_path
                    + options["parallelism"]
                    + "_is_incremental_"
                    + str(options["use_incremental_solving"])
                    + "_plan.txt"
                )
                writeSolutionToFile(result.plan, solution_path)
            return result.plan
        else:
            print("No plan found!")
            return None


def run_all(
    env,
    problem,
    write_solution=False,
    solution_path="",
    TIMEOUT=10,
    statistics_path=None,
    verbose=False,
):
    # Delete the old statistics file
    deleteFile(statistics_path)

    options = {
        "parallelism": "sequential",
        "use_incremental_solving": False,
        "stats_output": statistics_path,
    }
    failed = 0
    options["parallelism"] = "sequential"
    options["use_incremental_solving"] = True
    failed = (
        failed + 1
        if (
            run_one(
                env, options, problem, verbose, write_solution, solution_path, TIMEOUT
            )
            is None
        )
        else failed
    )

    options["use_incremental_solving"] = False
    failed = (
        failed + 1
        if (
            run_one(
                env, options, problem, verbose, write_solution, solution_path, TIMEOUT
            )
            is None
        )
        else failed
    )

    options["parallelism"] = "ForAll"
    options["use_incremental_solving"] = True
    failed = (
        failed + 1
        if (
            run_one(
                env, options, problem, verbose, write_solution, solution_path, TIMEOUT
            )
            is None
        )
        else failed
    )

    options["use_incremental_solving"] = False
    failed = (
        failed + 1
        if (
            run_one(
                env, options, problem, verbose, write_solution, solution_path, TIMEOUT
            )
            is None
        )
        else failed
    )

    options["parallelism"] = "ThereExists"
    options["use_incremental_solving"] = True
    failed = (
        failed + 1
        if (
            run_one(
                env, options, problem, verbose, write_solution, solution_path, TIMEOUT
            )
            is None
        )
        else failed
    )

    options["use_incremental_solving"] = False
    failed = (
        failed + 1
        if (
            run_one(
                env, options, problem, verbose, write_solution, solution_path, TIMEOUT
            )
            is None
        )
        else failed
    )

    options["parallelism"] = "relaxed_relaxed_ThereExists"
    options["use_incremental_solving"] = True
    failed = (
        failed + 1
        if (
            run_one(
                env, options, problem, verbose, write_solution, solution_path, TIMEOUT
            )
            is None
        )
        else failed
    )

    options["use_incremental_solving"] = False
    failed = (
        failed + 1
        if (
            run_one(
                env, options, problem, verbose, write_solution, solution_path, TIMEOUT
            )
            is None
        )
        else failed
    )

    print("Failed attempts = " + str(failed))


def main(
    use_PDDL,
    api_test,
    timeout,
    test_all,
    domain_path,
    problem_path,
    solution_path,
    write_solution,
    statistics_path,
):
    env = up.environment.get_env()
    env.factory.add_engine("SMTPlanner", __name__, "SMTPlanner")
    if use_PDDL:
        problem = PDDLToProblem(domain_path, problem_path)
    else:
        problem = CustomAPITests(env, api_test)

    # test_all
    if test_all:
        print("\nproblemkind:")
        print(problem.kind)
        run_all(
            env, problem, write_solution, solution_path, timeout, statistics_path, True
        )
    else:
        options = {
            "parallelism": "ThereExists",
            "use_incremental_solving": True,
        }
        run_one(env, options, problem, True, write_solution, solution_path, timeout)


if __name__ == "__main__":
    # Handle arguments
    args = sys.argv[1:]
    # 0: True/False Choose whether to use PDDL or not
    use_PDDL = "-use_PDDL" in args
    # 1: (If 0 = True): True/False Choose whether to write solution to file. Writes to same file directory as PDDL domain file
    write_solution = "-solution_path" in args
    solution_path = ""
    if write_solution:
        i = args.index("-solution_path")
        solution_path = args[i + 1]
    timeout = -1
    if "-timeout" in args:
        i = args.index("-timeout")
        timeout = int(args[i + 1])
    api_test = 1
    if "-api_test" in args:
        i = args.index("-api_test")
        api_test = int(args[i + 1])
    test_all = "-test_all" in args
    domain_path = ""
    problem_path = ""
    if use_PDDL:
        i = args.index("-domain_path")
        domain_path = args[i + 1]
        i = args.index("-problem_path")
        problem_path = args[i + 1]
    statistics_path = None
    if "-statistics" in args:
        i = args.index("-statistics_path")
        statistics_path = args[i + 1]
    main(
        use_PDDL,
        api_test,
        timeout,
        test_all,
        domain_path,
        problem_path,
        solution_path,
        write_solution,
        statistics_path,
    )
