import json
import logging
import os
import sys
import time
from pprint import pprint
from typing import Any, Literal
import re
from copy import deepcopy as copy

import requests
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.web.client import WebClient  # for typing
from slack_sdk.web.slack_response import SlackResponse  # for typing

from util import formatters, misc, slackUtils, strings, tidyhq, blocks

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

# Log cli arguments
logger.info(f"CLI arguments: {sys.argv}")

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
    slackUtils.updateHome(user=event["user"], client=client, config=config, cache=cache)  # type: ignore


@app.action("refresh_home")
def refresh_home(ack, body, client):
    ack()
    global cache
    cache = tidyhq.fresh_cache(cache=cache, config=config)
    slackUtils.updateHome(user=body["user"]["id"], client=client, config=config, authed_slack_users=authed_slack_users, contacts=contacts, current_members=current_members, cache=cache)  # type: ignore


# Category buttons
cat_pattern = re.compile("category-.*")


@app.action({"block_id": "check_training", "action_id": cat_pattern})
def check_own_training(ack, body, client):
    ack()

    global cache
    cache = tidyhq.fresh_cache(cache=cache, config=config)

    # Get the category from the action ID
    category = body["actions"][0]["value"]
    slackUtils.authed_tools_modal(
        user=body["user"]["id"],
        config=config,
        client=client,
        cache=cache,
        categories=[category],
        trigger=body["trigger_id"],
        machine_list=machine_list,
    )


@app.view("filter_authed_tools_modal")
def filter_authed_tools_modal(ack, body, client):
    ack()
    # pprint(body)

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

    # pprint(categories)
    slackUtils.authed_tools_modal(
        user=body["user"]["id"],
        config=config,
        client=client,
        cache=cache,
        categories=categories,
        trigger=body["trigger_id"],
        machine_list=machine_list,
    )


# Trainer buttons
@app.action("trainer-select")
def select_user(ack, body, client):
    ack()

    global cache
    cache = tidyhq.fresh_cache(cache=cache, config=config)

    slackUtils.select_user_modal(
        user=body["user"]["id"],
        config=config,
        client=client,
        cache=cache,
        trigger=body["trigger_id"],
    )


@app.action("trainer-add_training")
def add_training(ack, body, client):
    # Get selected user
    user = list(body["view"]["state"]["values"].values())[0]["select_user"][
        "selected_option"
    ]["value"]

    view_id = body["view"]["id"]

    slackUtils.trainer_change_authed_machines_modal(
        user=user,
        config=config,
        client=client,
        cache=cache,
        trigger=body["trigger_id"],
        machine_list=machine_list,
        action="add",
        view_id=view_id,
    )
    ack()


@app.action("trainer-remove_training")
def remove_training(ack, body, client):
    ack()

    # Get selected user
    user = list(body["view"]["state"]["values"].values())[0]["select_user"][
        "selected_option"
    ]["value"]

    view_id = body["view"]["id"]

    slackUtils.trainer_change_authed_machines_modal(
        user=user,
        config=config,
        client=client,
        cache=cache,
        trigger=body["trigger_id"],
        machine_list=machine_list,
        action="remove",
        view_id=view_id,
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

    # Get a list of machines to change
    machines = []

    for section in body["view"]["state"]["values"]:
        for section2 in body["view"]["state"]["values"][section]:
            for option in body["view"]["state"]["values"][section][section2][
                "selected_options"
            ]:
                machines.append(option["value"])

    for machine in machines:
        success = tidyhq.update_group_membership(
            tidyhq_id=user, group_id=machine, action=action, config=config
        )
        if success:
            logging.info(f"{action}'d {user} for {machine}")
            # Get info to construct message
            machine_info = tidyhq.get_group_info(id=machine, cache=cache, config=config)
            user_contact = contact = tidyhq.get_contact(contact_id=user, cache=cache)
            if user_contact:
                user_name = tidyhq.format_contact(contact=user_contact)
            else:
                user_name = "UNKNOWN"

            # Construct message
            message = f'{"✅" if action == "add" else "🚫"}{user_name} has been {"authorised" if action == "add" else "deauthorised"} for {machine_info["name"]} ({machine_info.get("level","⚪")}) by <@{body["user"]["id"]}>'

            slackUtils.send(
                app=app,
                channel=config["slack"]["notification_channel"],
                message=message,
            )

            # Log the change to file
            with open("tidyhq_changes.log", "a") as f:
                f.write(
                    f"{time.time()},{body['user']['id']},{action},{user},{machine}\n"
                )

        else:
            logging.error(f"Failed to {action} {user} for {machine}")

    # Once all the changes have been made refresh the cache
    cache = tidyhq.fresh_cache(config=config, force=True)


# Silence notifications of individual checkboxes
checkbox_pattern = re.compile(r"trainer-(add|remove)_training_write-\d*")


@app.action({"action_id": checkbox_pattern})
def handle_some_action(ack, body, logger):
    ack()


@app.view("filter_trainer_select_modal")
def check_user_training(ack, body, client):
    ack()

    # Get selected user
    user = list(body["view"]["state"]["values"].values())[0]["select_user"][
        "selected_option"
    ]["value"]

    view_id = body["view"]["id"]

    slackUtils.trainer_authed_tools_modal(
        user=user,
        config=config,
        client=client,
        cache=cache,
        trigger=body["trigger_id"],
        machine_list=machine_list,
        view_id=view_id,
    )


@app.action("trainer-check_tool_training")
def check_tool_training(ack, body, client):
    ack()

    global cache
    cache = tidyhq.fresh_cache(cache=cache, config=config)

    slackUtils.tool_selector_modal(
        config=config,
        client=client,
        cache=cache,
        trigger=body["trigger_id"],
        machine_list=machine_list,
    )


@app.view("tool_selector_modal")
def handle_view_submission_events(ack, body, client):
    ack()
    # pprint(body)

    # Get selected option
    choice = list(body["view"]["state"]["values"].values())[0]["tool_selector"][
        "selected_option"
    ]["value"]
    # We added the category to this value earlier to create a unique value but we don't need it now
    machine = choice.split("-")[0]

    slackUtils.machine_report_modal(
        config=config,
        client=client,
        cache=cache,
        trigger=body["trigger_id"],
        machine_list=machine_list,
        machine=machine,
        view_id=body["view"]["id"],
    )


@app.action("trainer-refresh")
def refresh_tidyhq(ack, body, client):
    ack()
    logging.info(f'User {body["user"]["id"]} refreshed data from TidyHQ')
    global cache
    cache = tidyhq.fresh_cache(config=config, force=True)
    # Refresh the user's home
    slackUtils.updateHome(
        user=body["user"]["id"], client=client, config=config, cache=cache
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


# Get all linked users from TidyHQ

logger.info("Getting TidyHQ data from cache")

cache = tidyhq.fresh_cache(config=config)

logger.info("Loading machine categories")
with open("machines.json", "r") as f:
    machine_list: dict = json.load(f)

logger.debug(
    f'Loaded {len(cache["contacts"])} contacts and {len(cache["groups"])} groups'
)

# Get our user ID
info = app.client.auth_test()
logger.debug(f'Connected as @{info["user"]} to {info["team"]}')


# Check whether we're running as a cron job
if "-c" in sys.argv:
    # Update homes for all slack users
    logger.info("Updating homes for all users")

    # Get a list of all users from slack
    slack_response = app.client.users_list()
    slack_users = slack_response.data["members"]  # type: ignore

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
