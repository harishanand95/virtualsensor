# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.shortcuts import render
from .forms import Input
import requests
import json
from django.http import JsonResponse
import time
import subprocess
import atexit
child = None


def create_tcp_connection():
    """ Creates a single tcp connection to middleware and writes its streaming contents asynchronously to a file
    named output.txt"""
    global child
    child = subprocess.Popen(["python3", "air_pollution/async_http_read_files/async_http_read.py",
                              "https://smartcity.rbccps.org/api/0.1.0/subscribe?name=virtual_device_demo_subscriber"])


def kill_child():
    """ Kills the spawned python3 async_http_read.py process on close of the server"""
    global child
    if child is None:
        pass
    else:
        print("killing async_http_read {}".format(str(child.pid)))
        child.kill()
        child = None

atexit.register(kill_child)


def index(request):
    """ Renders the page '/' """
    data = dict()
    if child is None:
        create_tcp_connection()
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
            print(form.cleaned_data)
            data["city"] = form.cleaned_data["city"]
            data["humidity"] = form.cleaned_data["humidity"]
            data["pressure"] = form.cleaned_data["pressure"]
            data["ozone"] = form.cleaned_data["ozone"]
            data["temperature"] = form.cleaned_data["temperature"]
            data["time"] = form.cleaned_data["time"]
            send_data(form.cleaned_data)

    elif request.method == 'GET':
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
    """ Manually tries to run async_http_read.py incase of failures at /restart"""
    if child is not None:
        kill_child()
        create_tcp_connection()
        context = {"connection": "restarted"}
    else:
        context = {"connection": "started"}
        create_tcp_connection()
    return JsonResponse(context)


def read_from_file(request):
    """ Reads from output.txt file the json data that came from the middleware."""

    with open('air_pollution/async_http_read_files/output.txt') as f:
        content = json.loads(f.read())
    return JsonResponse(content["data_schema"])


def fetch_data(city="bangalore"):
    """ Fetches AQI data for bangalore from api.waqi.info site. """
    token = "22a7ea10a287c7d9ff26771099a975f48db68e52"  # AQI api token
    url = "http://api.waqi.info/feed/{0}/?token={1}".format(city, token)
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
    publish_headers = {"apikey": "1daa9ea1779642619e00d1e30163cb3e"}
    publish_data = {"exchange": "amq.topic",
                    "key": "virtual_device_demo_publisher",
                    "body": str(json.dumps(data))}

    print("Provider: Sending data to Middleware\n")
    r = requests.post(publish_url, json.dumps(publish_data), headers=publish_headers)
    print("Provider: Received response from Middleware\n")
    print(r.content)
