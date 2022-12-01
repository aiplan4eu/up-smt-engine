from unified_planning.io import PDDLReader
import os
import csv


def PDDLToProblem(domain_path, problem_path):
    """Using the path of a domain and instance file parse them into a unified planning problem object. Used by the test_runner.

    Args:
        domain_path (String): path to a domain file
        problem_path (String): path to a problem file

    Returns:
        unified planning problem: A unified planning problem object
    """
    # Importing the PDDLReader and PDDLWriter
    # Creating a PDDL reader
    reader = PDDLReader()
    # Parsing a PDDL problem from file
    problem = reader.parse_problem(
        domain_path,
        problem_path,
    )
    return problem


def writeSolutionToFile(solution, solution_path):
    """Save plan to a txt file, in a format which may be verified by VAL. Only used by the test_runner

    Args:
        solution (List of ActionInstances): Ordered list of actions solving the problem
        solution_path (String): Path to output file
    """
    dirname = os.getcwd()
    filename = os.path.join(dirname, solution_path)
    output_string = "\n".join(
        "("
        + str(x.action.name)
        + " "
        + " ".join(str(param) for param in x.actual_parameters)
        + ")"
        for x in solution.actions
    )
    f = open(filename, "w")
    f.write(output_string)
    f.close()


# Save stats to CSV file
def save_stats_to_file(
    formula_data, eval_data, stats_output, parallelism, is_incremental
):
    """Save performance statistics to a designated file. Appends onto existing files.

    Args:
        formula_data (Dictionary): Dictionary of formula data per step
        eval_data (List): Array of time required per step
        stats_output (String): Path to output file
        parallelism (String): Type of parallelism
        is_incremental (bool): True if using incremental solving, False otherwise
    """
    file_was_created = not os.path.exists(stats_output)
    csv_rows = []
    for step in range(0, len(eval_data)):
        current_row = []
        current_row.append(parallelism)
        current_row.append(is_incremental)
        current_row.append(step)
        current_row.append(eval_data[step])
        current_row.append(formula_data["variables_per_step"][step])
        current_row.append(formula_data["clauses_per_step"][step])
        current_row.append(formula_data["mutexes_per_step"][step])
        current_row.append("instance")
        current_row.append("domain")
        csv_rows.append(current_row)
    with open(stats_output, "w", encoding="UTF8", newline="") as csvfile:
        w = csv.writer(csvfile)
        # This makes collating data more difficult so skip for now
        # if file_was_created:
        #     w.writerow(
        #         [
        #             "Encoding",
        #             "is_incremental",
        #             "Steps",
        #             "Solving Time per Step",
        #             "Variables per Step",
        #             "Clauses per Step",
        #             "Mutexes per Step",
        #         ]
        #     )
        w.writerows(csv_rows)


def print_eval_data(eval_data):
    """Function used to print the time per each step

    Args:
        eval_data (List): Time per each step
    """
    total_time = 0
    print("{:<8} {:<20} {:<15}".format("Step", "Time per Step", "Total Time"))
    for i in range(0, len(eval_data)):
        total_time += eval_data[i]
        print("{:<8} {:<20} {:<15}".format(i, eval_data[i], total_time))


def print_formula_data(formula_data):
    """Function used to print the formula data per each step

    Args:
        formula_data (Dictionary): Formula data per each step
    """
    print(
        "{:<8} {:<10} {:<10} {:<10}".format("Step", "variables", "clauses", "mutexes")
    )
    for i in range(0, len(formula_data["variables_per_step"])):
        print(
            "{:<8} {:<10} {:<10} {:<10}".format(
                i,
                formula_data["variables_per_step"][i],
                formula_data["clauses_per_step"][i],
                formula_data["mutexes_per_step"][i],
            )
        )
