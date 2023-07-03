from z3 import And, Or, Implies, Real, Int, Bool
from up_SMT_engine.helper_functions.FNODEHelperFunctions import (
    convert_FNODE_to_Z3,
    create_stated_action_instance,
)


class BaseFluent:
    """Custom fluent object used to generate Frame Axiom constraints, value bound constraints and to handle variables and chained variables for Fluents.
    Able to handle all methods for sequential, and therefore most parallel plans
    """

    def __init__(self, name, API_fluent):
        self.base_name = name
        API_type = API_fluent.type
        if API_type.is_real_type():
            self.lower_bound = API_type.lower_bound
            self.upper_bound = API_type.upper_bound
            self.fluent_type = "Real"
        elif API_type.is_int_type():
            self.lower_bound = API_type.lower_bound
            self.upper_bound = API_type.upper_bound
            self.fluent_type = "Int"
        else:
            self.lower_bound = None
            self.upper_bound = None
            self.fluent_type = "Bool"
        # Used for creating frame axiom constraints
        self.action_condition_pairs = set()

    def check_name_match(self, name):
        """Return true/false if name matches this fluent's base name

        Args:
            name (String): name to match

        Returns:
            Bool: True if match, False otherwise
        """
        return self.base_name == name

    # Override equality method for use in sets
    def __eq__(self, other):
        """Return true/false if this fluent is the same fluent as the other fluent

        Args:
            other (BaseFluent): Other BaseFluent to compare with

        Returns:
            Bool: True if match, False otherwise
        """
        try:
            if isinstance(other, BaseFluent) or issubclass(other, BaseFluent):
                return self.check_name_match(other.base_name)
            return False
        except:
            return False

    def __hash__(self):
        return hash(repr(self))

    def __get_predicate_at_t(self, timestep):
        """Method used to generate this fluent's Bool representing its state at t = 'timestep'

        Args:
            timestep (int): Timestep value for the variable

        Returns:
            z3.Real or z3.Int or z3.Bool: Variable expression of value of Fluent at timestep t
        """
        predicate_name = self.base_name + "_@t" + str(timestep)
        if self.fluent_type == "Real":
            predicate = Real(predicate_name)
        elif self.fluent_type == "Int":
            predicate = Int(predicate_name)
        else:
            predicate = Bool(predicate_name)
        return predicate

    def get_fluents_up_to_t(self, timestep):
        """Method for finding the list of state predicates corresponding to this fluent's variables in each state from t = 0, to t = timestep

        Args:
            timestep (int): Last timestep

        Returns:
            List: List of variables expressing this fluent's values from timestep 0 to timestep
        """
        fluent_array = []
        for t in range(0, timestep + 1):
            fluent_array.append(self.__get_predicate_at_t(t))
        return fluent_array

    def add_action_condition(self, action, condition):
        """Used by actions to register as effecting this fluent

        Args:
            action (BaseAction or BaseAction subclass): Action which may affect this fluent when executed
            condition (FNODE): FNODE expression for action's effect condition affecting this fluent
        """
        action_condition_tuple = (action, condition)
        self.action_condition_pairs.add(action_condition_tuple)

    def get_action_conditions(self):
        """Return set of actions that may affect this fluent, with their conditions

        Returns:
            List: List of (BaseAction or BaseAction subclass, FNODE) pairs. The Action is an action which affects this fluent as part of its effects. The FNODE is the condition of the effect, if it has one
        """
        return self.action_condition_pairs

    def __get_bound_constraints_at_t(self, timestep, is_lower):
        """Method used to generate bound constraints for either upper, or lower bound at timestep t

        Args:
            timestep (int): Timestep value
            bound (Numeric type): upper or lower bound value
            is_lower (bool): True if is lower, False if is upper bound

        Returns:
            _type_: _description_
        """
        pred_at_t = self.__get_predicate_at_t(timestep)
        bound = self.lower_bound if (is_lower) else self.upper_bound
        if is_lower:
            return pred_at_t >= bound
        else:
            return pred_at_t <= bound

    def get_bound_constraints_up_to_t(self, timestep):
        """Method used to generate all bound constraints up to timestep t, can be called if no constraints are needed

        Args:
            timestep (int): Last timestep value

        Returns:
            List: List of bound constraints up to t
        """
        if self.lower_bound or self.upper_bound is not None:
            bound_constraints = []
            if self.lower_bound is not None:
                for t in range(0, timestep + 1):
                    bound_constraints.append(self.__get_bound_constraints_at_t(t, True))
            if self.upper_bound is not None:
                for t in range(0, timestep + 1):
                    bound_constraints.append(
                        self.__get_bound_constraints_at_t(t, False)
                    )
            return bound_constraints
        return None

    def get_bound_constraints_at_t(self, timestep):
        """Returns bound constraints at t. Used for incremental solving.

        Args:
            timestep (int): current timestep

        Returns:
            z3 expression: z3 expression for bound constraints at timestep t
        """
        if self.lower_bound or self.upper_bound is not None:
            bound_constraints = []
            if self.lower_bound is not None:
                bound_constraints.append(
                    self.__get_bound_constraints_at_t(timestep, True)
                )
            if self.upper_bound is not None:
                bound_constraints.append(
                    self.__get_bound_constraints_at_t(timestep, False)
                )
            return And(bound_constraints)
        return True

    def __generate_frame_axiom_constraints_at_t(self, timestep):
        """Method used internally to generate the frame axiom constraints for this fluent at time timestep

        Args:
            timestep (int): current timestep

        Returns:
            z3 expression: z3 expression for Frame axiom constraints at timestep t
        """
        current_state = self.__get_predicate_at_t(timestep)
        future_state = self.__get_predicate_at_t(timestep + 1)
        # No actions effect this fluent, so assert no changes of value between states
        if len(self.action_condition_pairs) == 0:
            # return Implies((current_state != future_state), False)
            # Same meaning, but shorter
            return current_state == future_state
        constraints = []
        # Actions exist that effect this fluent, assert a change of value implies the action (and effect condition)
        for action_tuple in self.action_condition_pairs:
            action_bool = create_stated_action_instance(
                action_tuple[0].get_name(), timestep
            )
            constraint_as_Z3 = convert_FNODE_to_Z3(action_tuple[1], timestep)
            constraints.append(And(constraint_as_Z3, action_bool))
        # Essentially: change in value implies at least one (action, precondition) tuple is true
        return Implies((current_state != future_state), Or(constraints))

    def generate_frame_axiom_constraints_up_to_t(self, timestep):
        """Generate frame axiom constraints for each timestep point up to t

        Args:
            timestep (int): final timestep

        Returns:
            List(z3 expression): List of z3 expressions for frame axiom constraints up to timestep t
        """
        constraints_list = []
        # Only need to handle frame axiom constraints for states 1 ... (n - 1), where n is final state
        # Because we don't care what happens in state n + 1
        for t in range(0, timestep):
            axiom = self.__generate_frame_axiom_constraints_at_t(t)
            constraints_list.append(axiom)
        return constraints_list

    def generate_frame_axiom_constraints_at_t(self, timestep):
        """Returns frame axioms at t. Used for incremental solving.

        Args:
            timestep (int): current timestep

        Returns:
            z3 expression: z3 expressions for frame axiom constraints at timestep t
        """
        # No frame axiom constraints necessary when there is only one timestep
        if timestep == 0:
            return True
        # Only need to handle frame axiom constraints for states 1 ... (n - 1), where n is final state
        # Because we don't care what happens in state n + 1
        return self.__generate_frame_axiom_constraints_at_t(timestep - 1)
