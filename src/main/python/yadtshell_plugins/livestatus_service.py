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

from twisted.web.client import Agent, HTTPConnectionPool
from twisted.internet import reactor
import logging
import simplejson as json

HTTP_CONNECT_TIMEOUT_IN_SECONDS = 120

'''
    The livestatus_service module
    Provides convenience classes to
      * build deferreds for host/service notifications status and livestatus commands
      * deal with the output from a livestatus_service server
'''

logger = logging.getLogger('yadtshell.plugins.livestatus_service')


class LivestatusServiceHandler(object):

    def __init__(self, livestatus_server, host):
        self.livestatus_server = livestatus_server
        self.host = host
        self.is_starting = None

    def _encode(self, url):
        url = url.replace(' ', '%20')
        url = url.replace('\n', '\\n')
        return url

    def _encode_and_defer_url_call(self, url, callback):
        url = self._encode(url)
        d = self._get_page(url)
        timeout_call = reactor.callLater(30, d.cancel)

        def success_or_failure(passthrough):
            if timeout_call.active():
                timeout_call.cancel()
            else:
                logger.error('Connected to livestatus server, but timed out waiting for an answer.')
            return passthrough
        d.addBoth(success_or_failure)
        d.addCallback(callback)
        return d

    def _get_page(self, url):
        agent = Agent(reactor,
                      connectTimeout=HTTP_CONNECT_TIMEOUT_IN_SECONDS,
                      pool=HTTPConnectionPool(reactor))
        deferred = agent.request('GET', url)
        return deferred

    def build_deferred_for_service_notification_status(self, callback):
        url = '''http://%s:8080/query?q=GET hosts
Columns: alias notifications_enabled
Filter: alias = %s&key=alias''' % (self.livestatus_server, self.host)
        return self._encode_and_defer_url_call(url, callback)

    def build_deferred_livestatus_command(self, command, callback):
        url = 'http://%s:8080/cmd?q=%s;%s' % (
            self.livestatus_server, command, self.host)
        return self._encode_and_defer_url_call(url, callback)

    def build_deferred_livestatus_wait_for_notifications_state(self, callback):
        target_notifications_state = 1 if self.is_starting else 0
        url = '''http://{0}:8080/query?q=GET hosts
Columns: host_name notifications_enabled
Filter: host_name = {1}
WaitObject: {1}
WaitCondition: notifications_enabled = {2}
WaitTimeout: 20000'''.format(self.livestatus_server, self.host, target_notifications_state)
        return self._encode_and_defer_url_call(url, callback)


class LivestatusServiceStatusResponse(object):

    def __init__(self, response, host):
        self.response = response
        self.host = host

    def notifications_are_enabled(self):
        response = json.loads(self.response)
        host_state = response[self.host]
        host_notifications_state = host_state['notifications_enabled']
        if host_notifications_state == 1:
            return True
        if host_notifications_state == 0:
            return False
        raise ValueError('unknown service notifications state : %s' %
                         host_notifications_state)
