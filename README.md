Quick and dirty CLI script to give an overview of one's worked hours on Click-Up by project between two dates.

## Usage

1. Add your Click-Up private key to `.env` (a copy of `.env.tpl`)
1. Install dependencies (at best in Python virtual environment):
  ``pip install -r requirements.txt``
1. Run with date boundaries parameters:
  ``python get_time_entries.py 2022-11-01 2022-11-30``

## License

Public domain.
