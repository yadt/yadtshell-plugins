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
from mock import Mock, call, patch

from yadtshell_plugins.services import (LivestatusService,
                                        handle_connection_error)


class LivestatusServiceTests(unittest.TestCase):

    def test_start_should_enable_host_service_notifications(self):
        mock_service = Mock(LivestatusService)
        mock_service.livestatus = Mock()

        LivestatusService.start(mock_service)

        self.assertEqual(call('enable'), mock_service._service_call.call_args)

    def test_stop_should_disable_host_service_notifications(self):
        mock_service = Mock(LivestatusService)
        mock_service.livestatus = Mock()

        LivestatusService.stop(mock_service)

        self.assertEqual(call('disable'), mock_service._service_call.call_args)

    def test_status_should_return_deferred_service_notifications_status(self):
        mock_service = Mock(
            LivestatusService,
            host='any.host',
            livestatus_server='any.icinga.server',
            livestatus=Mock()
        )
        mock_deferred = Mock()
        mock_service.livestatus.build_deferred_for_service_notification_status.return_value = mock_deferred
        mock_service.uri = 'service://host/monitoring'

        deferred_status = LivestatusService.status(mock_service)

        self.assertEqual(deferred_status, mock_deferred)

    @patch('yadtshell_plugins.services.logger')
    def test_should_return_status_unknown_when_connection_failure_occurs(self, _):
        self.assertEqual(
            handle_connection_error(Mock(), 'any.host', 'any.icinga.server'),
            'unknown'
        )

    def test_should_hook_errback_to_deferred_request(self):
        mock_service = Mock(
            LivestatusService,
            host='any.host',
            livestatus_server='any.icinga.server',
            livestatus=Mock()
        )
        mock_deferred = Mock()
        mock_service.livestatus.build_deferred_for_service_notification_status.return_value = mock_deferred
        mock_service.uri = 'service://host/monitoring'

        deferred_status = LivestatusService.status(mock_service)

        errback_function = deferred_status.addErrback
        errback_function.assert_called_with(handle_connection_error, 'any.host', 'any.icinga.server')
