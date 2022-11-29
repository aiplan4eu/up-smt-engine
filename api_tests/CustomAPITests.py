# Problems for testing engine implementation
from collections import OrderedDict
import unified_planning as up


def CustomAPITests(env, model_to_use):
    emgr = env.expression_manager

    # 1 = Robot problem, modified from original to include more expressions and a function. No meaningful change
    # 2 = Stacking blocks problem, designed for parallelism tests. There are finite different coloured blocks in bags which
    # must be stacked. These blocks may only be stacked onto blocks of the same colour. Each stack has a height property.
    # Goal is to stack each tower up to an arbitrary height.
    # 3 = Multiple piggybanks problem. Three children are trying to split their money between two piggy banks. Each child
    # has a coin jar filled with 1 penny coins.
    # 4 = Russian dolls problem. This problem should result in a 1 step plan for ThereExists parallelism, and a n step plan for
    # any other type, where n = number of dolls.

    if model_to_use == 5:
        # Simple robot problem
        Location = env.type_manager.UserType("Location")
        robot_at = up.model.Fluent(
            "robot_at", env.type_manager.BoolType(), loc=Location
        )
        battery_charge = up.model.Fluent(
            "battery_charge", env.type_manager.RealType(0, 100)
        )
        move = up.model.InstantaneousAction("move", l_from=Location, l_to=Location)
        l_from = move.parameter("l_from")
        l_to = move.parameter("l_to")
        move.add_precondition(emgr.GE(battery_charge, 10))
        move.add_precondition(emgr.Not(emgr.Equals(l_from, l_to)))
        move.add_precondition(robot_at(l_from))
        move.add_precondition(emgr.Not(robot_at(l_to)))
        move.add_effect(robot_at(l_from), False)
        move.add_effect(robot_at(l_to), True)
        move.add_effect(battery_charge, emgr.Minus(battery_charge, 10))
        l1 = up.model.Object("l1", Location)
        l2 = up.model.Object("l2", Location)
        problem = up.model.Problem("robot")
        problem.add_fluent(robot_at)
        problem.add_fluent(battery_charge)
        problem.add_action(move)
        problem.add_object(l1)
        problem.add_object(l2)
        problem.set_initial_value(robot_at(l1), True)
        problem.set_initial_value(robot_at(l2), False)
        problem.set_initial_value(battery_charge, 100)
        problem.add_goal(robot_at(l2))
        problem.add_goal(emgr.Equals(battery_charge, 70))
    elif model_to_use == 4:
        Doll = env.type_manager.UserType("Doll")

        # Fluent function defining if a doll is outside of any other dolls. For a doll to be moved, or filled it msut be 'out'
        doll_params = OrderedDict()
        doll_params["doll_number"] = Doll
        is_out = up.model.Fluent("is_out", env.type_manager.BoolType(), doll_params)

        doll_empty_params = OrderedDict()
        doll_empty_params["doll_number"] = Doll
        is_empty = up.model.Fluent(
            "is_empty", env.type_manager.BoolType(), doll_empty_params
        )

        doll_in_params = OrderedDict()
        doll_in_params["smaller_doll_number"] = Doll
        doll_in_params["larger_doll_number"] = Doll
        is_in = up.model.Fluent("is_in", env.type_manager.BoolType(), doll_in_params)

        # Action to place the smaller doll inside the larger doll
        move_doll = up.model.InstantaneousAction(
            "move_doll", smaller_doll=Doll, larger_doll=Doll
        )
        smaller_doll = move_doll.parameter("smaller_doll")
        larger_doll = move_doll.parameter("larger_doll")

        move_doll.add_precondition(is_out(smaller_doll))
        move_doll.add_precondition(is_out(larger_doll))
        move_doll.add_precondition(is_empty(larger_doll))
        move_doll.add_precondition(emgr.Not(emgr.Equals(larger_doll, smaller_doll)))

        move_doll.add_effect(is_out(smaller_doll), False)
        move_doll.add_effect(is_empty(larger_doll), False)
        move_doll.add_effect(is_in(smaller_doll, larger_doll), True)

        doll_1 = up.model.Object("doll_1", Doll)
        doll_2 = up.model.Object("doll_2", Doll)
        doll_3 = up.model.Object("doll_3", Doll)
        doll_4 = up.model.Object("doll_4", Doll)

        problem = up.model.Problem("nesting_dolls")

        problem.add_fluent(is_out)
        problem.add_fluent(is_empty)
        problem.add_fluent(is_in)

        problem.add_action(move_doll)

        problem.add_object(doll_1)
        problem.add_object(doll_2)
        problem.add_object(doll_3)
        problem.add_object(doll_4)

        problem.set_initial_value(is_out(doll_1), True)
        problem.set_initial_value(is_out(doll_2), True)
        problem.set_initial_value(is_out(doll_3), True)
        problem.set_initial_value(is_out(doll_4), True)

        problem.set_initial_value(is_empty(doll_1), True)
        problem.set_initial_value(is_empty(doll_2), True)
        problem.set_initial_value(is_empty(doll_3), True)
        problem.set_initial_value(is_empty(doll_4), True)

        problem.set_initial_value(is_in(doll_1, doll_1), False)
        problem.set_initial_value(is_in(doll_1, doll_2), False)
        problem.set_initial_value(is_in(doll_1, doll_3), False)
        problem.set_initial_value(is_in(doll_1, doll_4), False)

        problem.set_initial_value(is_in(doll_2, doll_1), False)
        problem.set_initial_value(is_in(doll_2, doll_2), False)
        problem.set_initial_value(is_in(doll_2, doll_3), False)
        problem.set_initial_value(is_in(doll_2, doll_4), False)

        problem.set_initial_value(is_in(doll_3, doll_1), False)
        problem.set_initial_value(is_in(doll_3, doll_2), False)
        problem.set_initial_value(is_in(doll_3, doll_3), False)
        problem.set_initial_value(is_in(doll_3, doll_4), False)

        problem.set_initial_value(is_in(doll_4, doll_1), False)
        problem.set_initial_value(is_in(doll_4, doll_2), False)
        problem.set_initial_value(is_in(doll_4, doll_3), False)
        problem.set_initial_value(is_in(doll_4, doll_4), False)

        # problem.add_goal(is_in(doll_1, doll_2))
        # problem.add_goal(is_in(doll_2, doll_3))
        # problem.add_goal(is_in(doll_3, doll_4))
        problem.add_goal(
            emgr.And(
                emgr.And(is_in(doll_1, doll_2), is_in(doll_2, doll_3)),
                is_in(doll_3, doll_4),
            )
        )

    elif model_to_use == 3:
        Coin_Jar = env.type_manager.UserType("Coin_Jar")
        Piggy_Bank = env.type_manager.UserType("Piggy_Bank")

        jar_params = OrderedDict()
        jar_params["jar_number"] = Coin_Jar
        jar_coins = up.model.Fluent("jar_coins", env.type_manager.IntType(), jar_params)

        piggybank_params = OrderedDict()
        piggybank_params["piggybank_number"] = Piggy_Bank
        piggybank_coins = up.model.Fluent(
            "piggybank_coins", env.type_manager.IntType(), piggybank_params
        )

        # When grounded this becomes 3*2 = 6 grounded actions. Each grounded action shares a precondition with
        # one other action, and an effect with two other actions.
        add_to_piggybank = up.model.InstantaneousAction(
            "add_to_piggybank", c_from=Coin_Jar, p_to=Piggy_Bank
        )
        c_from = add_to_piggybank.parameter("c_from")
        p_to = add_to_piggybank.parameter("p_to")

        add_to_piggybank.add_precondition(emgr.GT(jar_coins(c_from), 0))

        add_to_piggybank.add_effect(
            piggybank_coins(p_to), emgr.Plus(piggybank_coins(p_to), 1)
        )
        add_to_piggybank.add_effect(jar_coins(c_from), emgr.Minus(jar_coins(c_from), 1))

        jar_1 = up.model.Object("jar_1", Coin_Jar)
        jar_2 = up.model.Object("jar_2", Coin_Jar)
        jar_3 = up.model.Object("jar_3", Coin_Jar)

        bank_1 = up.model.Object("bank_1", Piggy_Bank)
        bank_2 = up.model.Object("bank_2", Piggy_Bank)

        problem = up.model.Problem("piggy_banks")

        problem.add_fluent(jar_coins)
        problem.add_fluent(piggybank_coins)

        problem.add_action(add_to_piggybank)

        problem.add_object(jar_1)
        problem.add_object(jar_2)
        problem.add_object(jar_3)
        problem.add_object(bank_1)
        problem.add_object(bank_2)

        problem.set_initial_value(piggybank_coins(bank_1), 0)
        problem.set_initial_value(piggybank_coins(bank_2), 0)

        # Total must be divisible by 2
        problem.set_initial_value(jar_coins(jar_1), 4)
        problem.set_initial_value(jar_coins(jar_2), 5)
        problem.set_initial_value(jar_coins(jar_3), 7)

        problem.add_goal(emgr.Equals(piggybank_coins(bank_1), piggybank_coins(bank_2)))
        problem.add_goal(emgr.Equals(jar_coins(jar_1), 0))
        problem.add_goal(emgr.Equals(jar_coins(jar_2), 0))
        problem.add_goal(emgr.Equals(jar_coins(jar_3), 0))

    elif model_to_use == 2:
        Block_Colour = env.type_manager.UserType("Block_Colour")

        # Include a function just to help test handling of functions
        stack_params = OrderedDict()
        stack_params["stack_colour"] = Block_Colour
        # Function used to find the height of a stack (equals the number of blocks on a stack)
        stack_height = up.model.Fluent(
            "stack_height", env.type_manager.IntType(), stack_params
        )

        # Function used to find the remaining number of blocks in a bag
        bag_params = OrderedDict()
        bag_params["bag_colour"] = Block_Colour
        remaining_in_bag = up.model.Fluent(
            "remaining_in_bag", env.type_manager.IntType(), bag_params
        )

        # Action used to move a block from a bag onto the corresponding stack
        add_to_stack = up.model.InstantaneousAction(
            "add_to_stack", block_colour=Block_Colour
        )
        block_colour = add_to_stack.parameter("block_colour")

        add_to_stack.add_precondition(emgr.GT(remaining_in_bag(block_colour), 0))

        add_to_stack.add_effect(
            stack_height(block_colour), emgr.Plus(stack_height(block_colour), 1)
        )
        add_to_stack.add_effect(
            remaining_in_bag(block_colour),
            emgr.Minus(remaining_in_bag(block_colour), 1),
        )

        red_block = up.model.Object("Red", Block_Colour)
        green_block = up.model.Object("Green", Block_Colour)
        blue_block = up.model.Object("Blue", Block_Colour)

        problem = up.model.Problem("stacking_blocks")

        problem.add_fluent(stack_height)
        problem.add_fluent(remaining_in_bag)

        problem.add_action(add_to_stack)

        problem.add_object(red_block)
        problem.add_object(green_block)
        problem.add_object(blue_block)

        problem.set_initial_value(stack_height(red_block), 0)
        problem.set_initial_value(stack_height(green_block), 0)
        problem.set_initial_value(stack_height(blue_block), 0)

        problem.set_initial_value(remaining_in_bag(red_block), 3)
        problem.set_initial_value(remaining_in_bag(green_block), 5)
        problem.set_initial_value(remaining_in_bag(blue_block), 5)

        problem.add_goal(emgr.Equals(stack_height(red_block), 3))
        problem.add_goal(emgr.Equals(stack_height(green_block), 2))
        problem.add_goal(emgr.Equals(stack_height(blue_block), 5))

    else:
        Location = env.type_manager.UserType("Location")
        Battery = env.type_manager.UserType("Battery")

        params = OrderedDict()
        param_name = "battery_name"
        param_type = Battery
        params[param_name] = param_type
        robot_has_battery = up.model.Fluent(
            "robot_has_battery", env.type_manager.BoolType(), battery=Battery
        )
        # This has been included to prove that Functions can be handled (PDDL functions are converted into API Fluents with parameters)
        specific_battery_charge = up.model.Fluent(
            "specific_battery_charge", env.type_manager.RealType(), params
        )

        robot_at = up.model.Fluent(
            "robot_at", env.type_manager.BoolType(), loc=Location
        )
        battery_charge = up.model.Fluent("battery_charge", env.type_manager.RealType())
        move = up.model.InstantaneousAction(
            "move", l_from=Location, l_to=Location, robot_battery=Battery
        )
        l_from = move.parameter("l_from")
        l_to = move.parameter("l_to")
        robot_battery = move.parameter("robot_battery")

        move.add_precondition(robot_has_battery(robot_battery))

        # Preconditions used to test convert_FNODE_to_z3 implementation:
        # Testing And, Not, Fluent expressions (and object expressions as paramter to fluent)
        move.add_precondition(emgr.And(robot_at(l_from), emgr.Not(robot_at(l_to))))
        # Testing Or, GE, Equals, Variable expressions, Int constant
        move.add_precondition(
            emgr.Or(emgr.GE(battery_charge, 10), emgr.Equals(battery_charge, 100))
        )
        # Testing Implies, LT, LE
        move.add_precondition(
            emgr.Implies(emgr.LT(battery_charge, 100), emgr.LE(battery_charge, 90))
        )
        # Testing IFF
        move.add_precondition(emgr.Iff(robot_at(l_from), emgr.Not(robot_at(l_to))))
        # Testing Bool constant, this is usually compiled away as either redundant, equating to Not(x), or x, or ensuring the preconditions are always unsatisfiable
        move.add_precondition(emgr.Iff(emgr.TRUE(), emgr.TRUE()))
        # For example in this case, in the grounded problems adding False as a precondition removes the affected actions from the problem entirely
        # move.add_precondition(emgr.FALSE())
        # Testing GT, Times, Div
        # When using decimals results in huge numbers, error. TODO investigate this, e.g. 10 * 0.1
        move.add_precondition(emgr.GT(battery_charge, emgr.Times(100, emgr.Div(9, 80))))
        # Testing Plus, Minus
        move.add_precondition(
            emgr.GT(battery_charge, emgr.Plus(battery_charge, emgr.Minus(9, 10)))
        )

        move.add_precondition(emgr.GT(specific_battery_charge(robot_battery), 10))

        move.add_precondition(emgr.GE(battery_charge, 10))
        move.add_precondition(emgr.Not(emgr.Equals(l_from, l_to)))
        move.add_precondition(robot_at(l_from))
        move.add_precondition(emgr.Not(robot_at(l_to)))
        move.add_effect(robot_at(l_from), False)
        move.add_effect(robot_at(l_to), True, emgr.Not(robot_at(l_to)))
        move.add_effect(battery_charge, emgr.Minus(battery_charge, 10))

        move.add_effect(
            specific_battery_charge(robot_battery),
            emgr.Minus(specific_battery_charge(robot_battery), 10),
        )

        l1 = up.model.Object("l1", Location)
        l2 = up.model.Object("l2", Location)

        b2 = up.model.Object("b2", Battery)

        problem = up.model.Problem("robot")
        problem.add_fluent(robot_at)
        problem.add_fluent(battery_charge)

        problem.add_fluent(robot_has_battery)
        problem.add_fluent(specific_battery_charge)

        problem.add_action(move)
        problem.add_object(l1)
        problem.add_object(l2)

        problem.add_object(b2)

        problem.set_initial_value(robot_at(l1), True)
        problem.set_initial_value(robot_at(l2), False)
        problem.set_initial_value(battery_charge, 100)

        problem.set_initial_value(robot_has_battery(b2), True)
        problem.set_initial_value(specific_battery_charge(b2), 100)

        problem.add_goal(robot_at(l2))
        problem.add_goal(emgr.LE(battery_charge, 50))
        problem.add_goal(emgr.Equals(specific_battery_charge(b2), 30))
    return problem
