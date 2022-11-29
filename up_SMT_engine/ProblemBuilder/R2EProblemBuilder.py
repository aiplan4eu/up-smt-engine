from up_SMT_engine.ProblemBuilder.BaseProblemBuilder import BaseProblemBuilder


class R2EProblemBuilder(BaseProblemBuilder):
    """Subclass of BaseProblemBuilder, overriding build and adding new methods to implement relaxed relaxed ThereExists parallelism"""

    def add_fluent_constraints(self, problem_instance, plan_len):
        """For each fluent object generate all relevant constraints

        Args:
            problem_instance (z3.Solver): The solver to which clauses are added
            plan_len (int): The plan length
        """
        if plan_len > 0:
            # Generate explanatory axioms, these are responsible for linking each fluent to the next similar to frame axioms
            for fluent in self.fluents:
                if self.incremental:
                    problem_instance.add(
                        fluent.generate_explanatory_axioms_at_t(
                            plan_len, self.fluents, self.actions
                        )
                    )
                    problem_instance.add(
                        fluent.link_chained_vars_to_majors_at_t(plan_len)
                    )
                else:
                    axioms = fluent.generate_explanatory_axioms_up_to_t(
                        plan_len, self.fluents, self.actions
                    )
                    for axiom in axioms:
                        problem_instance.add(axiom)
                    links = fluent.link_chained_vars_to_majors_up_to_t(plan_len)
                    for linking_constraint in links:
                        problem_instance.add(linking_constraint)

            # Generate bound constraints over chained variables
            for fluent in self.fluents:
                if self.incremental:
                    problem_instance.add(
                        fluent.get_chained_vars_bound_constraints_at_t(plan_len)
                    )
                else:
                    bound_constraints = (
                        fluent.get_chained_vars_bound_constraints_up_to_t(plan_len)
                    )
                    if bound_constraints is not None:
                        for constraint in bound_constraints:
                            problem_instance.add(constraint)

        # Generate bound constraints over non-chained fluents
        for fluent in self.fluents:
            if self.incremental:
                problem_instance.add(fluent.get_bound_constraints_at_t(plan_len))
            else:
                bound_constraints = fluent.get_bound_constraints_up_to_t(plan_len)
                if bound_constraints is not None:
                    for constraint in bound_constraints:
                        problem_instance.add(constraint)

    def add_action_constraints(self, problem_instance, plan_len):
        """For each action object generate all relevant constraints

        Args:
            problem_instance (z3.Solver): The solver to which clauses are added
            plan_len (int): The plan length
        """
        # Generate all causal constraints over all actions. These require that an action occurring causes the correct effects
        for action in self.actions:
            if self.incremental:
                problem_instance.add(
                    action.get_causal_axioms_at_t(plan_len, self.fluents, self.actions)
                )
            else:
                axioms = action.get_causal_axioms_up_to_t(
                    plan_len, self.fluents, self.actions
                )
                for axiom in axioms:
                    problem_instance.add(axiom)

        # Generate all precondition constraints over all actions. These require that an action occurring only happens when preconditions are satisfied
        for action in self.actions:
            if self.incremental:
                problem_instance.add(
                    action.get_precondition_constraints_at_t(
                        plan_len, self.fluents, self.actions
                    )
                )
            else:
                constraints = action.get_precondition_constraints_up_to_t(
                    plan_len, self.fluents, self.actions
                )
                for constraint in constraints:
                    problem_instance.add(constraint)

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
            # No mutexes required

        if self.incremental:
            # Create a breakpoint, allowing the current goals to be removed if they are unsatisfiable
            problem_instance.push()

        problem_instance.add(goal_clause)
