#!/usr/bin/env python
#
# Copyright 2016 Canonical, Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import unittest

from bundleplacer.charmstore_api import CharmStoreID
from bundleplacer.bundle import create_service

log = logging.getLogger('bundleplacer.test_service')


class TestService(unittest.TestCase):

    def setUp(self):
        self.service_1 = create_service("nova-compute", {
            "num_units": 1,
            "charm": "cs:trusty/nova-compute"}, {}, [])

    def test_changing_csid_changes_deployargs(self):
        self.assertEqual(self.service_1.as_deployargs()['CharmUrl'],
                         "cs:trusty/nova-compute")
        new_id = "cs:trusty/nova-compute-10"
        self.service_1.csid = CharmStoreID(new_id)
        self.assertEqual(self.service_1.as_deployargs()['CharmUrl'],
                         new_id)
