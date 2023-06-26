# Parallel Planning functions
from up_SMT_engine.helper_functions.FNODEHelperFunctions import get_effected_fluent_name


def __convert_FNODE_args_for_Fluents(args, basename_set):
    """Handles recursively calling search_FNODE_for_Fluents for each FNODE argument

    Args:
        args (list): List of the current FNODE's arguments
        basename_set (set(String)): The set of basenames for each fluent found

    Returns:
        set(String): The set of basenames for each fluent found
    """
    for argument in args:
        search_FNODE_for_Fluents(argument, basename_set)
    return basename_set


def search_FNODE_for_Fluents(FNODE, basename_set):
    """Used to search for fluents, returns a set of basenames, which can then be used to match with the corresponding fluent objects
    Should only be called after convert_FNODE_to_Z3 has been called on all FNODEs

        Args:
            FNODE (unified-planning FNODE): The current FNODE being searched
            basename_set (set(String)): The set of basenames for each fluent found

        Returns:
            None: Skip if a dead end has been found
    """
    # Check if FNODE is null (e.g. when argument list is empty)
    if FNODE is None:
        # Do nothing
        return None
    if FNODE.is_fluent_exp():
        # Base case
        fluent = FNODE.fluent()
        name = get_effected_fluent_name(fluent.name, FNODE.args)
        basename_set.add(name)
    elif FNODE.is_constant():
        # Base case
        # Do nothing
        return None
    else:
        # This function will always be called after all relevant FNODES have been parsed by convert_FNODE_to_Z3, so any unexpected types will have been caught already
        basename_set = basename_set.union(
            __convert_FNODE_args_for_Fluents(FNODE.args, basename_set)
        )
