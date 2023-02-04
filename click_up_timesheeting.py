#!/usr/bin/env python
# builtin modules
import base64
from datetime import datetime
import json
import os
import os.path
import sys

# contrib modules
from babel.dates import format_date
from dateutil import tz
import dateutil.parser
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
import fire
import gettext
from jinja2 import Environment, FileSystemLoader
import requests


# Environment variables retrieval
load_dotenv()
CLICKUP_PK = os.getenv("CLICKUP_PK", False)
CLICKUP_TEAM_ID = os.getenv("CLICKUP_TEAM_ID", False)

# Global constants
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


class ClickUpTimesheetMaker:
    # Tasks-based view for time tracking
    TASKS = {}
    # Days-based view for time tracking
    DAYS = {}

    click_up_token = None
    click_up_team_id = None
    time_zone = None
    language = None

    def __init__(
        self,
        click_up_token=None,
        click_up_team_id=None,
        time_zone=DEFAULT_TIMEZONE,
        language=DEFAULT_LANGUAGE,
    ) -> None:
        # API token is compulsory
        if not click_up_token:
            if CLICKUP_PK:
                click_up_token = CLICKUP_PK
            else:
                print(
                    "Missing Click-Up REST API token (pk_* value), set it in .env or through the --click-up-token command line parameter (see --help)."
                )
                sys.exit(1)

        # team_id can be provided or will be guessed from https://clickup.com/api/clickupreference/operation/GetAuthorizedTeams/
        if not click_up_team_id:
            if CLICKUP_TEAM_ID:
                print("Using CLICKUP_TEAM_ID from environment.")
                click_up_team_id = CLICKUP_TEAM_ID
            else:
                user_teams = self.fetch_user_teams()
                if not user_teams:
                    print(
                        "Missing Click-Up team parameter (--click-up-team-id or CLICKUP_TEAM_ID environment variable) not found and user for given Click-Up user API key has no teams. Giving up."
                    )
                    exit(1)
                elif len(user_teams) > 1:
                    user_teams_overview = [
                        {"id": team["id"], "name": team["name"]} for team in user_teams
                    ]
                    print(
                        "Missing Click-Up team parameter (--click-up-team-id or CLICKUP_TEAM_ID environment variable) not found and user for given Click-Up user API key has several teams to choose from: {}. Giving up.".format(
                            user_teams_overview
                        )
                    )
                    exit(1)
                else:
                    click_up_team_id = user_teams[0]["id"]
                    print(
                        "Guessing team_id as user's only assigned team: {} ({}).".format(
                            user_teams[0]["name"], click_up_team_id
                        )
                    )
        self.click_up_token = click_up_token
        self.click_up_team_id = click_up_team_id
        self.time_zone = tz.gettz(time_zone)
        self.language = (
            DEFAULT_LANGUAGE
            if not language
            else (
                "fr_FR"
                if language.startswith("fr")
                else ("en_US" if language.startswith("en") else "en_US")
            )
        )

    def fetch_task_general_data(self, task_id):
        """Get task information from the Click-Up API. Skip fetching if information is already in cache."""
        if task_id in self.TASKS.keys():
            return self.TASKS[task_id]
        url = "https://api.clickup.com/api/v2/task/" + task_id

        query = {"custom_task_ids": "true", "include_subtasks": "true"}

        headers = {
            "Content-Type": "application/json",
            "Authorization": self.click_up_token,
        }

        response = requests.get(url, headers=headers, params=query)

        data = response.json()
        self.TASKS[task_id] = data
        return data

    def formatted_total_duration_human(self, tdh):
        """Returns a nice NNhNNmNN time representation for a total duration in seconds, from a tuple as returned by tupled_total_duration_human()."""
        return f"{tdh[0]:.0f}h{tdh[1]:.0f}m{tdh[2]:.0f}s"

    def tupled_total_duration_human(self, undived_seconds):
        """Returns a 3-tuplet of integers (hours, minutes, seconds) from undived_seconds integer."""
        total_minutes, total_seconds = divmod(undived_seconds, 60)
        total_hours, total_minutes = divmod(total_minutes, 60)
        return (
            total_hours,
            total_minutes,
            total_seconds,
        )

    def fetch_user_teams(self):
        url = "https://api.clickup.com/api/v2/team"

        headers = {"Authorization": self.click_up_token}

        response = requests.get(url, headers=headers)

        data = response.json()
        return data["teams"]

    def fetch_time_entries(self, from_date, to_date):
        url = (
            "https://api.clickup.com/api/v2/team/"
            + str(self.click_up_team_id)
            + "/time_entries"
        )

        datetime_format = "%Y-%m-%d %H:%M:%S"

        if not to_date:
            to_date = datetime.today().strftime(datetime_format)
        else:
            to_date += " 23:59:59"

        if not from_date:
            from_date = (
                (
                    datetime.strptime(to_date, datetime_format)
                    - relativedelta(months=DEFAULT_MONTHS_BACKWARDS)
                )
                .replace(tzinfo=self.time_zone)
                .strftime(datetime_format)
            )
        else:
            from_date += " 00:00:00"

        print(
            "Gathering Click-Up time entries from {} to {}".format(
                from_date, to_date if to_date else "now"
            )
        )

        from_date_ts = (
            datetime.strptime(from_date, datetime_format)
            .replace(tzinfo=self.time_zone)
            .timestamp()
            * 1000
            if from_date
            else "0"
        )
        to_date_ts = (
            datetime.strptime(to_date, datetime_format)
            .replace(tzinfo=self.time_zone)
            .timestamp()
            * 1000
            if to_date
            else "0"
        )

        query = {
            "start_date": str(int(from_date_ts)),
            "end_date": str(int(to_date_ts)),
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": self.click_up_token,
        }

        response = requests.get(url, headers=headers, params=query)

        data = response.json()
        return data["data"]

    def grab_time_entries(
        self,
        from_date=None,
        to_date=None,
    ):
        """Populates TASKS and DAYS views from Click-Up's API between from_date and to_date using the click_up_token and click_up_team_id."""
        data = self.fetch_time_entries(
            from_date=from_date,
            to_date=to_date,
        )

        undived_total_seconds = 0

        # Browse each time entry within dates range
        for d in data:
            # Convert microseconds time entry duration to hours, minutes, seconds
            duration_seconds = int(d["duration"]) / 1000
            undived_total_seconds += duration_seconds
            minutes, seconds = divmod(duration_seconds, 60)
            hours, minutes = divmod(minutes, 60)

            # Fill TASK[task_id] with task info if unfetched yet, and add up duration
            task_id = d["task"]["id"]
            self.fetch_task_general_data(task_id)
            if not "total_duration" in self.TASKS[task_id].keys():
                self.TASKS[task_id]["total_duration"] = 0
            self.TASKS[task_id]["total_duration"] += duration_seconds

            # Add up duration in DAYS[task_date]
            task_start_ts = datetime.fromtimestamp(int(d["start"]) / 1000).replace(
                tzinfo=self.time_zone
            )
            task_date = task_start_ts.strftime("%Y-%m-%d")
            if not task_date in self.DAYS.keys():
                self.DAYS[task_date] = {
                    "total_duration": 0,
                    "iso_date": task_start_ts.isoformat(),
                    "human_date": format_date(
                        task_start_ts, format="full", locale=self.language
                    ),  # task_start_ts.strftime("%a, %d %b %Y"),
                }
            self.DAYS[task_date]["total_duration"] += duration_seconds

            # Prepare TASKS[...]["total_duration_human"] for futher summarizing
            self.TASKS[task_id][
                "total_duration_human"
            ] = self.tupled_total_duration_human(self.TASKS[task_id]["total_duration"])

            # Prepare DAYS[...]["total_duration_human"] for futher summarizing
            self.DAYS[task_date][
                "total_duration_human"
            ] = self.tupled_total_duration_human(self.DAYS[task_date]["total_duration"])

            # Step progress output
            print(".", end="", flush=True)
        print()

    def get_time_entries(self, from_date, to_date):
        """Prepares a time entries and total dictionary from TASKS and DAYS views.
        This function's results can be piped into print_time_entries() or render_time_entries_html() for console or HTML/PDF rendering.

        This should be called after grab_time_entries() which takes care of populating depending data views.
        """
        days = [
            {
                "human_date": self.DAYS[date]["human_date"],
                "iso_date": self.DAYS[date]["iso_date"],
                "total_duration_raw": self.DAYS[date]["total_duration_human"],
                "total_duration_human": self.formatted_total_duration_human(
                    self.DAYS[date]["total_duration_human"]
                ),
            }
            for date in sorted(self.DAYS)
        ]
        tasks = [
            {
                "name": v["name"],
                "list": v.get("list", {}).get("name"),
                "project": v.get("project", {}).get("name"),
                "folder": v.get("folder", {}).get("name"),
                "total_duration_raw": v.get("total_duration_human", 0),
                "total_duration_human": self.formatted_total_duration_human(
                    v.get("total_duration_human", 0)
                ),
            }
            for k, v in self.TASKS.items()
        ]

        undived_total_seconds = sum(v["total_duration"] for v in self.TASKS.values())
        minutes, seconds = divmod(undived_total_seconds, 60)
        hours, minutes = divmod(minutes, 60)

        return {
            "from_date": from_date,
            "to_date": to_date,
            "days": days,
            "tasks": tasks,
            "total_duration": {"hours": hours, "minutes": minutes, "seconds": seconds},
        }

    def print_time_entries(self, entries):
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

    def render_time_entries_html(
        self,
        time_entries,
        title=None,
        company_logo=None,
        customer_name=None,
        consultant_name=None,
        customer_signature_field=None,
        consultant_signature_field=None,
    ):
        company_logo_base64 = None
        if company_logo:
            with open(company_logo, "rb") as logo_fp:
                company_logo_base64 = "data:image/png;base64," + base64.encodebytes(
                    logo_fp.read()
                ).decode("utf-8")

        def jinja_render_date_str_with_babel(a_date, format="full"):
            date = dateutil.parser.parse(a_date) if a_date else None
            return format_date(date, format=format, locale=self.language)

        environment = Environment(
            loader=FileSystemLoader(DEFAULT_HTML_JINJA_TEMPLATE_DIRECTORY),
            extensions=["jinja2.ext.i18n"],
        )
        translations = gettext.translation(
            "messages",
            os.path.abspath(os.path.join(os.path.dirname(__file__), "locale")),
            languages=[self.language],
        )
        environment.install_gettext_translations(translations)

        if not title:
            title = gettext.gettext(DEFAULT_HTML_TITLE)

        template = environment.get_template(DEFAULT_HTML_JINJA_TEMPLATE)
        template.globals["str_to_date"] = jinja_render_date_str_with_babel
        content = template.render(
            {
                "document_title": title,
                "html_lang": ("fr" if self.language.startswith("fr") else "en"),
                "customer_name": customer_name,
                "consultant_name": consultant_name,
                "time_entries": time_entries,
                "base64_company_logo": company_logo_base64,
                "customer_signature_field": customer_signature_field,
                "consultant_signature_field": consultant_signature_field,
            },
            presentational_hints=True,
        )
        return content

    def render_pdf(self, html_content, pdf_output_path=DEFAULT_PDF_OUTPUT_PATH):
        try:
            from weasyprint import HTML
        except ModuleNotFoundError:
            print(
                "The --as-pdf and --pdf-output-path options required the Python weasyprint module to be installed."
            )
            exit(1)

        HTML(string=html_content).write_pdf(pdf_output_path)


def main(
    from_date=None,
    to_date=None,
    click_up_token=CLICKUP_PK,
    click_up_team_id=CLICKUP_TEAM_ID,
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
    company_logo_img_path=None,
    customer_name=None,
    consultant_name=None,
    customer_signature_field=False,
    consultant_signature_field=False,
):
    maker = ClickUpTimesheetMaker(
        click_up_token=click_up_token,
        click_up_team_id=click_up_team_id,
        time_zone=time_zone,
        language=language,
    )

    print("Language:", maker.language)

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
        maker.grab_time_entries(from_date=from_date, to_date=to_date)

        # Make a nice consolidated dictionary ready for all forms of template rendering
        time_entries = maker.get_time_entries(from_date, to_date)

    # JSON output
    if as_json:
        json_output_path = json_output_path or DEFAULT_JSON_OUTPUT_PATH
        with open(json_output_path, "w") as fp:
            fp.write(json.dumps(time_entries, indent=DEFAULT_JSON_INDENTS))
        print("Wrote", json_output_path)

    # CLI standard output
    maker.print_time_entries(time_entries)

    if company_logo_img_path:
        if not os.path.exists(company_logo_img_path):
            print("Provided company logo file does not exist.")
            exit(1)

    html_content = maker.render_time_entries_html(
        time_entries,
        title=output_title,
        company_logo=company_logo_img_path,
        customer_name=customer_name,
        consultant_name=consultant_name,
        customer_signature_field=customer_signature_field,
        consultant_signature_field=consultant_signature_field,
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
        maker.render_pdf(html_content=html_content, pdf_output_path=pdf_output_path)
        print("Wrote", pdf_output_path)


if __name__ == "__main__":
    fire.Fire(main)
