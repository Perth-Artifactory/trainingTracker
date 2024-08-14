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
    if "-cv" in sys.argv:
        sys.argv.remove("-cv")
    if "-vc" in sys.argv:
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

if "-c" in sys.argv:
    logging.info("Running in cron mode, will check for sign offs that need a follow up")

    # Compile a list of machine operator groups
    cache = tidyhq.fresh_cache(config=config)

    machine_group_ids = tidyhq.find_all_groups(config=config, cache=cache)

    machine_groups = {}
    longest_check_in = 0
    for group_id in machine_group_ids:
        group = tidyhq.get_group_info(config=config, id=group_id, cache=cache)
        if "first_use_check_in" in group.keys():
            machine_groups[group_id] = group
            if int(group["first_use_check_in"]) > longest_check_in:
                longest_check_in = int(group["first_use_check_in"])
    logging.info(
        f"Found {len(machine_groups)} machine operator groups with a configured first use check in"
    )

    # Convert number of days (longest_check_in) to unix timestamp starting from the beginning of the day
    current_time = int(time.time())
    longest_check_in_timestamp = (
        current_time - (current_time % 86400) - longest_check_in * 86400
    )
    print(longest_check_in_timestamp)
    # Check recent messages for sign offs that need to be checked in
    response = app.client.conversations_history(
        channel=config["slack"]["notification_channel"],
        oldest=str(longest_check_in_timestamp),
    )
    messages = response["messages"]
    logging.info(
        f'Found {len(messages)} messages in channel {config["slack"]["notification_channel"]} in the last {longest_check_in} days'
    )

    for message in messages:
        # Confirm the message is a sign off
        if "has been authorised" not in message["text"]:
            continue

        for machine in machine_groups:
            if machine_groups[machine]["name"] in message["text"]:
                logging.debug(
                    f"Found a message about {machine_groups[machine]['name']}"
                )

                # Check if the sign off occurred on the correct day
                sign_off_days_ago = (
                    current_time - int(float(message["ts"]))
                ) // 86400 + 1
                if sign_off_days_ago == int(
                    machine_groups[machine]["first_use_check_in"]
                ):
                    pprint(message["text"])
                    logging.debug(
                        f"Sign off occurred {sign_off_days_ago} days ago, which is the correct day"
                    )
                    operator_patten = re.compile(r"\(<@(\w+)>\)")
                    trainer_pattern = re.compile(r"by <@(\w*)>")

                    operator_search = operator_patten.search(message["text"])
                    trainer_search = trainer_pattern.search(message["text"])

                    if operator_search:
                        operator = operator_search.group(1)

                    if trainer_search:
                        trainer = trainer_search.group(1)

                    if not trainer:
                        logging.warning("No trainer found in message")
                        continue

                    # Look for replies to the message that indicate that the sign off has already been checked on

                    replies = app.client.conversations_replies(
                        channel=config["slack"]["notification_channel"],
                        ts=message["ts"],
                    )

                    for reply in replies["messages"]:
                        if (
                            "This induction was confirmed by" in reply["text"]
                            or "This induction was removed by" in reply["text"]
                        ):
                            logging.debug("This sign off has already been checked")
                            break
                    else:
                        # If no replies indicate that the sign off has been checked, send a message to the trainer
                        logging.info(
                            f"Sending a message to <@{trainer}> to follow up with <@{operator}>"
                        )
                        slackUtils.send(
                            app=app,
                            channel=config["slack"]["notification_channel"],
                            thread_ts=message["ts"],
                            message=f"Hey <@{trainer}>, can you please follow up with <@{operator}> about their recent sign off for {machine_groups[machine]['name']}? It's been {sign_off_days_ago} days since the sign off.",
                        )

                        # An auth will only match one machine
                        break
