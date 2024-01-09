# Script that generates a markdown report of memberships of specific TidyHQ groups

import os
import sys
import json
import requests
import datetime
import logging
from pprint import pprint
from typing import Any

from util import tidyhq


def get_group_info(id=None, name=None):
    group = None
    if not id and not name:
        logging.error("Provide either an ID or a group name")
        sys.exit(1)
    if id:
        group = tidyhq.query(cat="groups", config=config, term=id, cache=cache)

    elif name:
        for group_i in cache["groups"]:
            trim_group_i = cache["groups"][group_i]["label"].replace(
                "Machine Operator - ", ""
            )
            if trim_group_i == name:
                group = cache["groups"][group_i]
                break
        if not group:
            logging.debug(f'Could not find group with name "{name}" in cache')
            groups = tidyhq.query(cat="groups", config=config)
            for group_i in groups:
                trim_group_i = group_i["label"].replace("Machine Operator - ", "")
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
    name = group["label"].replace("Machine Operator - ", "")
    processed["name"] = name
    return processed


# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Load config from file
with open("config.json") as f:
    config: dict = json.load(f)

# Load the list of reports from file
with open("machines.json") as f:
    reports: dict = json.load(f)

# Load data from cache and check if it's still valid
with open("cache.json") as f:
    cache: dict = json.load(f)
    cache_epoch = int(cache.get("time", 0))
    if cache_epoch < datetime.datetime.now().timestamp() - config["cache_expiry"]:
        logging.info(f'Cache is older than {config["cache_expiry"]} seconds, refreshing')
        cache = {}
    elif "contacts" not in cache or "groups" not in cache:
        logging.info("Cache is missing contacts or groups, refreshing")
        cache = {}
    else:
        logging.info ("Loaded cache")

if not cache:
    logging.debug("Getting contacts from TidyHQ")
    cache["contacts"] = tidyhq.query(cat="contacts", config=config)
    logging.debug(f"Got {len(cache["contacts"])} contacts from TidyHQ")

    logging.debug("Getting groups from TidyHQ")
    cache["groups"] = tidyhq.query(cat="groups", config=config)

    logging.debug(f"Got {len(cache["groups"])} groups from TidyHQ")

    logging.debug("Writing cache to file")
    cache["time"] = datetime.datetime.now().timestamp()
    with open("cache.json", "w") as f:
        json.dump(cache, f)


if len(sys.argv) < 2:
    print("Usage: python3 operator_report.py [report name]")

    # Print a list of all reports if no report name is given and translate group IDs to names
    print("Available reports:")
    for report in reports:
        print(f"{report}")
        for group in reports[report]:
            info = get_group_info(group)
            print(f'\t{info["name"]} ({group})')
            for field in info:
                if field != "name":
                    print(f"\t\t{field}: {info[field]}")
        print("")
    print(
        "You can also use 'all' to get a list of operators from all groups. Each group will only be listed once and specific groups can be excluded by adding them to the 'exclude' list in machines.json"
    )

    sys.exit(1)

report_name = sys.argv[1]

if report_name == "all":
    # check for exclusion report
    if "exclude" not in reports.keys():
        exclusions = []
    else:
        exclusions = reports["exclude"]

    deduped_reports = []
    for report in reports:
        for group in reports[report]:
            if group not in deduped_reports and group not in exclusions:
                deduped_reports.append(group)
    report = deduped_reports
elif report_name not in reports:
    print(f"Report {report_name} not found in file")
    sys.exit(1)

else:
    report = reports[report_name]

# Index by contact instead
contacts_indexed = {}
machines = []

for group in report:
    info = get_group_info(id=group)
    machine_name = info["name"]
    machines.append(machine_name)
    for contact in tidyhq.find_users_in_group(
        group_id=group, contacts=cache["contacts"] # type: ignore
    ):
        contact_name = tidyhq.format_contact(contact=contact)
        if contact_name not in contacts_indexed:
            contacts_indexed[contact_name] = []
        contacts_indexed[contact_name].append(machine_name)

# Cache and index machines by name
machines_by_name = {}
for machine in machines:
    info = get_group_info(name=machine)
    machines_by_name[info["name"]] = machine

# Sort machines by name
machines = sorted(machines, key=lambda x: machines_by_name[x])


# Generate the report

# Generate header
header = "| Operator | "
for machine in machines:
    info = get_group_info(name=machine)
    if "url" in info:
        header += f'[{info["name"]}]({info["url"]}) {info.get("level","")}| '
    else:
        header += f'{info["name"]} {info.get("level","")}| '

lines = [header]


# Add separator
lines.append(f'| --- | {" | ".join(["---"] * len(machines))} |')

# Add each operator as a line
for operator in sorted(contacts_indexed):
    s = f"| {operator} | "
    for machine in machines:
        if machine in contacts_indexed[operator]:
            s += "✅ | "
        else:
            s += "❌ | "
    lines.append(s)

for line in lines:
    print(line)
