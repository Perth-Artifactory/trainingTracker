import logging
import os
from copy import deepcopy as copy
from datetime import datetime, timedelta
from pprint import pprint
from typing import Any, Literal
import json

import requests

from . import blocks, misc, slackUtils, machines, tidyhq
from editable_resources import strings

# Set up logging

logger = logging.getLogger("formatters")


def home(user, config, client, cache, machine_raw):
    complete_section_emoji_map = {
        "3d": ":3d-printer:",
        "air": ":dash:",
        "wood": ":deciduous_tree:",
        "metal": ":compression:",
        "electronics": ":bulb:",
        "laser": ":laser_beam:",
        "craft": ":sewing_needle:",
        "fire": ":fire:",
        "org": ":artifactory2-black-fringed:",
    }

    block_list: list[dict] = []

    # Header
    block_list = home_header(block_list)

    # low risk info
    block_list = home_low_risk(block_list)

    # Medium risk info
    block_list = home_medium_risk(block_list)

    # High risk info
    block_list = home_high_risk(block_list)

    # Check training
    block_list = slackUtils.add_block(
        block_list=block_list,
        block=slackUtils.inject_text(
            block_list=blocks.header, text=strings.check_training_header
        ),
    )

    # get user authed machines
    authed_machines = machines.user(
        id=user, cache=cache, machines=machine_raw, config=config
    )

    # If the user is not authed for any machines, authed_machines will be None. We want it to be an empty dict instead so it doesn't break iteration
    if not authed_machines:
        authed_machines = {}

    # Calculate buttons
    button_actions = copy(blocks.actions)
    button_actions["block_id"] = "check_training"

    # Get tool categories
    tool_categories = machines.all(cache=cache, config=config, machines=machine_raw)

    for category in tool_categories:
        # Calculate total while accounting for excluded machines and probationary sign offs
        total = 0
        for machine in tool_categories[category]:
            if machine not in machine_raw.get("exclude", []):
                if (
                    machine.get("level", "⚪") == "🅿️"
                    and machine not in authed_machines[category]
                ):
                    continue

                total += 1

        # Create button text
        if authed_machines:
            if category in authed_machines:
                button_text = f"{category.capitalize()} ({len(authed_machines[category])}/{total})"
                if len(authed_machines[category]) == total:
                    button_text += (
                        f" {complete_section_emoji_map.get(category.lower(), ':star:')}"
                    )
            else:
                button_text = f"{category.capitalize()} (0/{total})"
        else:
            button_text = (
                f"{category.capitalize()} (0/{len(tool_categories[category])})"
            )

        button_actions = slackUtils.inject_button(
            actions=button_actions,
            text=button_text,
            value=category,
            action_id="category-" + category,
        )

    # Calculate button text for category that includes all tools

    # Create deduplicated list of all machines in all categories with list comprehension and excluding excluded machines
    all_machines = []

    # Generate flattened list of all machines
    all_machines_flat = list(
        set(
            [
                machine["id"]
                for category in tool_categories
                if category != "exclude"
                for machine in tool_categories[category]
                if machine not in machine_raw.get("exclude", [])
            ]
        )
    )

    # Count all authed machines
    if not authed_machines:
        authed_machines_flat = []
    else:
        authed_machines_flat = list(
            set(
                [
                    machine
                    for category in authed_machines
                    for machine in authed_machines[category]
                    if machine not in machine_raw.get("exclude", [])
                ]
            )
        )

    # Remove probationary sign offs from all machines if they're not present in auth'd machines
    for machine in all_machines_flat:
        machine_info = tidyhq.get_group_info(id=machine, cache=cache, config=config)

        if (
            machine_info.get("level", "⚪") == "🅿️"
            and machine not in authed_machines_flat
        ):
            all_machines_flat.remove(machine)

    if authed_machines:
        button_text = f"All ({len(authed_machines_flat)}/{len(all_machines_flat)})"
        if len(authed_machines_flat) >= len(all_machines_flat):
            button_text += " :partyparrot:"
    else:
        button_text = f"All (0/{len(all_machines_flat)})"

    category = "all"
    button_actions = slackUtils.inject_button(
        actions=button_actions,
        text=button_text,
        value=category,
        action_id="category-" + category,
    )

    block_list = slackUtils.add_block(block_list=block_list, block=button_actions)

    if not authed_machines:
        block_list = slackUtils.add_block(
            block_list=block_list,
            block=slackUtils.inject_text(
                block_list=blocks.context, text=strings.no_tools_all
            ),
        )

    block_list = slackUtils.add_block(block_list=block_list, block=blocks.divider)

    # Requesting training
    block_list = home_requesting_training(block_list)

    # Admin

    # Skip checking trainer status for users with no sign offs since they can't be trainers and usergroups.list is rate limited
    if authed_machines:
        # Check if the user is a trainer
        if slackUtils.is_trainer(user=user, client=client, config=config):
            trainer_blocks = []

            # Add trainer explainer
            trainer_blocks = slackUtils.add_block(
                block_list=trainer_blocks,
                block=slackUtils.inject_text(
                    block_list=blocks.header, text=strings.trainer_header
                ),
            )
            trainer_blocks = slackUtils.add_block(
                block_list=trainer_blocks,
                block=slackUtils.inject_text(
                    block_list=blocks.text, text=strings.trainer_explainer
                ),
            )

            # Add trainer buttons
            button_actions = copy(blocks.actions)
            button_actions["block_id"] = "trainer_home"
            button_actions = slackUtils.inject_button(
                actions=button_actions,
                text="Select user",
                value="trainer-select",
                action_id="trainer-select",
            )
            button_actions = slackUtils.inject_button(
                actions=button_actions,
                text="Search by tool",
                value="trainer-check_tool_training",
                action_id="trainer-check_tool_training",
            )
            button_actions = slackUtils.inject_button(
                actions=button_actions,
                text="Refresh from TidyHQ",
                value="trainer-refresh",
                action_id="trainer-refresh",
            )
            trainer_blocks = slackUtils.add_block(
                block_list=trainer_blocks, block=button_actions
            )

            trainer_blocks = slackUtils.add_block(
                block_list=trainer_blocks, block=blocks.divider
            )

            block_list = trainer_blocks + block_list

    return block_list


def authed_machines_modal(
    user: str, config: dict, client, cache: dict, categories: list, machine_list: dict
):
    # Generate list of machines
    all_machines = machines.all(cache=cache, config=config, machines=machine_list)
    authed_machines = machines.user(
        id=user, cache=cache, config=config, machines=machine_list
    )

    # If the user is not authed for any machines, authed_machines will be None. We want it to be an empty dict instead so it doesn't break iteration
    if not authed_machines:
        authed_machines = {}

    block_list: list[dict] = []
    block_list = slackUtils.add_block(
        block_list=block_list,
        block=slackUtils.inject_text(
            block_list=blocks.text, text=strings.trained_tools_modal_explainer
        ),
    )

    # Generate input wrapper

    input_wrapper = copy(blocks.input_wrapper)
    input_wrapper["label"]["text"] = strings.trained_tools_modal_picker_label

    # Generate picker
    picker = copy(blocks.multi_static_select)

    # Set the placeholder text
    picker["placeholder"]["text"] = strings.trained_tools_modal_picker_placeholder

    # Set the action ID
    picker["action_id"] = "filter_authed_tools"

    # Add options to picker

    for category in all_machines:
        if category != "exclude":
            # Create a button
            option = create_option(text=category, value=category)

            # Add the button to the picker
            picker["options"].append(option)

    # Add preselected options to picker if category is not all
    if "all" not in categories:
        picker["initial_options"] = []
        for category in categories:
            # Create a button
            option = create_option(text=category, value=category)

            # Add the button to the picker
            picker["initial_options"].append(option)

    # Add picker to input wrapper
    input_wrapper["element"] = picker

    # Add input wrapper to block list
    block_list = slackUtils.add_block(block_list=block_list, block=input_wrapper)

    block_list = slackUtils.add_block(block_list=block_list, block=blocks.divider)

    # Deduplicate and flatten authed machines
    if authed_machines:
        authed_machines = list(
            set(
                [
                    machine
                    for category in authed_machines
                    for machine in authed_machines[category]
                ]
            )
        )

    # Generate list of machines to display, index by name, and sort
    display_machines = {}

    if "all" in categories:
        categories = list(all_machines.keys())
    for category in categories:
        for machine in all_machines[category]:
            if machine["name"] not in display_machines:
                display_machines[machine["name"]] = machine

    # sort display_machines by key
    display_machines = dict(sorted(display_machines.items()))

    # Format machines as string
    formatted_tools = ""
    for machine in display_machines:
        if display_machines[machine]["id"] in authed_machines:
            formatted_tools += (
                f"{display_machines[machine].get('level', '⚪')}✅ {machine}\n"
            )
        elif display_machines[machine].get("level", "⚪") == "🅿️":
            # Skip probationary sign offs the user doesn't have
            continue
        else:
            formatted_tools += (
                f"{display_machines[machine].get('level', '⚪')}❌ {machine}"
            )
            # Check if the current machine has training info
            if "training" in display_machines[machine]:
                formatted_tools += (
                    f" (Training: {display_machines[machine]['training']})"
                )
            formatted_tools += "\n"

    # Add explainer if no tools are authed
    if not authed_machines:
        if len(categories) > 1:
            no_tools = copy(strings.no_tools)
            no_tools = no_tools.replace("this category", "these categories")
        else:
            no_tools = strings.no_tools
        block_list = slackUtils.add_block(
            block_list=block_list,
            block=slackUtils.inject_text(block_list=blocks.text, text=no_tools),
        )
        block_list = slackUtils.add_block(block_list=block_list, block=blocks.divider)

    block_list = slackUtils.add_block(
        block_list=block_list,
        block=slackUtils.inject_text(block_list=blocks.text, text=formatted_tools),
    )

    # Add blocks to modal
    modal = copy(blocks.modal)

    # This modal has input blocks so modify the buttons to make it clearer what they do
    modal["submit"] = {"type": "plain_text", "text": "Filter", "emoji": True}
    modal["close"] = {"type": "plain_text", "text": "Close", "emoji": True}

    # Construct title while staying under 25 characters
    title = ""
    for category in categories:
        if len(title) + len(category) + 2 > 24:
            title = title[:-2]
            title += "+"
            break
        title += category.capitalize() + ", "
    if title[-2:] == ", ":
        title = title[:-2]

    modal["title"]["text"] = title
    modal["blocks"] = block_list
    modal["callback_id"] = "filter_authed_tools_modal"

    return modal


def create_option(text, value, capitalisation=True):
    option = copy(blocks.static_select_option)

    # Add the text
    if capitalisation:
        option["text"]["text"] = text.capitalize()
    else:
        option["text"]["text"] = text

    # Add the value
    option["value"] = value

    return option


def home_header(block_list: list) -> list[Any]:
    block_list = slackUtils.add_block(
        block_list=block_list,
        block=slackUtils.inject_text(block_list=blocks.text, text=strings.explainer),
    )
    block_list = slackUtils.add_block(block_list=block_list, block=blocks.divider)
    return block_list


def home_low_risk(block_list: list) -> list[Any]:
    block_list = slackUtils.add_block(
        block_list=block_list,
        block=slackUtils.inject_text(
            block_list=blocks.header, text=strings.low_risk_header
        ),
    )
    block_list = slackUtils.add_block(
        block_list=block_list,
        block=slackUtils.inject_text(
            block_list=blocks.text, text=strings.low_risk_explainer
        ),
    )
    block_list = slackUtils.add_block(
        block_list=block_list,
        block=slackUtils.inject_text(
            block_list=blocks.context, text=strings.low_risk_context
        ),
    )
    block_list = slackUtils.add_block(block_list=block_list, block=blocks.divider)
    return block_list


def home_medium_risk(block_list: list) -> list[Any]:
    block_list = slackUtils.add_block(
        block_list=block_list,
        block=slackUtils.inject_text(
            block_list=blocks.header, text=strings.medium_risk_header
        ),
    )
    block_list = slackUtils.add_block(
        block_list=block_list,
        block=slackUtils.inject_text(
            block_list=blocks.text, text=strings.medium_risk_explainer
        ),
    )
    block_list = slackUtils.add_block(block_list=block_list, block=blocks.divider)
    return block_list


def home_high_risk(block_list: list) -> list[Any]:
    block_list = slackUtils.add_block(
        block_list=block_list,
        block=slackUtils.inject_text(
            block_list=blocks.header, text=strings.high_risk_header
        ),
    )
    block_list = slackUtils.add_block(
        block_list=block_list,
        block=slackUtils.inject_text(
            block_list=blocks.text, text=strings.high_risk_explainer
        ),
    )
    block_list = slackUtils.add_block(block_list=block_list, block=blocks.divider)
    return block_list


def home_requesting_training(block_list: list) -> list[Any]:
    block_list = slackUtils.add_block(
        block_list=block_list,
        block=slackUtils.inject_text(
            block_list=blocks.header, text=strings.requesting_training_header
        ),
    )
    block_list = slackUtils.add_block(
        block_list=block_list,
        block=slackUtils.inject_text(
            block_list=blocks.text, text=strings.requesting_training_explainer
        ),
    )

    return block_list


def select_users_modal(user, config, client, cache):
    block_list = []

    # Generate input wrapper

    input_wrapper = copy(blocks.input_wrapper)
    input_wrapper["label"]["text"] = strings.select_users_modal_picker_label

    # Create external selector
    external_selector = copy(blocks.external_select)
    external_selector["placeholder"]["text"] = (
        strings.select_users_modal_picker_placeholder
    )
    external_selector["action_id"] = "select_user"
    external_selector["min_query_length"] = 3
    external_selector["focus_on_load"] = True

    # Add external selector to input wrapper
    input_wrapper["element"] = external_selector

    # Add input wrapper to block list
    block_list = slackUtils.add_block(block_list=block_list, block=input_wrapper)

    button_actions = copy(blocks.actions)
    button_actions["block_id"] = "trainer_home"

    for button in ["add_training", "remove_training"]:
        text = button.replace("_", " ").capitalize()
        button_actions = slackUtils.inject_button(
            actions=button_actions,
            text=text,
            value=button,
            action_id="trainer-" + button,
        )
    block_list = slackUtils.add_block(block_list=block_list, block=button_actions)

    # Add blocks to modal
    modal = copy(blocks.modal)

    # This modal has input blocks so modify the buttons to make it clearer what they do
    modal["submit"] = {"type": "plain_text", "text": "Check", "emoji": True}
    modal["close"] = {"type": "plain_text", "text": "Cancel", "emoji": True}

    modal["title"]["text"] = "Select User"
    modal["blocks"] = block_list
    modal["callback_id"] = "filter_trainer_select_modal"

    return modal


def trainer_check_authed_machines_modal(
    user: str, config: dict, client, cache: dict, machine_list: dict
):
    # Generate list of machines
    all_machines = machines.all(cache=cache, config=config, machines=machine_list)
    authed_machines = machines.user(
        id=user, cache=cache, config=config, machines=machine_list
    )

    block_list: list[dict] = []
    block_list = slackUtils.add_block(
        block_list=block_list,
        block=slackUtils.inject_text(
            block_list=blocks.text, text=strings.trainer_tools_modal_explainer
        ),
    )

    if authed_machines:
        # Deduplicate and flatten authed machines
        authed_machines = list(
            set(
                [
                    machine
                    for category in authed_machines
                    for machine in authed_machines[category]
                ]
            )
        )

        # Generate list of machines to display, index by name, and sort
        display_machines = {}

        for category in list(all_machines.keys()):
            for machine in all_machines[category]:
                if machine["name"] not in display_machines:
                    display_machines[machine["name"]] = machine

        # sort display_machines by key
        display_machines = dict(sorted(display_machines.items()))

        # Format machines as string
        formatted_tools = ""
        for machine in display_machines:
            if display_machines[machine]["id"] in authed_machines:
                formatted_tools += (
                    f"{display_machines[machine].get('level', '⚪')}✅ {machine}\n"
                )
            else:
                formatted_tools += (
                    f"{display_machines[machine].get('level', '⚪')}❌ {machine}\n"
                )

    else:
        formatted_tools = strings.trainer_no_tools

    block_list = slackUtils.add_block(
        block_list=block_list,
        block=slackUtils.inject_text(block_list=blocks.text, text=formatted_tools),
    )

    # Add blocks to modal
    modal = copy(blocks.modal)

    # Set title to the user's name, if possible. The user field will always be a tidyHQ id here
    contact = tidyhq.get_contact(contact_id=user, cache=cache)
    if not contact:
        name = "Unknown user"
        logging.error(f"Could not find contact with id {user}")
    else:
        name = tidyhq.format_contact(contact=contact)

    if len(name) > 24:
        name = name[:21] + "..."

    modal["title"]["text"] = name
    modal["blocks"] = block_list
    modal["callback_id"] = "trainer_authed_tools_modal"

    return modal


def trainer_change_authed_machines_modal(
    user: str, config: dict, client, cache: dict, machine_list: dict, action: str
):
    text = ""  # This is here to make the linter happy. The text variable can't actually be unbound.
    if action not in ["add", "remove"]:
        logging.error(
            f"Invalid action {action} for function trainer_change_authed_machines_modal"
        )

    block_list: list[dict] = []

    # Generate list of machines
    all_machines = machines.all(cache=cache, config=config, machines=machine_list)
    authed_machines = machines.user(
        id=user, cache=cache, config=config, machines=machine_list
    )

    if authed_machines:
        authed_machines_flat = list(
            set(
                [
                    machine
                    for category in authed_machines
                    for machine in authed_machines[category]
                ]
            )
        )
    else:
        authed_machines_flat = []

    if not authed_machines and action == "remove":
        block_list = slackUtils.add_block(
            block_list=block_list,
            block=slackUtils.inject_text(
                block_list=blocks.text, text=strings.trainer_no_tools
            ),
        )
    else:
        # Calculate whether we should list authed machines or not authed machines
        display_machines = {}
        for category in all_machines:
            for tool in all_machines[category]:
                # When adding tools we exclude tools that are already authed
                if action == "add":
                    text = strings.trainer_add_explainer
                    if tool["id"] not in authed_machines_flat:
                        display_machines[tool["name"]] = tool
                # When removing tools we exclude tools that are not already authed. The logic above ensures that there will be at least one authed tool to remove.
                elif action == "remove":
                    if tool["id"] in authed_machines_flat:
                        display_machines[tool["name"]] = tool
                    text = strings.trainer_remove_explainer

        checkboxes = []

        # Iterate over display_machines in alphabetical order
        display_machines = dict(sorted(display_machines.items()))
        for machine in display_machines:
            # Create a checkbox
            checkbox = copy(blocks.check_box)
            checkbox["text"]["text"] = display_machines[machine]["name"]
            checkbox["value"] = str(display_machines[machine]["id"])
            checkbox["description"]["text"] = display_machines[machine].get(
                "level", "⚪"
            )
            checkboxes.append(checkbox)

        # We can only add 10 checkboxes to a checkbox container so we need to split them up
        box = 0
        while len(checkboxes) > 0:
            checkbox_container = copy(blocks.check_box_container)
            checkbox_container["text"]["text"] = text
            checkbox_container["accessory"]["action_id"] = (
                f"trainer-{action}_training_write-{box}"
            )
            checkbox_container["accessory"]["options"] = checkboxes[:10]
            block_list = slackUtils.add_block(
                block_list=block_list, block=checkbox_container
            )
            box += 1
            text = "⠀"  # We only need the explainer the first time
            checkboxes = checkboxes[10:]

    # Add blocks to modal
    modal = copy(blocks.modal)

    # Set title to the user's name, if possible. The user field will always be a tidyHQ id here
    contact = tidyhq.get_contact(contact_id=user, cache=cache)
    if not contact:
        name = "Unknown user"
        logging.error(f"Could not find contact with id {user}")
    else:
        name = tidyhq.format_contact(contact=contact)

    title = f"{action.capitalize()}: {name}"

    if len(title) > 24:
        title = title[:21] + "..."

    # If we're adding tools add an input block to record the time taken
    # this is passed on to the token system

    if action == "add":
        time_input = copy(blocks.input_wrapper)
        time_input["label"]["text"] = "Time taken (hours)"
        time_input["element"] = copy(blocks.number_input)
        time_input["element"]["action_id"] = "trainer-time_taken"
        time_input["optional"] = True
        time_input["block_id"] = "hours_input"
        time_input["element"]["min_value"] = "0"
        time_input["element"]["max_value"] = "100"
        time_input["element"]["is_decimal_allowed"] = True
        time_input["hint"] = copy(blocks.base_text)
        time_input["hint"]["type"] = "plain_text"
        time_input["hint"]["text"] = (
            "These hours will be added as time debt via the token system. Partial hours can be entered as a decimal (e.g. 0.5 for half an hour)"
        )

        block_list = [time_input] + block_list

    modal["title"]["text"] = title
    modal["blocks"] = block_list
    modal["callback_id"] = "trainer_authed_tools_modal_write"

    # This modal has input blocks so modify the buttons to make it clearer what they do
    if action == "add":
        modal["submit"] = {"type": "plain_text", "text": "Authorise", "emoji": True}
    else:
        modal["submit"] = {"type": "plain_text", "text": "Deauthorise", "emoji": True}
    modal["close"] = {"type": "plain_text", "text": "Cancel", "emoji": True}

    return modal


def tool_selector_modal(config, client, cache, machine_list):
    all_machines = machines.all(cache=cache, config=config, machines=machine_list)

    option_groups = []

    for category in all_machines:
        option_group = copy(blocks.option_group)
        option_group["label"]["text"] = category.capitalize()

        for machine in sorted(all_machines[category], key=lambda k: k["name"]):
            option = copy(blocks.static_select_option)
            option["text"]["text"] = f"{machine.get('level', '⚪')} {machine['name']}"
            option["value"] = f"{machine['id']}-{category}"
            option_group["options"].append(option)

        option_groups.append(option_group)

    # Create static select
    static_select = copy(blocks.single_static_select)
    static_select["placeholder"]["text"] = "Search..."
    static_select["action_id"] = "tool_selector"
    static_select["option_groups"] = option_groups

    # By default static select includes an options field. We're using option groups instead
    del static_select["options"]

    # Create input wrapper
    input_wrapper = copy(blocks.input_wrapper)
    input_wrapper["label"]["text"] = "Select tool"
    input_wrapper["element"] = static_select

    block_list = []
    block_list = slackUtils.add_block(block_list=block_list, block=input_wrapper)

    # Create modal
    modal = copy(blocks.modal)
    modal["title"]["text"] = "Tool report"

    # Add blocks
    modal["blocks"] = block_list

    # This modal has input blocks so modify the buttons to make it clearer what they do
    modal["submit"] = {"type": "plain_text", "text": "Report", "emoji": True}

    modal["callback_id"] = "tool_selector_modal"

    # pprint(modal)

    return modal


def machine_report_modal(config, cache, machine_list, machine):
    # Get info about the machine
    machine_info = tidyhq.get_group_info(id=machine, cache=cache, config=config)

    # Get all users for machine
    users = machines.machine(machine_id=machine, cache=cache)
    users_display = []
    for user in users:
        users_display.append(tidyhq.format_contact(contact=user))

    # Sort users by name
    users_display = sorted(users_display)

    # Construct tool text
    tool_text = f"""
*Tool name:* {machine_info["name"]}
*Risk level:* {machine_info.get("level", "⚪")}
*Training type:* {machine_info.get("training", "N/A")}
*Total authorised users:* {len(users_display)}
*Days until follow up:* {machine_info.get("first_use_check_in", "N/A")}
*Exclusive with*: {machine_info.get("exclusive_with", "N/A")}
*Children*: {machine_info.get("children", "N/A")}
    """
    tool_text = tool_text.strip()

    block_list = []

    # Add machine info
    block_list = slackUtils.add_block(block_list=block_list, block=blocks.text)

    block_list = slackUtils.inject_text(
        block_list=block_list,
        text=tool_text,
    )

    block_list = slackUtils.add_block(block_list=block_list, block=blocks.divider)  # type: ignore

    # Construct the list block
    list_block = copy(blocks.text)
    list_block = slackUtils.inject_text(
        block_list=list_block,
        text="\n".join(users_display),
    )

    block_list = slackUtils.add_block(block_list=block_list, block=list_block)

    # Create modal
    modal = copy(blocks.modal)
    machine_name = tidyhq.get_group_info(id=machine, cache=cache, config=config)["name"]
    modal["title"]["text"] = machine_name

    modal["blocks"] = block_list

    return modal


def follow_up_buttons(machine, follow_up_days, operator_id, trainer_id, has_slack=True):
    # Calculate human readable date for follow up days
    follow_up_date = datetime.now() + timedelta(days=int(follow_up_days))
    follow_up_date_str = follow_up_date.strftime("%B %d (%A)")

    block_list = []

    # Create explainer text
    block_list = slackUtils.add_block(
        block_list=block_list,
        block=slackUtils.inject_text(
            block_list=blocks.text,
            text=strings.check_in_explainer_trainer.format(
                follow_up_days, follow_up_date_str
            ),
        ),
    )

    block_list = slackUtils.add_block(block_list=block_list, block=blocks.divider)

    # Create action block
    button_actions = copy(blocks.actions)

    # Create approve button
    button_actions = slackUtils.inject_button(
        actions=button_actions,
        text="Approve",
        value=f"{machine['id']}-{operator_id}-{trainer_id}",
        action_id="checkin-approve",
        style="primary",
    )

    if has_slack:
        # Create contact button
        button_actions = slackUtils.inject_button(
            actions=button_actions,
            text="Contact",
            value=f"{machine['id']}-{operator_id}-{trainer_id}",
            action_id="checkin-contact",
        )

    # Create remove button
    button_actions = slackUtils.inject_button(
        actions=button_actions,
        text="Remove",
        value=f"{machine['id']}-{operator_id}-{trainer_id}",
        action_id="checkin-remove",
        style="danger",
    )

    block_list = slackUtils.add_block(block_list=block_list, block=button_actions)

    if not has_slack:
        block_list = slackUtils.add_block(block_list=block_list, block=blocks.divider)
        block_list = slackUtils.add_block(
            block_list=block_list,
            block=slackUtils.inject_text(
                block_list=blocks.text,
                text=strings.check_in_no_slack.format(operator_id),
            ),
        )

    return block_list


def placeholder_modal(text: str = "Loading... :loading-disc:") -> dict:
    """Returns a placeholder loading modal"""

    block_list = []
    block_list = slackUtils.add_block(block_list, blocks.text)
    block_list = slackUtils.inject_text(
        block_list=block_list,
        text=text,
    )

    # Create modal
    modal = copy(blocks.modal)
    modal["title"]["text"] = "Loading..."
    modal["blocks"] = block_list
    modal["callback_id"] = "placeholder_modal"
    return modal


def tidyhq_update_modal(time_taken):
    """Returns a modal to let the user know when updates from TidyHQ have been completed"""

    block_list = []
    block_list = slackUtils.add_block(block_list, blocks.text)
    block_list = slackUtils.inject_text(
        block_list=block_list,
        text=strings.tidyhq_update_complete.format(time_taken),
    )

    # Create modal
    modal = copy(blocks.modal)
    modal["title"]["text"] = "TidyHQ Update Complete"
    modal["blocks"] = block_list
    modal["callback_id"] = "tidyhq_update_complete_modal"
    return modal
