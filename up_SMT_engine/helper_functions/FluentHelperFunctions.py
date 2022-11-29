from up_SMT_engine.fluents.BaseFluent import BaseFluent
from up_SMT_engine.fluents.R2ExistsFluent import R2ExistsFluent
import itertools
from up_SMT_engine.helper_functions.FNODEHelperFunctions import get_effected_fluent_name


def handle_API_fluent(API_fluent, parallelism, grounded_objects):
    """Handles a single ungrounded api fluent, including grounding into each possible combination without parameters
    and creating a fluent object for each

    Args:
        API_fluent (unified-planning.model.Fluent): unified-planning API based Fluent to be grounded
        parallelism (String): Type of parallelism to use
        grounded_objects (List[unified-planning.model.Object]): List of user objects including all possible parameters for the ungrounded fluent

    Returns:
        BaseFluent or BaseFluent subclass object: Custom fluent object used to generate Frame Axiom constraints, value bound constraints and to handle variables and chained variables for Fluents
    """
    fluents_list = []
    arity = API_fluent.arity
    f_name = API_fluent.name
    # Handle the case if arity = 0
    if arity == 0:
        # No need to consider different combinations for different parameters
        new_fluent_name = f_name
        new_SmtFluent = (
            R2ExistsFluent(new_fluent_name, API_fluent)
            if (parallelism == "relaxed_relaxed_ThereExists")
            else BaseFluent(new_fluent_name, API_fluent)
        )
        fluents_list.append(new_SmtFluent)
        return fluents_list
    # Otherwise there are parameters that must be grounded
    param_values = []
    for i in range(0, arity):
        obj_type = API_fluent.signature[i].type
        object_values = grounded_objects(obj_type)
        obj_list = []
        for value in object_values:
            obj_list.append(value)
        param_values.append(obj_list)
    # We now have [arity] number of lists of parameters, these are the total combinations of parameter values for this fluent
    # To iterate over every combination where one element is chosen from each list I am using the solution from https://stackoverflow.com/a/798893
    param_combinations = list(itertools.product(*param_values))
    for combination in param_combinations:
        new_fluent_name = get_effected_fluent_name(f_name, combination)
        new_SmtFluent = (
            R2ExistsFluent(new_fluent_name, API_fluent)
            if (parallelism == "relaxed_relaxed_ThereExists")
            else BaseFluent(new_fluent_name, API_fluent)
        )
        fluents_list.append(new_SmtFluent)
    return fluents_list
