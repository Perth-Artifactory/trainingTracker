import logging
from typing import Any
from copy import deepcopy as copy
from slack_sdk.web.client import WebClient  # for typing
from pprint import pprint
from . import formatters, blocks, tidyhq

# Set up logging

logger = logging.getLogger("formatters")


def send(message: str, app, channel=None, thread_ts=None, blocks=None) -> Any:
    if not app:
        raise Exception("Global Slack client not provided")

    if not channel:
        return None

    # Prepare the parameters for the chat_postMessage call
    params = {
        "channel": channel,
        "text": message,
        "thread_ts": thread_ts,
        "blocks": blocks,
    }

    # Remove keys with None values
    params = {k: v for k, v in params.items() if v is not None}

    response = app.client.chat_postMessage(**params)

    return response.data["ts"]


def check_trainer(user, config, app=None, client=None):
    if app:
        r = app.client.usergroups_list(include_users=True)
    elif client:
        r = client.usergroups_list(include_users=True)
    else:
        raise Exception("Must provide either app or client")

    groups: list[dict[str, Any]] = r.data["usergroups"]
    for group in groups:
        if group["id"] in config["slack"]["trainers"]:
            if user in group["users"]:
                return True
    return False


def updateHome(
    user: str,
    client: WebClient,
    config,
    cache,
    machine_raw=None,
) -> None:
    home_view = {
        "type": "home",
        "blocks": formatters.home(
            user=user,
            config=config,
            client=client,
            cache=cache,
            machine_raw=machine_raw,
        ),
    }
    client.views_publish(user_id=user, view=home_view)


def authed_tools_modal(user, config, client, cache, categories, trigger, machine_list):
    modal = formatters.authed_machines_modal(
        user=user,
        config=config,
        client=client,
        cache=cache,
        categories=categories,
        machine_list=machine_list,
    )

    client.views_open(trigger_id=trigger, view=modal)


def trainer_authed_tools_modal(
    user, config, client, cache, trigger, machine_list, view_id=None
):
    modal = formatters.trainer_check_authed_machines_modal(
        user=user,
        config=config,
        client=client,
        cache=cache,
        machine_list=machine_list,
    )

    client.views_open(trigger_id=trigger, view=modal)


def trainer_change_authed_machines_modal(
    user, config, client, cache, trigger, machine_list, action, view_id
):
    modal = formatters.trainer_change_authed_machines_modal(
        user=user,
        config=config,
        client=client,
        cache=cache,
        machine_list=machine_list,
        action=action,
    )

    if modal:
        modal["private_metadata"] = f"{action}-{user}"

        client.views_push(trigger_id=trigger, view=modal)


def select_user_modal(user, config, client, cache, trigger):
    modal = formatters.select_users_modal(
        user=user,
        config=config,
        client=client,
        cache=cache,
    )

    client.views_open(trigger_id=trigger, view=modal)


def tool_selector_modal(config, client, cache, trigger, machine_list):
    modal = formatters.tool_selector_modal(
        config=config,
        client=client,
        cache=cache,
        machine_list=machine_list,
    )

    client.views_open(trigger_id=trigger, view=modal)


def machine_report_modal(
    config, client, cache, trigger, machine_list, machine, view_id
):
    modal = formatters.machine_report_modal(
        config=config, cache=cache, machine_list=machine_list, machine=machine
    )

    client.views_open(trigger_id=trigger, view=modal)


def get_name(id, client: WebClient) -> str:
    r = client.users_info(user=id)
    return r.data["user"]["profile"]["display_name"]  # type: ignore


def inject_text(block_list, text) -> dict[Any, Any] | list[Any] | Any:
    block_list = copy(block_list)
    if type(blocks) == dict:
        if "type" not in block_list:
            if "text" in block_list:
                if "text" in block_list["text"]:
                    block_list["text"]["text"] = text
        elif block_list["type"] in ["section", "header"]:
            block_list["text"]["text"] = text
        elif block_list["type"] == "context":
            block_list["elements"][0]["text"] = text
        elif block_list["type"] == "modal":
            block_list["title"]["text"] = text
        elif block_list["type"] == "input":
            block_list["label"]["text"] = text
        elif block_list["type"] == "multi_static_select":
            block_list["placeholder"]["text"] = text
    elif type(block_list) == list:
        if block_list[-1]["type"] in ["section", "header"]:
            block_list[-1]["text"]["text"] = text
        elif block_list[-1]["type"] == "context":
            block_list[-1]["elements"][0]["text"] = text
        elif block_list[-1]["type"] == "modal":
            block_list[-1]["title"]["text"] = text
    return block_list


def inject_button(actions: dict, text, value, action_id, style=None):
    actions = copy(actions)
    button = copy(blocks.button)
    button["text"]["text"] = text
    button["value"] = value
    button["action_id"] = action_id
    if style:
        button["style"] = style
    actions["elements"].append(button)
    return actions


def inject_element(body, element, action_id=None):
    body = copy(body)
    if "type" not in body:
        if "value" in body:
            body["value"] = element
    elif body["type"] == "input":
        body["element"] = element
    elif body["type"] == "multi_static_select":
        body["options"].append(element)
        body["action_id"] = action_id
    return body


def add_block(block_list: list, block: list | dict) -> list[Any]:
    block_list = copy(block_list)
    if type(block) == dict:
        block_list.append(block)
    elif type(block) == list:
        block_list += block
    return block_list


def is_trainer(user, client, config):
    r = client.usergroups_list(include_users=True)
    groups = r.data["usergroups"]
    for group in groups:
        if group["id"] in config["slack"]["trainers"]:
            if user in group["users"]:
                return True
    return False
