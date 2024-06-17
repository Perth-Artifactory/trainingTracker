# Generate a summary of current members with inductions and identify users that have not been inducted on anything yet

import os
import sys
import json
import datetime
import requests
from util import tidyhq, tidyauth
from pprint import pprint
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# If html_embed is passed as an argument then don't include any logging
if "html_embed" in sys.argv:
    logging.disable(logging.CRITICAL)

# Load the config file
with open("config.json", "r") as f:
    config = json.load(f)

# Load a cache of tidyhq data
cache = tidyhq.setup_cache(config)

# Detect all induction groups
all_groups = tidyhq.find_all_groups(config=config, cache=cache)
logging.info(f"Found {len(all_groups)} groups")

# Get a list of members

memberships = tidyhq.query(cat="memberships", term=None, config=config)
logging.info(f"Found {len(memberships)} memberships")

members = []

for membership in memberships:
    if (
        membership["state"] != "expired"
        and membership["membership_level"]["name"] != "Visitor"
    ):
        members.append(membership["adult_members"][0]["contact_id"])

logging.info(f"Found {len(members)} members")

lines = []
table_data = []
for member in members:
    row = []
    member_info = tidyhq.get_contact(contact_id=member, cache=cache)
    if type(member_info) != dict:
        sys.exit()
    name = tidyhq.format_contact(contact=member_info)
    lines.append(name)
    row.append(name)

    # Find all inductions for this member
    inductions = tidyhq.find_groups_for_user(contact=member_info, config=config)
    row.append(len(inductions))

    percentage = round(len(inductions) / len(all_groups) * 100)
    row.append(f"{percentage}%")
    lines.append(f"Inductions: {percentage}% ({len(inductions)}/{len(all_groups)})")

    table_data.append(row)

# Sort the table data by the number of inductions
table_data.sort(key=lambda x: x[1], reverse=True)

# This report is ingested by other scripts if html_embed is passed as a command line argument
if "html_embed" in sys.argv:
    # Add header
    header = ["Name", "Inductions", f"% of {len(all_groups)}"]
    table_data.insert(0, header)
    print(tidyauth.report_formatter(data=[{"table": table_data}], dtype="html_embed"))
else:
    for line in lines:
        print(line)
