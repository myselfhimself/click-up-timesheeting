import requests
from datetime import datetime, timezone
from dateutil import tz
import pytz
from sys import argv
from dotenv import load_dotenv
import os
import sys

load_dotenv()

CLICKUP_PK = os.getenv("CLICKUP_PK", False)
if not CLICKUP_PK:
    print("Please set CLICKUP_PK in a .env file, see .env.tpl")
    sys.exit(1)

TASKS = {}

def get_task_general_data(task_id):
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
      "Authorization": CLICKUP_PK
    }
    
    response = requests.get(url, headers=headers, params=query)
    
    data = response.json()
    TASKS[task_id] = data
    return data

def formatted_total_duration_human(tdh):
    return f"{tdh[0]:.0f}h{tdh[1]:.0f}m{tdh[2]:.0f}"

def print_time_entries(since_date=None, to_date=None):

    team_id = "4711228"
    url = "https://api.clickup.com/api/v2/team/" + team_id + "/time_entries"

    paris_tz = tz.gettz("Europe/Paris")

    if since_date:
        since_date += " 00:00:00"

    if to_date:
        to_date += " 23:59:59"

    print("Gathering Click-Up time entries from {} to {}".format(since_date, to_date if to_date else "now"))

    since_date_ts = datetime.strptime(since_date, "%Y-%m-%d %H:%M:%S").replace(tzinfo=paris_tz).timestamp()*1000 if since_date else "0"
    to_date_ts = datetime.strptime(to_date, "%Y-%m-%d %H:%M:%S").replace(tzinfo=paris_tz).timestamp()*1000 if to_date else "0"
    
    query = {
      "start_date": str(int(since_date_ts)),
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
      "Authorization": "***REMOVED***"
    }
    
    response = requests.get(url, headers=headers, params=query)
    
    data = response.json()
    
    total_hours = 0
    total_minutes = 0
    total_seconds = 0
    undived_total_seconds = 0
    
    for d in data['data']:
        #print(d['task']['id'])
        task_data = get_task_general_data(d['task']['id'])
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

if __name__ == "__main__":
    if len(argv) in (2,3):
        print_time_entries(argv[1] if len(argv) >= 2 else None, argv[2] if len(argv) == 3 else None)
