from z3 import And, Implies, Bool
from up_SMT_engine.helper_functions.FNODEHelperFunctions import (
    convert_FNODE_to_Z3,
    search_fluents_list,
    create_fluent_condition_tuple,
    convert_effect_to_Z3,
)


class BaseAction:
    """Simple action class, used to handle all methods for sequential plans"""

    def __init__(self, grounded_action):
        self.base_name = grounded_action.name
        self.preconditions = grounded_action.preconditions
        self.effects = grounded_action.effects

    def get_name(self):
        """Return action basename

        Returns:
            String: action basename
        """
        return self.base_name

    def check_name_match(self, other_action_name):
        """Check if the action basename matches this action's basename

        Args:
            other_action_name (String): other action's Basename

        Returns:
            Bool: True if matching, False otherwise
        """
        return self.base_name == other_action_name

    def __eq__(self, other):
        """Define two action objects as equal if they share the same grounded name, and are BaseActions or inherit from BaseAction. If two distinct actions happen to share the same grounded name
        an error has occurred

        Args:
            other_action (BaseAction or BaseAction subclass): Other action to compare against

        Returns:
            Bool: True if matching, False otherwise
        """
        try:
            if isinstance(other, BaseAction) or issubclass(other, BaseAction):
                return self.base_name == other.get_name()
            return False
        except:
            # Something went wrong, most likely an incompatible type
            return False

    def __hash__(self):
        return hash(repr(self))

    def get_action_at_t(self, timestep):
        """Method used to create an action at timestep t

        Args:
            timestep (int): Current timestep

        Returns:
            z3 Bool: z3 variable representing whether an action is executed at timstep t
        """
        stated_action_name = self.base_name + "_@t" + str(timestep)
        return Bool(stated_action_name)

    def __get_effects_at_t(self, timestep):
        """Each effect has three FNODE structures, the condition (optional, makes effect conditional), fluent (the stated variable to be changed)
        and the value (the new fluent value). These are separately converted into Z3, and returned as Implies(condition, (fluent == value))
        These statements are And'd together, as the set of effects of the action.
        n.b. The fluents in the 'fluent' part of the effect are in the next state (time + 1), because they are the result of
        the current action, while all other fluents are in the current state

        Args:
            timestep (int): Current timestep

        Returns:
            List(z3 expression): A list of z3 expressions representing the effects of this action at timestep t
        """
        effects_list = []
        for effect in self.effects:
            effects_list.append(convert_effect_to_Z3(effect, timestep))
        return effects_list

    def __get_causal_axioms_at_t(self, timestep):
        """The causal axioms assert the effects, given the action occurs

        Args:
            timestep (int): Current timestep

        Returns:
            z3 expression: A z3 expression representing the causal axioms of this action at timestep t
        """
        effects_list = self.__get_effects_at_t(timestep)
        axiom = Implies(self.get_action_at_t(timestep), And(effects_list))
        return axiom

    def get_causal_axioms_up_to_t(self, timestep):
        """Generate the list of causal axioms for a problem of length up to timestep t

        Args:
            timestep (int): Final timestep

        Returns:
            List(z3 expression): A list of z3 expressions representing the causal axioms of this action up to timestep t
        """
        if timestep > 0:
            causal_axioms = []
            # We don't consider actions occurring in the final state (at timestep 'timestep') because their effects cannot influence
            # the final state
            for t in range(0, timestep):
                causal_axioms.append(self.__get_causal_axioms_at_t(t))
            return causal_axioms
        return []

    # Returns causal axioms at t without adding to memory. Used for incremental solving.
    def get_causal_axioms_at_t(self, timestep):
        """Get causal axioms for the final timestep

        Args:
            timestep (int): Final timestep

        Returns:
            z3 expression: A z3 expression representing the causal axioms of this action at timestep t
        """
        if timestep > 0:
            # Use timestep - 1 because we don't consider actions in final timestep
            return self.__get_causal_axioms_at_t(timestep - 1)
        return []

    def __get_precondition_constraints_at_t(self, timestep):
        """Generate the precondition constraints for this action at timestep t
        Precondition constraint is: action occuring at timestep t implies preconditions are true at timestep t

        Args:
            timestep (int): Current timestep

        Returns:
            z3 expression: A z3 expression representing the precondition constraints for this action at timestep t
        """
        # First parses FNODEs for each precondition, converts into a list of Z3 statements, then uses And to join them
        precondition_constraint_list = []
        for precondition in self.preconditions:
            precondition_constraint_list.append(
                convert_FNODE_to_Z3(precondition, timestep)
            )
        preconditions = And(precondition_constraint_list)
        # Uses (action@t implies preconditions@t) to bind actions to preconditions
        return Implies(self.get_action_at_t(timestep), preconditions)

    def get_precondition_constraints_up_to_t(self, timestep):
        """Generate the list of precondition constraints for a problem of length up to timestep t

        Args:
            timestep (int): Final timestep

        Returns:
            List(z3 expression): A list of z3 expressions representing the precondition constraints of this action up to timestep t
        """
        precondition_constraints = []
        # We don't consider actions occurring in the final state (at timestep 'timestep') because their effects cannot influence
        # the final state
        for t in range(0, timestep):
            precondition_constraints.append(self.__get_precondition_constraints_at_t(t))
        return precondition_constraints

    # Returns precondition constraints at t without adding to memory. Used for incremental solving.
    def get_precondition_constraints_at_t(self, timestep):
        """Get precondition constraints for the final timestep

        Args:
            timestep (int): Final timestep

        Returns:
            z3 expression: A z3 expression representing the precondition constraints of this action at timestep t
        """
        if timestep > 0:
            # We don't consider actions occurring in the final state (at timestep 'timestep') because their effects cannot influence
            # the final state
            return self.__get_precondition_constraints_at_t(timestep - 1)
        return True

    def get_effected_fluent_basename_condition_tuples(self):
        """Method used to get a list of all effected fluents, and the conditions for the effect
        This is part of the process for sharing the information 'which actions affect which fluents' with fluent objects

        Returns:
            Tuple(String, FNODE): A tuple of a fluent basename, and a FNODE expressing the condition for that fluent being affected
        """
        tuple_list = []
        for effect in self.effects:
            tuple_list.append(create_fluent_condition_tuple(effect))
        return tuple_list

    def deliver_effect_tuples_to_Fluents(self, fluents_list):
        """Method used to deliver effect-fluent tupes for frame-axioms to the appropriate Fluent object. Should only be called once

        Args:
            fluents_list (List(BaseFluent or BaseFluent subclass)): List of fluents

        Raises:
            Exception: Raise an exception if an unknown fluent is affected by an action
        """
        tuple_list = self.get_effected_fluent_basename_condition_tuples()
        for effect_tuple in tuple_list:
            matched_fluent = search_fluents_list(fluents_list, effect_tuple[0])
            if not (matched_fluent is None):
                matched_fluent.add_action_condition(self, effect_tuple[1])
            else:
                print(effect_tuple[0])
                raise Exception(
                    "Fluent name not recognised, has the fluent list been initialised?"
                )
