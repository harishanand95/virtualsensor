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
from django.middleware.csrf import get_token
import atexit
from .models import User
child = None


def create_tcp_connection(api_key, resource_id):
    """ Creates a single tcp connection to middleware and writes its streaming contents asynchronously to a file
    named output.txt"""
    kill_child()
    global child
    child = subprocess.Popen(["python3", "air_pollution/async_http_read_files/async_http_read.py",
                              "https://smartcity.rbccps.org/api/0.1.0/subscribe?name={0}".format(resource_id),
                              "demo_{0}.txt".format(api_key),
                              api_key])


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
    response = r.content.decode("utf-8")
    print(response)
    response = json.loads(response[:-331] + "}")  # Temporary fix to a middleware bug, should be removed in future
    if "success" in r.content.decode("utf-8"):
        response["Registration"] = "success"
    else:
        response["Registration"] = "failure"
    # Add status to response
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
    # Add 'status' to response
    if 'bind queue ok' in str(r.content.decode("utf-8")):
        response["status"] = "success"
    else:
        response["status"] = "failure"
    response["response"] = str(r.content.decode("utf-8"))
    return response


def create(request):
    if request.method == 'POST':
        print("COOKIE TOKEN: " + request.COOKIES['token'])
        token = request.COOKIES['token']
        # REGISTER API REQUEST
        if request.POST.get("request") == "register":
            response = register_new_device(token)
            if response["status"] == "success":
                # Save new device details
                session = User(token=token,
                               api_key=response["APIKey"],
                               subscription_queue=response["Subscription Queue Name"],
                               resourceID=response["ResourceID"])
                session.save()
            else:
                # device already exists but in db
                response["response"] = "Device not registered in local DB."
            return JsonResponse(response)
        # SUBSCRIBE-BIND API REQUEST
        if request.POST.get("request") == "subscribe":
            response = subscriber_bind_queue(token)
            return JsonResponse(response)
    return render(request, 'air_pollution/create.html', {})


def set_cookie(request):
    response = render(request, 'air_pollution/login.html', {})
    response.set_cookie('token', get_token(request), max_age=300)
    return response

@csrf_protect
def index(request):
    """ Renders the page '/' """
    data = dict()
    if 'token' in request.COOKIES and User.objects.filter(token=request.COOKIES['token']).exists():
        token = request.COOKIES['token']
        print("\n COOKIE TOKEN: " + request.COOKIES['token'])
    else:
        print("no cookie")
        return set_cookie(request)
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
            send_data(token, form.cleaned_data)
        return JsonResponse({"status": "success"})
    elif request.method == 'GET':
        session = User.objects.get(token=token)
        create_tcp_connection(session.api_key, session.resourceID)
        api_json = fetch_data()
        data["city"] = api_json['data']['city']['name']
        data["geo"] = api_json['data']['city']['geo']  # not used
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


def read_from_file(request):
    """ Reads from output.txt file the json data that came from the middleware."""
    if 'token' in request.COOKIES and User.objects.filter(token=request.COOKIES['token']).exists():
        token = request.COOKIES['token']
    else:
        return JsonResponse({"restart": "true"})

    session = User.objects.get(token=token)
    outfile = Path('air_pollution/async_http_read_files/files/demo_{0}.txt'.format(session.api_key))
    if outfile.exists():
        print("\n*********    Reading from file demo_{0}    *********\n".format(session.api_key))
        with open('air_pollution/async_http_read_files/files/demo_{0}.txt'.format(session.api_key)) as f:
            content = json.loads(f.read())
    else:
        print("\n*********    Reading from file output.txt    *********\n")
        outfile = Path('air_pollution/async_http_read_files/files/output.txt')
        if outfile.exists():
            with open('air_pollution/async_http_read_files/files/output.txt') as f:
                content = json.loads(f.read())
    return JsonResponse(content["data_schema"])


def fetch_data(city="bangalore"):
    """ Fetches AQI data for bangalore from api.waqi.info site. """
    api_token = "22a7ea10a287c7d9ff26771099a975f48db68e52"  # AQI api token
    url = "http://api.waqi.info/feed/{0}/?token={1}".format(city, api_token)
    response = requests.get(url)
    return response.json()


def send_data(user_token, device_data=None):
    """ Sends user input data or device data (data from aqi.waqi.info site) to the middleware. Follows Schema"""
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

    session = User.objects.get(token=user_token)
    publish_url = "https://smartcity.rbccps.org/api/0.1.0/publish"
    publish_headers = {"apikey": session.api_key}
    publish_data = {"exchange": "amq.topic",
                    "key": session.resourceID,
                    "body": str(json.dumps(data))}

    print("\n*********    Publisher: Sending data to Middleware    *********\n")
    r = requests.post(publish_url, json.dumps(publish_data), headers=publish_headers)
    print(r.content.decode("utf-8"))
    print("\n*********    Publisher: Received response from Middleware    *********\n")


def streetlight(request):
    if request.method == 'GET':
        return render(request, 'air_pollution/streetlight.html', {})
    if request.method == 'POST':
        if not request.POST._mutable:
            request.POST._mutable = True
        if request.POST["brightness"] == "":
            request.POST["brightness"] = 0
        print(request.POST.get("brightness"))
        api_key = request.POST.get("apikey")
        data = {
            "ManualControlParams": {
                "targetBrightnessLevel": request.POST["brightness"]
            }
        }
        resource_id = "70b3d58ff0031f00_update"
        publish_url = "https://smartcity.rbccps.org/api/0.1.0/publish"
        publish_headers = {"apikey": api_key}
        publish_data = {"exchange": "amq.topic",
                        "key": resource_id,
                        "body": str(json.dumps(data))}

        print("\n*********    Publisher: Sending data to Middleware    *********\n")
        r = requests.post(publish_url, json.dumps(publish_data), headers=publish_headers)
        response = {
            "status": "success",
            "response": r.content.decode("utf-8")
        }
        print(response)
        print("\n*********    Publisher: Received response from Middleware    *********\n")
        return JsonResponse(response)
