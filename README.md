# Daily Timesheet Importer

Imports timesheet data exported from Daily (Mac app) into JIRA. 
Any issues which could not be found in JIRA are shown at the end for manual entry.

## Assumptions

The following assumptions have been made:

- You are using [Daily](https://dailytimetracking.com/) to track time.
- You have exported a CSV from Daily using "Export data..." and selected the "Daily" Report in CSV format for a given date range, with Duration in total minutes.
- When you record your entries in Daily, you use the JIRA Issue Key as your first word, either with or without hyphens. eg "JOB-123 eat lunch" or "Job123 cook dinner"
- You don't care what time of the day the work was done - you just want the time logged in JIRA against the right issue on the right day.
- You have a JIRA API key (which you can get from "Manage Account" -> "Security" -> "API token")
- You hate manually transcribing data from one place to another and would rather trust a mindless computer program to do it for you!

## Usage

Use the ```--live_mode``` flag when you are ready. Defaults to test mode which shows what would have been imported, and any issues that could not be found.

### Example usage:

```bash
python import_timesheet.py -s DailyExportSample.csv -j <jira_url> -u <jira_user> -t <jira_api_token>
```

## License

This project is licensed under the terms of the MIT license.