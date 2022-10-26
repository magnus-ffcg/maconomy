#!/usr/bin/python

import requests
from urllib.parse import urljoin
import argparse
import logging
import textwrap
import json
import sys

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

    def post(self, path='', data=None, extra_headers=None):
        return self._call(verb='POST', path=path, data=data, extra_headers=extra_headers)  


def command_report(args, logger):
    url = 'https://me47417-iaccess.deltekfirst.com/maconomy-api/containers/me47417/'
    api = MaconomyApiClient(url=url, username=args.username, password=args.password, logger=logger, verbose=args.verbose)

    timeperday = args.timeperday.split(',')
    if len(timeperday) != 5:
        logger.error('You need to report all week days att once sadly, -t/--timeperday "8,8,8,8,8" ')
        return

    # Login and create timereporting instance
    logger.info("Creating timereporting instance")
    headers = dict()
    headers["Maconomy-Authentication"] = "X-Basic"
    headers["Maconomy-Authentication"] = "X-Reconnect"

    response = api.post(path="timeregistration/instances", data=dict(), extra_headers=headers)
    if response and response.status_code == 200:
        instance_id = response.json()["meta"]["containerInstanceId"]
        reconnect_token = response.headers["Maconomy-Reconnect"]
        concurrency_token = response.headers["Maconomy-Concurrency-Control"]
        request_id = response.headers["Maconomy-RequestId"]
    else:
        logger.error("Request failed - Aborting")
        return
    
    # Need to reset auth as we use token from now on
    api.auth=None

    # Get data for this week
    logger.info("Fetching weekly timesheet")

    headers = dict()
    headers["Authorization"] = f"X-Reconnect {reconnect_token}"
    headers["Maconomy-Concurrency-Control"] = concurrency_token
    headers["Maconomy-RequestId"] = request_id

    response = api.post(path=f"timeregistration/instances/{instance_id}/data;any", extra_headers=headers)
    if response and response.status_code == 200:
        reconnect_token = response.headers["Maconomy-Reconnect"]
        concurrency_token = response.headers["Maconomy-Concurrency-Control"]
        request_id = response.headers["Maconomy-RequestId"]
    else:  
        logger.error("Request failed - Aborting")
        return

    # Get specific payload and post the data
    logger.info(f"Posting your timelog for row {args.row}")
    json_reponse = response.json()
    payload = json_reponse["panes"]["table"]["records"][int(args.row)]

    for i, time in enumerate(timeperday):
        payload["data"][f"numberday{(i+1)}"] = int(time)
    
    headers = dict()
    headers["Authorization"] = f"X-Reconnect {reconnect_token}"
    headers["Maconomy-Concurrency-Control"] = concurrency_token
    headers["Maconomy-RequestId"] = request_id
    headers["Maconomy-Authentication"] = "X-Log-Out"

    response = api.post(path=f"timeregistration/instances/{instance_id}/data/panes/table/{args.row}", data=payload, extra_headers=headers)

    if response and response.status_code == 200:
        employee = payload["data"]["employeenumber"]
        period = payload["data"]["periodstart"]
        jobnumber = payload["data"]["jobnumber"]
        logger.info(f"Success, Updated row {args.row} for {employee} and period {period} and jobnumber {jobnumber} ")
    else:  
        logger.error("Failed")

def command_submit(args, logger): 
    pass
    




if __name__ == "__main__":
    print("""      __  ___                                            
     /  |/  /___ __________  ____  ____  ____ ___  __  __
    / /|_/ / __ `/ ___/ __ \/ __ \/ __ \/ __ `__ \/ / / /
   / /  / / /_/ / /__/ /_/ / / / / /_/ / / / / / / /_/ / 
  /_/  /_/\__,_/\___/\____/_/ /_/\____/_/ /_/ /_/\__, /  
                                                /____/   
    """)
    parent_parser = argparse.ArgumentParser(description="", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parent_parser.add_argument('--username', '-u', help='username', required=True)
    parent_parser.add_argument('--password', '-p', help='password', required=True)
    parent_parser.add_argument('--verbose', '-v', action='store_true', help="verbose")

    parser = argparse.ArgumentParser(add_help=False) 
    subparsers = parser.add_subparsers(dest="command", required=True)   

    report_parser = subparsers.add_parser('report', add_help=False, parents = [parent_parser])
    report_parser.add_argument('--row', '-r', help='row in timesheet', required=True)
    report_parser.add_argument('--timeperday', '-t', help='time per day (8,8,8,8,8)', required=True)

    submit_parser = subparsers.add_parser('submit', add_help=False, parents = [parent_parser])
    
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