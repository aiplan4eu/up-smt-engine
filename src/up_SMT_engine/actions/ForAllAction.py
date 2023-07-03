from z3 import And, Not
from up_SMT_engine.helper_functions.ParallelPlanningHelperFunctions import (
    search_FNODE_for_Fluents,
)
from up_SMT_engine.helper_functions.FNODEHelperFunctions import (
    convert_FNODE_to_Z3,
    search_fluents_list,
    create_stated_action_instance,
)
from up_SMT_engine.actions.BaseAction import BaseAction


class ForAllAction(BaseAction):
    """Extension of BaseAction to support ForAll parallelism, allowing all non-interfering actions to be executed within a timestep"""

    def __init__(self, grounded_action):
        super().__init__(grounded_action)
        # For a coarse grained version of parallelism, where shared fluents imply affectation
        # An action has variables in the preconditions, effect preconditions, and effected variables
        # Affectation occurs if another action affects any of these
        # This set is the set of all fluents related to this action
        self.all_fluents = set()

    def __get_matching_fluent_set(self, fluents_list, name_set):
        """Method used to find the set of fluents matching a set of basenames

        Args:
            fluents_list (List(BaseFluent or BaseFluent subclass)): List of fluents
            name_set (Set(String)): Set of basenames

        Returns:
            Set(BaseFluent or BaseFluent subclass): Set of fluents matching the basenames
        """
        fluent_set = set()
        for basename in name_set:
            matched_fluent = search_fluents_list(fluents_list, basename)
            if matched_fluent is not None:
                fluent_set.add(matched_fluent)
        return fluent_set

    def __get_precondition_fluent_names(self):
        """Method used to find all fluents mentioned in preconditions. This is a coarse grained approach because
        each fluent's semantics are discarded
        Used with __get_matching_fluent_set to get matching fluent objects

        Returns:
            Set(String): Set of fluent basenames
        """
        # It's useful to use sets because we don't care about repeated occurences of the same fluent
        # We use syntactic based parallelism, so any semantic information is redundant anyway
        fluent_basename_set = set()
        for precondition in self.preconditions:
            search_FNODE_for_Fluents(precondition, fluent_basename_set)
        return fluent_basename_set

    def __get_effect_precondition_fluent_names(self):
        """Method used to find all fluents mentioned in effect preconditions. This is a coarse grained approach because
        each fluent's semantics are discarded.
        Effects without preconditions are skipped.
        Used with __get_matching_fluent_set to get matching fluent objects

        Returns:
            Set(String): Set of fluent basenames
        """
        fluent_basename_set = set()
        for effect in self.effects:
            if effect.is_conditional():
                effect_precondition = effect.condition
                search_FNODE_for_Fluents(effect_precondition, fluent_basename_set)
        return fluent_basename_set

    def __get_effect_fluent_names(self):
        """Method used to find all fluents affected by an effect, including conditional effects
        This is also a coarse grained approach.
        Used with __get_matching_fluent_set to get matching fluent objects

        Returns:
            Set(String): Set of fluent basenames
        """
        fluent_basename_set = set()
        for effect in self.effects:
            search_FNODE_for_Fluents(effect.fluent, fluent_basename_set)
        return fluent_basename_set

    def populate_all_fluents_set(self, fluents_list):
        """Method used to populate the all_fluents set for an action

        Args:
            fluents_list (List(BaseFluent or BaseFluent subclass)): List of all fluents
        """
        fluent_names = set()
        # Add fluents mentioned in preconditions:
        precondition_fluent_names = self.__get_precondition_fluent_names()
        # Add fluents mentioned in effect preconditions:
        effect_precondition_fluent_names = self.__get_effect_precondition_fluent_names()
        # Add fluents mentioned in effects:
        effect_fluent_names = self.__get_effect_fluent_names()
        # Create set of all fluent names mentioned
        fluent_names = fluent_names.union(effect_fluent_names)
        # Create set of all fluent names mentioned
        fluent_names = fluent_names.union(precondition_fluent_names)
        fluent_names = fluent_names.union(effect_precondition_fluent_names)
        # Create set of all fluents mentioned
        fluents = self.__get_matching_fluent_set(fluents_list, fluent_names)
        self.all_fluents = self.all_fluents.union(fluents)

    def __get_ForAll_constraints_at_time_t(self, timestep):
        """Method used to generate all parallelism constraints for this action for a ForAll encoding
        Affecting actions are found by finding affecting actions of fluents in all_fluents set

        Args:
            timestep (int): Current timestep

        Returns:
            List(z3 expression): List of constraints expressing the ForAll parallelism constraints over simultaneous actions
        """
        constraints = []
        this_action_bool = self.get_action_at_t(timestep)
        for fluent in self.all_fluents:
            for action_tuple in fluent.get_action_conditions():
                if not self == (action_tuple[0]):
                    affecting_action_bool = create_stated_action_instance(
                        action_tuple[0].get_name(), timestep
                    )
                    condition_as_Z3 = convert_FNODE_to_Z3(
                        action_tuple[1], timestep, None
                    )
                    constraints.append(
                        Not(
                            And(
                                this_action_bool, affecting_action_bool, condition_as_Z3
                            )
                        )
                    )
        return constraints

    def get_ForAll_constraints_up_to_t(self, timestep):
        """Method used to get all ForAll parallelism constraints over simultaneous actions up to timestep t

        Args:
            timestep (int): Final timestep

        Returns:
            List(z3 expression): List of constraints expressing the ForAll parallelism constraints over simultaneous actions
        """
        ForAll_constraints = []
        # We don't consider actions occuring at the final timestep
        for t in range(0, timestep):
            ForAll_constraints.append(self.__get_ForAll_constraints_at_time_t(t))
        return ForAll_constraints

    # Returns ForAll parallelism constraints at t without adding to memory. Used for incremental solving.
    def get_ForAll_constraints_at_t(self, timestep):
        """Method used to get all ForAll parallelism constraints over simultaneous actions at timestep t

        Args:
            timestep (int): Current timestep

        Returns:
            List(z3 expression): List of constraints expressing the ForAll parallelism constraints over simultaneous actions
        """
        if timestep > 0:
            return self.__get_ForAll_constraints_at_time_t(timestep - 1)
        return []
