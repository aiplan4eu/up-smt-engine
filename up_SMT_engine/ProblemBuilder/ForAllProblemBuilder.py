from up_SMT_engine.ProblemBuilder.BaseProblemBuilder import BaseProblemBuilder


class ForAllProblemBuilder(BaseProblemBuilder):
    """Subclass of BaseProblemBuilder, overriding build and __generate_parallelism_mutexes to implement ForAll parallelism"""

    def __generate_parallelism_mutexes(self, plan_len):
        """Generate mutexes for ForAll parallelism
        For every pair of actions if interference is found then add a mutex over those two actions

        Args:
            plan_len (int): Plan length

        Returns:
            Array of constraint clauses: Array of constraint clauses. If using incremental solving this only covers the penultimate timestep. Otherwise the array covers the first to penultimate timesteps
        """
        constraints = []
        for action in self.actions:
            if self.incremental:
                constraints.append(action.get_ForAll_constraints_at_t(plan_len))
            else:
                constraints.append(action.get_ForAll_constraints_up_to_t(plan_len))
        return constraints

    def build(self, problem_instance, plan_len, goal_clause):
        """Using clauses generated by actions and fluents build the problem in the z3 Solver

        Args:
            problem_instance (z3.Solver): The current solver to which clauses are added
            plan_len (int): The plan length
            goal_clause (Clause): The clause representing all goal conditions
        """
        self.add_init(problem_instance, plan_len)

        super().add_fluent_constraints(problem_instance, plan_len)

        # Don't consider actions, frame axiom constraints and chained variables until after timestep 0
        if plan_len > 0:
            super().add_action_constraints(problem_instance, plan_len)
            # Generate action parallelism constraints over all actions
            mutexes = self.__generate_parallelism_mutexes(plan_len)
            super().add_mutexes(problem_instance, mutexes)

        self.add_goal(problem_instance, goal_clause)
        return
