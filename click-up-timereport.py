import requests
from datetime import datetime, timezone
from dateutil import tz
from dateutil.relativedelta import relativedelta
import pytz
from sys import argv
from dotenv import load_dotenv
import os
import sys
import fire

load_dotenv()

CLICKUP_PK = os.getenv("CLICKUP_PK", False)

DEFAULT_MONTHS_BACKWARDS = 12

TASKS = {}

def get_task_general_data(task_id, click_up_token):
    if task_id in TASKS.keys():
        return TASKS[task_id]
    url = "https://api.clickup.com/api/v2/task/" + task_id
    
    query = {
      "custom_task_ids": "true",
      "team_id": "123",
      "include_subtasks": "true"
    }
    
    headers = {
      "Content-Type": "application/json",
      "Authorization": click_up_token
    }
    
    response = requests.get(url, headers=headers, params=query)
    
    data = response.json()
    TASKS[task_id] = data
    return data

def formatted_total_duration_human(tdh):
    return f"{tdh[0]:.0f}h{tdh[1]:.0f}m{tdh[2]:.0f}"

def print_time_entries(from_date=None, to_date=None, click_up_token=None):

    team_id = "4711228"
    url = "https://api.clickup.com/api/v2/team/" + team_id + "/time_entries"

    paris_tz = tz.gettz("Europe/Paris")
    datetime_format = "%Y-%m-%d %H:%M:%S"

    if not to_date:
        to_date = datetime.today().strftime(datetime_format)
    else:
        to_date += " 23:59:59"


    if not from_date:
        if not to_date:
            from_date = datetime.today().replace(day=1, hour=0, minute=0, second=0).strftime(datetime_format)
        else:
            from_date = (datetime.strptime(to_date, datetime_format) - relativedelta(months=DEFAULT_MONTHS_BACKWARDS)).strftime(datetime_format)
    else:
        from_date += " 00:00:00"


    if not click_up_token:
        if CLICKUP_PK:
            click_up_token = CLICKUP_PK
        else:
            print("Missing Click-Up token (pk_* value), set it in .env or through the appropriate command line parameter (see --help).")
            sys.exit(1)
    

    print("Gathering Click-Up time entries from {} to {}".format(from_date, to_date if to_date else "now"))

    from_date_ts = datetime.strptime(from_date, datetime_format).replace(tzinfo=paris_tz).timestamp()*1000 if from_date else "0"
    to_date_ts = datetime.strptime(to_date, datetime_format).replace(tzinfo=paris_tz).timestamp()*1000 if to_date else "0"

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
    
    headers = {
      "Content-Type": "application/json",
      "Authorization": click_up_token
    }
    
    response = requests.get(url, headers=headers, params=query)
    
    data = response.json()
    
    total_hours = 0
    total_minutes = 0
    total_seconds = 0
    undived_total_seconds = 0
    
    for d in data['data']:
        #print(d['task']['id'])
        task_data = get_task_general_data(d['task']['id'], click_up_token)
        #print(d['task']['name'], "---", task_data['list']['name'])
        duration_seconds = int(d['duration'])/1000
        undived_total_seconds += duration_seconds
        minutes, seconds = divmod(duration_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        #print(f"{hours:.0f}h{minutes:.0f}m{seconds:.0f}")
        #print(datetime.fromtimestamp(int(d['at'])/1000).astimezone(pytz.timezone("Europe/Paris")))
        if not 'total_duration' in TASKS[d['task']['id']].keys():
            TASKS[d['task']['id']]['total_duration'] = duration_seconds
        else:
            TASKS[d['task']['id']]['total_duration'] += duration_seconds
        
        minutes, seconds = divmod(TASKS[d['task']['id']]['total_duration'], 60)
        hours, minutes = divmod(minutes, 60)
 
        TASKS[d['task']['id']]['total_duration_human'] = (hours, minutes, seconds)
        print(".", end="", flush=True)
    
    print()
    print()
    minutes, seconds = divmod(undived_total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    
    print("Tasks summary:")
    for k, v in enumerate(TASKS):
        print(TASKS[v]['name'], TASKS[v]['list']['name'], TASKS[v]['project']['name'], TASKS[v]['folder']['name'], formatted_total_duration_human(TASKS[v]['total_duration_human']))

    print()
    print(f"Total: {hours:.0f}h{minutes:.0f}m{seconds:.0f}")

def main(from_date=None, to_date=None, click_up_token=None):
    print_time_entries(from_date, to_date, click_up_token)

if __name__ == "__main__":
    fire.Fire(main)
