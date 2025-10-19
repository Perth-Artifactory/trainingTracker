import logging
from typing import Any
from copy import deepcopy as copy
from slack_sdk.web.client import WebClient  # for typing
from slack_bolt import App  # for typing
from pprint import pprint

from editable_resources import strings
from . import formatters, blocks, tidyhq
import time


# Set up logging

logger = logging.getLogger("formatters")


def send(
    message: str,
    app: App,
    channel: str | None = None,
    slack_id: str | None = None,
    thread_ts: str | None = None,
    blocks: list | None = None,
    metadata: dict | None = None,
) -> str | None:
    """Send a message to a Slack channel or user."""
    if not app:
        raise Exception("Global Slack client not provided")

    if not channel and not slack_id:
        return None

    if metadata:
        if "event_type" not in metadata or "event_payload" not in metadata:
            raise Exception("Metadata must contain event_type and event_payload")

    if slack_id and not channel:
        # Open a DM with the user to get the channel ID
        r = app.client.conversations_open(users=slack_id)
        channel = r.data["channel"]["id"]  # type: ignore

    # Prepare the parameters for the chat_postMessage call
    params = {
        "channel": channel,
        "text": message,
        "thread_ts": thread_ts,
        "blocks": blocks,
        "metadata": metadata,
    }

    # Remove keys with None values
    params = {k: v for k, v in params.items() if v is not None}

    response = app.client.chat_postMessage(**params)

    return response.data["ts"]  # type: ignore


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


def notify_training(
    action: str,
    trainee: str,
    trainee_formatted: str,
    trainee_slack_id: str | None,
    machine_info: dict,
    config: dict,
    trainer: str,
    app: App,
) -> bool:
    """Notify Slack channel and trainee of training changes."""

    message = f"{'✅' if action == 'add' else '🚫'}{trainee_formatted} has been {'authorised' if action == 'add' else 'deauthorised'} for {machine_info['name']} ({machine_info.get('level', '⚪')}) by <@{trainer}>"

    # Send a notification to the training channel
    thread_ts = send(
        app=app,
        channel=config["slack"]["notification_channel"],
        message=message,
        metadata={
            "event_type": f"training_{action}",
            "event_payload": {
                "trainer": trainer,
                "operator": trainee,
                "machine": machine_info["id"],
                "action": action,
            },
        },
    )

    # Log the change to file
    with open("tidyhq_changes.log", "a") as f:
        f.write(f"{time.time()},{trainer},{action},{trainee},{machine_info['id']}\n")

    # Check if this tool requires a follow up check in
    if "first_use_check_in" in machine_info.keys() and action == "add":
        send(
            app=app,
            channel=config["slack"]["notification_channel"],
            message="This tool needs a follow up",
            blocks=formatters.follow_up_buttons(
                machine=machine_info,
                follow_up_days=machine_info["first_use_check_in"],
                operator_id=trainee_slack_id if trainee_slack_id else trainee,
                trainer_id=trainer,
                has_slack=trainee_slack_id is not None,
            ),
            thread_ts=thread_ts,
        )

    # Check if this tool has a trainee message to send
    if "trainee_message" in machine_info.keys() and action == "add":
        logging.info(f"Sending trainee message for {machine_info['name']}")

        if machine_info["trainee_message"] in strings.trainee_messages:
            message = strings.trainee_messages[machine_info["trainee_message"]]

            message = message.format(
                trainer=trainer,
                trainee_slack_id=trainee_slack_id,
                trainee_tidyhq_id=trainee,
                trainee_name=trainee_formatted,
                machine=machine_info["name"],
            )

            # Send the message to the trainee
            if trainee_slack_id:
                send(message=message, app=app, slack_id=trainee_slack_id)

            # Add a note to the sign off message
            if thread_ts:
                send(
                    app=app,
                    channel=config["slack"]["notification_channel"],
                    message=f"A post training message has been sent to {trainee_formatted}",
                    thread_ts=thread_ts,
                )
        else:
            logging.error(
                f"Trainee message {machine_info['trainee_message']} not found in strings.trainee_messages"
            )

    return True
