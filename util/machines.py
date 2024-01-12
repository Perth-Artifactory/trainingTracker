import json
from . import tidyhq
import logging


def all(cache, config, machines=None):
    # Load the list of reports from file
    if not machines:
        with open("machines.json") as f:
            categories: dict = json.load(f)
    else:
        categories = machines
    rich_categories = {}
    for category in categories:
        if category != "exclude":
            rich_categories[category] = []
            for machine in categories[category]:
                if machine not in categories.get("exclude", []):
                    rich_categories[category].append(
                        tidyhq.get_group_info(
                            id=machine,
                            config=config,
                            cache=cache,
                        )
                    )

    return rich_categories


def user(id, cache, config, machines=None):
    # Load the list of reports from file
    if not machines:
        with open("machines.json") as f:
            categories: dict = json.load(f)
    else:
        categories = machines

    # Check whether id is a Slack ID or a TidyHQ ID
    if id.startswith("U"):
        tidyhq_id = tidyhq.translate_slack_to_tidyhq(
            slack_id=id, cache=cache, config=config
        )
    else:
        tidyhq_id = id

    if not tidyhq_id:
        logging.debug(f"Could not find TidyHQ ID for {id}")
        return None

    in_groups = tidyhq.find_groups_for_user(
        contact=tidyhq.query(
            cat="contacts", config=config, term=tidyhq_id, cache=cache
        ),
        config=config,
    )
    if not in_groups:
        logging.debug(f"Translated {id} to {tidyhq_id}, but they are in no groups")
        return None

    authed_machines = {}
    for category in categories:
        for machine in categories[category]:
            if machine in in_groups:
                if category not in authed_machines:
                    authed_machines[category] = []
                authed_machines[category].append(machine)

    return authed_machines


def machine(machine_id, cache):
    users = tidyhq.find_users_in_group(group_id=machine_id, contacts=cache["contacts"])
    return users
