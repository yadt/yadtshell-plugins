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

from logging import getLogger

from yadtshell_plugins.rest import rest_call, new_basicauth_headers, HTTP_METHOD

from twisted.internet.defer import DeferredList


logger = getLogger("yadtshell.plugins.f5rest")


CONFIG = {
    "username": None,
    "password": None,
    "ltm_partition": None
}


class State(object):

    UP = ("user-enabled", "user-up")
    DOWN = ("user-disabled", "user-down")

    TEMPLATE = '{"name": "%s","session": "%s","state": "%s"}'

    @classmethod
    def up(cls, host):
        return cls.TEMPLATE % ((host,) + cls.UP)

    @classmethod
    def down(cls, host):
        return cls.TEMPLATE % ((host,) + cls.DOWN)


def configure(config, ltm_partition):
    CONFIG['username'] = config.RESTAPI_USERNAME
    CONFIG['password'] = config.RESTAPI_PASSWORD
    if not ltm_partition:
        raise RuntimeError("No ltm partition configured! Set it in the service definition or in the loadbalancer config")
    CONFIG['ltm_partition'] = ltm_partition


def query_status_from_single_lb(host, lb_ip):
    d = rest_call("https://%s/mgmt/tm/ltm/node/%s%s" % (lb_ip, CONFIG['ltm_partition'], host),
                  HTTP_METHOD.GET,
                  headers=new_basicauth_headers(CONFIG))

    def add_lb_ip_to_result(result):
        result['lb_ip'] = lb_ip
        return result

    def add_lb_ip_to_failure(failure):
        failure.lb_ip = lb_ip
        return failure

    d.addCallback(add_lb_ip_to_result)
    d.addErrback(add_lb_ip_to_failure)

    return d


def check_status_responses(responses):
    enabled_results = []

    for ok, lb_response in responses:
        if not ok:
            logger.error("Bad LB(%s) response/inconsistency : %s" % (lb_response.lb_ip, lb_response.value))
            enabled_results.append(None)
            continue

        if "state" not in lb_response:
            logger.error("Malformed LB(%s) response (missing 'state' key): %s" % (lb_response["lb_ip"], lb_response))
            enabled_results.append(None)
            continue

        if "session" not in lb_response:
            logger.error("Malformed LB(%s) response (missing monitor 'session' key): %s" % (lb_response["lb_ip"], lb_response))
            enabled_results.append(None)
            continue

        enabled = (lb_response["state"] == "up" and lb_response["session"] == "monitor-enabled")
        disabled = (lb_response["state"] == "user-down" and lb_response["session"] == "user-disabled")

        if not enabled and not disabled:
            logger.debug("host://%s : inconsistent state on LB %s: %s" % (lb_response["name"], lb_response["lb_ip"], lb_response))
            enabled_results.append(None)
        else:
            enabled_results.append(enabled)

    enabled = enabled_results[0]

    for enabled_result_from_one_lb in enabled_results:
        if enabled_result_from_one_lb is None:
            return None  # bad lb response / inconsistency on the lb
        if enabled_result_from_one_lb != enabled:
            logger.debug("inconsistency in LB cluster : %s" % [lb_response_tuple[1] for lb_response_tuple in responses])
            return None  # cluster inconsistency

    return 0 if enabled else 3


def query_status(host, loadbalancer_ips):
    ds = [query_status_from_single_lb(host, lb_ip) for lb_ip in loadbalancer_ips]
    dl = DeferredList(ds, consumeErrors=True)
    dl.addCallback(check_status_responses)
    return dl


def set_state_single_loadbalancer(host, lb_ip, payload):
    d = rest_call("https://%s/mgmt/tm/ltm/node/%s%s" % (lb_ip, CONFIG['ltm_partition'], host),
                  HTTP_METHOD.PUT,
                  headers=new_basicauth_headers(CONFIG),
                  data=payload)

    def add_lb_ip_to_result(result):
        result['lb_ip'] = lb_ip
        return result

    def add_lb_ip_to_failure(failure):
        failure.lb_ip = lb_ip
        return failure

    d.addCallback(add_lb_ip_to_result)
    d.addErrback(add_lb_ip_to_failure)

    return d


def set_state_multiple_loadbalancer(host, lb_ips, state):
    payload = state(host)
    ds = [set_state_single_loadbalancer(host, lb_ip, payload)
          for lb_ip in lb_ips]
    dl = DeferredList(ds, consumeErrors=True)

    def verify_change_successful(results):
        ok = True
        for success, response in results:
            if not success:
                logger.error('Unable to change state in LB(%s): %s' % (response.lb_ip, response.value))
                ok = False
            elif 'errorStack' in response:
                logger.error('Unable to change state in LB(%s): %s' % (response['lb_ip'], response))
                ok = False
        return 0 if ok else 1

    dl.addCallback(verify_change_successful)
    return dl


def set_status_up(host, loadbalancer_ips):
    return set_state_multiple_loadbalancer(host, loadbalancer_ips, State.up)


def set_status_down(host, loadbalancer_ips):
    return set_state_multiple_loadbalancer(host, loadbalancer_ips, State.down)
