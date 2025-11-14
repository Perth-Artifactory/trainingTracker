# Script that generates a markdown report of memberships of specific TidyHQ groups

import os
import sys
import json
import requests
import datetime
import logging
from pprint import pprint
from typing import Any

from util import tidyhq, machines

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Load config from file
with open("config.json") as f:
    config: dict = json.load(f)

cache = tidyhq.fresh_cache(config=config)

# Build the list of reports from TidyHQ
reports = machines.build_from_tidyhq(config=config, cache=cache)

if len(sys.argv) < 2:
    print("Usage: python3 operator_report.py [report name]")

    # Print a list of all reports if no report name is given and translate group IDs to names
    print("Available reports:")
    for report in reports:
        print(f"{report}")
        for group in reports[report]:
            info = tidyhq.get_group_info(cache=cache, id=group, config=config)
            print(f"\t{info['name']} ({group})")
            for field in info:
                if field != "name":
                    print(f"\t\t{field}: {info[field]}")
        print("")
    print(
        "You can also use 'all' to get a list of operators from all groups. Each group will only be listed once and you can exclude groups by adding them to the exclude category"
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
    info = tidyhq.get_group_info(id=group, cache=cache, config=config)
    machine_name = info["name"]
    machines.append(machine_name)
    for contact in tidyhq.find_users_in_group(
        group_id=group,
        contacts=cache["contacts"],  # type: ignore
    ):
        contact_name = tidyhq.format_contact(contact=contact)
        if contact_name not in contacts_indexed:
            contacts_indexed[contact_name] = []
        contacts_indexed[contact_name].append(machine_name)

# Cache and index machines by name
machines_by_name = {}
for machine in machines:
    info = tidyhq.get_group_info(name=machine, cache=cache, config=config)
    machines_by_name[info["name"]] = machine

# Sort machines by name
machines = sorted(machines, key=lambda x: machines_by_name[x])


# Generate the report

# Generate header
header = "| Operator | "
for machine in machines:
    info = tidyhq.get_group_info(name=machine, cache=cache, config=config)
    if "url" in info:
        header += f"[{info['name']}]({info['url']}) {info.get('level', '')}| "
    else:
        header += f"{info['name']} {info.get('level', '')}| "

lines = [header]


# Add separator
lines.append(f"| --- | {' | '.join(['---'] * len(machines))} |")

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
