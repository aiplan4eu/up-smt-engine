from z3 import And, Implies
from up_SMT_engine.helper_functions.FNODEHelperFunctions import (
    convert_FNODE_to_Z3,
    createR2ExistsTuple,
    convert_effect_to_Z3,
)
from up_SMT_engine.actions.BaseAction import BaseAction

# Represents an action used for relaxed relaxed ThereExists parallelism
class R2ExistsAction(BaseAction):
    """Extension of BaseAction to support relaxed relaxed ThereExists parallelism, allowing actions to be enabled, and change other action effects within a timestep"""

    def __get_effects_at_t(self, timestep, r2exists_tuple):
        """Each effect has three FNODE structures, the condition (optional, makes effect conditional), fluent (the stated variable to be changed)
        and the value (the new fluent value). These are separately converted into Z3, and returned as Implies(condition, (fluent == value))
        These statements are And'd together, as the set of effects of the action.
        n.b. The fluents in the 'fluent' part of the effect are in the next state (timestep + 1), because they are the result of
        the current action, while all other fluents are in the current state

        Args:
            timestep (int): current timestep
            r2exists_tuple (Tuple, optional): Tuple used to convey information needed for handling chained variables. Defaults to None.

        Returns:
            List(z3 expression): List of expressions for action effects
        """
        effects_list = []
        for effect in self.effects:
            effects_list.append(convert_effect_to_Z3(effect, timestep, r2exists_tuple))
        return effects_list

    def __get_causal_axioms_at_t(self, timestep, r2exists_tuple):
        """The causal axioms assert the effects, given the action occurs

        Args:
            timestep (int): Current timestep
            r2exists_tuple (Tuple, optional): Tuple used to convey information needed for handling chained variables. Defaults to None.

        Returns:
            z3 expression: A z3 expression representing the causal axioms of this action at timestep t
        """
        effects_list = self.__get_effects_at_t(timestep, r2exists_tuple)
        axiom = Implies(self.get_action_at_t(timestep), And(effects_list))
        return axiom

    def get_causal_axioms_up_to_t(self, timestep, fluents_list, actions_list):
        """Generate the list of causal axioms for a problem of length up to timestep t

        Args:
            timestep (int): Final timestep
            fluents_list (List(BaseFluent or BaseFluent subclass)): List of fluents
            actions_list (List(BaseAction or BaseAction subclass)): List of actions

        Returns:
            List(z3 expression): A list of z3 expressions representing the causal axioms of this action up to timestep t
        """
        if timestep > 0:
            causal_axioms = []
            # Tuple used to reference chained variables if relaxed relaxed ThereExists parallelism is used
            r2exists_tuple = None
            r2exists_tuple = createR2ExistsTuple(
                actions_list.index(self), True, fluents_list, actions_list
            )
            # We don't consider actions occurring in the final state (at timestep 'timestep') because their effects cannot influence
            # the final state
            for t in range(0, timestep):
                causal_axioms.append(self.__get_causal_axioms_at_t(t, r2exists_tuple))
            return causal_axioms
        return []

    def get_causal_axioms_at_t(self, timestep, fluents_list, actions_list):
        """Get causal axioms for a timestep

        Args:
            timestep (int): a timestep
            fluents_list (List(BaseFluent or BaseFluent subclass)): List of fluents
            actions_list (List(BaseAction or BaseAction subclass)): List of actions

        Returns:
            z3 expression: A z3 expression representing the causal axioms of this action at timestep t
        """
        if timestep > 0:
            # Tuple used to reference chained variables if relaxed relaxed ThereExists parallelism is used
            r2exists_tuple = None
            r2exists_tuple = createR2ExistsTuple(
                actions_list.index(self), True, fluents_list, actions_list
            )
            # Use timestep - 1 because we don't consider actions in final timestep
            return self.__get_causal_axioms_at_t(timestep - 1, r2exists_tuple)
        return []

    def __get_precondition_constraints_at_t(self, timestep, r2exists_tuple):
        """Generate the precondition constraints for this action at timestep t
        Precondition constraint is: action occuring at timestep t implies preconditions are true at timestep t

        Args:
            timestep (int): Current timestep
            r2exists_tuple (Tuple, optional): Tuple used to convey information needed for handling chained variables. Defaults to None.

        Returns:
            z3 expression: A z3 expression representing the precondition constraints for this action at timestep t
        """
        # First parses FNODEs for each precondition, converts into a list of Z3 statements, then uses And to join them
        precondition_constraint_list = []
        for precondition in self.preconditions:
            precondition_constraint_list.append(
                convert_FNODE_to_Z3(precondition, timestep, r2exists_tuple)
            )
        preconditions = And(precondition_constraint_list)
        # Uses (action@t implies preconditions@t) to bind actions to preconditions
        return Implies(self.get_action_at_t(timestep), preconditions)

    def get_precondition_constraints_up_to_t(
        self, timestep, fluents_list, actions_list
    ):
        """Generate the list of precondition constraints for a problem of length up to timestep t

        Args:
            timestep (int): Final timestep
            fluents_list (List(BaseFluent or BaseFluent subclass)): List of fluents
            actions_list (List(BaseAction or BaseAction subclass)): List of actions

        Returns:
            List(z3 expression): A list of z3 expressions representing the precondition constraints of this action up to timestep t
        """
        precondition_constraints = []
        # Tuple used to reference chained variables if relaxed relaxed ThereExists parallelism is used
        r2exists_tuple = createR2ExistsTuple(
            actions_list.index(self), False, fluents_list, actions_list
        )
        # We don't consider actions occurring in the final state (at timestep 'timestep') because their effects cannot influence
        # the final state
        for t in range(0, timestep):
            precondition_constraints.append(
                self.__get_precondition_constraints_at_t(t, r2exists_tuple)
            )
        return precondition_constraints

    def get_precondition_constraints_at_t(self, timestep, fluents_list, actions_list):
        """Get precondition constraints for a timestep

        Args:
            timestep (int): a timestep
            fluents_list (List(BaseFluent or BaseFluent subclass)): List of fluents
            actions_list (List(BaseAction or BaseAction subclass)): List of actions

        Returns:
            z3 expression: A z3 expression representing the precondition constraints of this action at timestep t
        """
        if timestep > 0:
            # Tuple used to reference chained variables if relaxed relaxed ThereExists parallelism is used
            r2exists_tuple = createR2ExistsTuple(
                actions_list.index(self), False, fluents_list, actions_list
            )
            # We don't consider actions occurring in the final state (at timestep 'timestep') because their effects cannot influence
            # the final state
            return self.__get_precondition_constraints_at_t(
                timestep - 1, r2exists_tuple
            )
        return True
