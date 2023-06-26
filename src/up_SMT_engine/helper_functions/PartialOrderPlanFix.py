import unified_planning as up
import unified_planning.plans as plans
from typing import Callable, Dict, List, Optional


def custom_replace_action_instances(
    plan,
    replace_function: Callable[
        ["plans.plan.ActionInstance"], Optional["plans.plan.ActionInstance"]
    ],
) -> "plans.plan.Plan":
    """
    Custom function for replacing action instances of a partial_order_plan
    The original function has two errors. First for plans of length 1 with no successors the plan is discarded.
    Second the successors are duplicated.
    Returns a new `PartialOrderPlan` where every `ActionInstance` of the current plan is replaced using the given `replace_function`.

    :param replace_function: The function that applied to an `ActionInstance A` returns the `ActionInstance B`; `B`
        replaces `A` in the resulting `Plan`.
    :return: The `PartialOrderPlan` where every `ActionInstance` is replaced using the given `replace_function`.
    """
    new_adj_list: Dict[
        "plans.plan.ActionInstance", List["plans.plan.ActionInstance"]
    ] = {}
    # The approach used is to generate equivalent keys for all nodes first, then add successors later.
    # This is done because successors need to map exactly to the corresponding node object, and so
    # the replace_function can only be called once per unique object.

    new_key_dict = {}
    # First add all replaced nodes as keys, but leave successors for later
    for node in plan._graph.nodes:
        key = replace_function(node)
        if key is not None:
            new_key_dict[node] = key
    # Populate the new adjacency dictionary with the replaced action instances
    # It is easier to match instances using the adjacency dict
    for node in plan._graph.nodes:
        if node in new_key_dict:
            key = new_key_dict[node]
            replaced_neighbors = []
            for successor in plan._graph.neighbors(node):
                if successor in new_key_dict:
                    replaced_neighbors.append(new_key_dict[successor])
            if len(replaced_neighbors) > 0:
                new_adj_list[key] = replaced_neighbors
            # This is the only functional change to this part of the code. Without this
            # else plans of length 1 are lost
            else:
                new_adj_list[key] = []
    new_env = plan._environment
    for ai in new_adj_list.keys():
        new_env = ai.action.env
        break
    return up.plans.PartialOrderPlan(new_adj_list, new_env)
