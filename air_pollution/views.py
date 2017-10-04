# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.shortcuts import render
from .forms import Input
import requests
import json
from django.http import JsonResponse
import time
from pathlib import Path
import subprocess
from django.views.decorators.csrf import csrf_protect
import atexit
from .models import User

child = None
token = None
device_apikey = None
device_Subscription_Queue = None
device_resourceID = None


def create_tcp_connection():
    """ Creates a single tcp connection to middleware and writes its streaming contents asynchronously to a file
    named output.txt"""
    kill_child()
    global child
    child = subprocess.Popen(["python3", "air_pollution/async_http_read_files/async_http_read.py",
                              "https://smartcity.rbccps.org/api/0.1.0/subscribe?name={0}".format(device_resourceID),
                              "demo_{0}.txt".format(device_apikey),
                              device_apikey])


def kill_child():
    """ Kills the spawned python3 async_http_read.py process on close of the server"""
    global child
    if child is None:
        pass
    else:
        print("\n*********    Killing async_http_read {}    *********\n".format(str(child.pid)))
        child.kill()
        child = None

atexit.register(kill_child)


def register_new_device(user_token):
    """ Registers a new device in the format virtual_device_<user_token>. This device has permissions for
    services like subscribe, publish, historicData.
    APIKEY used here is the provider's api key (only for demo purpose).

    Site: http://rbccps.org/smartcity/doku.php
    Args:
     user_token: user_token is unique id used to register new devices. It is derived from csrftoken.
    Returns:
     response: A json response from the middleware
    """
    register_url = "https://smartcity.rbccps.org/api/0.1.0/register"

    register_headers = {
        "apikey": "d1fd0ddee6b94d048f4bbb4a854ce56b",
        "resourceID": "virtual_device_{0}".format(user_token),
        "serviceType": "publish,subscribe,historicData"
    }

    print("\n*********    Registering device to Middleware    *********\n")
    r = requests.get(register_url, {}, headers=register_headers)
    print(r.content.decode("utf-8"))
    response = json.loads(r.content.decode("utf-8"))
    if response["Registration"] == "failure":
        response["status"] = "failure"
    else:
        response["status"] = "success"
    return response


def subscriber_bind_queue(token):
    """ Subscriber or the new virtual device application is binded to the provider queue.
    Site: http://rbccps.org/smartcity/doku.php

    Returns:
         JsonResponse from the middleware
    """
    session = User.objects.get(token=token)
    subscriber_url = "https://smartcity.rbccps.org/api/0.1.0/subscribe/bind"
    subscriber_headers = {"apikey": session.api_key}
    subscriber_data = {
        "exchange": "amq.topic",
        "keys": [session.resourceID],
        "queue": session.subscription_queue
    }

    print("\n*********    Using Subscriber-Bind API to subscribe    *********\n")
    r = requests.post(subscriber_url, json=subscriber_data, headers=subscriber_headers)
    print(r.content.decode("utf-8"))
    print(subscriber_url, subscriber_data, subscriber_headers)
    response = dict()
    if 'bind queue ok' in str(r.content.decode("utf-8")):
        response["status"] = "success"
    else:
        response["status"] = "failure"
    response["response"] = str(r.content.decode("utf-8"))
    return response


def create(request):
    if request.method == 'POST':
        global device_apikey
        global device_resourceID
        global device_Subscription_Queue
        global token
        if token is None:
            token = request.POST.get("X-CSRFToken")
        if request.POST.get("request") == "register" and token == request.POST.get("X-CSRFToken"):
            response = register_new_device(token)
            if response["status"] == "success":
                # new session
                device_resourceID = response["ResourceID"]
                device_Subscription_Queue = response["Subscription Queue Name"]
                device_apikey = response["APIKey"]
                session = User(token=token,
                               api_key=device_apikey,
                               subscription_queue=device_Subscription_Queue,
                               resourceID=device_resourceID)
                session.save()
            else:
                # session exists case
                session = User.objects.get(token=token)
                device_resourceID = session.resourceID
                device_Subscription_Queue = session.subscription_queue
                device_apikey = session.api_key

            return JsonResponse(response)
        if request.POST.get("request") == "subscribe" and token == request.POST.get("X-CSRFToken"):
            response = subscriber_bind_queue(token)
            return JsonResponse(response)

    return render(request, 'air_pollution/create.html', {})


@csrf_protect
def index(request):
    """ Renders the page '/' """
    data = dict()
    global device_apikey
    global device_resourceID
    global device_Subscription_Queue
    global token

    if token is None:
        return render(request, 'air_pollution/home.html', data)
    if request.method == 'POST':
        if not request.POST._mutable:
            request.POST._mutable = True
        data["display_humidity"] = request.POST.get("display_humidity")
        del request.POST["display_humidity"]
        data["display_pressure"] = request.POST.get("display_pressure")
        del request.POST["display_pressure"]
        data["display_ozone"] = request.POST.get("display_ozone")
        del request.POST["display_ozone"]
        data["display_temperature"] = request.POST.get("display_temperature")
        del request.POST["display_temperature"]
        data["display_time"] = request.POST.get("display_time")
        del request.POST["display_time"]
        data["display_city"] = request.POST.get("display_city")
        del request.POST["display_city"]

        form = Input(request.POST)

        if form.is_valid():
            print("\n*********    Sending DATA    *********\n")
            print(form.cleaned_data)
            data["city"] = form.cleaned_data["city"]
            data["humidity"] = form.cleaned_data["humidity"]
            data["pressure"] = form.cleaned_data["pressure"]
            data["ozone"] = form.cleaned_data["ozone"]
            data["temperature"] = form.cleaned_data["temperature"]
            data["time"] = form.cleaned_data["time"]
            send_data(form.cleaned_data)

    elif request.method == 'GET':
        session = User.objects.get(token=token)
        device_resourceID = session.resourceID
        device_Subscription_Queue = session.subscription_queue
        device_apikey = session.api_key

        create_tcp_connection()
        api_json = fetch_data()
        data["city"] = api_json['data']['city']['name']
        data["geo"] = api_json['data']['city']['geo']
        data["humidity"] = api_json['data']['iaqi']['h']['v']
        data["pressure"] = api_json['data']['iaqi']['p']['v']
        data["ozone"] = api_json['data']['iaqi']['o3']['v']
        data["temperature"] = api_json['data']['iaqi']['t']['v']
        data["time"] = int(time.time())
        data["display_humidity"] = "Humidity: Nil"
        data["display_pressure"] = "Pressure: Nil"
        data["display_ozone"] = "Ozone: Nil"
        data["display_temperature"] = "Temperature: Nil"
        data["display_time"] = "Time: Nil"
        data["display_city"] = "City: Nil"

    return render(request, 'air_pollution/index.html', data)


def manually_restart_async(request):
    """ Manually tries to run async_http_read.py in case of failures at /restart"""
    if child is not None:
        context = {"connection": "restarted"}
    else:
        context = {"connection": "started"}
    create_tcp_connection()
    return JsonResponse(context)


def read_from_file(request):
    """ Reads from output.txt file the json data that came from the middleware."""
    outfile = Path('air_pollution/async_http_read_files/files/demo_{0}.txt'.format(device_apikey))
    if outfile.exists():
        print("\n*********    Reading from file demo_{0}    *********\n".format(device_apikey))
        with open('air_pollution/async_http_read_files/files/demo_{0}.txt'.format(device_apikey)) as f:
            content = json.loads(f.read())
    else:
        print("\n*********    Reading from file output.txt    *********\n")
        outfile = Path('air_pollution/async_http_read_files/files/output.txt')
        if outfile.exists():
            with open('air_pollution/async_http_read_files/files/output.txt') as f:
                content = json.loads(f.read())
    print("\n*********    Closing File    *********\n")
    return JsonResponse(content["data_schema"])


def fetch_data(city="bangalore"):
    """ Fetches AQI data for bangalore from api.waqi.info site. """
    api_token = "22a7ea10a287c7d9ff26771099a975f48db68e52"  # AQI api token
    url = "http://api.waqi.info/feed/{0}/?token={1}".format(city, api_token)
    response = requests.get(url)
    return response.json()


def send_data(device_data=None):
    """ Sends user input data or device data (data from aqi.waqi.info site) to the middleware"""
    api_json = fetch_data()
    data = dict()
    data["id"] = "virtual_air_pollution_device_" + str(api_json["data"]["idx"])
    data["owner"] = {"name": "harish"}
    data["provider"] = {
        "name": "CPCB - India Central Pollution Control Board",
        "website": "http://aqicn.org/"}
    data["refCatalogueSchema"] = "air_quality_index_item.json"
    data["refCatalogueSchemaRelease"] = "0.1.0"
    data["tags"] = ["virtual_sensor", "test_sensor"]
    data["accessMechanism"] = {}
    data["latitude"] = {
        "value": 12.9715987,
        "ontologyRef": "http://www.w3.org/2003/01/geo/wgs84_pos#"}
    data["longitude"] = {
        "value": 77.5945627,
        "ontologyRef": "http://www.w3.org/2003/01/geo/wgs84_pos#"}
    if device_data is None:
        data_schema = dict()
        data_schema["city"] = api_json['data']['city']['name']
        data_schema["geo"] = api_json['data']['city']['geo']
        data_schema["humidity"] = api_json['data']['iaqi']['h']['v']
        data_schema["pressure"] = api_json['data']['iaqi']['p']['v']
        data_schema["ozone"] = api_json['data']['iaqi']['o3']['v']
        data_schema["temperature"] = api_json['data']['iaqi']['t']['v']
        data_schema["time"] = api_json['data']['time']['s']

        data["data_schema"] = data_schema
    else:
        data["data_schema"] = device_data

    publish_url = "https://smartcity.rbccps.org/api/0.1.0/publish"
    publish_headers = {"apikey": device_apikey}
    publish_data = {"exchange": "amq.topic",
                    "key": device_resourceID,
                    "body": str(json.dumps(data))}

    print("\n*********    Publisher: Sending data to Middleware    *********\n")
    r = requests.post(publish_url, json.dumps(publish_data), headers=publish_headers)
    print(r.content.decode("utf-8"))
    print("\n*********    Publisher: Received response from Middleware    *********\n")
