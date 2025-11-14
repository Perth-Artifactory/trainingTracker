import json
from . import tidyhq
import logging

# Set up logging
logger = logging.getLogger("machines")


def all(cache, config, machines):
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


def user(id, cache, config, machines):
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


def build_from_tidyhq(cache: dict, config: dict) -> dict[str, list[int]]:
    """Build a machine list from TidyHQ groups."""

    machine_list = {}
    machine_count = 0
    for group_id in cache["groups"]:
        # filter to only those that are current operator groups
        if cache["groups"][group_id]["label"].startswith(
            config["tidyhq"]["group_prefix"]
        ):
            machine_info = tidyhq.get_group_info(
                id=group_id, cache=cache, config=config
            )
            current_categories = machine_info.get("categories", None)
            if not current_categories:
                continue
            else:
                machine_count += 1
                for section in current_categories.split(","):
                    if section not in machine_list:
                        machine_list[section] = []
                    machine_list[section].append(int(group_id))
    logger.info(
        f"Constructed machine list with {machine_count} machines in {len(machine_list)} categories"
    )

    return machine_list
