# Used for measuring performance per step
import time as system_time
from up_SMT_engine.actions.BaseAction import BaseAction
from up_SMT_engine.actions.ForAllAction import ForAllAction
from up_SMT_engine.actions.ThereExistsAction import ThereExistsAction
from up_SMT_engine.actions.R2ExistsAction import R2ExistsAction
from up_SMT_engine.helper_functions.FNODEHelperFunctions import (
    convert_FNODE_to_Z3,
)
from up_SMT_engine.helper_functions.FluentHelperFunctions import handle_API_fluent
from up_SMT_engine.ProblemBuilder.BaseProblemBuilder import BaseProblemBuilder
from up_SMT_engine.ProblemBuilder.ForAllProblemBuilder import ForAllProblemBuilder
from up_SMT_engine.ProblemBuilder.ThereExistsProblemBuilder import (
    ThereExistsProblemBuilder,
)
from up_SMT_engine.ProblemBuilder.R2EProblemBuilder import R2EProblemBuilder
from z3 import And, sat, Solver, Bool


class ProblemManager:
    """Class used to handle Action and Fluent classes used to generate the clauses describing the problem for a SMT solver"""

    def __init__(
        self,
        grounded_problem,
        parallel_choice="sequential",
        run_incremental=True,
        reset_solver_between_runs=False,
    ):
        """Initialisation function used to generate the necessary classes. Actions, Fluents, and the ProblemBuilder have specialised subclasses for specific types of parallelism.

        Args:
            grounded_problem (unified_planning.model.Problem): A planning problem with grounded actions
            parallel_choice (str, optional): The choice of parallelism to implement for SMT solving. See SMTPlanner for more. Defaults to "sequential".
            run_incremental (bool, optional): Whether to run the solver incrementally. See SMTPlanner for more. Defaults to True.
        """
        # API representation of the PDDL problem
        self.grounded_problem = grounded_problem
        # String denoting choice of parallel execution
        self.parallelism = parallel_choice
        # Array of fluent objects representing a smt fluent
        self.smt_fluent = []
        # Array of fluent objects representing a smt action
        self.smt_action = []
        # Current solver instance
        self.solver_instance = None
        # Satisfying model from the Solver
        self.results = None
        # Boolean value, denotes whether the solver should preserve learned clauses between runs
        self.incremental = run_incremental
        # Time taken to add values to the solver and then solve
        self.run_time = -1
        # Number of steps in the current plan (including 0th step)
        self.max_steps = 0
        # Tailored function to each version of parallelism designed to allow modular use of parallel executions
        self.problem_builder = None
        # Create a grounded fluent object for each grounding of an API fluent variable
        self.__initialise_fluents()
        # Create a grounded action object for each grounding of an API action variable
        # Actions are pre-grounded so no further grounding is required
        self.__initialise_actions()

        # For each action find all fluents affected. Send a tuple (action, condition) to be stored by the affected fluent. When the condition is satisfied
        # that fluent may be affected by the action
        self.__share_effect_info()
        # if ForAll parallelism is chosen we need to populate the all_fluents set for each action
        if parallel_choice == "ForAll":
            # For each action populate 'all_fluents' sets. These sets contain all fluents in an action's preconditions, effect conditions and effects
            # Using each fluent's action_condition pairs we can find which actions interfere
            self.__populate_all_fluents_sets()
            self.problem_builder = ForAllProblemBuilder(
                self.smt_action,
                self.smt_fluent,
                self.incremental,
                reset_solver_between_runs,
                self.__create_initial_values(),
            )
        elif parallel_choice == "ThereExists":
            # Populate this set first to avoid duplication of work when populating all fluents sets
            # ThereExist actions require an 'affecting_fluents' set, in addition to 'all_fluents'. This is used to determine which actions affect
            # eachother
            self.__populate_affecting_fluents_sets()
            self.__populate_all_fluents_sets()
            self.problem_builder = ThereExistsProblemBuilder(
                self.smt_action,
                self.smt_fluent,
                self.incremental,
                reset_solver_between_runs,
                self.__create_initial_values(),
            )
        elif parallel_choice == "relaxed_relaxed_ThereExists":
            # Initialise the chained variables necessary for tracking value changes within a timestep in relaxed relaxed ThereExists parallelism
            # For each fluent find set of affecting actions. For each affecting action create a unique chained variable. Order the chained variables
            # according to the order of actions.
            self.__initialise_chained_variables()
            self.problem_builder = R2EProblemBuilder(
                self.smt_action,
                self.smt_fluent,
                self.incremental,
                reset_solver_between_runs,
                self.__create_initial_values(),
            )
        else:
            self.problem_builder = BaseProblemBuilder(
                self.smt_action,
                self.smt_fluent,
                self.incremental,
                reset_solver_between_runs,
                self.__create_initial_values(),
            )

    def get_ordered_actions(self):
        """The ThereExists implementation uses an arbitrary total ordering over all actions. The ordering used is the
        index of each action in smt_action

            Returns:
                List: Ordered list of actions
        """
        return self.smt_action

    def is_solved(self):
        """Check if a satisfying model has been found

        Returns:
            Boolean: True if found, False otherwise
        """
        if self.results is not None:
            return self.results == sat
        return False

    def print_results(self):
        """Print the satisfying model if one exists"""
        if self.solver_instance is not None:
            print(self.solver_instance.model())
        else:
            print("No results exist")

    def get_results(self):
        """Return the satisfying model if one exists

        Returns:
            z3.Model: The satisfying model
        """
        if self.solver_instance is not None:
            return self.solver_instance.model()
        else:
            return None

    def get_formula_data(self, formula_data):
        """Save the formula data (part of the performance statistics) for the most recent step to a dictionary

        Args:
            formula_data (Dictionary): The dictionary of lists for formula data
        """
        if self.solver_instance is not None:
            # Total number of variables added to the solver equals the number of action instances + fluent instances + (if using relaxed relaxed exists) chained variable instances
            # We have 1 grounded fluent instance per step, starting at step 0, 1 grounded action instance from step 1 (effectively), {size of set affecting a fluent} chained variables per step from step 1 (effectively)
            vars_per_step = (len(self.smt_fluent) * self.max_steps) + (
                len(self.smt_action) * (self.max_steps - 1)
            )
            if self.parallelism == "relaxed_relaxed_ThereExists":
                for fluent in self.smt_fluent:
                    vars_per_step += (self.max_steps - 1) * len(fluent.chained_vars)
            formula_data["variables_per_step"].append(vars_per_step)
            # Count the number of assertions added to the problem to approximate the space complexity
            # n.b. for incremental solving we pop the goal clause if the problem is not SAT. There is always exactly one goal
            # clause, so we add 1 if using incremental, and not SAT
            clauses_per_step = len(self.solver_instance.assertions())
            if self.incremental and not self.is_solved():
                clauses_per_step += 1
            formula_data["clauses_per_step"].append(clauses_per_step)
            # Count the number of constraints between parallel actions per step to approximcate complexity
            formula_data["mutexes_per_step"].append(
                self.problem_builder.get_mutex_count()
            )

    def get_eval_data(self, eval_data):
        """Save the evaluation data (part of the performance statistics) for the most recent step to a dictionary

        Args:
            eval_data (List): The evaluation data list
        """
        if self.solver_instance is not None:
            eval_data.append(self.run_time)

    def __initialise_fluents(self):
        """For each ungrounded fluent create a grounded fluent, using either the BaseFluent or R2ExistsFluent class"""
        API_fluents = self.grounded_problem.fluents
        for ungrounded_fluent in API_fluents:
            self.smt_fluent.extend(
                handle_API_fluent(
                    ungrounded_fluent, self.parallelism, self.grounded_problem.objects
                )
            )

    def __initialise_actions(self):
        """Converts grounded unified-planning actions into BaseAction, ForAllAction, ThereExistsAction or R2ExistsAction objects, depending on the parallel choice"""
        API_actions = self.grounded_problem.actions
        for API_action in API_actions:
            if self.parallelism == "ForAll":
                self.smt_action.append(ForAllAction(API_action))
            elif self.parallelism == "ThereExists":
                self.smt_action.append(ThereExistsAction(API_action))
            elif self.parallelism == "relaxed_relaxed_ThereExists":
                self.smt_action.append(R2ExistsAction(API_action))
            else:
                self.smt_action.append(BaseAction(API_action))

    def __share_effect_info(self):
        """Handles sharing effect info from actions to fluents to enable fluents generating frame axiom constraitns"""
        for action in self.smt_action:
            action.deliver_effect_tuples_to_Fluents(self.smt_fluent)

    def __populate_all_fluents_sets(self):
        """Handles creating the set of fluents relevant to each action. This is only used for parallel encodings"""
        for action in self.smt_action:
            action.populate_all_fluents_set(self.smt_fluent)

    def __populate_affecting_fluents_sets(self):
        """Handles creating the set of fluents affected by each action. This is only used for ThereExists encodings"""
        for action in self.smt_action:
            action.populate_affecting_fluents_set(self.smt_fluent)

    def __initialise_chained_variables(self):
        """Initialise chained variables for all fluents. This is only used for relaxed relaxed ThereExists encodings"""
        for fluent in self.smt_fluent:
            fluent.init_chained_vars(self.smt_action)

    def __create_initial_values(self):
        """Handles initial values, initial_values does computation so only call once"""
        z3_init_values = []
        API_init_values = self.grounded_problem.initial_values
        for fluent_fnode in API_init_values:
            z3_fluent = convert_FNODE_to_Z3(fluent_fnode, 0, None)
            z3_val = convert_FNODE_to_Z3(API_init_values[fluent_fnode], 0, None)
            z3_init_values.append((z3_fluent == z3_val))
        return z3_init_values

    def __create_goals(self, final_timestep):
        """Handles goals, time must be equal to the final state considered for the current problem

        Args:
            final_timestep (int): Final timestep of the problem

        Returns:
            Clause: Clause repreesnting all goals
        """
        fnode_goals = self.grounded_problem.goals
        current_goals = []
        for fnode_goal in fnode_goals:
            current_goals.append(convert_FNODE_to_Z3(fnode_goal, final_timestep, None))
        return And(current_goals)

    def check_sat(self, final_timestep):
        """Populates SMT problem instance and checks if the instance is satisfiable

        Args:
            time (int): Plan length
        """
        start_time = system_time.process_time()
        self.max_steps = final_timestep + 1
        # Debug info
        if final_timestep > 0 and False:
            print("Run " + str(time))
            print(self.num_mutexes)
            print(
                (len(self.smt_fluent) * self.max_steps)
                + (len(self.smt_action) * (self.max_steps - 1))
            )
            print(len(self.solver_instance.assertions()))
        if final_timestep == 0:
            self.solver_instance = Solver()
        current_goal_clause = self.__create_goals(final_timestep)
        # Use ProblemBuilder class tailored to parallelism choice to add the appropriate clauses to the problem
        self.problem_builder.build(
            self.solver_instance, final_timestep, current_goal_clause
        )
        if self.incremental:
            current_goal_bool = Bool("goal_@t" + str(final_timestep))
            # Solve
            self.results = self.solver_instance.check(current_goal_bool)
        else:
            # Solve
            self.results = self.solver_instance.check()

        self.run_time = system_time.process_time() - start_time
