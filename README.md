# trainingTracker

## Setup

* Ensure that TidyHQ credentials have been set in `config.json`
* `cp machines.json.example machines.json`
  * Configure at least one report. Report names should be alphanumeric.
  * Groups in TidyHQ that have a description set will be parsed for information. Each provided parameter should be on a new line and presented as `key=value`. Supported info is:
    * `url` = When this group appears as the header to a column it will be linked to this page. No checking is done on the content of the field so it supports internal/external/relative/absolute links.
    * `level` = Included after the name of a group/tool if present. Field can include unicode characters eg 🔴🟡🟢

## Report Generation

Formats a markdown table of approved operators based on whether a contact is in a configured TidyHQ group.

Passing the special report name "all" will generate a report including a deduplicated list of all other reports. Specific groups can be excluded from this report by adding them to the special "exclude" group.

`markdown_report.py` will output a list of possible reports including their contents with human readable names rather than just IDs. The script will exit with an error code to catch it being executed without a report name accidentally in automations.

`markdown_report.py report_name` will output a markdown formatted table. It explicitly does not include a "generated on" line so that it doesn't trigger unnecessary page changes.

This can be used to push a report by:

* Cloning the wiki
* `sed -i '11,$ d' path/to/wiki_page` - Remove the contents of the page after the header (header is typically 10 lines)
* `python3 operator_report.py report_name >> path/to/wiki_page`
* Commit the changed file
