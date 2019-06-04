#!/usr/bin/env python2
#  -*- coding: utf-8 -*-

"""A Webex Teams bot script that integrates with AWS Rekoginition
and hosted on AWS Lambda


A bot must be created and pointed to this server in the My Apps section of
https://developer.webex.com.  The bot's Access Token should be added as a
'WEBEX_TEAMS_ACCESS_TOKEN' environment variable on the Lambda function executing
this script.

This script only supports Python 2 at this time.

Copyright (c) 2019 George Diavatis.

Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import json
import os
import urllib
import boto3

from webexteamssdk import WebexTeamsAPI


api = WebexTeamsAPI(access_token=os.environ['WEBEX_TEAMS_ACCESS_TOKEN'])
rekognition = boto3.client('rekognition')


def main(event, context):

    # Convert lambda json string into python object
    message_data = json.loads(event['body'])

    #print the event details received for debugging
    #print("RECEIVED JSON DATA: " + json.dumps(event['body'], sort_keys=True, indent=2))
    #print("JSON DATA END")

    # Get the sender's details
    sender = api.people.get(message_data['actorId'])
    #print("SENDER")
    #print(sender.nickName)

    # LOOP PREVENTION MECHANISM
    # Stops the bot from responding to its own messages thus causing a loop
    if sender.id == api.people.me().id:
    	print("Ignoring event due to sender.id = me")
    	return 0


    room_id = message_data['data']['roomId']
    print("ROOM")
    print(room_id)

    # Get the room details
    current_room = api.rooms.get(room_id)
    #print("Current Room")
    #print(current_room.title)

    message_id = message_data['data']['id']
    #print("MESSAGE ID")
    #print(message_id)

    #Get the current message
    current_message = api.messages.get(message_id)
    #print("Current MESSAGE")
    #print(current_message.text)


    #help prompt for user
    if  'help' in current_message.text:
        response = 'Hey ' + sender.nickName
        response = response + ', I can help you rekognise what is in an image!\r\n'
        response = response + '\r\nSend me an image and I will tell you what I think...'
        print(response)
        api.messages.create(roomId=current_room.id, text=response)
        return 0


    if current_message.files:

        file_URL = json.dumps(current_message.files).encode('utf8')
        file_URL = file_URL.lstrip('["')
        file_URL = file_URL.rstrip(']"')
        print("FILE DETAILS")
        print(file_URL)

        if len(current_message.files) > 1:
            print("More than one files found in message id: " + message_id)
            status_message = "Sorry, I can only handle one image at a time!"
            api.messages.create(roomId=current_room.id, text=status_message)

        else:
            imageFile = download_image(file_URL)

            status_message = "According to my estimation, your image is: "
            api.messages.create(roomId=current_room.id, text=status_message)

            for label in find_labels(imageFile):
                print "{Name} - {Confidence}%".format(**label)
                api.messages.create(roomId=current_room.id, text=json.dumps(label, ensure_ascii=True, indent=2))


def find_labels(imageFile):
    ### Finds the labels for an image file using Amazon Rekoginition's object and scene detection deep learning feature

    try:
        response = rekognition.detect_labels(
            Image={
                'Bytes': imageFile,
            },
            MinConfidence=80.0,
            MaxLabels=10
        )
    except Exception as e:
        print(e)
        print('Unable to detect labels for image.')
        raise (e)

    return response['Labels']

def download_image(url):
    # Download image from Teams URL using bearer token authorization.

    request = urllib.request.Request(url, headers={'Authorization': 'Bearer %s' % os.environ['WEBEX_TEAMS_ACCESS_TOKEN']})
    return urllib.request.urlopen(request).read()


# the lambda handler function
def lambda_handler(event, context):
    try:
        return main(event, context)
    except Exception:
        print(event, context)
        raise
