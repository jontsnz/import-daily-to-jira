# Daily Timesheet Importer

Imports daily timesheets exported from Daily (Mac app) into JIRA

## Usage

use ```live_mode``` flag when you are ready. Defaults to test mode.

Example usage:

```bash
python import_timesheet.py -s data\Daily.csv -j <jira_url> -u <jira_user> -t <jira_api_token> --live_mode
```