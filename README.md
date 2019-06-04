

## WebEx teams bot scene and object detection ##

### High Level Steps

 - Create a bot in Webex teams and get the access token
 - Create IAM role for our Lambda function with permissions to Rekognition and Cloudwatch logs
 - Create a Lambda function for the bot
	  - An API should be implicitly created for the Lambda function
 - Register a Webhook in Webex Teams that points to API Gateway
 - Become familiar with CloudWatch whilst debugging


### Introduction

This post will show you how to build a serverless scene and object detecting WebEx teams bot utilising AWS API Gateway, Lambda and Rekognition. The Lambda function is coded in Python.

Although this example uses the Rekognition Label Detection API to recognise object and scene labels, it could easily be modified to identify faces (including faces from custom collections), perform sentiment analysis or recognise celebrities.

At a high level, the following steps occur:

 1. A user sends a message to the Webex Teams Rekognition bot which includes an attached image
 2. Webex Teams sends a webhook request to API gateway address associated with the Rekognition Lambda function
 3. API gateway triggers the invocation of the Rekognition Lambda function which makes use of the Rekognition API to perform object and scene detection on the image
 4. A number of a number of labels are returned from the function and posted to the WebEx Teams space. The labels consist of an attribute and the confidence that it is correct in percentages

### Register the WebEx Teams Bot

The first step is to head over to the WebEx Developer site and the [Create a New App](https://developer.webex.com/my-apps/new) page. On there click on Create a Bot.

Make a note of the access token as you will need it later.

### Create a IAM Role

 1. Within the IAM section of the AWS console, click on Roles and then Create a Role
 2. Select Lambda as the service that will use the role and then Next: Permissions
 3. Click on Create policy and then type Rekognition as the service
 4. Under Actions select Read and DetectLabels and DetectModerationLabels
 5. Back at the Service prompt type CloudWatch Logs and select CreateLogGroup,
CreateLogStream and PutLogEvents as the Actions.
 6. Then Review Policy and give it a name such as mywebexfunctionpolicy


### Create the lambda function

Now its time to create the lambda function that will perform the computations for our bot.

Within the lambda section of the AWS console click on Create function and Author from scratch. Give the function a name and select Python 2.7 as the runtime. Also create a new role with basic permissions for the execution role.


There should now be a new function. On the left hand side select API Gateway as the trigger. You want to create a new API with Security set to Open. Click Add and then Save.


Scroll down to the Execution role section and click on the **View the WebexFunctionName role** on the IAM Console.


On the Role Summary screen, click on Attach policies and search for the mywebexfunctionpolicy you created earlier. Attach that policy to your role. You should now have the mywebexfunctionpolicy and the AWSLambdaBasicExecutionRole policies attached.


Back on the Lambda screen, it is now time to upload the code which you can find on [my GitHub page](https://github.com/cmsgdiav/webex-teams-rekognition-lambda).

Start by cloning the repository to your local machine and navigating to the newly created directory.

~~~bash
git clone https://github.com/cmsgdiav/webex-teams-rekognition-lambda
cd webex-teams-rekognition-lambda/
~~~

We will be making use of the webexteamssdk which is a non standard python library. In order for lambda to be able to make use of that library, we have to upload it to lambda.

This is achieved by installing the libraries to a local folder and packaging them up into a zip file which we then upload to lambda.

~~~bash
pip install webexteamssdk -t .
~~~
 You should now have the packages that make up the webexteamssdk in your local folder which we will compress into a zip file with the below command.

~~~bash
zip -r ../mylambdafunction.zip ./ -x \*.pyc
~~~

The newly created zip file should be now uploaded to lambda. You will find the **Upload a .zip file** option under the code entry type drop box. Click Save for the file to be uploaded.

You should now see all the packages listed along with the lambda_function.py file that has our code.

An environment variable is required called WEBEX_TEAMS_ACCESS_TOKEN which should be populated with the Access Token value you noted down when creating the Bot.


Before we can try out our function, we need to register a webhook so Webex teams knows where to send the messages.

### Create a Webex Teams Webhook

Webex Teams needs to know how it reach our Lambda function in order to invoke it. It does this by means of a webhook that points to API Gateway.

You can create the webhook by going to the [Webex Developer site](https://developer.webex.com/docs/api/v1/webhooks/create-a-webhook).

Make sure you are using the bot token in the bearer field which you will have noted down when registering the bot.

Enter a name for the webhook, the targetUrl should be the address of your API and enter ***all*** in the resource and event boxes which gives the webhook access to all features.

### Testing our Bot ###

At this point, all being well, when you send a message to your bot from Webex teams it should respond to you.

![Success](https://github.com/cmsgdiav/webex-teams-rekognition-lambda/blob/master/parliament.gif)

But invariably something wont be quite right!

This is where CloudWatch is invaluable as it helps you debug your code so be sure to look through the logs.

Sometimes the code runs longer than usually, especially when processing a more complex image. Therefore it can help to set Lambda timer to 10 seconds to avoid time outs and give the code enough time to run.

### Python Code ###

I thought I would also include a section on the Python code used to implement the lambda function for those interested.

~~~python
import json #used to handle JSON data
import os #used to access the environment variable
import urllib #used to download the image from Teams
import boto3 # used to access Rekognition APIs

from webexteamssdk import WebexTeamsAPI #used to more easily interact with Teams


api = WebexTeamsAPI(access_token=os.environ['WEBEX_TEAMS_ACCESS_TOKEN']) #initialised the webex teams api with our access token
rekognition = boto3.client('rekognition') #initialised the boto3 client
~~~

Jumping to the bottom of the code we have the lambda handler which is the function lambda calls when invoked.

We have configured this to point to the main function in order to help us catch errors.

~~~python
# the lambda handler function
def lambda_handler(event, context):
    try:
        return main(event, context)
    except Exception:
        print(event, context)
        raise
~~~

The main function is where the majority of the work happens.

The main function loads the JSON data send from Webex teams into *message_data*.

You will note a number of commented out code that was used for debugging purposes. I have left that in case you find it useful. You can see the output from the print statements in CloudWatch logs.

Using the webex teams API we get the name of the sender based on the ID of the user who initiated the action in Webex teams.

We use that sender ID to confirm that the action was undertaken by a user and not the bot responding which would cause a loop.


~~~python
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
    #print("ROOM")
    #print(room_id)

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
~~~

We also get the roomId that the message was sent in so that we know which room to reply back to. We also need to find out what the current message ID is so that we can get the content and act accordingly.

~~~python
#help prompt for user
    if  'help' in current_message.text:
        response = 'Hey ' + sender.nickName
        response = response + ', I can help you rekognise what is in an image!\r\n'
        response = response + '\r\nSend me an image and I will tell you what I think...'
        print(response)
        api.messages.create(roomId=current_room.id, text=response)
        return 0
~~~

In this section of code we check to see if the sure typed *help* in their message and if so to respond back with instruction on what they need to do.

~~~python

    if current_message.files:

        file_URL = json.dumps(current_message.files).encode('utf8')
        file_URL = file_URL.lstrip('["')
        file_URL = file_URL.rstrip(']"')
        print("FILE DETAILS")
        print(file_URL)

   ~~~

Now we check to see if any files were attached to the message. As the URL of the file location is provided in JSON format, we need to strip out the unwanted characters first.

~~~python
   if len(current_message.files) > 1:
            print("More than one files found in message id: " + message_id)
            status_message = "Sorry, I can only handle one image at a time!"
            api.messages.create(roomId=current_room.id, text=status_message)
   else:
            imageFile = download_image(file_URL)

~~~

If the user tries to send more than one files we send out an error message otherwise we invoke the download_image function with the URL of the file in order to download it.

~~~python
def download_image(url):
    # Download image from Teams URL using bearer token authorization.

    request = urllib.request.Request(url, headers={'Authorization': 'Bearer %s' % os.environ['WEBEX_TEAMS_ACCESS_TOKEN']})
    return urllib.request.urlopen(request).read()
~~~

~~~python

            status_message = "According to my estimation, your image is: "
            api.messages.create(roomId=current_room.id, text=status_message)
~~~


With the image downloaded, we now send a message to the Webex teams space preparing the user for the information then will see.

We then invoke the *find_labels* function with an input the file we just downloaded.

~~~python
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
~~~

The *find_labels* function invokes the rekognition API to detect the labels in the provided image. We have set the threshold to a minimum 80% confidence and require a maximum of 10 labels for that image.

The function returns the Labels in the response object in JSON format.

~~~python
            for label in find_labels(imageFile):
                print "{Name} - {Confidence}%".format(**label)
                api.messages.create(roomId=current_room.id, text=json.dumps(label, ensure_ascii=True, indent=2))
~~~

When we invoke the find_labels function we iterate through it outputting the content to the Webex Space it was invoked from. As the data is in JSON format, we use to the json.dumps function to output it.

And that concluded the code. As you can see, it should be easy to modify it to make use of different Rekognition APIs. You can find examples of the other APIs [here](https://gist.github.com/alexcasalboni/0f21a1889f09760f8981b643326730ff).

