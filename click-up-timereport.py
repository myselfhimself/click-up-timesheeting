import requests
from babel.dates import format_date
from datetime import datetime, timezone
from dateutil import tz
from dateutil.relativedelta import relativedelta
import json
import pytz
from sys import argv
from dotenv import load_dotenv
import os
import sys
import fire
import gettext
import dateutil.parser

load_dotenv()

CLICKUP_PK = os.getenv("CLICKUP_PK", False)

DEFAULT_MONTHS_BACKWARDS = 12
DEFAULT_SUSTAINABLE_DATE_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
DEFAULT_TIMEZONE = "Europe/Paris"
DEFAULT_HTML_TITLE = "Time entries"  # This has a gettext entry
DEFAULT_HTML_JINJA_TEMPLATE_DIRECTORY = "templates/"
DEFAULT_HTML_JINJA_TEMPLATE = "simple-report.html.j2"
DEFAULT_LANGUAGE = "en_US"  # Also available: fr_FR
DEFAULT_PDF_OUTPUT_PATH = "time-entries.pdf"
DEFAULT_HTML_OUTPUT_PATH = "time-entries.html"
DEFAULT_JSON_OUTPUT_PATH = "time-entries.json"
DEFAULT_JSON_INDENTS = 2
JSON_REQUIRED_KEYS = {"from_date", "to_date", "days", "tasks", "total_duration"}

# Tasks-based view for time tracking
TASKS = {}
# Days-based view for time tracking
DAYS = {}


def fetch_task_general_data(task_id, click_up_token):
    """Get task information from the Click-Up API. Skip fetching if information is already in cache."""
    if task_id in TASKS.keys():
        return TASKS[task_id]
    url = "https://api.clickup.com/api/v2/task/" + task_id

    query = {"custom_task_ids": "true", "team_id": "123", "include_subtasks": "true"}

    headers = {"Content-Type": "application/json", "Authorization": click_up_token}

    response = requests.get(url, headers=headers, params=query)

    data = response.json()
    TASKS[task_id] = data
    return data


def formatted_total_duration_human(tdh):
    """Returns a nice NNhNNmNN time representation for a total duration in seconds, from a tuple as returned by tupled_total_duration_human()."""
    return f"{tdh[0]:.0f}h{tdh[1]:.0f}m{tdh[2]:.0f}s"


def tupled_total_duration_human(undived_seconds):
    """Returns a 3-tuplet of integers (hours, minutes, seconds) from undived_seconds integer."""
    total_minutes, total_seconds = divmod(undived_seconds, 60)
    total_hours, total_minutes = divmod(total_minutes, 60)
    return (
        total_hours,
        total_minutes,
        total_seconds,
    )


def grab_time_entries(
    from_date=None,
    to_date=None,
    click_up_token=None,
    time_zone=DEFAULT_TIMEZONE,
    language=DEFAULT_LANGUAGE,
):
    """Populates TASKS and DAYS views from Click-Up's API between from_date and to_date using the click_up_token."""

    team_id = "4711228"
    url = "https://api.clickup.com/api/v2/team/" + team_id + "/time_entries"

    current_tz = tz.gettz(time_zone)
    datetime_format = "%Y-%m-%d %H:%M:%S"

    if not to_date:
        to_date = datetime.today().strftime(datetime_format)
    else:
        to_date += " 23:59:59"

    if not from_date:
        if not to_date:
            from_date = (
                datetime.today()
                .replace(day=1, hour=0, minute=0, second=0, tzinfo=current_tz)
                .strftime(datetime_format)
            )
        else:
            from_date = (
                (
                    datetime.strptime(to_date, datetime_format)
                    - relativedelta(months=DEFAULT_MONTHS_BACKWARDS)
                )
                .replace(tzinfo=current_tz)
                .strftime(datetime_format)
            )
    else:
        from_date += " 00:00:00"

    if not click_up_token:
        if CLICKUP_PK:
            click_up_token = CLICKUP_PK
        else:
            print(
                "Missing Click-Up token (pk_* value), set it in .env or through the appropriate command line parameter (see --help)."
            )
            sys.exit(1)

    print(
        "Gathering Click-Up time entries from {} to {}".format(
            from_date, to_date if to_date else "now"
        )
    )

    from_date_ts = (
        datetime.strptime(from_date, datetime_format)
        .replace(tzinfo=current_tz)
        .timestamp()
        * 1000
        if from_date
        else "0"
    )
    to_date_ts = (
        datetime.strptime(to_date, datetime_format)
        .replace(tzinfo=current_tz)
        .timestamp()
        * 1000
        if to_date
        else "0"
    )

    query = {
        "start_date": str(int(from_date_ts)),
        "end_date": str(int(to_date_ts)),
        #  "assignee": "0",
        #  "include_task_tags": "true",
        #  "include_location_names": "true",
        #  "space_id": "0",
        #  "folder_id": "0",
        #  "list_id": "0",
        #  "task_id": "0",
        #  "custom_task_ids": "true",
        #  "team_id": "123"
    }

    headers = {"Content-Type": "application/json", "Authorization": click_up_token}

    response = requests.get(url, headers=headers, params=query)

    data = response.json()

    undived_total_seconds = 0

    # Browse each time entry within dates range
    for d in data["data"]:
        # Convert microseconds time entry duration to hours, minutes, seconds
        duration_seconds = int(d["duration"]) / 1000
        undived_total_seconds += duration_seconds
        minutes, seconds = divmod(duration_seconds, 60)
        hours, minutes = divmod(minutes, 60)

        # Fill TASK[task_id] with task info if unfetched yet, and add up duration
        task_id = d["task"]["id"]
        fetch_task_general_data(task_id, click_up_token)
        if not "total_duration" in TASKS[task_id].keys():
            TASKS[task_id]["total_duration"] = 0
        TASKS[task_id]["total_duration"] += duration_seconds

        # Add up duration in DAYS[task_date]
        task_start_ts = datetime.fromtimestamp(int(d["start"]) / 1000).replace(
            tzinfo=current_tz
        )
        task_date = task_start_ts.strftime("%Y-%m-%d")
        if not task_date in DAYS.keys():
            DAYS[task_date] = {
                "total_duration": 0,
                "iso_date": task_start_ts.isoformat(),
                "human_date": format_date(
                    task_start_ts, format="full", locale=language
                ),  # task_start_ts.strftime("%a, %d %b %Y"),
            }
        DAYS[task_date]["total_duration"] += duration_seconds

        # Prepare TASKS[...]["total_duration_human"] for futher summarizing
        TASKS[task_id]["total_duration_human"] = tupled_total_duration_human(
            TASKS[task_id]["total_duration"]
        )

        # Prepare DAYS[...]["total_duration_human"] for futher summarizing
        DAYS[task_date]["total_duration_human"] = tupled_total_duration_human(
            DAYS[task_date]["total_duration"]
        )

        # Step progress output
        print(".", end="", flush=True)
    print()


def get_time_entries(from_date, to_date):
    """Prepares a time entries and total dictionary from TASKS and DAYS views.
    This function's results can be piped into print_time_entries() or render_time_entries_html() for console or HTML/PDF rendering.

    This should be called after grab_time_entries() which takes care of populating depending data views.
    """
    days = [
        {
            "human_date": DAYS[date]["human_date"],
            "iso_date": DAYS[date]["iso_date"],
            "total_duration_raw": DAYS[date]["total_duration_human"],
            "total_duration_human": formatted_total_duration_human(
                DAYS[date]["total_duration_human"]
            ),
        }
        for date in sorted(DAYS)
    ]
    tasks = [
        {
            "name": v["name"],
            "list": v["list"]["name"],
            "project": v["project"]["name"],
            "folder": v["folder"]["name"],
            "total_duration_raw": v["total_duration_human"],
            "total_duration_human": formatted_total_duration_human(
                v["total_duration_human"]
            ),
        }
        for k, v in TASKS.items()
    ]

    undived_total_seconds = sum(v["total_duration"] for v in TASKS.values())
    minutes, seconds = divmod(undived_total_seconds, 60)
    hours, minutes = divmod(minutes, 60)

    return {
        "from_date": from_date,
        "to_date": to_date,
        "days": days,
        "tasks": tasks,
        "total_duration": {"hours": hours, "minutes": minutes, "seconds": seconds},
    }


def print_time_entries(entries):
    """Prints nicely day-based and task-based statistics, as stored in the TASKS and DAYS views."""
    print("Daily time sheet:")
    for date_entry in entries["days"]:
        print(date_entry["human_date"], date_entry["total_duration_human"])

    print()
    print("Tasks summary:")
    for task in entries["tasks"]:
        print(
            task["name"],
            task["list"],
            task["project"],
            task["folder"],
            task["total_duration_human"],
        )

    print()
    print(
        "Total: {hours:.0f}h{minutes:.0f}m{seconds:.0f}".format(
            **entries["total_duration"]
        )
    )


def render_time_entries_html(time_entries, title=None, language=None):
    from jinja2 import Environment, FileSystemLoader

    if not language:
        language = DEFAULT_LANGUAGE

    def jinja_render_date_str_with_babel(a_date, format="full"):
        date = dateutil.parser.parse(a_date)
        return format_date(date, format=format, locale=language)

    environment = Environment(
        loader=FileSystemLoader(DEFAULT_HTML_JINJA_TEMPLATE_DIRECTORY),
        extensions=["jinja2.ext.i18n"],
    )
    translations = gettext.translation(
        "messages",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "locale")),
        languages=[language],
    )
    environment.install_gettext_translations(translations)

    if not title:
        title = gettext.gettext(DEFAULT_HTML_TITLE)

    template = environment.get_template(DEFAULT_HTML_JINJA_TEMPLATE)
    template.globals["str_to_date"] = jinja_render_date_str_with_babel
    content = template.render({"document_title": title, "time_entries": time_entries})
    return content


def render_pdf(html_content, pdf_output_path=DEFAULT_PDF_OUTPUT_PATH):
    try:
        from weasyprint import HTML
    except ImportError:
        print(
            "The --as-pdf and --pdf-output-path options required the Python weasyprint module to be installed."
        )
        exit(1)

    HTML(string=html_content).write_pdf(pdf_output_path)


def main(
    from_date=None,
    to_date=None,
    click_up_token=None,
    time_zone=DEFAULT_TIMEZONE,
    from_json=False,
    json_input_path=None,
    as_json=False,
    json_output_path=DEFAULT_JSON_OUTPUT_PATH,
    as_html=False,
    html_output_path=DEFAULT_HTML_OUTPUT_PATH,
    as_pdf=False,
    pdf_output_path=DEFAULT_PDF_OUTPUT_PATH,
    output_title=DEFAULT_HTML_TITLE,
    language=DEFAULT_LANGUAGE,
):
    language = (
        "fr_FR"
        if language == "french"
        else ("en_US" if language == "english" else "en_US")
    )

    print("Language:", language)

    # The from_json and json_input_path options allow reusing a JSON file already output with the as_json+json_output_path options pair
    # This provides a manual form of caching
    if from_json:
        if not json_input_path:
            print("You must use --json-input-path with --from-json")
            exit(1)
        else:
            print("Using", json_input_path)
            with open(json_input_path, "r") as json_file:
                time_entries = json.load(json_file)
                if time_entries.keys() < JSON_REQUIRED_KEYS:
                    print(
                        "Input JSON file is missing keys, expected at least:",
                        JSON_REQUIRED_KEYS,
                    )
                    exit(1)
    else:
        # Grab time entries from Click-Up's online API
        grab_time_entries(
            from_date, to_date, click_up_token, time_zone=time_zone, language=language
        )

        # Make a nice consolidated dictionary ready for all forms of template rendering
        time_entries = get_time_entries(from_date, to_date)

    # JSON output
    if as_json:
        json_output_path = json_output_path or DEFAULT_JSON_OUTPUT_PATH
        with open(json_output_path, "w") as fp:
            fp.write(json.dumps(time_entries, indent=DEFAULT_JSON_INDENTS))
        print("Wrote", json_output_path)

    # CLI standard output
    print_time_entries(time_entries)

    html_content = render_time_entries_html(
        time_entries, title=output_title, language=language
    )

    # HTML output
    if as_html:
        html_output_path = html_output_path or DEFAULT_HTML_OUTPUT_PATH
        with open(html_output_path, "w") as fp:
            fp.write(html_content)
        print("Wrote", html_output_path)

    # PDF output
    if as_pdf:
        pdf_output_path = pdf_output_path or DEFAULT_PDF_OUTPUT_PATH
        render_pdf(html_content=html_content, pdf_output_path=pdf_output_path)
        print("Wrote", pdf_output_path)


if __name__ == "__main__":
    fire.Fire(main)
