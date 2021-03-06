from stravalib import Client
import requests
import os
from datetime import timedelta
from celery import Celery
from celery.task import periodic_task
import json


BACKEND = BROKER = os.getenv('BROKER', 'redis://localhost:6379')
celery = Celery(__name__, backend=BACKEND, broker=BROKER)

DATASERVICE = os.environ['DATA_SERVICE']


def fetch_all_runs():
    users = requests.get(DATASERVICE + '/users')
    users = users.json()
    runs_fetched = {}
    for user in users:
        strava_token = None

        if 'strava_token' in user:
            strava_token = user['strava_token']

        email = user['email']

        if strava_token is None:
            continue

        print('Fetching Strava for %s' % email)
        runs_fetched[user['id']] = fetch_runs(user)

    return runs_fetched


def push_to_dataservice(runs):  # pragma: no cover
    requests.post(DATASERVICE + '/runs', json=runs)


def activity2run(activity):
    """Used by fetch_runs to convert a strava entry.
    """
    run = {}
    run['strava_id'] = activity.id
    run['name'] = activity.name
    run['distance'] = activity.distance.num
    run['elapsed_time'] = activity.elapsed_time.total_seconds()
    run['average_speed'] = activity.average_speed.num
    run['average_heartrate'] = activity.average_heartrate
    run['total_elevation_gain'] = activity.total_elevation_gain.num
    run['start_date'] = activity.start_date.timestamp()
    run['title'] = activity.name
    run['description'] = activity.description
    return run


def fetch_runs(user):
    client = Client(access_token=user['strava_token'])
    runs = []
    for activity in client.get_activities(limit=10):
        if activity.type != 'Run':
            continue
        runs.append(activity2run(activity))
    return runs


@periodic_task(run_every=timedelta(seconds=3))
def periodic_fetch():  # pragma no cover
    push_to_dataservice(fetch_all_runs())


if __name__ == '__main__':
    periodic_fetch()
