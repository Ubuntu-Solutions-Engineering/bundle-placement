#!/usr/bin/env python
#
# tests placement/ui.py
#
# Copyright 2014 Canonical, Ltd.
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
import re
import unittest
import yaml
from tempfile import NamedTemporaryFile
from unittest.mock import MagicMock, patch

import bundleplacer.utils as utils
from bundleplacer.state import ServiceState
from bundleplacer.config import Config

from bundleplacer.controller import (AssignmentType,
                                     PlacementController)

from bundleplacer.ui.machines_list import MachinesList
from bundleplacer.ui.simple_machine_widget import SimpleMachineWidget
from bundleplacer.ui.services_list import ServicesList
from bundleplacer.ui.simple_service_widget import SimpleServiceWidget


log = logging.getLogger('cloudinstall.test_placement_ui')


def search_in_widget(pat, w):
    """Helper function to render a widget and check for a regex"""
    canvas = w.render((100,))
    all_lines = " ".join([t.decode() for t in canvas.text])
    matches = re.search(pat, all_lines)
    log.debug("search_in_widget({}, {}):\n"
              "all_lines is: {}\n"
              "matches is {}".format(pat, w, all_lines, matches))
    return matches is not None


def make_fake_machine(name, md=None):
    m = MagicMock(name=name)
    m.instance_id = "fake-iid-{}".format(name)
    m.hostname = "{}-hostname".format(name)
    m.status = "{}-status".format(name)

    if md is None:
        md = {}

    m.machine = md
    m.arch = md.get("arch", "{}-arch".format(name))
    m.cpu_cores = md.get("cpu_count", "{}-cpu_count".format(name))
    m.mem = md.get("mem", "{}-mem".format(name))
    m.storage = md.get("storage", "{}-storage".format(name))
    m.filter_label.return_value = "{}-filter_label".format(name)

    return m


class ServiceWidgetTestCase(unittest.TestCase):

    def setUp(self):
        self.mock_maas_state = MagicMock()

        with NamedTemporaryFile(mode='w+', encoding='utf-8') as tempf:
            utils.spew(tempf.name, yaml.dump(dict()))
            self.conf = Config({}, tempf.name, save_backups=False)

        self.pc = PlacementController(self.mock_maas_state,
                                      self.conf)

        self.mock_machine = make_fake_machine('machine1')
        self.mock_machine_2 = make_fake_machine('machine2')

        self.mock_machines = [self.mock_machine, self.mock_machine_2]

        self.mock_maas_state.machines.return_value = self.mock_machines

    def test_required_label_shown(self):
        """Widget showing a required charm should have a label showing how
        many units are required"""
        w = ServiceWidget(CharmKeystone, self.pc)

        self.assertTrue(search_in_widget("0 of 1 placed", w))

    def test_required_label_not_shown(self):
        """Widget showing a non-required charm should NOT have a label showing
        how many units are required.
        """
        w = ServiceWidget(CharmJujuGui, self.pc)

        self.assertFalse(search_in_widget(".* of .* placed", w))

    def test_show_placements(self):
        """Widget with show_placements set should show placements"""
        self.pc.assign(self.mock_machine, CharmNovaCompute, AssignmentType.LXC)
        w = ServiceWidget(CharmNovaCompute, self.pc, show_placements=True)

        self.assertTrue(search_in_widget("LXC.*machine1-hostname", w))

    def test_dont_show_placements(self):
        """Widget with show_placements set to FALSE should NOT show
        placements"""
        self.pc.assign(self.mock_machine, CharmNovaCompute, AssignmentType.LXC)
        w = ServiceWidget(CharmNovaCompute, self.pc, show_placements=False)

        self.assertFalse(search_in_widget("LXC.*machine1-hostname", w))

    def test_show_constraints(self):
        """Widget with show_constraints set should show constraints"""
        self.pc.assign(self.mock_machine, CharmNovaCompute, AssignmentType.LXC)
        w = ServiceWidget(CharmNovaCompute, self.pc, show_constraints=True)

        conpat = ("constraints.*" +
                  ".*".join(CharmNovaCompute.constraints.keys()))

        self.assertTrue(search_in_widget(conpat, w))

    def test_dont_show_constraints(self):
        """Widget with show_constraints set to FALSE should NOT show
        constraints"""
        self.pc.assign(self.mock_machine, CharmNovaCompute, AssignmentType.LXC)
        w = ServiceWidget(CharmNovaCompute, self.pc, show_constraints=False)
        self.assertFalse(search_in_widget("constraints", w))

    def test_show_actions(self):
        """Actions should be shown as buttons"""
        fake_action_func = MagicMock()
        actions = [("fake-action", fake_action_func)]
        w = ServiceWidget(CharmNovaCompute, self.pc, actions=actions)
        self.assertTrue(search_in_widget("fake-action", w))

    def test_actions_use_pred(self):
        """Action predicates control whether a button appears (disabled)"""

        # NOTE: this test assumes that disabled buttons are just the
        # button label with parentheses.

        fake_action_func = MagicMock()
        fake_pred = MagicMock()
        fake_pred.return_value = False
        actions = [(fake_pred, "fake-action", fake_action_func)]
        w = ServiceWidget(CharmNovaCompute, self.pc, actions=actions)

        self.assertTrue(search_in_widget("\(.*fake-action.*\)", w))
        fake_pred.assert_called_with(CharmNovaCompute)

        fake_pred.return_value = True
        fake_pred.reset_mock()

        w.update()
        self.assertTrue(search_in_widget("<.*fake-action.*>", w))
        fake_pred.assert_called_with(CharmNovaCompute)


class MachineWidgetTestCase(unittest.TestCase):

    def setUp(self):
        self.mock_maas_state = MagicMock()
        with NamedTemporaryFile(mode='w+', encoding='utf-8') as tempf:
            utils.spew(tempf.name, yaml.dump(dict()))
            self.conf = Config({}, tempf.name, save_backups=False)

        self.pc = PlacementController(self.mock_maas_state,
                                      self.conf)
        self.mock_machine = make_fake_machine('machine1')

        self.mock_machines = [self.mock_machine]

        self.mock_maas_state.machines.return_value = self.mock_machines

    def test_show_assignments(self):
        """Widget with show_assignments set should show assignments"""
        self.pc.assign(self.mock_machine, CharmNovaCompute, AssignmentType.LXC)
        w = SimpleMachineWidget(self.mock_machine, self.pc,
                                show_assignments=True)

        self.assertTrue(search_in_widget("LXC.*Compute", w))

    def test_dont_show_assignments(self):
        """Widget with show_assignments set to FALSE should NOT show
        assignments"""
        self.pc.assign(self.mock_machine, CharmNovaCompute, AssignmentType.LXC)
        w = SimpleMachineWidget(self.mock_machine, self.pc,
                                show_assignments=False)

        self.assertFalse(search_in_widget("LXC.*Compute", w))


@patch('bundleplacer.ui.machines_list.SimpleMachineWidget')
class MachinesListTestCase(unittest.TestCase):

    def setUp(self):
        self.mock_maas_state = MagicMock()
        with NamedTemporaryFile(mode='w+', encoding='utf-8') as tempf:
            utils.spew(tempf.name, yaml.dump(dict()))
            self.conf = Config({}, tempf.name, save_backups=False)

        self.pc = PlacementController(self.mock_maas_state,
                                      self.conf)
        self.mock_machine = make_fake_machine('machine1', {'cpu_count': 3})
        self.mock_machine2 = make_fake_machine('machine2')
        self.mock_machine3 = make_fake_machine('machine3')

        self.mock_machines = [self.mock_machine]

        self.mock_maas_state.machines.return_value = self.mock_machines

        self.actions = []

    def test_widgets_config(self, mock_machinewidget):
        for show_hardware in [False, True]:
            for show_assignments in [False, True]:
                MachinesList(self.pc, self.actions,
                             show_hardware=show_hardware,
                             show_assignments=show_assignments)
                mock_machinewidget.assert_any_call(self.mock_machine,
                                                   self.pc,
                                                   self.actions,
                                                   show_hardware,
                                                   show_assignments)
                mock_machinewidget.reset_mock()

    def test_show_matching_constraints(self, mock_machinewidget):
        ml = MachinesList(self.pc, self.actions,
                          {'cpu_cores': 2})
        self.assertEqual(1, len(ml.machine_widgets))

    def test_hide_non_matching_constraints(self, mock_machinewidget):
        ml = MachinesList(self.pc, self.actions,
                          {'cpu_cores': 16384})
        self.assertEqual(0, len(ml.machine_widgets))

    def test_show_matching_filter(self, mock_machinewidget):
        self.mock_maas_state.machines.return_value = [self.mock_machine,
                                                      self.mock_machine2,
                                                      self.mock_machine3]
        # a little extra work to ensure that calls to
        # MockWidget.__init__() return mocks with the intended machine
        # attribute set:
        mw1 = MagicMock(name="mw1")
        mw1.machine = self.mock_machine
        mw2 = MagicMock(name="mw2")
        mw2.machine = self.mock_machine2
        mw3 = MagicMock(name="mw3")
        mw3.machine = self.mock_machine3
        # the rest are the placeholders:
        mw4 = MagicMock(name="mock_placeholder_widget1")
        mw4.machine = self.pc.sub_placeholder
        mw5 = MagicMock(name="mock_placeholder_widget2")
        mw5.machine = self.pc.def_placeholder
        mock_machinewidget.side_effect = [mw1, mw2, mw3, mw4, mw5]

        ml = MachinesList(self.pc, self.actions)
        self.assertEqual(5, len(ml.machine_widgets))

        ml.filter_string = "machine1-filter_label"
        ml.update()
        print("ml.machinewidgets is {}".format(ml.machine_widgets))
        self.assertEqual(1, len(ml.machine_widgets))


@patch('bundleplacer.ui.services_list.ServiceWidget')
class ServicesListTestCase(unittest.TestCase):

    def setUp(self):
        self.mock_maas_state = MagicMock()
        with NamedTemporaryFile(mode='w+', encoding='utf-8') as tempf:
            utils.spew(tempf.name, yaml.dump(dict()))
            self.conf = Config({}, tempf.name, save_backups=False)

        self.pc = PlacementController(self.mock_maas_state,
                                      self.conf)
        self.mock_machine = make_fake_machine('machine1', {'cpu_count': 3})
        self.mock_machine2 = make_fake_machine('machine2')
        self.mock_machine3 = make_fake_machine('machine3')

        self.mock_machines = [self.mock_machine]

        self.mock_maas_state.machines.return_value = self.mock_machines

        self.actions = []
        self.sub_actions = []

