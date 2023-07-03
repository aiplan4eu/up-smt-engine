from z3 import And, Or, Implies, Real, Int, Bool
from up_SMT_engine.helper_functions.FNODEHelperFunctions import (
    convert_FNODE_to_Z3,
    createR2ExistsTuple,
    getR2ExistsTupleValue,
    create_stated_action_instance,
)
from up_SMT_engine.fluents.BaseFluent import BaseFluent


class R2ExistsFluent(BaseFluent):
    """R2ExistsFluent inherits methods from BaseFluent, it handles fluents for relaxed relaxed ThereExists parallelism. This subclass extends BaseFluent by adding chained variables."""

    def __init__(self, name, API_fluent):
        super().__init__(name, API_fluent)
        # We require the 'action_condition_pairs' set to be populated so we know the set of actions which may
        # affect this value. Do nothing for now.
        # Array of (chained_fluent_name, action) tuples. Only used for relaxed relaxed ThereExists encoding
        self.chained_vars = []
        # Array of ordered actions affecting this variable
        self.ordered_actions = []

    def __check_action_is_affecting(self, action):
        """Check if an action affects this fluent according to the action_condition tuples list

        Args:
            action (BaseAction or BaseAction subclass): Action to check for

        Returns:
            Bool: True if affecting, false otherwise
        """
        for action_tuple in self.action_condition_pairs:
            if action == action_tuple[0]:
                return True
        return False

    def init_chained_vars(self, ordered_actions):
        """Create a chained variable for each affecting action, plus one initial chained var.

        Args:
            ordered_actions (List): Ordered list of actions
        """
        # Create an ordered array of actions which affect this fluent
        for action in ordered_actions:
            if self.__check_action_is_affecting(action):
                self.ordered_actions.append(action)
        # 1 chained variable for each affecting action + 1 chained variable for start of timestep state
        initial_chained_var = self.base_name + "_0"
        self.chained_vars.append(initial_chained_var)
        for i in range(1, len(self.ordered_actions) + 1):
            # Identify chained variable by index in list of chained variables
            chained_var_name = self.base_name + "_" + str(i)
            self.chained_vars.append(chained_var_name)

    def __get_chained_var_instance(self, name, timestep):
        """Method used internally to create/reference a chained variable

        Args:
            name (String): chained variable name
            timestep (int): current timestep

        Returns:
            z3 expression: z3 variable for chained variable at timestep 'time'
        """
        predicate_name = name + "_@t" + str(timestep)
        if self.fluent_type == "Real":
            return Real(predicate_name)
        elif self.fluent_type == "Int":
            return Int(predicate_name)
        else:
            return Bool(predicate_name)

    def get_chained_var(self, r2exists_tuple):
        """Return chained variable corresponding to calling action. Returns previous chained variable if not for an effect

        Args:
            r2exists_tuple (Tuple): Tuple of values required for handling chained variables for relaxed relaxed ThereExists parallelism.

        Returns:
            z3 variable: Chained variable
        """
        is_effect = getR2ExistsTupleValue(r2exists_tuple, "is_effect")
        action_index = getR2ExistsTupleValue(r2exists_tuple, "action_index")
        ordered_actions_list = getR2ExistsTupleValue(r2exists_tuple, "actions_list")
        # If this is part of an effect expression then the action will be part of ordered_actions.
        if is_effect:
            action = ordered_actions_list[action_index]
            # sublist index + 1 corresponds to the relevant chained variable index
            sublist_action_index = self.ordered_actions.index(action)
            return self.chained_vars[sublist_action_index + 1]
        else:
            # Find action in ordered sublist with greatest index, where overall list index is closest to but before
            # the calling action's index
            # Index in ordered sublist
            sublist_index = -1
            # Index in ordered list of all actions
            closest_index = -1
            for action in self.ordered_actions:
                current_index = ordered_actions_list.index(action)
                if current_index > closest_index and current_index < action_index:
                    closest_index = current_index
                    sublist_index = self.ordered_actions.index(action)
            # If no actions in the sublist have lower indexes than the calling action this means the calling action
            # is executed before any of the sublist actions. Therefore it uses the initial chained variable
            if closest_index == -1:
                return self.chained_vars[0]
            else:
                # Corresponding chained variable index for an affecting action = sublist_index + 1
                return self.chained_vars[sublist_index + 1]

    def __get_chained_vars_bound_constraints_at_t(self, timestep):
        """Returns chained variable bound constraints at t.

        Args:
            timestep (int): Current timestep

        Returns:
            z3 expression: z3 expressions for bound constraints at timestep t
        """
        if self.lower_bound or self.upper_bound is not None:
            bound_constraints = []
            if self.lower_bound is not None:
                for chained_variable in self.chained_vars:
                    chained_var_at_t = self.__get_chained_var_instance(
                        chained_variable, timestep
                    )
                    constraint = chained_var_at_t >= self.lower_bound
                    bound_constraints.append(constraint)
            if self.upper_bound is not None:
                chained_var_at_t = self.__get_chained_var_instance(
                    chained_variable, timestep
                )
                constraint = chained_var_at_t <= self.upper_bound
                bound_constraints.append(constraint)
            return And(bound_constraints)
        return True

    def get_chained_vars_bound_constraints_up_to_t(self, last_timestep):
        """Method used to generate all bound constraints for chained variables up to time t, can be called if no constraints are needed

        Args:
            last_timestep (int): Final timestep

        Returns:
            List(z3 expression): List of z3 expressions for bound constraints up to timestep t
        """
        constraints = []
        for t in range(0, last_timestep):
            constraints.append(self.__get_chained_vars_bound_constraints_at_t(t))
        return constraints

    def get_chained_vars_bound_constraints_at_t(self, timestep):
        """Returns chained variable bound constraints at t. Used for incremental solving.

        Args:
            timestep (int): Current timestep

        Returns:
            z3 expression: z3 expressions for bound constraints at timestep t
        """
        return self.__get_chained_vars_bound_constraints_at_t(timestep)

    def __get_action_specific_action_condition_pairs(self, action):
        """Get action condition pairs corresponding to a specific action

        Args:
            action (BaseAction or BaseAction subclass): Action to search for in pairs

        Returns:
            List(Tuple(BaseAction or BaseAction subclass, condition)): List of pairs with matching actions
        """
        pairs_list = []
        for pair in self.action_condition_pairs:
            if pair[0] == action:
                pairs_list.append(pair)
        return pairs_list

    def __assert_explanatory_axioms_at_t(self, timestep, fluents_list, actions_list):
        """Assert explanatory axioms at t (these replace frame axioms for r2ThereExists parallelism) over chained variables

        Args:
            timestep (int): Current timestep
            fluents_list (List(BaseFluent or BaseFluent subclass)): List of fluents
            actions_list (List(BaseAction or BaseAction subclass): List of actions

        Returns:
            z3 expression: z3 expression for explanatory axioms at t
        """
        axioms = []
        current_value = self.__get_chained_var_instance(self.chained_vars[0], timestep)
        for i in range(1, len(self.chained_vars)):
            prev_value = current_value
            current_value = self.__get_chained_var_instance(
                self.chained_vars[i], timestep
            )
            relevant_action_condition_pairs = (
                self.__get_action_specific_action_condition_pairs(
                    self.ordered_actions[i - 1]
                )
            )
            action_bool = create_stated_action_instance(
                self.ordered_actions[i - 1].get_name(), timestep
            )
            # List of effects relevant to this fluent, owned by the same action.
            explanatory_effects_list = []
            for pair in relevant_action_condition_pairs:
                r2Exists_tuple = createR2ExistsTuple(
                    actions_list.index(pair[0]), False, fluents_list, actions_list
                )
                constraint_as_Z3 = convert_FNODE_to_Z3(
                    pair[1], timestep, r2Exists_tuple
                )
                explanatory_effects_list.append(And(constraint_as_Z3, action_bool))
            explanatory_axiom = Implies(
                (prev_value != current_value), Or(explanatory_effects_list)
            )
            axioms.append(explanatory_axiom)
        return And(axioms)

    def generate_explanatory_axioms_up_to_t(self, timestep, fluents_list, actions_list):
        """Assert explanatory axioms up to the final timestep (these replace frame axioms) over chained variables

        Args:
            timestep (int): Final timestep
            fluents_list (List(BaseFluent or BaseFluent subclass)): List of fluents
            actions_list (List(BaseAction or BaseAction subclass): List of actions

        Returns:
            List(z3 expression): List of z3 expressions for explanatory axioms up to timestep t
        """
        constraints = []
        # Explanatory axioms are used to link chained variables in a timestep. These are only needed when
        # actions are executed in that timestep. We only permit actions to be executed up to timestep t-1
        for t in range(0, timestep):
            constraints.append(
                self.__assert_explanatory_axioms_at_t(t, fluents_list, actions_list)
            )
        return constraints

    def generate_explanatory_axioms_at_t(self, timestep, fluents_list, actions_list):
        """Returns explanatory axioms at t. Used for incremental solving.

        Args:
            timestep (int): Current timestep
            fluents_list (List(BaseFluent or BaseFluent subclass)): List of fluents
            actions_list (List(BaseAction or BaseAction subclass): List of actions

        Returns:
            z3 expression: z3 expression for explanatory axioms at timestep t - 1
        """
        if timestep > 0:
            # Explanatory axioms are used to link chained variables in a timestep. These are only needed when
            # actions are executed in that timestep. We only permit actions to be executed up to timestep t-1
            return self.__assert_explanatory_axioms_at_t(
                timestep - 1, fluents_list, actions_list
            )
        return True

    def __link_chained_vars_to_majors_at_t(self, timestep):
        """Assert initial and final chained variables are linked with major timestep variables
        Even if no actions affect this, because of the 0th chained variable independent of an affecting
        action this method is valid, and equivalent to current_state_var == next_state_var

        Args:
            timestep (int): Current timestep

        Returns:
            z3 expression: z3 expression for linking chained variables to major variables
        """
        constraints = []
        # link first chained var to current major timestep variable
        current_state = self._BaseFluent__get_predicate_at_t(timestep)
        first_chained_var = self.__get_chained_var_instance(
            self.chained_vars[0], timestep
        )
        constraints.append(current_state == first_chained_var)
        # link last chained var to next major timestep variable
        next_state = self._BaseFluent__get_predicate_at_t(timestep + 1)
        last_chained_var = self.__get_chained_var_instance(
            self.chained_vars[len(self.chained_vars) - 1], timestep
        )
        constraints.append(next_state == last_chained_var)
        return And(constraints)

    def link_chained_vars_to_majors_up_to_t(self, timestep):
        """Assert all initial and final chained variables are linked with major timestep variables.

        Args:
            timestep (int): Final timestep

        Returns:
            List(z3 expression): List of z3 expressions for linking chained variables to major variables
        """
        constraints = []
        # Explanatory axioms are used to link chained variables in a timestep. These are only needed when
        # actions are executed in that timestep. We only permit actions to be executed up to timestep t-1
        for t in range(0, timestep):
            constraints.append(self.__link_chained_vars_to_majors_at_t(t))
        return constraints

    def link_chained_vars_to_majors_at_t(self, timestep):
        """Returns constraints linking chained variables at t. Used for incremental solving.

        Args:
            timestep (int): Final timestep

        Returns:
            z3 expression: z3 expression for linking chained variables to major variables at time 'timestep - 1'
        """
        if timestep > 0:
            # Explanatory axioms are used to link chained variables in a timestep. These are only needed when
            # actions are executed in that timestep. We only permit actions to be executed up to timestep t-1
            return self.__link_chained_vars_to_majors_at_t(timestep - 1)
        return True
