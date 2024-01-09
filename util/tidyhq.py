from typing import Literal
import requests
import logging
import sys
from pprint import pprint


def find_users_in_group(group_id, contacts: list) -> list[dict]:
    # Group endpoint doesn't return contacts, so we have to iterate over all contacts and check their groups
    c = []
    for contact in contacts:
        for group in contact["groups"]:
            if group["id"] == group_id:
                c.append(contact)
    return c


def format_contact(contact: dict) -> str:
    n = ""
    if contact["nick_name"]:
        n = f' ({contact["nick_name"]})'
    return (
        f'{contact["first_name"].capitalize()} {contact["last_name"].capitalize()}{n}'
    )


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

    if type == "groups" and not term:
        # Index groups by ID
        groups_indexed = {}
        for group in data:
            groups_indexed[group["id"]] = group
        return groups_indexed

    return data
