import json
import logging
import os
import re
import sys
import time
from copy import deepcopy as copy
from datetime import datetime
from pprint import pprint
from typing import Any, Literal

import requests
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.web.client import WebClient  # for typing
from slack_sdk.web.slack_response import SlackResponse  # for typing

from util import blocks, formatters, misc, slackUtils, tidyhq, machines
from editable_resources import strings

# Split up command line arguments
# -v: verbose logging
# -c: cron job

if "-cv" in sys.argv or "-vc" in sys.argv:
    sys.argv.remove("-cv")
    sys.argv.remove("-vc")
    sys.argv.append("-c")
    sys.argv.append("-v")

# Load config
with open("config.json", "r") as config_file:
    config = json.load(config_file)

# Set up root logger
root_logger = logging.getLogger()
if "-v" in sys.argv:
    root_logger.setLevel(logging.DEBUG)
else:
    root_logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
root_logger.addHandler(ch)

# Set up loop logging
logger = logging.getLogger("main loop")

# Changing logging level for slack_bolt to info
slack_logger = logging.getLogger("slack_bolt")
slack_logger.setLevel(logging.INFO)

# Connect to Slack
app = App(token=config["slack"]["bot_token"], logger=slack_logger)


# Update the app home in certain circumstances
@app.event("app_home_opened")  # type: ignore
def app_home_opened(event: dict[str, Any], client: WebClient, ack) -> None:
    ack()
    global cache
    cache = tidyhq.fresh_cache(cache=cache, config=config)
    slackUtils.updateHome(
        user=event["user"],
        client=client,
        config=config,
        cache=cache,
        machine_raw=machine_list,
    )  # type: ignore


@app.action("refresh_home")
def refresh_home(ack, body, client):
    ack()
    global cache
    cache = tidyhq.fresh_cache(cache=cache, config=config)
    slackUtils.updateHome(
        user=body["user"]["id"],
        client=client,
        config=config,
        cache=cache,
        machine_raw=machine_list,
    )


# Category buttons
cat_pattern = re.compile("category-.*")


@app.action({"block_id": "check_training", "action_id": cat_pattern})
def check_own_training(ack, body, client):
    ack()

    # Send a placeholder modal while we gather data
    v = app.client.views_open(
        trigger_id=body["trigger_id"],
        view=formatters.placeholder_modal(),
    )

    global cache
    cache = tidyhq.fresh_cache(cache=cache, config=config)

    # Get the category from the action ID
    category = body["actions"][0]["value"]

    modal = formatters.authed_machines_modal(
        user=body["user"]["id"],
        config=config,
        client=client,
        cache=cache,
        categories=[category],
        machine_list=machine_list,
    )
    app.client.views_update(
        view_id=v["view"]["id"],  # type: ignore
        view=modal,
    )


@app.view("filter_authed_tools_modal")
def filter_authed_tools_modal(ack, body, client):
    ack()

    # Send a placeholder modal while we gather data
    v = app.client.views_open(
        trigger_id=body["trigger_id"],
        view=formatters.placeholder_modal(),
    )

    global cache
    cache = tidyhq.fresh_cache(cache=cache, config=config)

    # Get options from body
    categories = []
    states = body["view"]["state"]["values"]
    for state in states:
        for field in states[state]:
            if field == "filter_authed_tools":
                for option in states[state][field]["selected_options"]:
                    categories.append(option["value"])

    modal = formatters.authed_machines_modal(
        user=body["user"]["id"],
        config=config,
        client=client,
        cache=cache,
        categories=categories,
        machine_list=machine_list,
    )
    app.client.views_update(
        view_id=v["view"]["id"],  # type: ignore
        view=modal,
    )


# Trainer buttons
@app.action("trainer-select")
def select_user(ack, body, client):
    ack()

    # Send a placeholder modal while we gather data
    v = app.client.views_open(
        trigger_id=body["trigger_id"],
        view=formatters.placeholder_modal(),
    )

    global cache
    cache = tidyhq.fresh_cache(cache=cache, config=config)

    modal = formatters.select_users_modal(
        user=body["user"]["id"],
        config=config,
        client=client,
        cache=cache,
    )

    app.client.views_update(
        view_id=v["view"]["id"],  # type: ignore
        view=modal,
    )


@app.action("trainer-add_training")
def add_training(ack, body, client):
    ack()

    # Get selected user (if any)
    try:
        user = list(body["view"]["state"]["values"].values())[0]["select_user"][
            "selected_option"
        ]["value"]
    except TypeError:
        # No user has been selected, don't do anything
        return

    # Send a placeholder modal while we gather data
    v = app.client.views_push(
        trigger_id=body["trigger_id"],
        view=formatters.placeholder_modal(),
    )

    modal = formatters.trainer_change_authed_machines_modal(
        user=user,
        config=config,
        client=client,
        cache=cache,
        machine_list=machine_list,
        action="add",
    )

    modal["private_metadata"] = f"add-{user}"

    app.client.views_update(
        view_id=v["view"]["id"],  # type: ignore
        view=modal,
    )


@app.action("trainer-remove_training")
def remove_training(ack, body, client):
    ack()

    # Get selected user (if any)
    try:
        user = list(body["view"]["state"]["values"].values())[0]["select_user"][
            "selected_option"
        ]["value"]
    except TypeError:
        # No user has been selected, don't do anything
        return

    # Send a placeholder modal while we gather data
    v = app.client.views_push(
        trigger_id=body["trigger_id"],
        view=formatters.placeholder_modal(),
    )

    modal = formatters.trainer_change_authed_machines_modal(
        user=user,
        config=config,
        client=client,
        cache=cache,
        machine_list=machine_list,
        action="remove",
    )

    modal["private_metadata"] = f"remove-{user}"

    app.client.views_update(
        view_id=v["view"]["id"],  # type: ignore
        view=modal,
    )


@app.view("trainer_authed_tools_modal_write")
def write_training_changes(ack, body, event):
    ack()

    # Check if log file exists and create it if not
    try:
        with open("tidyhq_changes.log", "r") as f:
            pass
    except FileNotFoundError:
        with open("tidyhq_changes.log", "w") as f:
            pass

    # We're going to be updating the cache later on
    global cache

    # Decide whether we're adding or removing and to whom
    action, user = body["view"]["private_metadata"].split("-")

    # Set a baseline blank Slack ID and user_name to catch times when the user isn't a slack user
    slack_id = ""
    user_name = ""

    # Get a list of machines to change
    machines = []

    for section in body["view"]["state"]["values"]:
        if section == "hours_input":
            continue
        for section2 in body["view"]["state"]["values"][section]:
            for option in body["view"]["state"]["values"][section][section2][
                "selected_options"
            ]:
                machines.append(option["value"])

    user_contact = tidyhq.get_contact(contact_id=user, cache=cache)
    if user_contact:
        user_name = tidyhq.format_contact(contact=user_contact)
        # Check for a slack user ID
        slack_id = tidyhq.get_slack_id(config=config, contact=user_contact, cache=cache)
        if slack_id:
            user_name += f" (<@{slack_id}>)"
    else:
        user_name = "UNKNOWN"

    children = []
    exclusive = []

    for machine in machines:
        success = tidyhq.update_group_membership(
            tidyhq_id=user, group_id=machine, action=action, config=config
        )
        if success:
            machine_info = tidyhq.get_group_info(id=machine, cache=cache, config=config)

            slackUtils.notify_training(
                action=action,
                trainee=user,
                trainee_formatted=user_name,
                trainee_slack_id=slack_id,
                machine_info=machine_info,
                config=config,
                trainer=body["user"]["id"],
                app=app,
            )

            if machine_info.get("children", False):
                children += machine_info["children"].split(",")
            if machine_info.get("exclusive_with", False):
                exclusive += machine_info["exclusive_with"].split(",")
        else:
            logging.error(f"Failed to {action} {user} for {machine}")

    # Handle children
    # These are groups that should be added when the parent is added
    for machine in set(children):
        success = tidyhq.update_group_membership(
            tidyhq_id=user, group_id=machine, action=action, config=config
        )
        if success:
            machine_info = tidyhq.get_group_info(id=machine, cache=cache, config=config)

            slackUtils.notify_training(
                action=action,
                trainee=user,
                trainee_formatted=user_name,
                trainee_slack_id=slack_id,
                machine_info=machine_info,
                config=config,
                trainer=body["user"]["id"],
                app=app,
            )
        else:
            logging.error(f"Failed to {action} {user} for {machine}")

    # Handle exclusive groups
    # These are groups that should be removed when the current group is added
    if action == "add":
        for machine in set(exclusive):
            success = tidyhq.update_group_membership(
                tidyhq_id=user, group_id=machine, action="remove", config=config
            )
            if success:
                machine_info = tidyhq.get_group_info(
                    id=machine, cache=cache, config=config
                )

                slackUtils.notify_training(
                    action="remove",
                    trainee=user,
                    trainee_formatted=user_name,
                    trainee_slack_id=slack_id,
                    machine_info=machine_info,
                    config=config,
                    trainer=body["user"]["id"],
                    app=app,
                )
            else:
                logging.error(f"Failed to remove {user} for {machine}")

    # Get the time debt if provided
    hours = (
        body["view"]["state"]["values"]
        .get("hours_input", {})
        .get("trainer-time_taken", {})
        .get("value", "")
    )

    try:
        hours = float(hours)
    except (ValueError, TypeError):
        hours = 0

    if hours > 0:
        # Send a message to the token channel
        slackUtils.send(
            app=app,
            channel=config["slack"]["token_channel"],
            message=f"Time debt of {hours}h hours recorded by <@{body['user']['id']}> for training {user_name}",
            metadata={
                "event_type": "time_debt",
                "event_payload": {
                    "trainer": body["user"]["id"],
                    "tidyhq_id": user,
                    "slack_id": slack_id,
                    "hours": hours,
                },
            },
        )

    # Once all the changes have been made refresh the cache
    cache = tidyhq.fresh_cache(config=config, force=True)


# Silence notifications of individual checkboxes
checkbox_pattern = re.compile(r"trainer-(add|remove)_training_write-\d*")


@app.action({"action_id": checkbox_pattern})
def ignore_individual_checkbox(ack, body, logger):
    ack()


@app.view("filter_trainer_select_modal")
def check_user_training(ack, body, client):
    ack()

    # Send a placeholder modal while we gather data
    v = app.client.views_open(
        trigger_id=body["trigger_id"],
        view=formatters.placeholder_modal(),
    )

    # Get selected user
    user = list(body["view"]["state"]["values"].values())[0]["select_user"][
        "selected_option"
    ]["value"]

    modal = formatters.trainer_check_authed_machines_modal(
        user=user,
        config=config,
        client=client,
        cache=cache,
        machine_list=machine_list,
    )

    app.client.views_update(
        view_id=v["view"]["id"],  # type: ignore
        view=modal,
    )


@app.action("trainer-check_tool_training")
def check_tool_training(ack, body, client):
    ack()

    # Send a placeholder modal while we gather data
    v = app.client.views_open(
        trigger_id=body["trigger_id"],
        view=formatters.placeholder_modal(),
    )

    global cache
    cache = tidyhq.fresh_cache(cache=cache, config=config)

    modal = formatters.tool_selector_modal(
        config=config,
        client=client,
        cache=cache,
        machine_list=machine_list,
    )

    app.client.views_update(
        view_id=v["view"]["id"],  # type: ignore
        view=modal,
    )


@app.view("tool_selector_modal")
def handle_view_submission_events(ack, body, client):
    ack()

    # Send a placeholder modal while we gather data
    v = app.client.views_open(
        trigger_id=body["trigger_id"],
        view=formatters.placeholder_modal(),
    )

    # Get selected option
    choice = list(body["view"]["state"]["values"].values())[0]["tool_selector"][
        "selected_option"
    ]["value"]
    # We added the category to this value earlier to create a unique value but we don't need it now
    machine = choice.split("-")[0]

    modal = formatters.machine_report_modal(
        config=config, cache=cache, machine_list=machine_list, machine=machine
    )
    app.client.views_update(
        view_id=v["view"]["id"],  # type: ignore
        view=modal,
    )


@app.action("trainer-refresh")
def refresh_tidyhq(ack, body, client):
    ack()

    # Send a placeholder message while we refresh data
    v = app.client.views_open(
        trigger_id=body["trigger_id"],
        view=formatters.placeholder_modal(
            text="Refreshing TidyHQ data. This may take a moment but you can close this window if you like."
        ),
    )

    # Start counting time
    start_time = time.time()

    logging.info(f"User {body['user']['id']} refreshed data from TidyHQ")
    global cache
    cache = tidyhq.fresh_cache(config=config, force=True)
    # Refresh the user's home
    slackUtils.updateHome(
        user=body["user"]["id"],
        client=client,
        config=config,
        cache=cache,
        machine_raw=machine_list,
    )

    # Let the user know the update was successful
    elapsed_time = time.time() - start_time
    app.client.views_update(
        view_id=v["view"]["id"],  # type: ignore
        view=formatters.placeholder_modal(
            text=strings.tidyhq_update_complete.format(elapsed_time)
        ),
    )


# Respond with users
@app.options("select_user")
def send_user_options(ack, body):
    search_query = body["value"]
    users = tidyhq.list_all(config=config, cache=cache, filters=[])
    options_existing = []
    options_new = []
    raw_options = []

    # We can't send more than 100 options total
    total_options = 0

    for tidy_user in users:
        if len(raw_options) > 100:
            break

        # Find the name
        contact = tidyhq.get_contact(contact_id=tidy_user, cache=cache)
        if not contact:
            break

        name = tidyhq.format_contact(contact=contact)

        if search_query.lower() in str(name).lower():
            # Check if the user has been trained on at least one machine

            # Create an item
            option = formatters.create_option(
                text=f"{name}", value=f"{tidy_user}", capitalisation=False
            )

            # Add the item to the correct group
            if total_options < 100:
                total_options += 1
                if tidyhq.find_groups_for_user(contact=contact, config=config):
                    options_existing.append(option)
                else:
                    options_new.append(option)

    # Set up option groups

    option_groups = []
    if options_existing:
        option_group = copy(blocks.option_group)
        option_group["label"]["text"] = "Existing trainees"
        option_group["options"] = options_existing
        option_groups.append(option_group)
    if options_new:
        option_group = copy(blocks.option_group)
        option_group["label"]["text"] = "New trainees"
        option_group["options"] = options_new
        option_groups.append(option_group)

    ack(option_groups=option_groups)


# Training Checkins


@app.action("checkin-contact")
def checkin_contact(ack, body, logger):
    ack()

    # Get information from the button
    info = body["actions"][0]["value"].split("-")
    machine_id = info[0]
    operator_id = info[1]
    trainer_id = info[2]

    # Calculate induction date
    sign_off_date = body["container"]["thread_ts"]
    sign_off_days_ago = (time.time() - float(sign_off_date)) // 86400 + 1

    # Get machine name
    machine_info = tidyhq.get_group_info(id=machine_id, cache=cache, config=config)

    # Open a conversation with the operator and trainer
    response: SlackResponse = app.client.conversations_open(
        users=f"{operator_id},{trainer_id}"
    )  # type: ignore
    if not response:
        logger.error(f"Failed to open conversation with {operator_id} and {trainer_id}")
        return

    channel_id = response.get("channel", {}).get("id")

    # Send an explainer message to the operator
    slackUtils.send(
        app=app,
        channel=channel_id,
        message=strings.checkin_explainer_operator.format(
            machine_info["name"], int(sign_off_days_ago)
        ),
    )

    # Send a message to the trainer channel letting other trainers know someone is following up
    slackUtils.send(
        app=app,
        channel=config["slack"]["notification_channel"],
        message=f"<@{body['user']['id']}> triggered a conversation regarding this induction",
        thread_ts=body["container"]["thread_ts"],
    )


@app.action("checkin-approve")
def checkin_approve(ack, body, logger):
    ack()
    # Get information from the button
    info = body["actions"][0]["value"].split("-")
    machine_id = info[0]
    operator_id = info[1]
    trainer_id = info[2]

    # Calculate induction date
    sign_off_date = body["container"]["thread_ts"]
    sign_off_days_ago = (time.time() - float(sign_off_date)) // 86400 + 1

    # Get machine name
    machine_info = tidyhq.get_group_info(id=machine_id, cache=cache, config=config)

    # Open a conversation with the operator and trainer
    response: SlackResponse = app.client.conversations_open(
        users=f"{operator_id},{trainer_id}"
    )  # type: ignore

    channel_id = response.get("channel", {}).get("id")

    # Send an explainer message to the operator
    slackUtils.send(
        app=app,
        channel=channel_id,
        message=strings.checkin_induction_approved.format(machine_info["name"]),
    )

    # Update the original message
    app.client.chat_update(
        channel=config["slack"]["notification_channel"],
        ts=body["container"]["message_ts"],
        text=strings.check_in_explainer_finished.format(
            machine_info["first_use_check_in"]
        ),
    )

    # Send notification that the induction has been approved
    slackUtils.send(
        app=app,
        channel=config["slack"]["notification_channel"],
        thread_ts=body["container"]["message_ts"],
        message=f"This induction was confirmed by <@{body['user']['id']}>",
    )


@app.action("checkin-remove")
def checkin_remove(ack, body, logger):
    ack()

    # We're going to be updating the cache later on
    global cache

    # Get information from the button
    info = body["actions"][0]["value"].split("-")
    machine_id = info[0]
    operator_id = info[1]
    trainer_id = info[2]

    # Get TidyHQ contact ID
    contact_id = tidyhq.translate_slack_to_tidyhq(
        slack_id=operator_id, cache=cache, config=config
    )

    # Calculate induction date
    sign_off_date = body["container"]["thread_ts"]
    sign_off_days_ago = (time.time() - float(sign_off_date)) // 86400 + 1

    # Get machine name
    machine_info = tidyhq.get_group_info(id=machine_id, cache=cache, config=config)

    # Remove the induction

    # Check if log file exists and create it if not
    try:
        with open("tidyhq_changes.log", "r") as f:
            pass
    except FileNotFoundError:
        with open("tidyhq_changes.log", "w") as f:
            pass

    action = "remove"
    success = tidyhq.update_group_membership(
        tidyhq_id=contact_id, group_id=machine_id, action=action, config=config
    )
    if success:
        logging.info(f"{action}'d {contact_id} for {machine_id}")
        # Get info to construct message
        machine_info = tidyhq.get_group_info(id=machine_id, cache=cache, config=config)
        user_contact = tidyhq.get_contact(contact_id=contact_id, cache=cache)
        if user_contact:
            user_name = tidyhq.format_contact(contact=user_contact)
        else:
            user_name = "UNKNOWN"

        # Construct message
        message = f'🚫{user_name} has been "deauthorised" for {machine_info["name"]} ({machine_info.get("level", "⚪")}) by <@{body["user"]["id"]}> after following up with the operator'

        slackUtils.send(
            app=app,
            channel=config["slack"]["notification_channel"],
            message=message,
        )

        # Log the change to file
        with open("tidyhq_changes.log", "a") as f:
            f.write(
                f"{time.time()},{body['user']['id']},{action},{contact_id},{machine_id}\n"
            )

        # Open a conversation with the operator and trainer
        response: SlackResponse = app.client.conversations_open(
            users=f"{operator_id},{trainer_id}"
        )  # type: ignore

        channel_id = response.get("channel", {}).get("id")

        # Send an explainer message to the operator
        slackUtils.send(
            app=app,
            channel=channel_id,
            message=strings.checkin_induction_rejected.format(machine_info["name"]),
        )

        # Update the original message
        app.client.chat_update(
            channel=config["slack"]["notification_channel"],
            ts=body["container"]["message_ts"],
            text=strings.check_in_explainer_finished.format(
                machine_info["first_use_check_in"]
            ),
        )

        slackUtils.send(
            app=app,
            channel=config["slack"]["notification_channel"],
            thread_ts=body["container"]["thread_ts"],
            message=f"This induction was removed by <@{body['user']['id']}>",
        )

        # Refresh the cache to reflect the change
        cache = tidyhq.fresh_cache(config=config, force=True)


# Get all linked users from TidyHQ

logger.info("Getting TidyHQ data from cache")

cache = tidyhq.fresh_cache(config=config)
logger.debug(
    f"Loaded {len(cache['contacts'])} contacts and {len(cache['groups'])} groups"
)

# Construct machine list
logger.info("Constructing machine list")
machine_list = machines.build_from_tidyhq(cache=cache, config=config)

# Get our user ID
info = app.client.auth_test()
logger.debug(f"Connected as @{info['user']} to {info['team']}")


# Check whether we're running as a cron job
if "-c" in sys.argv:
    # Update homes for all slack users
    logger.info("Updating homes for all users")

    # Get a list of all users from slack
    slack_response = app.client.users_list()
    slack_users = []
    while slack_response.data.get("response_metadata", {}).get("next_cursor"):  # type: ignore
        slack_users += slack_response.data["members"]  # type: ignore
        slack_response = app.client.users_list(
            cursor=slack_response.data["response_metadata"]["next_cursor"]  # type: ignore
        )
    slack_users += slack_response.data["members"]  # type: ignore

    users = []

    # Convert slack response to list of users since it comes as an odd iterable
    for user in slack_users:
        # pprint(user)
        if user["is_bot"] or user["deleted"]:
            continue
        users.append(user["id"])

    logger.info(f"Found {len(users)} users")

    x = 1
    for user in users:
        slackUtils.updateHome(
            user=user,
            client=app.client,
            config=config,
            cache=cache,
            machine_raw=machine_list,
        )
        logger.debug(f"Updated home for {user} ({x}/{len(users)})")
        x += 1
    logger.info("All homes updated ({x})")
    sys.exit(0)


if __name__ == "__main__":
    handler = SocketModeHandler(app, config["slack"]["app_token"])
    handler.start()
