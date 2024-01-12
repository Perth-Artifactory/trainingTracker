from typing import Literal
import requests
import logging
import sys
from pprint import pprint
import datetime
from typing import Any
import json
from copy import deepcopy as copy


def find_users_in_group(group_id, contacts: list) -> list[dict]:
    # Group endpoint doesn't return contacts, so we have to iterate over all contacts and check their groups
    c = []
    for contact in contacts:
        for group in contact["groups"]:
            if int(group["id"]) == int(group_id):
                c.append(contact)
    return c


def find_groups_for_user(contact, config):
    groups = []
    for group in contact["groups"]:
        if config["tidyhq"]["group_prefix"] in group["label"]:
            groups.append(group["id"])
    return groups


def format_contact(contact: dict, slack: bool = False, config={}) -> str:
    n = ""
    s = ""
    if contact["nick_name"]:
        n = f' ({contact["nick_name"]})'

    if slack and config:
        # Check if the user has a slack ID
        for field in contact["custom_fields"]:
            if field["id"] == config["tidyhq"]["ids"]["slack"]:
                if field["value"]:
                    s = f' <@{field["value"]}>'
                    break
    elif slack and not config:
        logging.error("No config provided")

    return f'{contact["first_name"].capitalize()} {contact["last_name"].capitalize()}{n}{s}'


def get_contact(contact_id, cache):
    if type(contact_id) == str:
        try:
            contact_id = int(contact_id)
        except:
            pass

    for contact in cache["contacts"]:
        if contact["id"] == contact_id:
            return contact
    return None


def query(
    cat: str | int,
    config: dict,
    term: str | Literal[None] = None,
    cache: dict | Literal[None] = None,
):
    if type(term) == int:
        term = str(term)

    # If we have a cache, try using that first before querying TidyHQ
    if cache:
        if cat in cache:
            # Groups are indexed by ID before being cached
            if cat == "groups":
                if term:
                    if term in cache["groups"]:
                        return cache["groups"][term]
                    else:
                        try:
                            if int(term) in cache["groups"]:
                                return cache["groups"][int(term)]
                        except:
                            pass
                    # If we can't find the group, handle via query instead
                    logging.debug(f"Could not find group with ID {term} in cache")
                else:
                    return cache["groups"]
            elif type == "contacts":
                if term:
                    for contact in cache["contacts"]:
                        if contact["id"] == term:
                            return contact
                    # If we can't find the contact, handle via query
                    logging.debug(f"Could not find contact with ID {term} in cache")
                else:
                    return cache["contacts"]

    append = ""
    if term:
        append = f"/{term}"

    logging.debug(f"Querying TidyHQ for {cat}{append}")
    try:
        r = requests.get(
            f"https://api.tidyhq.com/v1/{cat}{append}",
            params={"access_token": config["tidyhq"]["token"]},
        )
        data = r.json()
    except requests.exceptions.RequestException as e:
        logging.error("Could not reach TidyHQ")
        sys.exit(1)

    if cat == "groups" and not term:
        # Index groups by ID
        groups_indexed = {}
        for group in data:
            groups_indexed[group["id"]] = group
        return groups_indexed

    return data


def get_group_info(
    config: dict, id=None, name=None, cache: dict | Literal[None] = None
):
    group = None
    if not id and not name:
        logging.error("Provide either an ID or a group name")
        sys.exit(1)
    if id:
        group = query(cat="groups", config=config, term=id, cache=cache)

    elif name and cache:
        for group_i in cache["groups"]:
            trim_group_i = cache["groups"][group_i]["label"].replace(
                config["tidyhq"]["group_prefix"], ""
            )
            if trim_group_i == name:
                group = cache["groups"][group_i]
                break
        if not group:
            logging.debug(f'Could not find group with name "{name}" in cache')
            groups = query(cat="groups", config=config)
            for group_i in groups:
                trim_group_i = group_i["label"].replace(
                    config["tidyhq"]["group_prefix"], ""
                )
                if trim_group_i == name:
                    group = group_i
                    break
            if not group:
                logging.error(f'Could not find group with name "{name}"')
                sys.exit(1)

    if not group:
        logging.error(f'Trouble getting info for group "{name}"')
        sys.exit(1)

    processed = {}
    if group["description"]:
        desc_lines = group["description"].split("\n")
        for line in desc_lines:
            if "=" in line:
                key, value = line.split("=", maxsplit=1)
                processed[key.strip()] = value.strip()
    name = group["label"].replace(config["tidyhq"]["group_prefix"], "")
    processed["name"] = name
    processed["id"] = group["id"]
    return processed


def setup_cache(config) -> dict[str, Any]:
    cache = {}
    logging.debug("Getting contacts from TidyHQ")
    raw_contacts = query(cat="contacts", config=config)
    logging.debug(f"Got {len(raw_contacts)} contacts from TidyHQ")

    logging.debug("Getting groups from TidyHQ")
    cache["groups"] = query(cat="groups", config=config)

    logging.debug(f'Got {len(cache["groups"])} groups from TidyHQ')

    # Trim contact data to just what we need
    cache["contacts"] = []
    useful_fields = [
        "contact_id",
        "custom_fields",
        "first_name",
        "groups",
        "id",
        "last_name",
        "nick_name",
    ]

    for contact in raw_contacts:
        trimmed_contact = copy(contact)

        # Get rid of fields we don't need
        for field in contact:
            if field not in useful_fields:
                del trimmed_contact[field]

        # Get rid of groups we don't need
        useful_groups = []
        for group in trimmed_contact["groups"]:
            if config["tidyhq"]["group_prefix"] in group["label"]:
                useful_groups.append(group)
        trimmed_contact["groups"] = useful_groups

        # Get rid of custom fields we don't need
        useful_custom_fields = []
        for field in trimmed_contact["custom_fields"]:
            if field["id"] in config["tidyhq"]["ids"].values():
                useful_custom_fields.append(field)
        trimmed_contact["custom_fields"] = useful_custom_fields

        cache["contacts"].append(trimmed_contact)

    logging.debug("Writing cache to file")
    cache["time"] = datetime.datetime.now().timestamp()
    with open("cache.json", "w") as f:
        json.dump(cache, f)

    return cache


def translate_slack_to_tidyhq(slack_id: str, cache: dict, config: dict):
    for contact in cache["contacts"]:
        # Iterate over custom fields
        for field in contact["custom_fields"]:
            if field["id"] == config["tidyhq"]["ids"]["slack"]:
                if field["value"] == slack_id:
                    return contact["id"]
    return None


def fresh_cache(cache=None, config=None, force=False) -> dict[str, Any]:
    if not config:
        with open("config.json") as f:
            logging.debug("Loading config from file")
            config = json.load(f)

    if cache:
        # Check if the cache we've been provided with is fresh
        if (
            cache["time"] < datetime.datetime.now().timestamp() - config["cache_expiry"]
            or force
        ):
            logging.debug("Provided cache is stale")
        else:
            # If the provided cache is fresh, just return it
            return cache

    # If we haven't been provided with a cache, or the provided cache is stale, try loading from file
    try:
        with open("cache.json") as f:
            cache = json.load(f)
    except FileNotFoundError:
        logging.debug("No cache file found")
        cache = setup_cache(config=config)
        return cache

    # If the cache file is also stale, refresh it
    if (
        cache["time"] < datetime.datetime.now().timestamp() - config["cache_expiry"]
        or force
    ):
        logging.debug("Cache file is stale")
        cache = setup_cache(config=config)
        return cache
    else:
        logging.debug("Cache file is fresh")
        return cache


def is_member(contact):
    pass


def list_all(cache, config):
    contacts = []
    for contact in cache["contacts"]:
        # Iterate over custom fields
        for field in contact["custom_fields"]:
            if field["id"] == config["tidyhq"]["ids"]["slack"]:
                contacts.append(contact["id"])
    return contacts


def update_group_membership(tidyhq_id, group_id, action, config):
    if action not in ["add", "remove"]:
        logging.error("Action must be either 'add' or 'remove'")
        return False

    if action == "add":
        r = requests.put(
            f"https://api.tidyhq.com/v1/groups/{group_id}/contacts/{tidyhq_id}",
            params={"access_token": config["tidyhq"]["token"]},
        )

    else:
        r = requests.delete(
            f"https://api.tidyhq.com/v1/groups/{group_id}/contacts/{tidyhq_id}",
            params={"access_token": config["tidyhq"]["token"]},
        )

    if r.status_code == 204:  # Success
        return True
    else:
        logging.error(f"Error updating group membership: {r.status_code}")
        return False
