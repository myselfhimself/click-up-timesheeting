# builtin modules
import builtins
from copy import copy
import json
import os
import os.path
from pathlib import Path
import subprocess
import sys
import uuid

# third-party modules
import pytest
from dateutil import tz
import html5lib  # provided by weasyprint
import requests_mock as req_mock
from slugify import slugify

click_up_timereport = __import__("click-up-timereport")

# using pre-installed 'requests_mock' contribute module without needing to import it

# This is run by .github/workflows/ci.yml :)

EXECUTABLE_UNDER_TEST = "click-up-timereport.py"
ARTIFACTS_DIRECTORY = "artifacts"  # no trailing slash
ARTIFACTS_DIRECTORY_CLI = "artifacts-cli"  # no trailing slash
DEFAULT_TEAM_API_URL = "https://api.clickup.com/api/v2/team"
DEFAULT_TIME_ENTRIES_API_URL = "https://api.clickup.com/api/v2/team/{}/time_entries"
DEFAULT_TASK_API_URL = "https://api.clickup.com/api/v2/task/{}"
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
DEFAULT_USER_TEAMS_EMPTY_JSON = {"teams": []}
DEFAULT_USER_TEAMS_MULTIPLE_JSON = {
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
        },
        {
            "id": "1235",
            "name": "My ClickUp Workspace 2",
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
        },
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
    setup_requests_mock(requests_mock, task=True)

    result = click_up_timereport.fetch_task_general_data(
        DEFAULT_TASK_ID, DEFAULT_CLICKUP_TOKEN
    )
    assert result["name"] == DEFAULT_TASK_NAME
    assert result["id"] == DEFAULT_TASK_ID


def test_fetch_time_entries(requests_mock):
    setup_requests_mock(requests_mock, entries=True)

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
    setup_requests_mock(requests_mock, team=True)

    result = click_up_timereport.fetch_user_teams(DEFAULT_CLICKUP_TOKEN)
    assert result[0]["id"] == DEFAULT_TEAM_ID


@pytest.mark.parametrize("import_success", [True, False])
def test_render_pdf(monkeypatch, import_success):
    # Monkeypatching code inspired by http://materials-scientist.com/blog/2021/02/11/mocking-failing-module-import-python/
    real_import = builtins.__import__

    def monkey_import_notfound(name, globals=None, locals=None, fromlist=(), level=0):
        if name in ("weasyprint",):
            raise ModuleNotFoundError(f"Mocked module not found {name}")
        # return real_import(
        #    name, globals=globals, locals=locals, fromlist=fromlist, level=level
        # )

    with open("examples/example1.html", "r") as fp:
        html_content = fp.read()
    temp_pdf_path = "/tmp/abc.fr"
    if not import_success:
        with monkeypatch.context() as m:
            m.delitem(sys.modules, "weasyprint", raising=False)
            m.setattr(builtins, "__import__", monkey_import_notfound)
            with pytest.raises(SystemExit):
                click_up_timereport.render_pdf(
                    html_content, pdf_output_path=temp_pdf_path
                )
    else:
        click_up_timereport.render_pdf(html_content, pdf_output_path=temp_pdf_path)
        os.unlink(temp_pdf_path)


def test_render_time_entries_html():
    with open("examples/example1.json", "r") as fp:
        time_entries = json.loads(fp.read())
    html_str = click_up_timereport.render_time_entries_html(
        time_entries
    )  # calling with almost only default parameters
    html5parser = html5lib.HTMLParser(strict=True)
    html5parser.parse(html_str)


@pytest.mark.parametrize("missing_pk_env", [True, False])
@pytest.mark.parametrize("missing_team_id_env", [True, False])
@pytest.mark.parametrize("teams_found", [0, 1, 2])
def test_grab_time_entries(
    monkeypatch, missing_pk_env, missing_team_id_env, teams_found, requests_mock
):
    with monkeypatch.context() as m:
        m.setattr("click-up-timereport.CLICKUP_PK", DEFAULT_CLICKUP_TOKEN)
        m.setattr("click-up-timereport.CLICKUP_TEAM_ID", DEFAULT_TEAM_ID)
        setup_requests_mock(requests_mock, all=True)

        if missing_pk_env:
            m.setattr("click-up-timereport.CLICKUP_PK", None)
        else:
            m.setattr("click-up-timereport.CLICKUP_PK", DEFAULT_CLICKUP_TOKEN)

        if missing_team_id_env:
            m.setattr("click-up-timereport.CLICKUP_TEAM_ID", None)
        else:
            m.setattr("click-up-timereport.CLICKUP_TEAM_ID", DEFAULT_TEAM_ID)

        if missing_pk_env:
            with pytest.raises(SystemExit) as e:
                click_up_timereport.grab_time_entries()
        else:
            if missing_team_id_env:
                with req_mock.Mocker() as mocker:
                    if teams_found == 0:
                        mocker.get(
                            DEFAULT_TEAM_API_URL, json=DEFAULT_USER_TEAMS_EMPTY_JSON
                        )
                        with pytest.raises(SystemExit) as e:
                            click_up_timereport.grab_time_entries()
                    elif teams_found == 1:
                        mocker.get(DEFAULT_TEAM_API_URL, json=DEFAULT_USER_TEAMS_JSON)
                    elif teams_found > 1:
                        mocker.get(
                            DEFAULT_TEAM_API_URL, json=DEFAULT_USER_TEAMS_MULTIPLE_JSON
                        )
                        with pytest.raises(SystemExit) as e:
                            click_up_timereport.grab_time_entries()
            click_up_timereport.grab_time_entries()


def setup_requests_mock(
    requests_mock, team=False, entries=False, task=False, all=False
):
    if all:
        team = entries = task = True
    if team:
        requests_mock.get(DEFAULT_TEAM_API_URL, json=DEFAULT_USER_TEAMS_JSON)

    if entries:
        requests_mock.get(
            DEFAULT_TIME_ENTRIES_API_URL.format(DEFAULT_TEAM_ID),
            json=DEFAULT_TIME_ENTRIES_JSON,
        )

    if task:
        # Here the task_id is omitted, but URL matching will work
        # See https://requests-mock.readthedocs.io/en/latest/matching.html#query-strings
        requests_mock.get(
            DEFAULT_TASK_API_URL.format(DEFAULT_TASK_ID),
            json=DEFAULT_TASK_JSON,
        )


@pytest.mark.parametrize(
    "click_up_team_id", [DEFAULT_TEAM_ID]
)  # single value for speed
@pytest.mark.parametrize("missing_input_json_path", [True, False, "broken"])
@pytest.mark.parametrize("from_date", [DEFAULT_FROM_DATE, None])
@pytest.mark.parametrize("to_date", [DEFAULT_TO_DATE, None])
@pytest.mark.parametrize("output_format", ["json", "pdf", "html"])
@pytest.mark.parametrize("output_title", ["Some title", False])
@pytest.mark.parametrize("company_logo", ["templates/company-logo.png", None])
@pytest.mark.parametrize("customer_name", ["Mr Customer", False])
@pytest.mark.parametrize("consultant_name", ["Ms Consultant", False])
@pytest.mark.parametrize("customer_signature_field", [True, False])
@pytest.mark.parametrize("consultant_signature_field", [True, False])
@pytest.mark.parametrize("language", ["french", "english", False])
def test_cli_output_from_input_json(
    click_up_team_id,
    missing_input_json_path,
    from_date,
    to_date,
    output_format,
    output_title,
    company_logo,
    customer_name,
    consultant_name,
    customer_signature_field,
    consultant_signature_field,
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
        "--as-{}".format(output_format),
        "--{}-output-path".format(output_format),
        output_test_file_path,
    ]

    broken_input_json_path = "/tmp/broken.json"
    if missing_input_json_path == "broken":
        with open(broken_input_json_path, "w+") as fp:
            fp.write("{}")  # JSON with required keys missing
        command_line_list += ["--json-input-path", broken_input_json_path]
    elif not missing_input_json_path:
        command_line_list += ["--json-input-path", DEFAULT_INPUT_JSON_PATH]

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
    
    if customer_signature_field:
        command_line_list += ["--customer-signature-field"]
    
    if consultant_signature_field:
        command_line_list += ["--consultant-signature-field"]

    if language:
        command_line_list += ["--language", language]

    result = subprocess.run(command_line_list)
    if missing_input_json_path is True or missing_input_json_path == "broken":
        assert result.returncode > 0
        if missing_input_json_path == "broken":
            os.unlink(broken_input_json_path)
    else:
        assert result.returncode == 0
        assert Path(output_test_file_path).resolve().is_file()
        assert os.path.getsize(output_test_file_path) > 1000


@pytest.mark.parametrize("click_up_token", [DEFAULT_CLICKUP_TOKEN, "set_env", None])
@pytest.mark.parametrize("click_up_team_id", [DEFAULT_TEAM_ID, None])
@pytest.mark.parametrize("from_date", [DEFAULT_FROM_DATE, None])
@pytest.mark.parametrize("to_date", [DEFAULT_TO_DATE, None])
@pytest.mark.parametrize("output_format", ["json", "pdf", "html"])
@pytest.mark.parametrize("provide_output_path", [True, False])
@pytest.mark.parametrize("output_title", ["Some title", False])
@pytest.mark.parametrize(
    "company_logo", ["templates/company-logo.png", "notexists", None]
)
@pytest.mark.parametrize("customer_name", ["Mr Customer", False])
@pytest.mark.parametrize("consultant_name", ["Ms Consultant", False])
@pytest.mark.parametrize("language", ["french", "english", False])
def test_main_output_from_mocked_api(
    requests_mock,
    click_up_token,
    click_up_team_id,
    from_date,
    to_date,
    output_format,
    provide_output_path,
    output_title,
    company_logo,
    customer_name,
    consultant_name,
    language,
    monkeypatch,
):
    input_vars = locals()

    if click_up_token == "set_env":
        monkeypatch.setenv("CLICKUP_PK", DEFAULT_CLICKUP_TOKEN, prepend=False)

    os.makedirs(ARTIFACTS_DIRECTORY, exist_ok=True)

    setup_requests_mock(requests_mock, all=True)

    kwargs = {
        "click_up_token": DEFAULT_CLICKUP_TOKEN,
    }

    if output_format:
        output_test_file_path = get_output_filename_from_locals(
            input_vars, output_format, for_cli=False
        )
        kwargs["as_{}".format(output_format)] = True
        if provide_output_path:
            kwargs["{}_output_path".format(output_format)] = output_test_file_path

    if click_up_token != "set_env":
        kwargs["click_up_token"] = click_up_token

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

    if (
        not click_up_token and not os.environ.get("CLICKUP_PK")
    ) or company_logo == "notexists":
        with pytest.raises(SystemExit) as e:
            click_up_timereport.main(**kwargs)
    else:
        click_up_timereport.main(**kwargs)
        if output_format and provide_output_path:
            assert Path(output_test_file_path).resolve().is_file()
            assert os.path.getsize(output_test_file_path) > 500
