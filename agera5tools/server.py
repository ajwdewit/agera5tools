# -*- coding: utf-8 -*-
# Copyright (c) December 2022, Wageningen Environmental Research
# Allard de Wit (allard.dewit@wur.nl)
import logging
from pathlib import Path

import wsgiserver
from flask import Flask, request, Response
import json

from . import config
from .db_data_provider import get_agera5
from .util import BoundedFloat, json_date_serial

app = Flask(__name__)

AgERA5_bounded_lat = BoundedFloat(minvalue=-66.5, maxvalue=66.5, msg="Latitude should be between -66.5 and 66.5")
bounded_lon = BoundedFloat(minvalue=-180, maxvalue=180, msg="Longitude should be between -180 and 180")


def parse_inputs(params):
    """This retrieves and parses the parameters from the HTTP request.
    """
    inputs = {}
    for parname, func in params.items():
        try:
            inputs[parname] = func(request.args.get(parname))
        except TypeError as e:
            raise RuntimeError("Missing parameter '%s'" % parname)
        except Exception as e:
            raise RuntimeError(str(e))
    return inputs


def get_JSON_response(func, params, name):
    logger = logging.getLogger(name)
    inputs = "No inputs parsed yet"
    try:
        inputs = parse_inputs(params)
        r = {"success": True,
             "message": "success",
             "inputs": inputs,
             "data": func(**inputs)}
        logger.info("Successfully retrieved %s with inputs %s", name, inputs)
        return Response(json.dumps(r, default=json_date_serial), mimetype="application/json")
    except Exception as e:
        logger.exception("Failure getting %s with inputs %s", name, inputs)
        r = {"success": False,
             "inputs": inputs,
             "message": str(e)}
        return Response(json.dumps(r), mimetype="application/json")


@app.route("/")
def index():
    package_dir = Path(__file__).parent
    print(package_dir.absolute())
    with open(package_dir / "help.html") as fp:
        html = "".join(fp.readlines())
    return Response(html, mimetype="text/html")


@app.route("/api/v1/get_agera5")
def flask_get_agera5():
    params = {"latitude": AgERA5_bounded_lat, "longitude": bounded_lon, "startdate": str, "enddate": str}
    return get_JSON_response(get_agera5, params, "get_agera5")



def serve(port=8080):
    server = wsgiserver.WSGIServer(app, port=port)
    server.start()


if __name__ == "__main__":
    print("starting Flask in debug mode on http://localhost:5000")
    app.run(debug=True)