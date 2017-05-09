#!/usr/bin/env python

from __future__ import print_function
from future.standard_library import install_aliases
install_aliases()

from urllib.parse import urlparse, urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError

import json
import os
import datetime
import requests

from flask import Flask
from flask import request
from flask import make_response
from flask import jsonify

# Flask app should start in global layout
app = Flask(__name__)

CONST_API_BASE = "https://launchlibrary.net/1.2/"


@app.route('/status', methods=['GET'])
def status():
    return jsonify([{"status": "ok"}, {"system_time_utc": datetime.datetime.utcnow().isoformat()}])


@app.route('/launches/next', methods=['GET'])
def launches_next():
    next_launch_string = getNextLaunchString()
    print("Returning result: " + next_launch_string)
    return next_launch_string


@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)

    print("Received request:")
    print(json.dumps(req, indent=4))

    res = processRequest(req)

    res = json.dumps(res, indent=4)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r


def getNextLaunchString():
    query_url = CONST_API_BASE + "launch?limit=1&agency=spx&mode=verbose&sort=asc&startdate=2017-05-09"
    print("Requesting: " + query_url)
    fetched_json = requests.get(query_url).json()
    launch = fetched_json['launches'][0]
    rocket_name = launch['rocket']['name']
    mission_name = launch['missions'][0]['name']
    launch_date = launch['net']
    launch_window_calc = launch['westamp'] - launch['wsstamp']
    launch_window = 'an instantaneous window' if launch_window_calc == 0 else 'a window of {} minutes'.format(launch_window_calc/60)
    launch_location = launch['location']['pads'][0]['name']
    formatted_string = 'The next SpaceX launch will be the {} rocket, performing the {} mission. The launch is planned for {}, with {}, flying from {}.'.format(rocket_name, mission_name, launch_date, launch_window, launch_location)
    return formatted_string



def processRequest(req):
    action = req.get("result").get("action")
    if action == 'nextLaunch':
        speech_string = getNextLaunchString()
    else:
        return {}

    return makeWebhookResult(speech_string)


def makeWebhookResult(speech_string):
    print("Response: " + speech_string)

    return {
        "speech": speech_string,
        "displayText": speech_string,
        "source": "com.jamiepitts.space-chatbot"
    }


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))

    print("Starting app on port %d" % port)

    app.run(debug=False, port=port, host='0.0.0.0')