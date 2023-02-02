# builtin modules
from copy import copy
import os
import os.path
from pathlib import Path
import shutil
import subprocess
import uuid

# third-party modules
import pytest
from dateutil import tz
from slugify import slugify

click_up_timereport = __import__("click-up-timereport")

# using pre-installed 'requests_mock' contribute module without needing to import it

# This is run by .github/workflows/ci.yml :)

EXECUTABLE_UNDER_TEST = "click-up-timereport.py"
ARTIFACTS_DIRECTORY = "artifacts"  # no trailing slash
ARTIFACTS_DIRECTORY_CLI = "artifacts-cli"  # no trailing slash
DEFAULT_TEAM_ID = "1234"
DEFAULT_CLICKUP_TOKEN = "anytoken"
DEFAULT_INPUT_JSON_PATH = "examples/example1.json"
DEFAULT_TASK_ID = "1vwwavv"
DEFAULT_TASK_NAME = "Develop Python"
DEFAULT_FROM_DATE = "2023-01-01"
DEFAULT_TO_DATE = "2023-01-31"
DEFAULT_TASK_JSON = {
    "id": DEFAULT_TASK_ID,
    "custom_id": "string",
    "name": DEFAULT_TASK_NAME,
    "text_content": "string",
    "description": "string",
    "status": {
        "status": "in progress",
        "color": "#d3d3d3",
        "orderindex": 1,
        "type": "custom",
    },
    "orderindex": "string",
    "date_created": "string",
    "date_updated": "string",
    "date_closed": "string",
    "creator": {
        "id": 183,
        "username": "John Doe",
        "color": "#827718",
        "profilePicture": "https://attachments-public.clickup.com/profilePictures/183_abc.jpg",
    },
    "assignees": ["string"],
    "checklists": ["string"],
    "tags": ["string"],
    "parent": "string",
    "priority": "string",
    "due_date": "string",
    "start_date": "string",
    "time_estimate": "string",
    "time_spent": "string",
    "custom_fields": [
        {
            "id": "string",
            "name": "string",
            "type": "string",
            "type_config": {},
            "date_created": "string",
            "hide_from_guests": True,
            "value": {
                "id": 183,
                "username": "John Doe",
                "email": "john@example.com",
                "color": "#7b68ee",
                "initials": "JD",
                "profilePicture": None,
            },
            "required": True,
        }
    ],
    "list": {"id": "123"},
    "folder": {"id": "456"},
    "space": {"id": "789"},
    "url": "string",
}
DEFAULT_TIME_ENTRIES_JSON = {
    "data": [
        {
            "id": "1963465985517105840",
            "task": {
                "id": "1vwwavv",
                "custom_id": "JOSH-917",
                "name": "woof",
                "status": {
                    "status": "open yes",
                    "color": "#d3d3d3",
                    "type": "open",
                    "orderindex": 0,
                },
                "custom_type": None,
            },
            "wid": "300702",
            "user": {
                "id": 1,
                "username": "first_name last_name",
                "email": "test@gmail.com",
                "color": "#08c7e0",
                "initials": "JK",
                "profilePicture": "https://dev-attachments-public.clickup.com/profilePictures/1_HHk.jpg",
            },
            "billable": False,
            "start": 1592841559129,
            "end": 1592845899021,
            "duration": "4339892",
            "description": "",
            "tags": [],
            "source": "clickup",
            "at": "1592845899021",
            "task_location": {
                "list_id": 1560300071,
                "folder_id": 468300080,
                "space_id": 22800253,
                "list_name": "List",
                "folder_name": "Folder",
                "space_name": "Space",
            },
            "task_tags": [
                {
                    "name": "content-request",
                    "tag_fg": "#800000",
                    "tag_bg": "#2ecd6f",
                    "creator": 301828,
                },
                {
                    "name": "marketing-okr",
                    "tag_fg": "#800000",
                    "tag_bg": "#7C4DFF",
                    "creator": 301828,
                },
            ],
            "task_url": "https://staging.clickup.com/t/1vwwavv",
        }
    ]
}
DEFAULT_USER_TEAMS_JSON = {
    "teams": [
        {
            "id": "1234",
            "name": "My ClickUp Workspace",
            "color": "#000000",
            "avatar": "https://clickup.com/avatar.jpg",
            "members": [
                {
                    "user": {
                        "id": 123,
                        "username": "John Doe",
                        "color": "#000000",
                        "profilePicture": "https://clickup.com/avatar.jpg",
                    }
                }
            ],
        }
    ]
}


def get_output_filename_from_locals(input_vars, output_format, for_cli=False):
    if "requests_mock" in input_vars:
        del input_vars["requests_mock"]
    output_test_filename_prefix = slugify(
        "_".join([str(v) for v in copy(input_vars).values()])
    )
    return "{}/{}_test_{}.{}".format(
        ARTIFACTS_DIRECTORY_CLI if for_cli else ARTIFACTS_DIRECTORY,
        output_test_filename_prefix,
        uuid.uuid4(),
        output_format,
    )


def test_fetch_task_general_data(requests_mock):
    requests_mock.get(
        "https://api.clickup.com/api/v2/task/" + DEFAULT_TASK_ID, json=DEFAULT_TASK_JSON
    )

    result = click_up_timereport.fetch_task_general_data(
        DEFAULT_TASK_ID, DEFAULT_CLICKUP_TOKEN
    )
    assert result["name"] == DEFAULT_TASK_NAME
    assert result["id"] == DEFAULT_TASK_ID


def test_fetch_time_entries(requests_mock):
    requests_mock.get(
        "https://api.clickup.com/api/v2/team/" + DEFAULT_TEAM_ID + "/time_entries",
        json=DEFAULT_TIME_ENTRIES_JSON,
    )

    result = click_up_timereport.fetch_time_entries(
        **{
            "click_up_token": DEFAULT_CLICKUP_TOKEN,
            "click_up_team_id": DEFAULT_TEAM_ID,
            "from_date": "2023-01-01",
            "to_date": "2023-01-31",
            "current_tz": tz.tzfile("/usr/share/zoneinfo/Europe/Paris"),
        }
    )
    assert result[0]["id"] == "1963465985517105840"


def test_fetch_user_teams(requests_mock):
    requests_mock.get(
        "https://api.clickup.com/api/v2/team", json=DEFAULT_USER_TEAMS_JSON
    )

    result = click_up_timereport.fetch_user_teams(DEFAULT_CLICKUP_TOKEN)
    assert result[0]["id"] == DEFAULT_TEAM_ID


@pytest.mark.parametrize("click_up_team_id", [DEFAULT_TEAM_ID, None])
@pytest.mark.parametrize("from_date", [DEFAULT_FROM_DATE, None])
@pytest.mark.parametrize("to_date", [DEFAULT_TO_DATE, None])
@pytest.mark.parametrize("output_format", ["json", "pdf", "html"])
@pytest.mark.parametrize("output_title", ["Some title", False])
@pytest.mark.parametrize("company_logo", ["templates/company-logo.png", False])
@pytest.mark.parametrize("customer_name", ["Mr Customer", False])
@pytest.mark.parametrize("consultant_name", ["Ms Consultant", False])
@pytest.mark.parametrize("language", ["french", "english", False])
def test_cli_output_from_input_json(
    click_up_team_id,
    from_date,
    to_date,
    output_format,
    output_title,
    company_logo,
    customer_name,
    consultant_name,
    language,
):
    os.makedirs(ARTIFACTS_DIRECTORY_CLI, exist_ok=True)

    input_vars = locals()
    output_test_file_path = get_output_filename_from_locals(
        input_vars, output_format, for_cli=True
    )

    command_line_list = [
        "python",
        EXECUTABLE_UNDER_TEST,
        "--from-json",
        "--json-input-path",
        DEFAULT_INPUT_JSON_PATH,
        "--as-{}".format(output_format),
        "--{}-output-path".format(output_format),
        output_test_file_path,
    ]

    if click_up_team_id:
        command_line_list += ["--click-up-team-id", click_up_team_id]

    if from_date:
        command_line_list += ["--from-date", from_date]

    if to_date:
        command_line_list += ["--to-date", to_date]

    if output_title:
        command_line_list += ["--output-title", output_title]

    if company_logo:
        command_line_list += ["--company-logo-img-path", company_logo]

    if customer_name:
        command_line_list += ["--customer-name", customer_name]

    if consultant_name:
        command_line_list += ["--consultant-name", consultant_name]

    if language:
        command_line_list += ["--language", language]

    result = subprocess.run(command_line_list)
    assert result.returncode == 0
    assert Path(output_test_file_path).resolve().is_file()
    assert os.path.getsize(output_test_file_path) > 1000
    if not os.environ.get("KEEP_FILES_FOR_ARTIFACTS"):
        shutil.rmtree(ARTIFACTS_DIRECTORY_CLI, ignore_errors=True)


@pytest.mark.parametrize("click_up_team_id", [DEFAULT_TEAM_ID, None])
@pytest.mark.parametrize("from_date", [DEFAULT_FROM_DATE, None])
@pytest.mark.parametrize("to_date", [DEFAULT_TO_DATE, None])
@pytest.mark.parametrize("output_format", ["json", "pdf", "html"])
@pytest.mark.parametrize("output_title", ["Some title", False])
@pytest.mark.parametrize("company_logo", ["templates/company-logo.png", False])
@pytest.mark.parametrize("customer_name", ["Mr Customer", False])
@pytest.mark.parametrize("consultant_name", ["Ms Consultant", False])
@pytest.mark.parametrize("language", ["french", "english", False])
def test_main_output_from_mocked_api(
    requests_mock,
    click_up_team_id,
    from_date,
    to_date,
    output_format,
    output_title,
    company_logo,
    customer_name,
    consultant_name,
    language,
):
    input_vars = locals()
    output_test_file_path = get_output_filename_from_locals(
        input_vars, output_format, for_cli=False
    )

    os.makedirs(ARTIFACTS_DIRECTORY, exist_ok=True)

    requests_mock.get(
        "https://api.clickup.com/api/v2/team", json=DEFAULT_USER_TEAMS_JSON
    )

    requests_mock.get(
        "https://api.clickup.com/api/v2/team/" + DEFAULT_TEAM_ID + "/time_entries",
        json=DEFAULT_TIME_ENTRIES_JSON,
    )

    # Here the task_id is omitted, but URL matching will work
    # See https://requests-mock.readthedocs.io/en/latest/matching.html#query-strings
    requests_mock.get("https://api.clickup.com/api/v2/task/", json=DEFAULT_TASK_JSON)

    kwargs = {
        "as_{}".format(output_format): True,
        "{}_output_path".format(output_format): output_test_file_path,
        "click_up_token": DEFAULT_CLICKUP_TOKEN,
    }

    if click_up_team_id:
        kwargs["click_up_team_id"] = click_up_team_id

    if from_date:
        kwargs["from_date"] = from_date

    if to_date:
        kwargs["to_date"] = to_date

    if output_title:
        kwargs["output_title"] = output_title

    if company_logo:
        kwargs["company_logo_img_path"] = company_logo

    if customer_name:
        kwargs["customer_name"] = customer_name

    if consultant_name:
        kwargs["consultant_name"] = consultant_name

    if language:
        kwargs["language"] = language

    click_up_timereport.main(**kwargs)
    assert Path(output_test_file_path).resolve().is_file()
    assert os.path.getsize(output_test_file_path) > 500
    if not os.environ.get("KEEP_FILES_FOR_ARTIFACTS"):
        shutil.rmtree(ARTIFACTS_DIRECTORY, ignore_errors=True)
