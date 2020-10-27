# -*- coding: utf-8 -*-
# Copyright 2019 Boris Feld <boris@comet.ml>

""" Retrieve a Comet Experiment ID based on its ID and write a summary of the metrics as a comment
to the Github PR.

This script require the Comet API Key to be configured, easiest is by setting the COMET_API_KEY
environment variable.

You can also select which metrics and hyper-parameter to display by setting the
INPUT_DISPLAY_METRICS and INPUT_DISPLAY_PARAMS environment variables. If set, they should be a json
array containing the strings of metric names and hyper-params names.
"""

import argparse
import json
import os

import comet_ml
import requests
from tabulate import tabulate

parser = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
)
parser.add_argument(
    "experiment_id",
    help="The experiment id in the following format 'workspace/project_name/experiment_id'",
)

args = parser.parse_args()

api = comet_ml.API()
apie = api.get(args.experiment_id)

# Filter down to specific metrics and params
filter_metrics = os.environ.get("INPUT_DISPLAY_METRICS")
if filter_metrics:
    filter_metrics = json.loads(filter_metrics)

filter_params = os.environ.get("INPUT_DISPLAY_PARAMS")
if filter_params:
    filter_params = json.loads(filter_params)

data = [
    ["**ID**", "**[%s](%s)**" % (apie.id, apie._get_experiment_url())],
    ["**SHA**", apie.get_git_metadata()["parent"]],
]

# Metrics filtering
for metric in apie.get_metrics_summary():
    metric_name = metric["name"]

    if metric_name.startswith("sys"):
        continue

    if filter_metrics and metric_name not in filter_metrics:
        continue

    data.append([metric_name, metric["valueCurrent"]])

# Params filtering
for param in apie.get_parameters_summary():
    param_name = param["name"]

    if filter_params and param_name not in filter_params:
        continue

    data.append([param_name, param["valueCurrent"]])

data.append(["**Duration**", apie.duration_millis // 1000])

table = tabulate(data, tablefmt="github", headers="firstrow", showindex=False)
message = f"### Comet Experiment results\n\n{table}"

print(message)

nwo = os.environ["GITHUB_REPOSITORY"]
token = os.environ["GITHUB_TOKEN"]
pr_num = os.environ["PR_NUM"]

headers = {
    "Accept": "application/vnd.github.v3+json",
    "Authorization": f"token {token}",
}
url = f"https://api.github.com/repos/{nwo}/issues/{pr_num}/comments"
data = {"body": f"{message}"}
result = requests.post(url=url, headers=headers, json=data)

assert (
    result.status_code == 201
), f"Data summary did not post to PR successfully, received error code: {result.status_code}, result: {result.content!r}"
