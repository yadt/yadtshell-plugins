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

import unittest
from mock import patch
from yadtshell_plugins.livestatus_service import (LivestatusServiceHandler,
                                                  LivestatusServiceStatusResponse)


class LivestatusServiceHandlerTests(unittest.TestCase):

    @patch('yadtshell_plugins.livestatus_service.LivestatusServiceHandler._get_page')
    def test_should_call_correct_url_when_building_deferred_livestatus_command(self, mock_get_page):
        livestatus = LivestatusServiceHandler('livestatus_server', 'host')

        livestatus.build_deferred_livestatus_command('command', lambda: None)

        mock_get_page.assert_called_with(
            'http://livestatus_server:8080/cmd?q=command;host')

    @patch('yadtshell_plugins.livestatus_service.LivestatusServiceHandler._get_page')
    def test_should_call_correct_url_when_building_deferred_service_notifications_status(self, mock_get_page):
        livestatus = LivestatusServiceHandler('livestatus_server', 'host')

        livestatus.build_deferred_for_service_notification_status(lambda: None)

        mock_get_page.assert_called_with(
            'http://livestatus_server:8080/query?q=GET%20hosts\\nColumns:%20alias%20notifications_enabled\\nFilter:%20alias%20=%20host&key=alias')

    @patch('yadtshell_plugins.livestatus_service.LivestatusServiceHandler._get_page')
    def test_should_call_correct_url_when_building_deferred_host_notifications_service_wait(self, mock_get_page):
        livestatus = LivestatusServiceHandler('livestatus_server', 'host')

        livestatus.build_deferred_livestatus_wait_for_notifications_state(
            lambda: None)

        mock_get_page.assert_called_with(
            'http://livestatus_server:8080/query?q=GET%20hosts\\nColumns:%20host_name%20notifications_enabled\\nFilter:%20host_name%20=%20host\\nWaitObject:%20host\\nWaitCondition:%20notifications_enabled%20=%200\\nWaitTimeout:%2020000')

    @patch('yadtshell_plugins.livestatus_service.LivestatusServiceHandler._get_page')
    def test_should_wait_for_notifications_enabled_to_be_1_when_host_notifications_were_enabled(self, mock_get_page):
        livestatus = LivestatusServiceHandler('livestatus_server', 'host')
        livestatus.is_starting = True
        livestatus.build_deferred_livestatus_wait_for_notifications_state(
            lambda: None)

        mock_get_page.assert_called_with(
            'http://livestatus_server:8080/query?q=GET%20hosts\\nColumns:%20host_name%20notifications_enabled\\nFilter:%20host_name%20=%20host\\nWaitObject:%20host\\nWaitCondition:%20notifications_enabled%20=%201\\nWaitTimeout:%2020000')

    @patch('yadtshell_plugins.livestatus_service.LivestatusServiceHandler._get_page')
    def test_should_wait_for_notifications_enabled_to_be_0_when_host_notifications_were_disabled(self, mock_get_page):
        livestatus = LivestatusServiceHandler('livestatus_server', 'host')
        livestatus.is_starting = False
        livestatus.build_deferred_livestatus_wait_for_notifications_state(
            lambda: None)

        mock_get_page.assert_called_with(
            'http://livestatus_server:8080/query?q=GET%20hosts\\nColumns:%20host_name%20notifications_enabled\\nFilter:%20host_name%20=%20host\\nWaitObject:%20host\\nWaitCondition:%20notifications_enabled%20=%200\\nWaitTimeout:%2020000')


class LivestatusServiceStatusResponseTests(unittest.TestCase):

    def test_should_return_true_when_service_notifications_are_enabled(self):
        response_with_enabled_notifications = '{"host_name":{"notifications_enabled":1}}'
        actual_response = LivestatusServiceStatusResponse(
            response_with_enabled_notifications,
            'host_name')

        self.assertTrue(actual_response.notifications_are_enabled())

    def test_should_return_false_when_service_notifications_are_disabled(self):
        response_with_enabled_notifications = '{"host_name":{"notifications_enabled":0}}'
        actual_response = LivestatusServiceStatusResponse(
            response_with_enabled_notifications,
            'host_name')

        self.assertFalse(actual_response.notifications_are_enabled())

    def test_should_raise_exception_when_service_notifications_are_unknown(self):
        response_with_unknown_notifications = '{"host_name":{"notifications_enabled":1337}}'
        actual_response = LivestatusServiceStatusResponse(
            response_with_unknown_notifications,
            'host_name')

        self.assertRaises(
            ValueError, actual_response.notifications_are_enabled)

    def test_should_raise_exception_when_host_state_is_unknown(self):
        response_with_unknown_notifications = '{"other_host":{"notifications_enabled":1}}'
        actual_response = LivestatusServiceStatusResponse(
            response_with_unknown_notifications,
            'host_name')

        self.assertRaises(
            KeyError, actual_response.notifications_are_enabled)
