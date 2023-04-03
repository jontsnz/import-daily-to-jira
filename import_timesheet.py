#! /usr/bin/env python
"""Imports timesheet from Daily in Daily Export format and turns into JIRA import format.

Usage - help:
    $ python import_timesheet.py -h
    
Usage:
    $ python import_timesheet.py -s temp/Daily.csv -j <jira_url> -u <jira_user> -t <jira_api_token> --live_mode
"""

import argparse
import logging
import csv
import datetime
from jira import JIRA
import sys

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)

def read_source_data_from_file(source_file: str) -> list:
    """Read the CSV file straight from Daily
    """
    logger.info("Processing source file: %s", source_file)
    with open(source_file, newline='', encoding='utf-8') as csvfile:
        csv_reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        data = [row for row in csv_reader]

    # Remove the first 6 rows
    data = data[6:]

    # show the jobs
    # for row in data[1:]:
    #     jobno = row[0].upper().replace('-','').split(' ')[0]
    #     logger.info(f"Job: {jobno} ==> {row[0]}")
    return data

def consolidate_data(data: list) -> list:
    """ Consolidate the data by jobno
    """
        
    # build a dictionary of jobnos containing a list of jobs that match
    job_dict = {}
    for i in range(1, len(data)):
        row = data[i]
        jobno = build_jobno(row[0])
        if jobno in job_dict:
            job_dict[jobno].append(i)
        else:
            job_dict[jobno] = [i]

    # show the job_dicts
    # for jobno, jobs in job_dict.items():
    #     logger.info(f"Job: {jobno} ==> {jobs}")
        
    # build a new data array combining the cells for each jobno
    consolidated_data = [data[0]]
    for jobno, jobs in job_dict.items():
        new_row = [jobno]
        for i in range(1, len(data[0])):
            new_row.append(sum([int(data[j][i]) for j in jobs]))
        consolidated_data.append(new_row)

    return consolidated_data
    
def build_jobno(desc: str) -> str:
    jobno = desc.upper().replace('-','').split(' ')[0]
    # find the index of the first digit in jobno
    for i in range(len(jobno)):
        if jobno[i].isdigit():
            proj =  jobno[:i]
            seq = jobno[i:]
            jobno = proj + '-' + seq
            break
    return jobno

def build_daily_totals(data: list) -> list:
    # sum the mins for each day (column)
    daily_totals = [0] * len(data[0])
    for row in data[1:]:
        for i in range(1, len(row)):
            daily_totals[i] += int(row[i])
        
    # display the column headers
    total_mins = 0
    for i in range(1, len(data[0])):
        total_mins += daily_totals[i]
        # logger.info(f"{i}: {data[0][i]}: {daily_totals[i]} mins")
    logger.info(f"Total mins: {total_mins} for {len(data[0])-1} days and {len(data)-1} jobs")
    logger.info("=====================================")

    return daily_totals

def display_data(data: list) -> None:
    """ show jobs by day, where there are mins > 0
    """
    start_col = 1
    end_col = len(data[0])
    logger.info(f"Jobs by day from {data[0][start_col]} to {data[0][end_col-1]}")
    for i in range(start_col, end_col):
        work_date = data[0][i]
        worklog_date = datetime.datetime.strptime(work_date, '%d/%m/%Y').strftime('%Y-%m-%dT%H:%M:%S.000+0000')
        logger.info(f"{worklog_date}")
        for j in range(1, len(data)):
            row = data[j]
            if int(row[i]) > 0:
                # display padding row[0] to 20 space
                job_no = row[0]
                mins_worked = row[i]
                logger.info(f" {job_no:14} {mins_worked} mins")
    return
    
def convert_data_to_work_logs(data: list) -> list:
    work_logs = []
    for i in range(1, len(data[0])):
        worklog_date = datetime.datetime.strptime(data[0][i], '%d/%m/%Y').strftime('%Y-%m-%dT%H:%M:%S.000+0000')
        for j in range(1, len(data)):
            row = data[j]
            if int(row[i]) > 0:
                job_no = row[0]
                mins_worked = row[i]
                work_log = {
                    "date_worked": worklog_date,
                    "job_number": job_no,
                    "minutes_worked": mins_worked
                }
                work_logs.append(work_log)
    return work_logs
    
def display_work_logs(work_logs: list) -> None:
    """ show all the work logs
    """
    for work_log in work_logs:
        logger.info(f"{work_log['date_worked']} {work_log['job_number']} {work_log['minutes_worked']} mins")
    return
    
def connect_to_jira(jira_url: str, jira_username: str, jira_api_token: str) -> JIRA:
    """Connect to JIRA
    """

    # Connect to JIRA
    try:
        jira = JIRA(jira_url, basic_auth=(jira_username, jira_api_token), validate=True)
    except Exception as e:
        logger.error(f"Unable to connect to JIRA: {e}")
        sys.exit(1)
    return jira

def import_work_logs(work_logs: list, jira_url: str, username: str, token: str, live_mode: bool) -> None:
    jira = connect_to_jira(jira_url, username, token)
    manual_entry_jobs = {}
    
    logger.info(f"Importing {len(work_logs)} work logs to JIRA...")
    cnt = 0
    total_minutes_worked = 0
    for work_log in work_logs:
        cnt += 1
        worklog_date = work_log['date_worked']
        started_date = datetime.datetime.strptime(worklog_date, '%Y-%m-%dT%H:%M:%S.000+0000')
        issue_key = work_log['job_number']
        minutes_worked = work_log['minutes_worked']
        total_minutes_worked += minutes_worked

        try:
            issue = jira.issue(issue_key)
        except Exception as e:
            if issue_key in manual_entry_jobs:
                manual_entry_jobs[issue_key].append(work_log)
            else:
                manual_entry_jobs[issue_key] = [work_log]
            logger.warning(f"Warning: Could not find issue with key {issue_key}. Skipping...")
            continue

        try:
            # Convert minutes to seconds for JIRA's worklog API
            seconds_worked = minutes_worked * 60
            if live_mode:
                jira.add_worklog(issue, timeSpentSeconds=seconds_worked, started=started_date)
                logger.info(f"{cnt}/{len(work_logs)}: Successfully added work log of {minutes_worked} minutes to issue {issue_key} on {worklog_date}.")
            else:
                logger.info(f"{cnt}/{len(work_logs)}: Would have added work log of {minutes_worked} minutes to issue {issue_key} on {worklog_date}.")                
        except Exception as e:
            logger.warning(f"Error: Could not add work log to issue {issue_key}. Reason: {e}")        
    

    if len(manual_entry_jobs) > 0:
        logger.info("The following jobs need to be entered manually:")
        for key, value in manual_entry_jobs.items():
            logger.info(f" {key}")
            for work_log in value:
                worklog_date = work_log['date_worked']
                fmt_date = datetime.datetime.strptime(worklog_date, '%Y-%m-%dT%H:%M:%S.000+0000').strftime('%d/%m/%Y')
                logger.info(f" - {fmt_date} {work_log['minutes_worked']} mins")

    # Display total hours worked
    total_hours_worked = total_minutes_worked / 60
    logger.info(f"Total hours worked: {total_hours_worked:.2f} hours")
    return
        
def process(source_file: str, jira_url: str, username: str, token: str, live_mode: bool):
    """Process the source file and create the JIRA import file
    """
    data = read_source_data_from_file(source_file)
    consolidated_data = consolidate_data(data)
    # display_data(consolidated_data)
    work_logs = convert_data_to_work_logs(consolidated_data)
    # display_work_logs(work_logs)
    
    if live_mode:
        proceed = input(f"LIVE mode selected. Proceed with importing {len(work_logs)} time entries? (Y/N) ")
        if proceed.lower() != "y":
            logger.info("Exiting...")
            return        

    import_work_logs(work_logs, jira_url, username, token, live_mode)
    logger.info("Done")
    return


def parse_opt():
    """ Parse command line options """

    ap = argparse.ArgumentParser()
    ap.add_argument("-s", "--source_file", type=str, required=True, help="Source CSV file")
    ap.add_argument("-j", "--jira_url", type=str, required=True, help="JIRA Url")
    ap.add_argument("-u", "--username", type=str, required=True, help="JIRA username")
    ap.add_argument("-t", "--token", type=str, required=True, help="JIRA API token")
    ap.add_argument("--live_mode", type=bool, action=argparse.BooleanOptionalAction, help="Update data?")
    return ap.parse_args()


def main(opt):
    process(**vars(opt))


if __name__ == "__main__":
    opt = parse_opt()
    main(opt)