# Regex used for finding action base names
import re

# unified_planning Used for converting the SAT model into a plan
import unified_planning as up
from z3 import BoolRef, FuncDeclRef


def get_z3_FuncDecl_name(obj):
    """Function used to get the string name of a variable in the Model result

    Args:
        obj: object to check

    Returns:
        String: The object's name
    """
    if type(obj) == FuncDeclRef:
        return obj.name()
    else:
        return None


def split_stated_action_name(action_name):
    """Splits action name from 'action_@tx' to ['action', 'x'], giving the action basename, and time of execution

    Args:
        action_name (String): An action basename with time of execution

    Returns:
        String: The action basename
    """
    return re.split("_@t", action_name)


def get_action_by_name(name, grounded_actions):
    """Function used to find corresponding action to string action name in grounded_actions, if one exists

    Args:
        name (String): Action name
        grounded_actions (List of InstantaneousAction objects): List of grounded actions

    Returns:
        InstantaneousAction: The grounded InstantaneousAction corresponding to the name
    """
    for action in grounded_actions:
        if name == action.name:
            return action
    return None


def get_goal_actions_list(solution, grounded_actions, plan_len, parallelism):
    """Using the full z3 solution model compare each True boolean variable against the name of a grounded_action
    If the names match then the variable shows that action is executed at time x, given the variable name is 'action_@tx'
    Iterate over each variable in the model, setting the corresponding ground action to index x in the plan array
    Return the plan array
    'solution' parameter should be a Solver.model() object

        Args:
            solution (z3.Model): The model satisfying the problem as SMT
            grounded_actions (List of InstantaneousAction objects): List of grounded actions
            plan_len (int): Plan length
            parallelism (String): The type of parallelism chosen

        Returns:
            List or List of sets: If sequential this returns a list of actions in the order the appear in the plan. Otherwise this returns a list of sets, each set corresponding to the parallel actions taken at that timestep
    """
    # Get TRUE booleans from solution, these will include the actions we want
    true_values = []
    for val in solution:
        if type(solution[val]) == BoolRef and solution[val]:
            true_values.append(val)
    # if the plan is parallel we need a list of sets of actions, otherwise just a list
    if parallelism == "sequential":
        # Plan list, consisting of actions from grounded_actions where index corresponds to execution order
        plan = [None] * plan_len
    else:
        plan = [set() for _ in range(plan_len)]
    for val in true_values:
        val_name = get_z3_FuncDecl_name(val)
        split_name = split_stated_action_name(val_name)
        ground_name = split_name[0]
        state = split_name[1]
        matched_action = get_action_by_name(ground_name, grounded_actions)
        if matched_action is not None:
            if parallelism == "sequential":
                plan[int(state)] = up.plans.ActionInstance(matched_action)
            else:
                plan[int(state)].add(up.plans.ActionInstance(matched_action))
    return plan


def find_action_in_ordered_list(action_instance, ordered_list):
    """Custom index finding function, for finding the action of an action_instance in an ordered list
    Uses the action's name to find the action

        Args:
            action_instance (ActionInstance): a unified-planning Action instance
            ordered_list (List): ordered list of actions

        Returns:
            int: action index
    """
    name = action_instance.action.name
    for action in ordered_list:
        if action.check_name_match(name):
            return ordered_list.index(action)
    print("Error. Action not found.")
    return -1


def convert_action_sequence_to_plan(
    actions, parallelism, ForAll_get_sets, ordered_list
):
    """Function used to convert a list or list of sets to a corresponding unified-planning Plan object.

    Args:
        actions (list or list of sets): list or list of sets of InstantaneousActions
        parallelism (String): Choice of parallelism
        ForAll_get_sets (Boolean): True if the user wants to maintain the sets of parallel actions
        ordered_list (list): Ordered list of actions

    Returns:
        PartialOrderPlan or SequentialPlan: If ForAll_get_sets is true we return a PartialOrderPlan. Otherwise we return a SequentialPlan
    """
    if parallelism == "sequential":
        # The candidate plan, initially empty
        plan = up.plans.SequentialPlan([])
        for action in actions:
            plan.actions.append(action)
        return plan
    elif parallelism == "ForAll" and ForAll_get_sets:
        # Represent parallel plans as a partial order plan, this plan is initialised after full construction
        # of the plan as a dictionary
        plan_dict = {}
        plan_len = len(actions)
        for i in range(0, plan_len):
            action_set = actions[i]
            for action in action_set:
                affected_list = []
                if i + 1 < plan_len:
                    other_action_sets = actions[i + 1]
                    for other_actions in other_action_sets:
                        affected_list.append(other_actions)
                plan_dict[action] = affected_list
        return up.plans.PartialOrderPlan(plan_dict)
    elif (
        parallelism == "ForAll"
        or parallelism == "ThereExists"
        or parallelism == "relaxed_relaxed_ThereExists"
    ):
        # Convert parallel action sets into sequential plan, using total ordering assigned
        # We need to iterate over each set, turning them into ordered sub-plans
        # For each set. Iterate while action has members. Iterate over each member, remembering
        plan = up.plans.SequentialPlan([])
        for action_set in actions:
            # Iterate over every item in action set
            for _ in range(0, len(action_set)):
                earliest_action = None
                earliest_action_index = -1
                for action in action_set:
                    if earliest_action is None:
                        earliest_action = action
                        earliest_action_index = find_action_in_ordered_list(
                            earliest_action, ordered_list
                        )
                    else:
                        current_action_index = find_action_in_ordered_list(
                            action, ordered_list
                        )
                        if earliest_action_index > current_action_index:
                            earliest_action = action
                            earliest_action_index = find_action_in_ordered_list(
                                earliest_action, ordered_list
                            )
                plan.actions.append(earliest_action)
                action_set.remove(earliest_action)
        return plan
    else:
        print("Error. Parallelism type not currently handled: ")
        print(parallelism)
