import unified_planning as up
import sys

from up_SMT_engine.SMTPlanner import SMTPlanner
from up_SMT_engine.helper_functions.IOHelperFunctions import  (
    PDDLToProblem,
    writeSolutionToFile,
)

from api_tests.CustomAPITests import CustomAPITests

# Install commands required:
# pip install z3-solver
# pip install --pre unified-planning


def generate_stats_path(basepath, parallelism, is_incremental):
    incremental_string = "incremental" if (is_incremental) else "non-incremental"
    path = basepath + parallelism + "_" + incremental_string + ".csv"
    return path


def generate_plan_path(basepath, parallelism, is_incremental):
    incremental_string = "incremental" if (is_incremental) else "non-incremental"
    path = basepath + parallelism + "_" + incremental_string + ".txt"
    return path


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
                print("\nPlan length: " + str(len(result.plan.actions)) + "\n")
            if write_solution and len(solution_path) > 0:
                solution_path = generate_plan_path(
                    solution_path,
                    options["parallelism"],
                    options["use_incremental_solving"],
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

    options = {
        "parallelism": "sequential",
        "use_incremental_solving": True,
        "stats_output": generate_stats_path(statistics_path, "sequential", True),
    }
    failed = 0
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
    options["stats_output"] = generate_stats_path(statistics_path, "sequential", False)
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
    options["stats_output"] = generate_stats_path(statistics_path, "ForAll", True)
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
    options["stats_output"] = generate_stats_path(statistics_path, "ForAll", False)
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
    options["stats_output"] = generate_stats_path(statistics_path, "ThereExists", True)
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
    options["stats_output"] = generate_stats_path(statistics_path, "ThereExists", False)
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
    options["stats_output"] = generate_stats_path(
        statistics_path, "relaxed_relaxed_ThereExists", True
    )
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
    options["stats_output"] = generate_stats_path(
        statistics_path, "relaxed_relaxed_ThereExists", False
    )
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
    test_choice,
    incremental,
    domain_path,
    problem_path,
    solution_path,
    write_solution,
    statistics_path,
):
    env = up.environment.get_environment()
    env.factory.add_engine("SMTPlanner", __name__, "SMTPlanner")
    if use_PDDL:
        problem = PDDLToProblem(domain_path, problem_path)
    else:
        problem = CustomAPITests(env, api_test)

    # test_all
    if test_choice == "all":
        print("\nproblemkind:")
        print(problem.kind)
        run_all(
            env, problem, write_solution, solution_path, timeout, statistics_path, True
        )
    else:
        if incremental == "both":
            options = {
                "parallelism": test_choice,
                "use_incremental_solving": True,
                "stats_output": generate_stats_path(statistics_path, test_choice, True),
            }
            run_one(
                env, options, problem, False, write_solution, solution_path, timeout
            )
            options["use_incremental_solving"] = False
            options["stats_output"] = generate_stats_path(
                statistics_path, test_choice, False
            )
            run_one(
                env, options, problem, False, write_solution, solution_path, timeout
            )
        else:
            incremental = (
                True if (incremental == "true" or incremental == "True") else False
            )
            options = {
                "parallelism": test_choice,
                "use_incremental_solving": incremental,
            }
            if statistics_path is not None:
                options["stats_output"] = generate_stats_path(
                    statistics_path, test_choice, incremental
                )
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
    # Choice of parallelism
    test_choice = "all"
    incremental = "both"
    if "-p" in args:
        i = args.index("-p")
        test_choice = str(args[i + 1])
    if "-incremental" in args:
        i = args.index("-incremental")
        incremental = args[i + 1]
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
        test_choice,
        incremental,
        domain_path,
        problem_path,
        solution_path,
        write_solution,
        statistics_path,
    )
