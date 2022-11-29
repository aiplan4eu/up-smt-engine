from up_SMT_engine.ProblemBuilder.BaseProblemBuilder import BaseProblemBuilder


class ThereExistsProblemBuilder(BaseProblemBuilder):
    """Subclass of BaseProblemBuilder, overriding build and __generate_parallelism_mutexes to implement ThereExists parallelism"""

    def __generate_parallelism_mutexes(self, plan_len):
        """Generate mutexes for ThereExists parallelism
        Using an ordered array of actions, if an earlier action interferes with a later action then add a mutex for those actions

        Args:
            plan_len (int): Plan length

        Returns:
            Array of constraint clauses: Array of constraint clauses. If using incremental solving this only covers the penultimate timestep. Otherwise the array covers the first to penultimate timesteps
        """
        constraints = []
        # Get list of affecting action tuples. Check action index in self.actions
        # If index < i, then add clause constraining with condition.
        # No need to check the first action
        for i in range(1, len(self.actions)):
            if self.incremental:
                later_action = self.actions[i]
                constraints.append(
                    later_action.get_ThereExists_constraints_at_t(
                        plan_len, self.actions
                    )
                )
            else:
                later_action = self.actions[i]
                constraints.append(
                    later_action.get_ThereExists_constraints_up_to_t(
                        plan_len, self.actions
                    )
                )
        return constraints

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

        super().add_fluent_constraints(problem_instance, plan_len)

        # Don't consider actions, frame axiom constraints and chained variables until after timestep 0
        if plan_len > 0:
            super().add_action_constraints(problem_instance, plan_len)
            # Generate action parallelism constraints over all actions
            mutexes = self.__generate_parallelism_mutexes(plan_len)
            super().add_mutexes(problem_instance, mutexes)

        if self.incremental:
            # Create a breakpoint, allowing the current goals to be removed if they are unsatisfiable
            problem_instance.push()

        problem_instance.add(goal_clause)
        return
