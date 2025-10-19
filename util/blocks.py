from editable_resources import strings

divider = [{"type": "divider"}]
base_text = {"type": "mrkdwn", "text": ""}
text = [{"type": "section", "text": base_text}]
context = [
    {
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": ""}],
    }
]
header = [{"type": "header", "text": {"type": "plain_text", "text": "", "emoji": True}}]
actions = {"type": "actions", "elements": []}
button = {
    "type": "button",
    "text": {"type": "plain_text", "text": "", "emoji": True},
    "value": "",
    "action_id": "",
}
modal = {
    "type": "modal",
    "title": {"type": "plain_text", "text": "", "emoji": True},
    "blocks": [],
}

input_wrapper = {
    "type": "input",
    "element": {},
    "label": {"type": "plain_text", "text": "", "emoji": True},
}

multi_static_select = {
    "type": "multi_static_select",
    "placeholder": {"type": "plain_text", "text": "", "emoji": True},
    "options": [],
    "action_id": "",
}

single_static_select = {
    "type": "static_select",
    "placeholder": {"type": "plain_text", "text": "", "emoji": True},
    "options": [],
    "action_id": "",
}

static_select_option = {
    "text": {
        "type": "plain_text",
        "text": "",
        "emoji": True,
    },
    "value": "",
}

option_group = {
    "label": {"type": "plain_text", "text": ""},
    "options": [],
}

external_select = {
    "type": "external_select",
    "action_id": "",
    "placeholder": {
        "type": "plain_text",
        "text": "",
    },
    "min_query_length": 0,
}

check_box_container = {
    "type": "section",
    "text": {"type": "mrkdwn", "text": ""},
    "accessory": {"type": "checkboxes", "options": [], "action_id": ""},
}

check_box = {
    "text": {"type": "mrkdwn", "text": ""},
    "description": {"type": "mrkdwn", "text": ""},
    "value": "",
}

number_input = {"type": "number_input", "is_decimal_allowed": False, "action_id": ""}
