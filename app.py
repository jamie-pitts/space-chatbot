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
import re

from flask import Flask
from flask import request
from flask import make_response
from flask import jsonify

# Flask app should start in global layout
app = Flask(__name__)

CONST_LAUNCH_API_BASE = "https://launchlibrary.net/1.2/"
CONST_WIKI_SUMMARY_API_FORMATTED = "https://en.wikipedia.org/w/api.php?format=json&action=query&redirects=1&prop=extracts&exintro=&explaintext=&indexpageids&titles={}"


@app.route('/status', methods=['GET'])
def status():
    return jsonify([{"status": "ok"}, {"system_time_utc": datetime.datetime.utcnow().isoformat()}])


@app.route('/launches/next', methods=['GET'])
def launches_next():
    return to_json_response(get_next_launch())


@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)

    print("Received request:")
    print(json.dumps(req, indent=4))

    res = process_request(req)
    print("Sending result:" + json.dumps(res, indent=4))

    return to_json_response(res)


def process_request(req):
    action = req.get("result").get("action")
    contexts = req.get("result").get("contexts") if req.get("result").get("contexts") else None

    if action == 'nextLaunch':
        return get_next_launch()

    if contexts is not None:
        if action == 'missionInfo':
            return get_mission_info(get_context(contexts, "launch"))
        elif action == 'rocketInfo':
            return get_rocket_info(get_context(contexts, "launch"))
        elif action == 'rocketInfo':
            return []

    return {}


def get_context(contexts, name):
    if contexts is None or len(contexts) == 0:
        return None
    for c in contexts:
        if c['name'] == name:
            return c
    return None


def to_json_response(data):
    res = json.dumps(data, indent=4)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r


def get_next_launch():
    query_url = CONST_LAUNCH_API_BASE + "launch?limit=1&agency=spx&mode=verbose&sort=asc&startdate=2017-05-09"
    print("Requesting: " + query_url)
    fetched_json = requests.get(query_url).json()
    launch = fetched_json['launches'][0]
    launch_id = launch['id']
    agency_id = launch['rocket']['agencies'][0]['id']
    rocket_name = launch['rocket']['name']
    rocket_id = launch['rocket']['id']
    rocket_img_url = launch['rocket']['imageURL']
    mission_name = launch['missions'][0]['name']
    mission_id = launch['missions'][0]['id']
    launch_date = launch['net']
    launch_window_calc = launch['westamp'] - launch['wsstamp']
    launch_window = 'an instantaneous window' if launch_window_calc == 0 else 'a window of {} minutes'.format(launch_window_calc/60)
    launch_location = launch['location']['pads'][0]['name']
    location_id = launch['location']['pads'][0]['id']
    formatted_string = 'The next SpaceX launch will be the {} rocket, performing the {} mission. The launch is planned for {}, with {}, flying from {}.'\
        .format(rocket_name, mission_name, launch_date, launch_window, launch_location)
    return makeWebhookResult(formatted_string, create_context("launch", 5, {"launch-id": launch_id, "agency-id": agency_id, "rocket-id": rocket_id,
                                                                            "mission-id": mission_id, "location-id": location_id}))


def get_mission_info(context):
    if context is None:
        return []
    query_url = CONST_LAUNCH_API_BASE + "mission/{}".format(int(float(context['parameters']['mission-id'])))
    print("Requesting: " + query_url)
    fetched_json = requests.get(query_url).json()
    mission = fetched_json['missions'][0]
    description = mission['description']
    info_url = mission['infoURL']
    wiki_url = mission['wikiURL']
    formatted_string = '{} \n'.format(description)
    if wiki_url is not None and wiki_url != "":
        formatted_string += '\n Wiki: {}'.format(wiki_url)
    if info_url is not None and info_url != "":
        formatted_string += '\nMore information: {}'.format(info_url)
    return makeWebhookResult(description, [], formatted_string)


def get_rocket_info(context):
    if context is None:
        return []
    query_url = CONST_LAUNCH_API_BASE + "rocket/{}".format(int(float(context['parameters']['rocket-id'])))
    print("Requesting: " + query_url)
    fetched_json = requests.get(query_url).json()
    rocket = fetched_json['rockets'][0]
    rocket_wiki = rocket['wikiURL']
    description = ""

    if rocket_wiki is not None and rocket_wiki != "":
        matcher = re.match("http[s]?://en.wikipedia.org/wiki/(.*)", rocket_wiki)
        if len(matcher.groups()) > 0:
            description = query_wiki_summary(matcher.group(1))

    if description == "":
        family = rocket['family']['name']
        name = rocket['name']
        description = "The {} rocket belongs to the {} rocket family.".format(name, family)

    info_urls = rocket['infoURLs']
    formatted_string = '{} \n'.format(description)
    if len(info_urls) > 0 and info_urls[0] != "":
        formatted_string += '\nSee for more information:'
        for url in info_urls:
            formatted_string += '\n{}'.format(url)

    return makeWebhookResult(description, [], formatted_string)


def create_context(name, lifespan, parameters):
    return [{"name": name, "lifespan": lifespan, "parameters": parameters}]


def makeWebhookResult(speech_string, output_context, display_string=None):
    if display_string is None:
        display_string = speech_string
    return {
        "speech": speech_string,
        "displayText": display_string,
        "contextOut": output_context,
        "data": [],
        "source": "com.jamiepitts.space-chatbot",
        "messages": [
            {
                "type": 0,
                "speech": speech_string
            }
        ]
    }


def query_wiki_summary(page_name):
    query_url = CONST_WIKI_SUMMARY_API_FORMATTED.format(page_name)
    print("Requesting: " + query_url)
    fetched_json = requests.get(query_url).json()
    page_id = fetched_json['query']['pageids'][0]
    summary = fetched_json['query']['pages'][page_id]['extract']
    return summary


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))

    print("Starting app on port %d" % port)

    app.run(debug=False, port=port, host='0.0.0.0')