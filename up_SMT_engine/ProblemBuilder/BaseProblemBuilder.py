from z3 import And, Not, Or


class BaseProblemBuilder:
    """Class used to handle constructing the SMT problem for Z3 to solve
    Suitable for sequential planning
    """

    def __init__(self, actions, fluents, is_incremental, initial_values):
        self.actions = actions
        self.fluents = fluents
        self.incremental = is_incremental
        self.initial_values = initial_values
        self.num_mutexes = 0

    def get_mutex_count(self):
        return self.num_mutexes

    def __generate_parallelism_mutexes(self, plan_len):
        """Generate mutexes for sequential parallelism
        Use basic encoding requiring O(n^2) constraints per timestep
        Assert that, for every pair of actions at time t, only one can be true
        Assert that, for every action at time t at least one can be true (using OR)

        Args:
            plan_len (int): Plan length

        Returns:
            Array of constraint clauses: Array of constraint clauses. If using incremental solving this only covers the penultimate timestep. Otherwise the array covers the first to penultimate timesteps
        """
        constraints = []
        if self.incremental:
            t = plan_len - 1
            actions_at_t = []
            for i in range(0, len(self.actions)):
                action_a = self.actions[i].get_action_at_t(t)
                actions_at_t.append(action_a)
                for j in range(0, i):
                    action_b = self.actions[j].get_action_at_t(t)
                    constraints.append(Not(And(action_a, action_b)))
            constraints.append(Or(actions_at_t))
        else:
            for t in range(0, plan_len):
                timestep_constraints = []
                actions_at_t = []
                for i in range(0, len(self.actions)):
                    action_a = self.actions[i].get_action_at_t(t)
                    actions_at_t.append(action_a)
                    for j in range(0, i):
                        action_b = self.actions[j].get_action_at_t(t)
                        timestep_constraints.append(Not(And(action_a, action_b)))
                timestep_constraints.append(Or(actions_at_t))
                constraints.append(timestep_constraints)
        return constraints

    def add_mutexes(self, instance, mutex_array):
        """Add mutex clauses to the solver while counting each mutex

        Args:
            instance (z3.Solver): Current Solver to which clauses can be added
            mutex_array (Array of constraint clauses): Array of mutex clauses to add
        """
        if self.incremental:
            # Expect a 1d array of constraints
            self.num_mutexes += len(mutex_array)
            for constraint in mutex_array:
                instance.add(constraint)
        else:
            # Expect a 2d array of constraints
            for constraint_set in mutex_array:
                self.num_mutexes += len(constraint_set)
                for constraint in constraint_set:
                    instance.add(constraint)

    def add_action_constraints(self, problem_instance, plan_len):
        """For each action object generate all relevant constraints

        Args:
            problem_instance (z3.Solver): Current Solver to which clauses can be added
            plan_len (int): Plan length
        """
        # Generate all causal constraints over all actions
        for action in self.actions:
            if self.incremental:
                problem_instance.add(action.get_causal_axioms_at_t(plan_len))
            else:
                axioms = action.get_causal_axioms_up_to_t(plan_len)
                for axiom in axioms:
                    problem_instance.add(axiom)

        # Generate all precondition constraints over all actions
        for action in self.actions:
            if self.incremental:
                problem_instance.add(action.get_precondition_constraints_at_t(plan_len))
            else:
                constraints = action.get_precondition_constraints_up_to_t(plan_len)
                for constraint in constraints:
                    problem_instance.add(constraint)

    def add_fluent_constraints(self, problem_instance, plan_len):
        """For each fluent object generate all relevant constraints

        Args:
            problem_instance (z3.Solver): Current Solver to which clauses can be added
            plan_len (int): Plan length
        """
        # Generate bound constraints over all fluents
        for fluent in self.fluents:
            if self.incremental:
                problem_instance.add(fluent.get_bound_constraints_at_t(plan_len))
            else:
                bound_constraints = fluent.get_bound_constraints_up_to_t(plan_len)
                if bound_constraints is not None:
                    for constraint in bound_constraints:
                        problem_instance.add(constraint)
        if plan_len > 0:
            # Generate frame axiom constraints over all fluents
            for fluent in self.fluents:
                if self.incremental:
                    problem_instance.add(
                        fluent.generate_frame_axiom_constraints_at_t(plan_len)
                    )
                else:
                    problem_instance.add(
                        fluent.generate_frame_axiom_constraints_up_to_t(plan_len)
                    )

    def build(self, problem_instance, plan_len, goal_clause):
        """Using clauses generated by actions and fluents build the problem in the z3 Solver

        Args:
            problem_instance (z3.Solver): The current solver to which clauses are added
            plan_len (int): The plan length
            goal_clause (Clause): The clause representing all goal conditions
        """
        if plan_len == 0 or not self.incremental:
            # Reset mutex count
            self.num_mutexes = 0
            # Add initial state constraints
            for init_value in self.initial_values:
                problem_instance.add(init_value)
        elif problem_instance is not None and self.incremental:
            # Pop previous goal clause
            problem_instance.pop()

        self.add_fluent_constraints(problem_instance, plan_len)

        # Don't consider actions, frame axiom constraints and chained variables until after timestep 0
        if plan_len > 0:
            self.add_action_constraints(problem_instance, plan_len)
            # Generate action parallelism constraints over all actions
            mutexes = self.__generate_parallelism_mutexes(plan_len)
            self.add_mutexes(problem_instance, mutexes)

        if self.incremental:
            # Create a breakpoint, allowing the current goals to be removed if they are unsatisfiable
            # Using push automatically turns on incremental mode for the solver
            problem_instance.push()

        problem_instance.add(goal_clause)
        return