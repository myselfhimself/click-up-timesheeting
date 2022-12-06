Quick and dirty CLI script to give an overview of one's worked hours on Click-Up by project between two dates.

## Usage

1. Optionally add your Click-Up private key to `.env` (a copy of `.env.tpl`)
1. Install dependencies (at best in Python virtual environment):

    ``pip install -r requirements.txt``

    Below step creates and enables a virtual environment if you have none yet:

    ``python -m venv venv; . venv/bin/activate``

1. Run with optional date boundaries parameters and Click-Up token:

    ``python get_time_entries.py # from now since 1 year ago``

    Output:
    ```
     Gathering Click-Up time entries from 2021-12-06 18:20:16 to 2022-12-06 18:20:16
     ...................................................................................................................................
     
     Tasks summary:
     Task 1 Project B Listing C 2h36m55
     Task 2 Project C Listing C 5h24m00
     ....
     
     Total: 8h00m55
     ```

    ``python get_time_entries.py --from_date=2022-11-01 # till now``

    ``python get_time_entries.py --to_date=2022-12-30 # from 1 year before that date (default shift)``

    ``python get_time_entries.py --from_date=2022-11-01 --to_date=2022-11-30 # with times from 00:00:00 to 23:59:59``

    ``python get_time_entries.py --from_date=2022-11-01 --to_date=2022-11-30 --click_up_token=pk_SOMETHING # with token provided on CLI instead of .env``

## License

Public domain.
