"""
This sample demonstrates a simple skill built with the Amazon Alexa Skills Kit.
The Intent Schema, Custom Slots, and Sample Utterances for this skill, as well
as testing instructions are located at http://amzn.to/1LzFrj6

For additional samples, visit the Alexa Skills Kit Getting Started guide at
http://amzn.to/1LGWsLG
"""

from __future__ import print_function

import datetime
import requests

CONST_LAUNCH_API_BASE = "https://launchlibrary.net/1.2/"
CONST_WIKI_SUMMARY_API_FORMATTED = "https://en.wikipedia.org/w/api.php?format=json&utf8=true&action=query&redirects=1&prop=extracts&exintro=&explaintext=&indexpageids&titles={}"


# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': title,
            'content': output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }


# --------------- Functions that control the skill's behavior ------------------

def get_welcome_response():
    """ If we wanted to initialize the session to have some attributes we could
    add those here
    """

    session_attributes = {}
    card_title = "Welcome"
    speech_output = "Hey there! " \
                    "Ask me about upcoming SpaceX launches"
    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = "Ask me when the next SpaceX launch is"
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def handle_session_end_request():
    card_title = "Session Ended"
    speech_output = "Have a nice day!"
    # Setting this to true ends the session and exits the skill.
    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


def create_favorite_color_attributes(favorite_color):
    return {"favoriteColor": favorite_color}

def perform_next_launch_intent(intent, session):
    return get_next_launch(intent, session)

def get_next_launch(intent, session, offset=0, is_after=True):
    query_url = CONST_LAUNCH_API_BASE
    if offset >= 0:
        query_url += "launch?limit=1&agency=spx&mode=verbose&sort=asc&startdate={}&offset={}".format(utc_date_hour_now(), offset)
    else:
        query_url += "launch?limit=1&agency=spx&mode=verbose&sort=desc&enddate={}&offset={}".format(utc_date_hour_now(), abs(offset + 1))
    print("Requesting: " + query_url)
    fetched_json = requests.get(query_url).json()
    launch = fetched_json['launches'][0]
    launch_id = launch['id']
    agency_id = launch['rocket']['agencies'][0]['id']
    rocket_name = launch['rocket']['name']
    rocket_id = launch['rocket']['id']
    mission_name = "the" + launch['missions'][0]['name'] if launch['missions'] is not None and len(launch['missions']) > 0 else "a secret"
    mission_id = launch['missions'][0]['id'] if launch['missions'] is not None and len(launch['missions']) > 0 else 0
    launch_date = launch['windowstart']
    launch_date_ms = launch['wsstamp'] * 1000
    launch_window_calc = launch['westamp'] - launch['wsstamp']
    launch_window = 'an instantaneous window' if launch_window_calc == 0 else 'a window of {} minutes'.format(launch_window_calc/60)
    launch_location = launch['location']['pads'][0]['name']
    pad_location_id = launch['location']['pads'][0]['id']

    intro_phrase = ""
    time_phrase = ""
    if offset == 0:
        intro_phrase = "The next SpaceX launch will be the"
        time_phrase = "The launch is planned for"
    elif offset > 0:
        time_phrase = "The launch is planned for"
        if is_after:
            intro_phrase = "After that, the next SpaceX launch will be the"
        else:
            intro_phrase = "Before that, the next SpaceX launch will be the"
    elif offset < 0:
        time_phrase = "The launch happened on"
        if is_after:
            intro_phrase = "After that, the next SpaceX launch was the"
        else:
            intro_phrase = "Before that, the previous SpaceX launch was the"
    formatted_string = '{} {} rocket, performing {} mission. {} {}, with {}, flying from {}.'\
        .format(intro_phrase, rocket_name, mission_name, time_phrase, launch_date, launch_window, launch_location)

    if is_launch_soon(launch_date_ms):
        formatted_string += "\n\nThis launch is happening soon!"

    session["launch"] = {"launch-id": launch_id, "agency-id": agency_id, "rocket-id": rocket_id,
                         "mission-id": mission_id, "pad-location-id": pad_location_id, "offset": offset}

    return build_response(session, build_speechlet_response("Next Launch", formatted_string, None, True))

def is_launch_soon(launch_time_ms):
    ten_hours_ms = 10 * 60 * 60 * 1000
    return True if (ten_hours_ms + TimestampMillisec64() >= launch_time_ms) and (TimestampMillisec64() - ten_hours_ms <= launch_time_ms) else False

def TimestampMillisec64():
    return int((datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).total_seconds() * 1000)

def utc_date_hour_now():
    return datetime.datetime.utcnow().strftime('%Y-%m-%d-%H')

def set_color_in_session(intent, session):
    """ Sets the color in the session and prepares the speech to reply to the
    user.
    """

    card_title = intent['name']
    session_attributes = {}
    should_end_session = False

    if 'Color' in intent['slots']:
        favorite_color = intent['slots']['Color']['value']
        session_attributes = create_favorite_color_attributes(favorite_color)
        speech_output = "I now know your favorite color is " + \
                        favorite_color + \
                        ". You can ask me your favorite color by saying, " \
                        "what's my favorite color?"
        reprompt_text = "You can ask me your favorite color by saying, " \
                        "what's my favorite color?"
    else:
        speech_output = "I'm not sure what your favorite color is. " \
                        "Please try again."
        reprompt_text = "I'm not sure what your favorite color is. " \
                        "You can tell me your favorite color by saying, " \
                        "my favorite color is red."
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def get_color_from_session(intent, session):
    session_attributes = {}
    reprompt_text = None

    if session.get('attributes', {}) and "favoriteColor" in session.get('attributes', {}):
        favorite_color = session['attributes']['favoriteColor']
        speech_output = "Your favorite color is " + favorite_color + \
                        ". Goodbye."
        should_end_session = True
    else:
        speech_output = "I'm not sure what your favorite color is. " \
                        "You can say, my favorite color is red."
        should_end_session = False

    # Setting reprompt_text to None signifies that we do not want to reprompt
    # the user. If the user does not respond or says something that is not
    # understood, the session will end.
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))


# --------------- Events ------------------

def on_session_started(session_started_request, session):
    """ Called when the session starts """

    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """

    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return get_welcome_response()


def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # Dispatch to your skill's intent handlers
    if intent_name == "NextLaunchIntent":
        return perform_next_launch_intent(intent, session)
    elif intent_name == "MissionDetailIntent":
        return get_color_from_session(intent, session)
    elif intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    else:
        raise ValueError("Invalid intent")


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # add cleanup logic here


# --------------- Main handler ------------------

def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    # if (event['session']['application']['applicationId'] !=
    #         "amzn1.echo-sdk-ams.app.[unique-value-here]"):
    #     raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])
