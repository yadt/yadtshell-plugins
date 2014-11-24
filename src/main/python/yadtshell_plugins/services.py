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

from __future__ import absolute_import

import logging
import shlex
import sys

import twisted
from twisted.internet import reactor, defer
from twisted.internet.protocol import Protocol

import yadtshell.settings
import yadtshell.components
import yadtshell.util
import yadtshell.twisted

from yadtshell_plugins.livestatus_service import (LivestatusServiceHandler,
                                                  LivestatusServiceStatusResponse)

logger = logging.getLogger('yadtshell.plugins.services')

DISABLE_COMMAND = 'disable'
ENABLE_COMMAND = 'enable'


class GuardedService(yadtshell.components.Service):

    """
    A base class for a guarded service.
    This is basically a plain yadt `Service` which performs
    *guarded* commands i.E. ensures that we have write access to the
    service before running the command with `_service_call`.
    We have write access to the service if the remote command
    `yadt-service-checkaccess SERVICE` succeeds. (This checks if the host
                                                  is locked by another for
                                                  example).

    If we have write access, this class will call `_guarded_service_call`
    on the service, passing the command `cmd` given to `_service_call`).
    Thus subclasses should implement only `_guarded_service_call` and call
    to `_service_call` in their start|stop implementation.
    """

    def _service_call(self, cmd):
        """
        Make a service call with `cmd` and return a deferred.
        If we have write access to the service (`self.name`), the deferred will
        callback on `self._guarded_service_call` with the parameter `cmd`.
        """
        guard_cmd = self.remote_call('yadt-service-checkaccess %s' % self.name)
        p = yadtshell.twisted.YadtProcessProtocol(self, guard_cmd)
        p.deferred = defer.Deferred()
        guard_cmd = shlex.split(guard_cmd)
        reactor.spawnProcess(p, guard_cmd[0], guard_cmd, None)
        p.deferred.addCallback(self._guarded_service_call, cmd)
        return p.deferred

    def _create_service_ignored_failure(self):
        failure = lambda: None
        failure.exitCode = 151  # Exit code 151 : service ignored
        return failure


def handle_connection_error(failure, host, livestatus_server, fail=False):
    message = 'Monitoring state for %s is unknown due to %r while connecting to %s'
    error_message = message % (host, failure.getErrorMessage(), livestatus_server)
    if fail:
        raise RuntimeError(error_message)
    else:
        logger.error(error_message)
    return 'unknown'


class LivestatusService(GuardedService):

    def __init__(self, host, name, settings):
        yadtshell.components.Service.__init__(self, host, name, settings)
        loc_type = yadtshell.util.determine_loc_type(host.host)

        try:
            import livestatusservice
            self.config = livestatusservice
        except ImportError, e:
            logger.critical(
                'cannot find module livestatusservice, should be in /etc/yadtshell')
            raise e

        if not hasattr(self, "livestatus_server"):
            self.livestatus_server = self.config.SERVERS[loc_type['loc']]

        self.livestatus = LivestatusServiceHandler(
            self.livestatus_server, self.host)

    def _guarded_service_call(self, ignored, cmd):

        def on_host_notifications_successfully_modified(page):
            logger.debug(
                'on host notifications successfully modified : %s' % page)

        def on_host_notifications_modified(page):
            logger.debug('on host notifications modified : %s' % page)
            return self.livestatus.build_deferred_livestatus_wait_for_notifications_state(on_host_notifications_successfully_modified)

        def on_service_notifications_modified(page):
            logger.debug('on service notifications modified : %s' % page)
            if isinstance(page, twisted.internet.error.TimeoutError):
                logger.error(
                    "Could not enable/disable service notifications due to timeout after %d seconds", page._timeout)
            if cmd == DISABLE_COMMAND:
                modify_host_notifications = 'DISABLE_HOST_NOTIFICATIONS'
            else:
                modify_host_notifications = 'ENABLE_HOST_NOTIFICATIONS'
            return self.livestatus.build_deferred_livestatus_command(modify_host_notifications, on_host_notifications_modified)

        if cmd == DISABLE_COMMAND:
            modify_service_notifications = 'DISABLE_HOST_SVC_NOTIFICATIONS'
        else:
            modify_service_notifications = 'ENABLE_HOST_SVC_NOTIFICATIONS'

        d = self.livestatus.build_deferred_livestatus_command(modify_service_notifications, on_service_notifications_modified)
        d.addErrback(handle_connection_error, self.host, self.livestatus_server, fail=True)
        return d

    def start(self):
        self.livestatus.is_starting = True
        return self._service_call(ENABLE_COMMAND)

    def stop(self):
        self.livestatus.is_starting = False
        return self._service_call(DISABLE_COMMAND)

    def _create_service_ignored_failure(self):
        failure = lambda: None
        failure.exitCode = 151
        return failure

    def status(self):
        if hasattr(self, 'ignored'):
            return defer.succeed(None)
        logger.debug('requesting status for %s' % self.uri)

        def read_body(response):
            d = defer.Deferred()
            response.deliverBody(BodyConsumer(d, self.host))
            return d

        def parse_page(page):
            response = LivestatusServiceStatusResponse(page, self.host)
            try:
                notifications_enabled = response.notifications_are_enabled()
                if notifications_enabled:
                    self.state = 0
                else:
                    self.state = 1
            except:  # NOQA
                logger.warning(
                    'Monitoring state for %s unknown, response from %s was %s' %
                    (self.host, self.livestatus_server, page))
                self.state = 'unknown'
            return self.state

        body_deferred = self.livestatus.build_deferred_for_service_notification_status(
            read_body)
        body_deferred.addErrback(
            handle_connection_error, self.host, self.livestatus_server)
        body_deferred.addCallback(parse_page)
        return body_deferred


class BodyConsumer(Protocol):

    def __init__(self, finished, host):
        self.finished = finished
        self.host = host
        self.data = ""

    def connectionMade(self, *args, **kwargs):
        logger.debug("Livestatus connection made for %s" % self.host)

    def dataReceived(self, data):
        self.data += data

    def connectionLost(self, reason):
        self.finished.callback(self.data)


class LB(GuardedService):

    def __init__(self, host, name, settings):
        yadtshell.components.Service.__init__(self, host, name, settings)
        try:
            import loadbalancerservice
            self.config = loadbalancerservice
            self.ltm_partition = settings.get('ltm_partition', None) or getattr(self.config, 'LTM_PARTITION', None)
        except ImportError, e:
            logger.critical('cannot find module loadbalancerservice')
            raise e

        module_name = settings.get("implementation", None) or getattr(self.config, "IMPLEMENTATION", None)
        logger.debug("module_name: %s" % module_name)
        if not module_name:
            raise RuntimeError('Configuration problem : no loadbalancer api implementation found.')
        __import__(module_name)
        self.implementation = sys.modules[module_name]

    def prepare(self, host):
        self.ip_list = filter(None, host.interface.values())
        if hasattr(self, 'loadbalancer_clusters'):
            self.loadbalancer_ips = []
            logger.debug('%s clusters: %s' %
                         (self.uri, ', '.join(self.loadbalancer_clusters)))
            for cluster in self.loadbalancer_clusters:
                self.loadbalancer_ips.extend(self.config.CLUSTERS[cluster])
        logger.debug('%s ips: %s' %
                     (self.uri, ', '.join(self.loadbalancer_ips)))
        logger.debug('%s ips: %s' % (self.host, ', '.join(self.ip_list)))

    def status(self):
        self.implementation.configure(self.config, getattr(self, "ltm_partition", None))
        if hasattr(self, 'ignored'):
            logger.debug('%s is ignored' % self.uri)
            return defer.succeed(None)
        logger.debug('requesting status for %s' % self.uri)

        return self.implementation.query_status(self.host, self.loadbalancer_ips)

    def stop(self):
        return self._service_call("stop")

    def start(self):
        return self._service_call("start")

    def _guarded_service_call(self, ignored, cmd):
        self.implementation.configure(self.config, getattr(self, "ltm_partition", None))
        return {
            "start": self.implementation.set_status_up,
            "stop": self.implementation.set_status_down
        }[cmd](self.host, self.loadbalancer_ips)
