"""
Helper functions for calculating CO2 emissions on highways project
Part of a FastApi project
Fetches data from different sources (TomTom, GCP, Openweathermap).
"""

import requests
import time
import logging
import os
import json
from hashlib import md5
import math
import configparser

config = configparser.ConfigParser()
configFilePath = r'./config.conf'
config.read(configFilePath)

TomTomKey = config.get("config","TomTomKey")
GGLKey = config.get("config","GGLKey")
OWMKey = config.get("config","OWMKey")


emptySpeedLimit =  {"summary": {"queryTime": 0, "numResults": 1}, "addresses": [{"address": {"routeNumbers": [],
                                                                                 "street": "",
                                                                                 "streetName": "",
                                                                                 "speedLimit": "0.00KPH",
                                                                                 "countryCode": "HU",
                                                                                 "countrySubdivision": "Budapest",
                                                                                 "municipality": "Budapest",
                                                                                 "postalCode": "1000",
                                                                                 "municipalitySubdivision": "",
                                                                                 "country": "Magyarorsz\u00e1g",
                                                                                 "countryCodeISO3": "HUN",
                                                                                 "freeformAddress": "",
                                                                                 "boundingBox": {
                                                                                     "northEast": "47.444523,19.129375",
                                                                                     "southWest": "47.444455,19.129269",
                                                                                     "entity": "position"},
                                                                                 "localName": "Budapest"},
                                                                     "position": "47.444523,19.129272"}]}


def getCoordForCity(city):
    """
     :param city: City, Country
     :return:  { e.g.:
            "name": "Gleiming",
            "lat": 47.3892841,
            "lon": 13.5950327,
            "country": "AT",
            "state": "Styria"
        }
    """

    url = 'https://api.openweathermap.org/geo/1.0/direct?q=%s&limit=1&appid=%s'
    r = requests.get(url % (city, OWMKey))
    return r.json()


def getRoute(lat1, lon1, lat2, lon2):
    """
    get route from (lat1,lon1) to (lat2,lon2) from TomTom API
    https://developer.tomtom.com/routing-api/documentation/routing/calculate-route
    :param lat1:
    :param lon1:
    :param lat2:
    :param lon2:
    :return: https://developer.tomtom.com/routing-api/documentation/routing/calculate-route
    """
    url = f'https://api.tomtom.com/routing/1/calculateRoute/{lat1},{lon1}:{lat2},{lon2}/json?key={TomTomKey}'

    print(f"Route from {lat1,lon1} to {lat2,lon2}")

    # cache to reduce requests
    md5x = md5(url.encode()).hexdigest()
    filename = "cache/routes/%s.json" % (md5x)

    if os.path.exists(filename):
        with open(filename) as file:
            result = json.load(file)
            file.close()
    else:
        r = requests.get(url=url)

        try:
            result = r.json()
            with open(filename, 'w') as file:
                file.write(json.dumps(result))
                file.close()

        except Exception as e:
            logging.exception(msg=f'getSpeedLimit, lat: {lat1} , lon: {lon1}   Exception: {e}')
            result = {}
            pass

    return result

def snapToRoad(leg):
    """
    Snap leg to road using Google Map API: 
    https://developers.google.com/maps/documentation/roads/snap
    :param leg:
    :return: array(latitude, longitude)
    """
    road = []
    points = leg["points"]
    while(True):
        path = ""
        for point in points[:100]:
            lat = point["latitude"]
            lon = point["longitude"]
            path += f"{lat},{lon}|"
        path = path[:-1]

        url = f'https://roads.googleapis.com/v1/snapToRoads?key={GGLKey}&interpolate=true&path={path}'
        r = requests.get(url=url)
        try:
            result = r.json()
            for snappedPoint in result["snappedPoints"]:
                road.append({"latitude": snappedPoint["location"]["latitude"], "longitude": snappedPoint["location"]["longitude"]})

        except Exception as e:
            logging.exception(msg=f'snapToRoads, points: {points}   Exception: {e}')
            pass

        points = points[100:]
        if len(points) == 0:
            break

    return road


def getElevations(points):
    """
    Get elevation for position(lat,lon) from google maps
    https://developers.google.com/maps/documentation/elevation/start
    :param lat:
    :param lon:
    :return: elevation for (lat,lon)
    """

    elevations = []

    while(True):
        locations = ""
        for point in points[:500]:
            locations += f'{round(point["latitude"],5)},{round(point["longitude"],5)}|'
        locations = locations[:-1]

        url = f'https://maps.googleapis.com/maps/api/elevation/json?key={GGLKey}&locations={locations}'

        # cache to reduce requests
        md5x = md5(url.encode()).hexdigest()
        filename = "cache/elevations/%s.json" % (md5x)

        if os.path.exists(filename):
            with open(filename) as file:
                result = json.load(file)
                file.close()
        else:
            r = requests.get(url=url)

            try:
                result = r.json()
                with open(filename, 'w') as file:
                    file.write(json.dumps(result))
                    file.close()
                    time.sleep(0.2)

            except Exception as e:
                logging.exception(msg=f'getElevations, points:    Exception: {e}')
                pass
        for elev in result["results"]:
            elevations.append(elev["elevation"])

        points = points[500:]

        if len(points)==0:
            break

    return elevations

def calcDistance( lat1, lon1, lat2, lon2):
    """
    Calculate distance between two geo coords
    :param lat1:
    :param lon1:
    :param lat2:
    :param lon2:
    :return: distance in  meters
    """
    r = 6371000
    f1 = lat1*math.pi/180
    f2 = lat2*math.pi/180
    df = (lat2-lat1)*math.pi/180
    dl = (lon2-lon1)*math.pi/180
    a = math.sin(df/2) * math.sin(df/2) + math.cos(f1) * math.cos(f2) * math.sin(dl/2) * math.sin(dl/2)
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = r*c  # distance in meters
    return d


def getSpeedLimit(lat, lon, streetNo=""):
    """
    Get Speed limit for position(lat,lon) from TomTom API
    :param lat:
    :param lon:
    :param streetNo, optional the actual StreetNumber where are travelling on, useful @ intersections, parallel roads
    :return: limit: speed limit for (lat,lon)
    :return: stn: streetNo
    :return: slic: TomTom request counter
    """

    url = f'https://api.tomtom.com/search/2/reverseGeocode/{lat},{lon}.json?key={TomTomKey}&returnSpeedLimit=true&heading=0&radius=10'

    # cache to reduce requests
    md5x = md5(url.encode()).hexdigest()
    slic = 0
    filename = "cache/speedlimits/%s.json" % (md5x)
    stn = streetNo
    print('getSpeedLimit::', filename, end="")

    result = {}
    if os.path.exists(filename):
        try:
            with open(filename) as file:
                result = json.load(file)
                file.close()
                print(" - from cache")
        except:
            pass
    else:
        print(" - from TomTom")
        r = requests.get(url=url)
        slic = 1
        try:
            result = r.json()
            time.sleep(0.1)
            with open(filename, 'w') as file:
                file.write(json.dumps(result))
                file.close()

        except Exception as e:
            result = emptySpeedLimit
            with open(filename, 'w') as file:
                file.write(json.dumps(result))
                file.close()
                print(" - from TomTom - failed")

            logging.exception(msg=f'getSpeedLimit, lat: {lat} , lon: {lon}   Exception: {e}')
            pass

    try:
        limit = int(float((result["addresses"][0]["address"]["speedLimit"].replace("KPH", "").replace("MPH", ""))))
        stn = result["addresses"][0]["address"]["routeNumbers"][0]

        if streetNo != "":
            if streetNo not in result["addresses"][0]["address"]["routeNumbers"]:
                limit = 0

    except:
        limit = 0

    return limit, stn, slic
