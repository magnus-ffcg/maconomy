#!/usr/bin/python

import requests
from urllib.parse import urljoin
import argparse
import logging
import textwrap
import json
import sys
from tabulate import tabulate
from argparse_formatter import ParagraphFormatter

class ApiClient():
    def __init__(self, url, headers=None, auth=None, logger=None, verbose=False):
        self.url  = url
        self.auth = auth
        self.headers = headers
        self.logger = logger
        self.verbose = verbose

    def _call(self, verb, path='', data=None, extra_headers=dict()):
        headers = {**self.headers, **extra_headers}
        
        try:
            url = urljoin(self.url, path)
            self.logger.debug(f"--- REQUEST ---------")
            self.logger.debug(f'Request url:\n{url}\n')
            self.logger.debug(f"Request headers:\n{headers}\n")
            self.logger.debug(f"Request payload:\n{data}")
            self.logger.debug(f"-------------------")
            response = requests.request(method=verb, headers=headers, auth=self.auth, url=url, json=data)   
            self.logger.debug(f"--- RESPONSE ---------")
            self.logger.debug(f"Response status_code:\n{response.status_code}\n")
            self.logger.debug(f"Response text:\n{response.text}\n")
            self.logger.debug(f"Response headers:\n{response.headers}")
            self.logger.debug(f"-------------------")
            return response
        except Exception as e:
            self.logger.error("Request failed")
            self.logger.debug("--- EXCEPTION ------")
            self.logger.debug(e)
            self.logger.debug(f"-------------------")
        
        return None

class MaconomyApiClient(ApiClient):
    logger = None
    verbose = False
    previous_reconnect_token = None
    previous_concurrency_token = None
    previous_request_id = None

    def __init__(self, url, username, password, logger=None, verbose=False):
        self.logger = logger
        self.verbose = verbose

        headers = {
            'X-Forwarded-Proto': 'https',
            'Maconomy-Forwarded-Base-Path': 'maconomy-api',
            'Accept': 'application/vnd.deltek.maconomy.containers-v2+json; charset=utf-8',
            'Content-type': 'application/vnd.deltek.maconomy.containers-v2+json',
            'Accept-Language': 'en-US',
        }

        super().__init__(url=url, headers=headers, auth=(username, password), logger=logger, verbose=self.verbose)

    def _post(self, path='', data=None, extra_headers=None):
        response = self._call(verb='POST', path=path, data=data, extra_headers=extra_headers)  

        if not self.previous_reconnect_token and 'Maconomy-Reconnect' in response.headers:
            self.previous_reconnect_token = response.headers["Maconomy-Reconnect"]

        if 'Maconomy-Concurrency-Control' in response.headers:   
            self.previous_concurrency_token = response.headers["Maconomy-Concurrency-Control"]

        self.previous_request_id = response.headers["Maconomy-RequestId"] 

        return response

    def get_timereport_instance(self):
        self.logger.info("Creating timereporting instance")
        
        headers = dict()
        headers["Maconomy-Authentication"] = "X-Basic"
        headers["Maconomy-Authentication"] = "X-Reconnect"

        response = self._post(path="timeregistration/instances", data=dict(), extra_headers=headers)
        if response and response.status_code == 200:
            return response.json()    

        logger.error("Request failed - Aborting")
        return None
        
    def get_weekly_timereport(self, instance_id, logout=False):
        self.logger.info("Fetching weekly timesheet")

        headers = dict()
        headers["Authorization"] = f"X-Reconnect {self.previous_reconnect_token}"
        headers["Maconomy-Concurrency-Control"] = self.previous_concurrency_token
        headers["Maconomy-RequestId"] = self.previous_request_id

        if logout:
            headers["Maconomy-Authentication"] = "X-Log-Out"

        response = self._post(path=f"timeregistration/instances/{instance_id}/data;any", extra_headers=headers)
        if response and response.status_code == 200:
            return response.json()
    
        self.logger.error("Request failed - Aborting")
        return None

    def post_timereport(self, instance_id, row, payload):
        self.logger.info(f"Posting your timelog for row {row}")

        headers = dict()
        headers["Authorization"] = f"X-Reconnect {self.previous_reconnect_token}"
        headers["Maconomy-Concurrency-Control"] = self.previous_concurrency_token
        headers["Maconomy-RequestId"] = self.previous_request_id
        headers["Maconomy-Authentication"] = "X-Log-Out"

        response = self._post(path=f"timeregistration/instances/{instance_id}/data/panes/table/{row}", data=payload, extra_headers=headers)

        if response and response.status_code == 200:
            return response.json()

        self.logger.error("Request failed - Aborting")
        return None

    def submit_timereport(self, instance_id):
        self.logger.info(f"Submitting your timereport for this week")

        headers = dict()
        headers["Authorization"] = f"X-Reconnect {self.previous_reconnect_token}"
        headers["Maconomy-Concurrency-Control"] = self.previous_concurrency_token
        headers["Maconomy-RequestId"] = self.previous_request_id
        headers["Maconomy-Authentication"] = "X-Log-Out"
        
        response = self._post(path=f"timeregistration/instances/{instance_id}/data/panes/card/0/action;name=submittimesheet", extra_headers=headers)

        if response and response.status_code == 200:
            return response.json()

        self.logger.error("Request failed - Aborting")
        return None


def command_report(args, logger):
    api = MaconomyApiClient(url=url, username=args.username, password=args.password, logger=logger, verbose=args.verbose)

    timeperday = args.timeperday.split(',')
    if len(timeperday) != 5:
        logger.error('You need to report all week days att once sadly, -t/--timeperday "8,8,8,8,8" ')
        return
   
    if args.row.isnumeric() == False or int(args.row) < 0:
        logger.error("You need to pass a number >= 0 to -r/--row")
        return
    row = int(args.row)

    # Login and create timereporting instance
    response = api.get_timereport_instance()
    if not response or not 'meta' in response:
        return

    # Get instance id
    instance_id = response["meta"]["containerInstanceId"]

    if not instance_id:
        return

    # Need to reset auth as we use token from now on
    api.auth=None

    # Get data for this week
    response = api.get_weekly_timereport(instance_id)
    if not response or not 'panes' in response: 
        return

    # Get specific payload for row
    payload = response["panes"]["table"]["records"][row]
    for i, time in enumerate(timeperday):
        payload["data"][f"numberday{(i+1)}"] = int(time)

    # Post the time report row
    response = api.post_timereport(instance_id, row, payload)
    if not response:
        return

    employee = payload["data"]["employeenumber"]
    period = payload["data"]["periodstart"]
    jobnumber = payload["data"]["jobnumber"]
    
    logger.info(f"Success, Updated row {args.row} for {employee} and period {period} and jobnumber {jobnumber} ")


def command_submit(args, logger): 
    api = MaconomyApiClient(url=url, username=args.username, password=args.password, logger=logger, verbose=args.verbose)

    response = api.get_timereport_instance()
    if not response or not 'meta' in response:
        return

    instance_id = response["meta"]["containerInstanceId"]

    if not instance_id:
        return

    # Need to reset auth as we use token from now on
    api.auth=None

    # Need to reset auth as we use token from now on
    api.auth=None

    # Get data for this week
    response = api.get_weekly_timereport(instance_id)
    if not response or not 'panes' in response: 
        return

    # Get data for this week
    response = api.submit_timereport(instance_id)
    if not response: 
        return

    logger.info("Success")


def command_view(args, logger):
    api = MaconomyApiClient(url=url, username=args.username, password=args.password, logger=logger, verbose=args.verbose)

    # Login and create timereporting instance
    response = api.get_timereport_instance()
    if not response or not 'meta' in response:
        return

    # Get instance id
    instance_id = response["meta"]["containerInstanceId"]

    if not instance_id:
        return

    # Need to reset auth as we use token from now on
    api.auth=None

    # Get data for this week
    response = api.get_weekly_timereport(instance_id, logout=True)
    if not response or not 'panes' in response: 
        return

    # Get specific payload for row
    meta = response["panes"]["card"]["records"][0]["data"]
    records = response["panes"]["table"]["records"]

    data = []
    print(f'Timereport for {meta["employeenamevar"]}')

    headers = ["Row", "Job", "Task", "Mon", "Tue", "Wed", "Thu", "Fri"]
    for record in records:
        row = record["data"]
        data.append([row["linenumber"]-1, row["description"], row["entrytext"], row["numberday1"], row["numberday2"], row["numberday3"], row["numberday4"], row["numberday5"]])

    print(tabulate(data, headers=headers))


url = 'https://me47417-iaccess.deltekfirst.com/maconomy-api/containers/me47417/' 

if __name__ == "__main__":
    print("""      __  ___                                            
     /  |/  /___ __________  ____  ____  ____ ___  __  __
    / /|_/ / __ `/ ___/ __ \/ __ \/ __ \/ __ `__ \/ / / /
   / /  / / /_/ / /__/ /_/ / / / / /_/ / / / / / / /_/ / 
  /_/  /_/\__,_/\___/\____/_/ /_/\____/_/ /_/ /_/\__, /  
                                                /____/   
    """)
    parent_parser = argparse.ArgumentParser(description="", formatter_class=ParagraphFormatter)
    parent_parser.add_argument('--username', '-u', help='username', required=True)
    parent_parser.add_argument('--password', '-p', help='password', required=True)
    parent_parser.add_argument('--verbose', '-v', action='store_true', help="verbose")

    parser = argparse.ArgumentParser(add_help=False) 
    subparsers = parser.add_subparsers(dest="command", required=True)   

    report_parser = subparsers.add_parser('report', add_help=False, parents = [parent_parser])
    report_parser.add_argument('--row', '-r', help='row in timesheet', required=True)
    report_parser.add_argument('--timeperday', '-t', help='time per day (8,8,8,8,8)', required=True)

    submit_parser = subparsers.add_parser('submit', add_help=False, parents = [parent_parser])
    view_parser = subparsers.add_parser('view', add_help=False, parents = [parent_parser])
    
    args = parser.parse_args()
    
    if args.command is None:
        exit(1)

    level = logging.INFO
    if args.verbose:
        level = logging.DEBUG

    logging.basicConfig(stream=sys.stdout, level=level, format="%(message)s")
    logger = logging.getLogger('MACONOMY')

    if args.command == 'report':
        command_report(args, logger)

    if args.command == 'submit':
        command_submit(args, logger)  

    if args.command == 'view':
        command_view(args, logger) 
