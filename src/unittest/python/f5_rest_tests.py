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

from unittest import TestCase

from twisted.python.failure import Failure
from mock import patch

from yadtshell_plugins.f5rest import check_status_responses


class CheckStatusResponsesForOneLbTest(TestCase):

    def test_should_return_0_when_node_is_enabled(self):
        responses = [(True, {'name': 'devytc97', 'state': 'up', 'session': 'monitor-enabled'})]

        self.assertEquals(0, check_status_responses(responses))

    def test_should_return_3_when_node_is_disabled(self):
        responses = [(True, {'name': 'devytc97', 'state': 'user-down', 'session': 'user-disabled'})]

        self.assertEquals(3, check_status_responses(responses))

    @patch('yadtshell_plugins.f5rest.logger')
    def test_should_return_None_when_exception_raised(self, _):
        failure = Failure(RuntimeError())
        failure.lb_ip = '192.168.0.1'
        responses = [(False, failure)]

        self.assertEquals(None, check_status_responses(responses))

    def test_should_return_None_when_node_is_inconsistent(self):
        responses = [(True, {'name': 'devytc97', 'state': 'up', 'session': 'user-disabled', 'lb_ip': 'some-lb'})]

        self.assertEquals(None, check_status_responses(responses))


class CheckStatusResponsesForXLbsTest(TestCase):

    def test_should_return_0_when_node_is_enabled_on_all_lbs(self):
        responses = [(True, {'name': 'devytc97', 'state': 'up', 'session': 'monitor-enabled'}),
                     (True, {'name': 'devytc98', 'state': 'up', 'session': 'monitor-enabled'})]

        self.assertEquals(0, check_status_responses(responses))

    def test_should_return_3_when_node_is_disabled_on_all_lbs(self):
        responses = [(True, {'name': 'devytc97', 'state': 'user-down', 'session': 'user-disabled'}),
                     (True, {'name': 'devytc98', 'state': 'user-down', 'session': 'user-disabled'})]

        self.assertEquals(3, check_status_responses(responses))

    def test_should_return_None_when_node_is_inconsisten_across_lbs(self):
        responses = [(True, {'name': 'devytc97', 'state': 'up', 'session': 'monitor-enabled', 'lb_ip': 'some-lb'}),
                     (True, {'name': 'devytc98', 'state': 'user-down', 'session': 'user-disabled', 'lb_ip': 'some-lb'})]

        self.assertEquals(None, check_status_responses(responses))

    def test_should_return_None_when_node_is_inconsisten_on_one_lb(self):
        responses = [(True, {'name': 'devytc97', 'state': 'up', 'session': 'monitor-enabled', 'lb_ip': 'some-lb'}),
                     (True, {'name': 'devytc98', 'state': 'up', 'session': 'user-disabled', 'lb_ip': 'some-lb'})]

        self.assertEquals(None, check_status_responses(responses))

    @patch('yadtshell_plugins.f5rest.logger')
    def test_should_return_None_when_exception_raised(self, _):

        failure = Failure(RuntimeError())
        failure.lb_ip = '192.168.0.1'
        responses = [(True, {'name': 'devytc97', 'state': 'up', 'session': 'monitor-enabled'}),
                     (False, failure)]

        self.assertEquals(None, check_status_responses(responses))
