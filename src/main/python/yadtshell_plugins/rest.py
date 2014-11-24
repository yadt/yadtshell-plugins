#   YADT - an Augmented Deployment Tool
#   Copyright (C) 2010-2014  Immobilien Scout GmbH
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

__author__ = 'Maximilien Riehl'

import json
import base64
from logging import getLogger

try:
    from StringIO import StringIO  # py2
except ImportError:
    from io import StringIO  # py3

from twisted.internet import defer, reactor
from twisted.internet.protocol import Protocol
from twisted.web.client import Agent, FileBodyProducer
from twisted.web.http_headers import Headers
from twisted.internet.ssl import ClientContextFactory


logger = getLogger("yadtshell.plugins.rest_library")


HTTP_CONNECT_TIMEOUT_IN_SECONDS = 30


class HTTP_METHOD(object):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"


def new_basicauth_headers(config):
    """
    Returns new HTTP headers (twisted.web.http_headers.Headers)
    with basic auth configured based on *config*.
    *config* must be a dictionary with "username" and "password" set.
    """

    creds = base64.b64encode('{0}:{1}'.format(config["username"], config["password"]))
    headers = Headers({'Authorization': ['Basic {0}'.format(creds)]})
    return headers


def rest_call(url, http_method, headers=Headers(), data=""):
    """
    Returns a deferred that will callback with the response to a rest call.

    Required positional arguments:
    -------------------------------

      * url
        The HTTP endpoint URI (string)
      * http_method
        The HTTP method that should be used. Valid methods are fields of
        the rest.HTTP_METHOD enum.

    Optional kwargs:
    -----------------

      * headers
        an instance of twisted.web.http_headers.Headers
      * data
        string with data to submit - no special treatment (e.G. no URL encoding!)
    """

    headers.addRawHeader("Content-Type", "application/json")

    agent = Agent(reactor, WebClientContextFactory(), connectTimeout=HTTP_CONNECT_TIMEOUT_IN_SECONDS)

    deferred = agent.request(http_method,
                             url,
                             headers,
                             FileBodyProducer(StringIO(data)) if data else None)
    deferred.addCallback(read_response)
    deferred.addCallback(deserialize_response)
    return deferred


class WebClientContextFactory(ClientContextFactory):
    def getContext(self, hostname, port):
        return ClientContextFactory.getContext(self)


def read_response(response):
    d = defer.Deferred()
    response.deliverBody(BodyConsumer(d))
    return d


def deserialize_response(response):
    try:
        return json.loads(response)
    except Exception:
        logger.warning("Cannot decode json response : %s" % response)
        raise


class BodyConsumer(Protocol):

    def __init__(self, finished):
        self.finished = finished
        self.data = ""

    def connectionMade(self, *args, **kwargs):
        pass

    def dataReceived(self, data):
        self.data += data

    def connectionLost(self, reason):
        self.finished.callback(self.data)
