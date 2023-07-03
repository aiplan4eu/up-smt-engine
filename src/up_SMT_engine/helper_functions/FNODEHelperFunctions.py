# Custom functions for conversion to Z3 format
# Helper functions for SmtFluent and SmtAction classes
from z3 import Bool, Real, Int, Implies, And, Or, Not, Exists, ForAll
from unified_planning.model import FNode


def get_fluent_name_at_state(fluent_name, t):
    """Generate the variable name for a Fluent, at timestep t

    Args:
        fluent_name (String): The Fluent's name
        t (int): timestep

    Returns:
        String: variable name for a Fluent, at timestep t
    """
    name = fluent_name + "_@t" + str(t)
    return name


def create_stated_action_instance(action, t):
    """Creates a Bool for the fluent or action at time 't', if a bool with that name exists then returns a reference to that bool

    Args:
        action (String): Action name
        t (int): timestep

    Returns:
        z3.Bool: a Bool for the fluent or action at time 't', if a bool with that name exists then returns a reference to that bool
    """
    name = action + "_@t" + str(t)
    return Bool(name)


def __convert_FNODE_args(args, t, r2exists_tuple=None):
    """Handles recursively calling convert_FNODE_to_Z3 for each FNODE argument

    Args:
        args (FNODE.args): An FNODE's arguments
        t (int): current timestep
        r2exists_tuple (Tuple, optional): Tuple of values required for handling chained variables for relaxed relaxed ThereExists parallelism. Defaults to None.

    Returns:
        Array: Array of z3 expressions
    """
    parsed_args = []
    for argument in args:
        parsed_args.append(convert_FNODE_to_Z3(argument, t, r2exists_tuple))
    return parsed_args


def get_effected_fluent_name(fluent_name, args):
    """If a fluent has arguments then ground it by including arguments in name

    Args:
        fluent_name (String): Ungrounded fluent name
        args (FNODE.args): Parameter values for ungrounded fluent

    Returns:
        String: Grounded fluent name
    """
    if not (args is None) and (len(args) > 0):
        args_string = ""
        for arg in args:
            if isinstance(arg, FNode) and arg.is_object_exp():
                if arg.is_object_exp():
                    args_string = args_string + "_" + arg.object().name
                else:
                    print("Unexpected FNODE parameter type:")
                    print(arg.node_type)
            else:
                args_string = args_string + "_" + arg.name
        name = fluent_name + args_string
    else:
        name = fluent_name
    return name


def createR2ExistsTuple(action_index, is_effect, fluents_list, actions_list):
    """Function for creating a relaxed relaxed ThereExists tuple, used to convey information required to handle chained variables

    Args:
        action_index (int): Index of current action in ordered action list.
        is_effect (bool): If True find chained variable corresponding to the current action
        fluents_list (List): List of fluents
        actions_list (List): Ordered list of Actions

    Returns:
        Tuple: Tuple used to convey information required to handle chained variables
    """
    return (action_index, is_effect, fluents_list, actions_list)


def getR2ExistsTupleValue(info_tuple, val_name):
    """Tuple used to convey information needed for converting an FNODE to z3 for relaxed relaxed ThereExists encoding
    Extra information is needed due to chained variables

        Args:
            info_tuple (Tuple): Tuple used to convey information needed for converting an FNODE to z3 for relaxed relaxed ThereExists encoding
            val_name (String): Information required from tuple

        Returns:
            int or Bool or List: action index, or is_effect, or fluents list, or actions list
    """
    if info_tuple is None:
        return None
    if val_name == "action_index":
        # action_index: The calling action's index. Used for relaxed relaxed ThereExists to find the corresponding chain variable
        return info_tuple[0]
    elif val_name == "is_effect":
        # is_effect: A boolean value. If true we are concerned with the corresponding chain variable to current action. If false we are concerned with the previous chained variable
        return info_tuple[1]
    elif val_name == "fluents_list":
        # fluents_list: A list of all fluents. Used to find chained-variables
        return info_tuple[2]
    elif val_name == "actions_list":
        # actions_list: A list of all actions, in order. Used to find chained-variables
        return info_tuple[3]
    else:
        return None


def __create_stated_fluent_instance(fluent, args, t, r2exists_tuple=None):
    """Creates a Bool, Real or Int for the fluent at time 't', if a value with that name exists then returns a reference
    This effectively both grounds a fluent, and transforms it into a variable representing that fluent at time t.

        Args:
            fluent (FNODE.fluent): Fluent contained by FNODE
            args (FNODE.args): Fluent arguments
            t (int): current timestep
            r2exists_tuple (Tuple, optional): Tuple used to convey information needed for converting an FNODE to z3 for relaxed relaxed ThereExists encoding. Defaults to None.

        Returns:
            z3.Bool or z3.Real or z3.Int: Grounded variable corresponding to fluent at timestep t
    """
    fluent_name = get_effected_fluent_name(fluent.name, args)
    if r2exists_tuple is None:
        name = fluent_name
    else:
        # We must first find the referenced SmtFluent object
        fluents_list = getR2ExistsTupleValue(r2exists_tuple, "fluents_list")
        matching_fluent = next(
            (x for x in fluents_list if (x.check_name_match(fluent_name))), None
        )
        if matching_fluent is None:
            print("Error. Unrecognised fluent instance:")
            print(fluent_name)
            return None
        name = matching_fluent.get_chained_var(r2exists_tuple)
    stated_name = get_fluent_name_at_state(name, t)
    if fluent.type.is_bool_type():
        return Bool(stated_name)
    elif fluent.type.is_real_type():
        return Real(stated_name)
    elif fluent.type.is_int_type():
        return Int(stated_name)


# Convert FNODE to Z3, this is only done when creating a new Z3 problem instance
# Parameters:
# FNODE: AIPLAN4EU API, which uses a directed acyclic graph to represent logical relations between fluents and other objects
# t: the time or state for which the current logical relation will be created
# r2exists_tuple: a tuple containing information required for relaxed relaxed ThereExists encoding. See getR2ExistsTupleValue for more information. None if relaxed relaxed ThereExists is not used
def convert_FNODE_to_Z3(FNODE, t, r2exists_tuple=None):
    """Convert FNODE to z3 expression equivalent

    Args:
        FNODE (FNODE): AIPLAN4EU API object used to express logical relations between fluents and other objects
        t (int): current timestep
        r2exists_tuple (Tuple, optional): Tuple used to convey information needed for converting an FNODE to z3 for relaxed relaxed ThereExists encoding. Defaults to None.

    Raises:
        Exception: Raise exception when FNODE does not match expected logical relation structure

    Returns:
        z3 expression: Equivalent expression expressued using z3
    """

    # Check if FNODE is null (e.g. when argument list is empty)
    # Generally z3 has helpful error messages, and with python's traceback this makes bugfixing simple
    # so error checking code has been only added where necessary
    if FNODE is None:
        return True
    if FNODE.is_and():
        # Z3 permits empty relations, e.g. And(), so do not throw an error
        return And(__convert_FNODE_args(FNODE.args, t, r2exists_tuple))
    elif FNODE.is_or():
        return Or(__convert_FNODE_args(FNODE.args, t, r2exists_tuple))
    elif FNODE.is_not():
        # Z3 does not permit Not(), but throws a helpful error so no need to add error checking code here
        parsed_args = __convert_FNODE_args(FNODE.args, t, r2exists_tuple)
        if len(parsed_args) != 1:
            raise Exception("Unexpected number of variables for Not relation")
        return Not(parsed_args[0])
    elif FNODE.is_implies():
        # Must supply exactly two arguments
        parsed_args = __convert_FNODE_args(FNODE.args, t, r2exists_tuple)
        if len(parsed_args) != 2:
            raise Exception("Unexpected number of variables for implies relation")
        return Implies(parsed_args[0], parsed_args[1])
    elif FNODE.is_iff():
        # Z3 does not have an operator for iff, but can be represented this way:
        parsed_args = __convert_FNODE_args(FNODE.args, t, r2exists_tuple)
        if len(parsed_args) != 2:
            raise Exception("Unexpected number of variables for iff relation")
        return And(
            Implies(parsed_args[0], parsed_args[1]),
            Implies(parsed_args[1], parsed_args[0]),
        )
    elif FNODE.is_exists():
        # Z3 expects a very specific format for the arguments of Exists()
        # TODO consider more thorough error checking
        # This should be grounded out in pre-processing, but worth considering ensuring pre-processing is conducted
        # on an API based input
        return Exists(__convert_FNODE_args(FNODE.args, t, r2exists_tuple))
    elif FNODE.is_forall():
        # Z3 expects a very specific format for the arguments of Forall()
        # TODO consider more thorough error checking
        return ForAll(__convert_FNODE_args(FNODE.args, t, r2exists_tuple))
    elif FNODE.is_fluent_exp():
        # Base case
        return __create_stated_fluent_instance(
            FNODE.fluent(), FNODE.args, t, r2exists_tuple
        )
    elif FNODE.is_constant():
        # Base case for is_bool_constant, is_int_constant, is_real_constant
        # Handle this like a fluent
        return FNODE.constant_value()
    elif FNODE.is_plus():
        # Assert that plus requires exactly two parameters
        parsed_args = __convert_FNODE_args(FNODE.args, t, r2exists_tuple)
        if len(parsed_args) != 2:
            raise Exception("Unexpected number of variables for plus relation")
        return parsed_args[0] + parsed_args[1]
    elif FNODE.is_minus():
        # Assert that minus requires exactly two parameters
        parsed_args = __convert_FNODE_args(FNODE.args, t, r2exists_tuple)
        if len(parsed_args) != 2:
            raise Exception("Unexpected number of variables for minus relation")
        return parsed_args[0] - parsed_args[1]
    elif FNODE.is_times():
        # Assert that times requires exactly two parameters
        parsed_args = __convert_FNODE_args(FNODE.args, t, r2exists_tuple)
        if len(parsed_args) != 2:
            raise Exception("Unexpected number of variables for times relation")
        return parsed_args[0] * parsed_args[1]
    elif FNODE.is_div():
        # Assert that dividing requires exactly two parameters
        parsed_args = __convert_FNODE_args(FNODE.args, t, r2exists_tuple)
        if len(parsed_args) != 2:
            raise Exception("Unexpected number of variables for div relation")
        return parsed_args[0] / parsed_args[1]
    elif FNODE.is_le():
        # Assert that inequality relations requires exactly two parameters
        parsed_args = __convert_FNODE_args(FNODE.args, t, r2exists_tuple)
        if len(parsed_args) != 2:
            raise Exception("Unexpected number of variables for le relation")
        return parsed_args[0] <= parsed_args[1]
    elif FNODE.is_lt():
        # Assert that inequality relations requires exactly two parameters
        parsed_args = __convert_FNODE_args(FNODE.args, t, r2exists_tuple)
        if len(parsed_args) != 2:
            raise Exception("Unexpected number of variables for lt relation")
        return parsed_args[0] < parsed_args[1]
    elif FNODE.is_equals():
        # Assert that equality relations requires exactly two parameters
        parsed_args = __convert_FNODE_args(FNODE.args, t, r2exists_tuple)
        if len(parsed_args) != 2:
            raise Exception("Unexpected number of variables for equals relation")
        return parsed_args[0] == parsed_args[1]
    else:
        print(FNODE.node_type())
        raise Exception("FNODE type not implemented")


def convert_effect_to_Z3(effect, t, r2exists_tuple=None):
    """Function used to convert an Effect object into Z3 equivalent expression for a given time t

    Args:
        effect (unified-planning.Model.effect): The effect to be converted
        t (int): current timestep
        r2exists_tuple (Tuple, optional): Tuple used to convey information needed for converting an FNODE to z3 for relaxed relaxed ThereExists encoding. Defaults to None.

    Returns:
        z3 expression: An action's effect on a fluent expressed as a z3 expression at timestep t
    """
    effect_value = effect.value
    # Create a tuple allowing reference to previous chained variables. Used for new value calculation, and conditions
    r2exists_non_effect_tuple = None
    if r2exists_tuple is None:
        # The effected fluent is in the next state, this is not guaranteed to be a simple fluent because it is an FNODE structure
        fluent = convert_FNODE_to_Z3(effect.fluent, (t + 1), None)
        # Get old value of the fluent to be incremented/decremented
        if effect.is_increase() or effect.is_decrease():
            old_fluent = convert_FNODE_to_Z3(effect.fluent, (t), None)
        # The resulting value can only refer to constants, or values in the current state
        value = convert_FNODE_to_Z3(effect_value, (t), None)
    else:
        r2exists_non_effect_tuple = createR2ExistsTuple(
            r2exists_tuple[0], False, r2exists_tuple[2], r2exists_tuple[3]
        )
        # The effected fluent is in the current state, using the assigned chained variable
        fluent = convert_FNODE_to_Z3(effect.fluent, (t), r2exists_tuple)
        # Get old value of the fluent to be incremented/decremented
        if effect.is_increase() or effect.is_decrease():
            old_fluent = convert_FNODE_to_Z3(
                effect.fluent, (t), r2exists_non_effect_tuple
            )
        # The resulting value can only refer to constants, or values in the current state
        value = convert_FNODE_to_Z3(effect_value, (t), r2exists_non_effect_tuple)
    # Build effect operation
    if effect.is_assignment():
        operation = fluent == value
    elif effect.is_increase():
        operation = fluent == (old_fluent + value)
    else:
        # Effect causes a decrement in value
        operation = fluent == (old_fluent - value)
    # Handle the effect's precondition
    if effect.is_conditional():
        # The condition is in the current state
        condition = convert_FNODE_to_Z3(
            effect.condition, (t), r2exists_non_effect_tuple
        )
        return Implies(condition, operation)
    else:
        return operation


def get_base_fluent_name(FNODE):
    """Function used to return a grounded fluent name, given it is the correct FNODE type

    Args:
        FNODE (FNODE): unified-planning FNODE

    Raises:
        Exception: Raise an exception if FNODE is not a fluent

    Returns:
        String: Grounded fluent name
    """
    if FNODE.is_fluent_exp():
        return get_effected_fluent_name(FNODE.fluent().name, FNODE.args)
    else:
        raise Exception("Unexpected FNODE type")


def create_fluent_condition_tuple(effect):
    """Function used to extract and package useful effect information before passing to a Fluent class for
    generating frame axiom constraints

    Args:
        effect (unified-planning.Model.effect): Effect, changing a fluent value, with optional condition

    Returns:
        Tuple: (grounded fluent basename, effect condition as FNODE expression)
    """
    fluent_basename = get_base_fluent_name(effect.fluent)
    API_condition = None
    if effect.is_conditional():
        API_condition = effect.condition
    return (fluent_basename, API_condition)


def search_fluents_list(fluents_list, fluent_basename):
    """Return fluent object corresponding to basename, returns fluent if matched, None if no match

    Args:
        fluents_list (List(BaseFluent or BaseFluent subclass)): List of fluents
        fluent_basename (String): Name of fluent

    Returns:
        BaseFluent or BaseFluent subclass: Fluent corresponding to the fluent basename
    """
    for fluent in fluents_list:
        if fluent.check_name_match(fluent_basename):
            return fluent
    return None
