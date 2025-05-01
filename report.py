# Generate a summary of current members with inductions and identify users that have not been inducted on anything yet

import os
import sys
import json
import datetime
import requests
from util import tidyhq
from util import tidyauth  # type: ignore
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

# Calculate total number of inductions
total_inductions = 0
induction_counts = {}
for group in all_groups:
    users = tidyhq.find_users_in_group(group_id=group, contacts=cache["contacts"])
    total_inductions += len(users)
    induction_counts[group] = len(users)

# Get a list of members

memberships = tidyhq.query(cat="memberships", term=None, config=config)
logging.info(f"Found {len(memberships)} memberships")

members = []
members_by_date = {}

for membership in memberships:
    if (
        membership["state"] != "expired"
        and membership["membership_level"]["name"] != "Visitor"
        and "band" not in membership["membership_level"]["name"].lower()
        and "ambassador" not in membership["membership_level"]["name"].lower()
    ):
        member = membership["adult_members"][0]

        members.append(member["contact_id"])

        # Prioritise older membership
        new_date = datetime.datetime.strptime(member["member_since"], "%Y-%m-%d")

        if member["contact_id"] not in members_by_date:
            members_by_date[member["contact_id"]] = {"since": new_date}
        else:
            if new_date < members_by_date[member["contact_id"]]["since"]:
                members_by_date[member["contact_id"]]["since"] = new_date

# dedupe members
members = list(set(members))

# Add days since to members by date
for member in members_by_date:
    members_by_date[member]["days_since"] = (
        datetime.datetime.now() - members_by_date[member]["since"]
    ).days

logging.info(f"Found {len(members)} members")

lines = []
table_data = []
for member in members:
    row = []
    member_info = tidyhq.get_contact(contact_id=member, cache=cache)
    if type(member_info) is not dict:
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

    # Add the inductions/name to the members_by_date dict
    if member not in members_by_date:
        continue
    members_by_date[member]["inductions"] = inductions
    members_by_date[member]["name"] = name

# Sort the table data by the number of inductions
table_data.sort(key=lambda x: x[1], reverse=True)

# Calculate some basic statistics about induction distribution
current_inductions = [x[1] for x in table_data]
average_inductions = sum(current_inductions) / len(members)

stat_table_data = []
stat_table_data.append(["", ""])
stat_table_data.append(["Total current members", len(members)])
stat_table_data.append(
    ["Average inductions of current members", round(average_inductions)]
)
stat_table_data.append(["Total inductions", total_inductions])
stat_table_data.append(
    ["Total inductions for current members", sum(current_inductions)]
)
stat_table_data.append(
    [
        "Total inductions for non members (or past members)",
        total_inductions - sum(current_inductions),
    ]
)

# distribution of inductions by percentage (10% increments)
distribution = {}
for row in table_data:
    percentage = int(row[2].replace("%", ""))
    if percentage == 0:
        bucket = 0
    elif percentage < 10:
        bucket = 1
    else:
        bucket = (percentage // 10) * 10  # Calculate the bucket for the 10% increment
    if bucket not in distribution:
        distribution[bucket] = 0
    distribution[bucket] += 1

distribution_table_data = []
distribution_table_data.append(
    ["Range", "Number of members", "Percentage of total members"]
)
for key in sorted(distribution.keys()):
    if key == 0:
        distribution_table_data.append(
            [
                "0%",
                distribution[key],
                f"{round(distribution[key] / len(members) * 100)}%",
            ]
        )
    else:
        distribution_table_data.append(
            [
                f"{key}-{key + 9}%",
                distribution[key],
                f"{round(distribution[key] / len(members) * 100)}%",
            ]
        )

# Calculate distributions for how many people are inducted on each tool
# This is useful for identifying tools that are not being used
# Splitting into buckets of 5 and a separate bucket for 0
tool_distribution = {}
for group in induction_counts.keys():
    count = induction_counts[group]
    if count == 0:
        bucket = 0  # Separate bucket for 0
    else:
        bucket = (
            (count - 1) // 5 + 1
        ) * 5  # Buckets of 5, adjusting for 1-based indexing
    if bucket not in tool_distribution:
        tool_distribution[bucket] = 0
    tool_distribution[bucket] += 1

tool_distribution_table_data = []
tool_distribution_table_data.append(["Range", "Tools"])

for key in sorted(tool_distribution.keys()):
    if key == 0:
        label = "0 inducted users"
    else:
        start_range = (
            key - 4 if key != 5 else 1
        )  # Adjust start range for the first bucket
        label = f"{start_range}-{key} inducted users"
    tool_distribution_table_data.append([label, tool_distribution[key]])


# Show members without member inductions
member_induction_table_data = []
member_induction_table_data.append(["Member", "Membership age"])

# iterate over members_by_date oldest first
for member in sorted(
    members_by_date.keys(),
    key=lambda x: members_by_date[x]["days_since"],
):
    if 174897 in members_by_date[member]["inductions"]:
        continue

    # Convert days_since to a useful string that includes months/years if applicable
    days = members_by_date[member]["days_since"]
    if days < 30:
        days_str = f"{days} day{'s' if days != 1 else ''}"
    elif days < 365:
        months = days // 30
        days_str = f"{months} month{'s' if months != 1 else ''}, {days % 30} day{'s' if days % 30 != 1 else ''}"
    else:
        years = days // 365
        months = (days % 365) // 30
        if months == 0:
            days_str = f"{years} year{'s' if years != 1 else ''}, {days % 365} day{'s' if days % 365 != 1 else ''}"
        else:
            days_str = f"{years} year{'s' if years != 1 else ''}, {months} month{'s' if months != 1 else ''}"

    member_induction_table_data.append([members_by_date[member]["name"], days_str])


# This report is ingested by other scripts if html_embed is passed as a command line argument
if "html_embed" in sys.argv:
    # Add header
    header = ["Name", "Inductions", f"% of {len(all_groups)}"]
    table_data.insert(0, header)
    print(
        tidyauth.report_formatter(
            data=[
                {"title": "Basic stats", "table": stat_table_data},
                {
                    "title": "Individual sign-off distribution",
                    "table": distribution_table_data,
                },
                {
                    "title": "Tool induction distribution",
                    "table": tool_distribution_table_data,
                },
                {"title": "Individual Members", "table": table_data},
                {
                    "title": "Members without member induction",
                    "table": member_induction_table_data,
                },
            ],
            dtype="html_embed",
        )
    )
else:
    for line in lines:
        print(line)
