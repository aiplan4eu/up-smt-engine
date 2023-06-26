from multiprocessing import Process, Manager
from io import StringIO
import sys
from typing import Optional, Callable, IO
from unified_planning.engines.results import PlanGenerationResultStatus
import unified_planning as up
import unified_planning.engines as engines
from unified_planning.model import ProblemKind
from up_SMT_engine.ProblemManager.ProblemManager import *
from up_SMT_engine.helper_functions.PartialOrderPlanFix import (
    custom_replace_action_instances,
)
from up_SMT_engine.helper_functions.IOHelperFunctions import (
    save_stats_to_file,
    print_eval_data,
    print_formula_data,
)
from up_SMT_engine.helper_functions.SmtModelHelperFunctions import (
    convert_action_sequence_to_plan,
    get_goal_actions_list,
)

# Core function for building SMT based problem and solving the same problem via z3
# In order to allow clean timeouts this can be run as a Process which can be killed without running into any z3 related problems
# It was found using a signal to throw an exception on timeout was inconsistent.
def run_smt_planner(problem, smt_planner, return_queue):
    """Function used to ground a Unified Planning API based problem, reformat into SMT friendly classes, use class methods to
    generate clauses necessary for SMT and then check for satisfiability

    Args:
        problem (up.model.Problem): The API based model of the current planning problem
        smt_planner (SMTPlanner): The SMTPlanner object holding user options, and shared-memory objects for returning values
        return_queue (multiprocessing.Queue): Shared memory queue, used to return a satisfying plan, or if one cannot be found: None

    Returns:
        unified_planning.plans.sequential_plan.SequentialPlan or unified_planning.plans.PartialorderPlan or None: Satisfying plan. When executed without a timeout this
        normally returns a SequentialPlan object containing the satisfying series of actions, but if one cannot be found then return None. If the ForAll_get_sets option
        is chosen then returns a PartialOrderPlan containing the sets of actions which may be executed in parallel to satisfy the problem.

    """
    # Use try and finally to ensure something is added to the Queue to avoid deadlock
    try:
        env = problem.environment
        # First we ground the problem. This doesn't ground the fluents, but does ground the actions.
        with env.factory.Compiler(
            problem_kind=problem.kind,
            compilation_kind=engines.CompilationKind.GROUNDING,
        ) as grounder:
            grounding_result = grounder.compile(
                problem, engines.CompilationKind.GROUNDING
            )
        grounded_problem = grounding_result.problem
        # We store the grounded actions in a list which is later used to build a unified-planning API based plan from the grounded SMT model
        actions = list(grounded_problem.instantaneous_actions)

        smt_manager = ProblemManager(
            grounded_problem,
            smt_planner.parallelism,
            smt_planner.use_incremental_solving,
            smt_planner.reset_solver,
        )

        # If no valid plan length is set then disable it
        max_plan_length = (
            int(smt_planner.max_length)
            # Allow assertion that plans have length 0, meaning no actions are required
            if (smt_planner.max_length is not None and smt_planner.max_length > -1)
            else None
        )
        with env.factory.PlanValidator(name="sequential_plan_validator") as pv:
            # Plan length variable
            t = 0
            while (max_plan_length is None) or (t <= max_plan_length):
                # Check for solution with plan length = t
                smt_manager.check_sat(t)
                # Record performance metrics
                if smt_planner.stats_output is not None:
                    smt_manager.get_eval_data(smt_planner.eval_data)
                    smt_manager.get_formula_data(smt_planner.formula_data)
                # If solved create a unified-planning API based plan from the SMT Model
                if smt_manager.is_solved():
                    # Convert SAT model() to sequence of actions from the grounded_problem
                    action_sequence = get_goal_actions_list(
                        smt_manager.get_results(), actions, t, smt_planner.parallelism
                    )
                    # Return action_sequence for use with unit testing
                    if smt_planner.unit_test:
                        if return_queue is not None:
                            return_queue.put(action_sequence)
                            return None
                        else:
                            return action_sequence
                    # Order the sequence of actions into a plan for the expected PlanGenerationResult output
                    plan = convert_action_sequence_to_plan(
                        action_sequence,
                        smt_planner.parallelism,
                        smt_planner.ForAll_get_sets,
                        smt_manager.get_ordered_actions(),
                    )
                    # If the user wants to see the sets of parallel actions executed at each step we preserve these using a PartialOrderPlan
                    if smt_planner.ForAll_get_sets:
                        # Check that the sequential representation of this partial order plan is valid. n.b. This does not check if the plan is correct
                        assert pv.validate(grounded_problem, plan.to_sequential_plan())
                        # Un-ground the action instances
                        # The replace_action_instances method of the PartialOrderPlan class is broken, so use a custom function
                        resplan = custom_replace_action_instances(
                            plan, grounding_result.map_back_action_instance
                        )
                        # Check that the un-grounded plan is valid
                        assert pv.validate(problem, resplan.to_sequential_plan())
                    else:
                        # Check that the plan is valid. n.b. This does not check if the plan is correct
                        assert pv.validate(grounded_problem, plan)
                        # Un-ground the action instances
                        resplan = plan.replace_action_instances(
                            grounding_result.map_back_action_instance
                        )
                        # Check that the un-grounded plan is valid
                        assert pv.validate(problem, resplan)
                    # Check if a timeout has been set, which determines where the output is expected
                    if return_queue is not None:
                        return_queue.put(resplan)
                        return None
                    else:
                        return resplan
                t += 1
            # Plan length limit reached, return None which results in Timeout
            if return_queue is not None:
                return_queue.put(None)
                return None
            else:
                return None
    finally:
        # Add an item to the return queue to avoid locking the parent thread which may expect a value in the queue
        if return_queue is not None:
            return_queue.put(None)


class SMTPlanner(engines.Engine, engines.mixins.OneshotPlannerMixin):
    """Main engine class, used to handle user options and to call run_smt_planner."""

    def __init__(self, **options):
        engines.Engine.__init__(self)
        engines.mixins.OneshotPlannerMixin.__init__(self)

        # Read known user-options and store them for using in the `solve` method
        # Set a maximum plan length bound
        self.max_length = options.get("max_length", None)
        # Option choosing the type of parallalelism. Chooses between 'sequential', 'ForAll', 'ThereExists' and 'relaxed_relaxed_ThereExists'
        # 'sequential' corresponds to a traditional approach, choosing one action per timestep
        # 'ForAll' corresponds to temporal parallelism, choosing a set of non-interfering actions per timestep
        # 'ThereExists' chooses a set of actions for each timestep such that there is at least one valid sequential ordering. This corresponds to sequential plans and aims to improve performance
        # 'relaxed_relaxed_ThereExists' is a relaxation of ThereExists, and aims to increase the number of possible actions per step further, at the cost of individual steps becoming more expensive
        self.parallelism = options.get("parallelism", None)
        # Option choosing whether to output a partial order plan for ForAll parallelism to see the parallel action sets
        self.ForAll_get_sets = options.get("ForAll_get_sets", None)
        # Option choosing the whether to use SMT's incremental solving or not
        # Incremental solving preserves learned clauses after a plan length has been found unsatisfiable, reducing search for the next step at the cost of requiring more clauses maintained
        self.use_incremental_solving = options.get("use_incremental_solving", None)
        # If a string is provided then generate statistics, and save to file, using stats_output as filepath
        self.stats_output = options.get("stats_output", None)
        # Get action sequence for unit tests
        self.unit_test = options.get("unit_test", False)

    @property
    def name(self) -> str:
        return "SMTPlanner"

    # This planner supports numeric planning
    @staticmethod
    def supported_kind():
        supported_kind = ProblemKind()
        supported_kind.set_conditions_kind("NEGATIVE_CONDITIONS")
        supported_kind.set_conditions_kind("DISJUNCTIVE_CONDITIONS")
        supported_kind.set_conditions_kind("EQUALITIES")
        supported_kind.set_conditions_kind("EXISTENTIAL_CONDITIONS")
        supported_kind.set_conditions_kind("UNIVERSAL_CONDITIONS")
        supported_kind.set_effects_kind("CONDITIONAL_EFFECTS")
        supported_kind.set_effects_kind("INCREASE_EFFECTS")
        supported_kind.set_effects_kind("DECREASE_EFFECTS")
        supported_kind.set_fluents_type("NUMERIC_FLUENTS")
        supported_kind.set_fluents_type("OBJECT_FLUENTS")
        supported_kind.set_numbers("CONTINUOUS_NUMBERS")
        supported_kind.set_numbers("DISCRETE_NUMBERS")
        supported_kind.set_problem_class("ACTION_BASED")
        supported_kind.set_problem_type("GENERAL_NUMERIC_PLANNING")
        supported_kind.set_typing("FLAT_TYPING")
        supported_kind.set_typing("HIERARCHICAL_TYPING")
        return supported_kind

    @staticmethod
    def supports(problem_kind):
        return problem_kind <= SMTPlanner.supported_kind()

    def _solve(
        self,
        problem: "up.model.Problem",
        callback: Optional[Callable[["up.engines.PlanGenerationResult"], None]] = None,
        timeout: Optional[float] = -1,
        output_stream: Optional[IO[str]] = None,
    ) -> "up.engines.results.PlanGenerationResult":
        """Parse engine run parameters and run the run_smt_planner function

        Args:
            problem (up.model.Problem): A unified-planning API based problem to solve
            callback (Optional[Callable[[&quot;up.engines.PlanGenerationResult&quot;], None]], optional): Not currently implemented.
            timeout (Optional[float], optional): Timeout in seconds for the solver. Defaults to -1, representing no timeout.
            output_stream (Optional[IO[str]], optional): New output stream. Defaults to None.

        Returns:
            up.engines.results.PlanGenerationResult: Represents either a TIMEOUT, or a satisfying plan
        """
        if output_stream is not None:
            standard_stdout = sys.stdout
            sys.stdout = output_stream = StringIO()
        # Ensure output redirection is restored
        try:

            # Handle option sanitation
            self.parallelism = (
                self.parallelism if (self.parallelism is not None) else "sequential"
            )
            self.ForAll_get_sets = (
                True
                if (
                    self.ForAll_get_sets is not None
                    and self.ForAll_get_sets == True
                    and self.parallelism == "ForAll"
                )
                else False
            )
            self.reset_solver = False
            if self.use_incremental_solving is None:
                self.use_incremental_solving = True
            elif self.use_incremental_solving == "reset_solver":
                self.use_incremental_solving = False
                self.reset_solver = True
            # If using a timeout create a manager for handling the Process running the solver
            if timeout > 0:
                manager = Manager()

            # Filepath for statistics
            self.stats_output = (
                self.stats_output
                if (
                    self.stats_output is not None and isinstance(self.stats_output, str)
                )
                else None
            )

            # Handle datastructures for storing statistics
            self.eval_data = None
            self.formula_data = None
            if self.stats_output is not None:
                if timeout > 0:
                    # If using a timeout we generate datastructures in a Process, and need to use a dictionary in shared memory for each
                    # eval_data is concerned with time per step, time to check for satisfiability for each plan length, total time, and number of steps.
                    self.eval_data = manager.list()
                    # formula_data is concerned with the number of variables, clauses and mutexes (constraining parallel actions) per step
                    self.formula_data = manager.dict()
                    self.formula_data["variables_per_step"] = manager.list()
                    self.formula_data["clauses_per_step"] = manager.list()
                    self.formula_data["mutexes_per_step"] = manager.list()
                else:
                    # eval_data is concerned with time per step used to solve the problem, this includes time taken to build the SMT problem
                    # because Z3 performs preprocessing in this phase
                    self.eval_data = []
                    self.formula_data = {}
                    # formula_data is concerned with the number of variables, clauses and mutexes (constraining parallel actions) per step
                    self.formula_data["variables_per_step"] = []
                    self.formula_data["clauses_per_step"] = []
                    self.formula_data["mutexes_per_step"] = []

            if timeout > 0:
                # If using a timeout run the smt solver as a process
                # Use a shared memory queue to retrieve the plan from the Process
                return_queue = manager.Queue()

                smt_process = Process(
                    target=run_smt_planner, args=(problem, self, return_queue)
                )
                # Start the solver Process
                smt_process.start()
                # Try to join the Process before a timeout
                smt_process.join(timeout)
                # If the Process hasn't been joined then the timeout has been reached
                if smt_process.is_alive():
                    # Terminate the Process and return Timeout
                    smt_process.terminate()
                    smt_process.join()
                    return up.engines.PlanGenerationResult(
                        PlanGenerationResultStatus.TIMEOUT, None, self.name
                    )
                else:
                    # If Process is completed then expect complete stats, or plan length based timeout
                    # Queue first value is either None, or a plan. If None then plan length based timeout has occurred
                    plan = return_queue.get()
            else:
                # Run without time based timeout, plan length based 'timeout' is still possible
                plan = run_smt_planner(problem, self, None)

            if plan is None:
                return up.engines.PlanGenerationResult(
                    PlanGenerationResultStatus.TIMEOUT, None, self.name
                )
            # If expecting stats output:
            if self.stats_output is not None:
                if False:
                    print_formula_data(self.formula_data)
                    print_eval_data(self.eval_data)
                save_stats_to_file(
                    self.formula_data,
                    self.eval_data,
                    self.stats_output,
                    self.parallelism,
                    self.use_incremental_solving,
                )
            # If unit testing is done we return the raw action sets for examination
            if self.unit_test:
                return plan
            return up.engines.PlanGenerationResult(
                PlanGenerationResultStatus.SOLVED_SATISFICING, plan, self.name
            )
        finally:
            if output_stream is not None:
                sys.stdout = standard_stdout

    def destroy(self):
        pass
