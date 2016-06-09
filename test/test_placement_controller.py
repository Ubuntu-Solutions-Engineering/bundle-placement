#!/usr/bin/env python
#
# tests placement/controller.py
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
import os
import unittest
from unittest.mock import MagicMock, PropertyMock, patch
import yaml
from tempfile import NamedTemporaryFile

from bundleplacer.bundle import create_service
from bundleplacer.config import Config

import bundleplacer.utils as utils

from bundleplacer.controller import AssignmentType, PlacementController


DATA_DIR = os.path.join(os.path.dirname(__file__), 'maas-output')

log = logging.getLogger('bundleplacer.test_placement_controller')


class PlacementControllerTestCase(unittest.TestCase):

    def setUp(self):
        self.mock_maas_state = MagicMock()
        with NamedTemporaryFile(mode='w+', encoding='utf-8') as tempf:
            utils.spew(tempf.name, yaml.dump(dict()))
            self.conf = Config(tempf.name, {}, save_backups=False)

        temp_bundle_f = NamedTemporaryFile(mode='r')
        self.conf.setopt('bundle_filename', temp_bundle_f.name)
        self.service_1 = create_service("nova-compute", {
            "num_units": 1,
            "charm": "cs:trusty/nova-compute-100"}, {}, [])
        self.service_2 = create_service("keystone", {
            "num_units": 1,
            "charm": "cs:trusty/keystone-100"}, {}, [])

        self.bundle_patcher = patch("bundleplacer.controller.Bundle")
        self.mock_bundle = self.bundle_patcher.start()
        self.mock_bundle_i = self.mock_bundle.return_value
        pm = PropertyMock(return_value=[self.service_1, self.service_2])
        type(self.mock_bundle_i).services = pm

        self.pc = PlacementController(self.mock_maas_state,
                                      self.conf)
        self.mock_machine = MagicMock(name='machine1')
        pmid = PropertyMock(return_value='fake-instance-id-1')
        type(self.mock_machine).instance_id = pmid

        self.mock_machine_2 = MagicMock(name='machine2')
        pmid2 = PropertyMock(return_value='fake-instance-id-2')
        type(self.mock_machine_2).instance_id = pmid2

        self.mock_machines = [self.mock_machine, self.mock_machine_2]

        self.mock_maas_state.machines.return_value = self.mock_machines

    def tearDown(self):
        self.bundle_patcher.stop()

    def test_get_assignments_atype(self):
        self.assertEqual(0,
                         len(self.pc.get_assignments(self.service_1)))
        self.pc.assign(self.mock_machine, self.service_1, AssignmentType.LXC)
        self.pc.assign(self.mock_machine, self.service_1, AssignmentType.LXC)
        md = self.pc.get_assignments(self.service_1)
        self.assertEqual(1, len(md))
        self.assertEqual(2, len(md[AssignmentType.LXC]))

    def _do_test_simple_assign_type(self, assignment_type):
        self.pc.assign(self.mock_machine, self.service_1, assignment_type)
        print("assignments is {}".format(self.pc.assignments))
        machines = self.pc.get_assignments(self.service_1)
        print('machines for charm is {}'.format(machines))
        self.assertEqual(machines,
                         {assignment_type: [self.mock_machine]})

        ma = self.pc.assignments_for_machine(self.mock_machine)

        self.assertEqual(ma[assignment_type], [self.service_1])

    def test_simple_assign_bare(self):
        self._do_test_simple_assign_type(AssignmentType.BareMetal)

    def test_simple_assign_lxc(self):
        self._do_test_simple_assign_type(AssignmentType.LXC)

    def test_simple_assign_kvm(self):
        self._do_test_simple_assign_type(AssignmentType.KVM)

    def test_assign_multi(self):
        self.pc.assign(self.mock_machine, self.service_1, AssignmentType.LXC)
        self.assertEqual(self.pc.get_assignments(self.service_1),
                         {AssignmentType.LXC: [self.mock_machine]})

        self.pc.assign(self.mock_machine, self.service_1, AssignmentType.KVM)
        self.assertEqual(self.pc.get_assignments(self.service_1),
                         {AssignmentType.LXC: [self.mock_machine],
                          AssignmentType.KVM: [self.mock_machine]})

        ma = self.pc.assignments_for_machine(self.mock_machine)
        self.assertEqual(ma[AssignmentType.LXC], [self.service_1])
        self.assertEqual(ma[AssignmentType.KVM], [self.service_1])

    def test_remove_assignment_multi(self):
        self.pc.assign(self.mock_machine, self.service_1, AssignmentType.LXC)
        self.pc.assign(self.mock_machine_2, self.service_1,
                       AssignmentType.LXC)

        mfc = self.pc.get_assignments(self.service_1)

        mfc_lxc = set(mfc[AssignmentType.LXC])
        self.assertEqual(mfc_lxc, set(self.mock_machines))

        self.pc.clear_assignments(self.mock_machine)
        self.assertEqual(self.pc.get_assignments(self.service_1),
                         {AssignmentType.LXC: [self.mock_machine_2]})

    def test_remove_one_assignment_sametype(self):
        self.pc.assign(self.mock_machine, self.service_1, AssignmentType.LXC)
        self.pc.assign(self.mock_machine, self.service_1, AssignmentType.LXC)

        self.pc.remove_one_assignment(self.mock_machine, self.service_1)
        md = self.pc.assignments[self.mock_machine.instance_id]
        lxcs = md[AssignmentType.LXC]
        self.assertEqual(lxcs, [self.service_1])

        self.pc.remove_one_assignment(self.mock_machine, self.service_1)
        md = self.pc.assignments[self.mock_machine.instance_id]
        lxcs = md[AssignmentType.LXC]
        self.assertEqual(lxcs, [])

    def test_remove_one_assignment_othertype(self):
        self.pc.assign(self.mock_machine, self.service_1, AssignmentType.LXC)
        self.pc.assign(self.mock_machine, self.service_1, AssignmentType.KVM)

        self.pc.remove_one_assignment(self.mock_machine, self.service_1)
        md = self.pc.assignments[self.mock_machine.instance_id]
        lxcs = md[AssignmentType.LXC]
        kvms = md[AssignmentType.KVM]
        self.assertEqual(1, len(lxcs) + len(kvms))

        self.pc.remove_one_assignment(self.mock_machine, self.service_1)
        md = self.pc.assignments[self.mock_machine.instance_id]
        lxcs = md[AssignmentType.LXC]
        kvms = md[AssignmentType.KVM]
        self.assertEqual(0, len(lxcs) + len(kvms))

    def test_clear_all(self):
        self.pc.assign(self.mock_machine, self.service_1, AssignmentType.LXC)
        self.pc.assign(self.mock_machine_2,
                       self.service_1, AssignmentType.KVM)
        self.pc.clear_all_assignments()
        # check that it's empty:
        self.assertEqual(self.pc.assignments, {})
        # and that it's still a defaultdict(lambda: defaultdict(list))
        mid = self.mock_machine.machine_id
        lxcs = self.pc.assignments[mid][AssignmentType.LXC]
        self.assertEqual(lxcs, [])

    def test_unassigned_starts_full(self):
        self.assertEqual(len(self.pc.unassigned_undeployed_services()),
                         len(self.pc.services()))

    def test_assigned_services_starts_empty(self):
        self.assertEqual(0, len(self.pc.assigned_services))

    def test_reset_unassigned_undeployed_none(self):
        """Assign all charms, ensure that unassigned is empty"""
        for cc in self.pc.services():
            self.pc.assign(self.mock_machine, cc, AssignmentType.LXC)

        self.pc.reset_assigned_deployed()

        self.assertEqual(0, len(self.pc.unassigned_undeployed_services()))

    def test_reset_unassigned_undeployed_two(self):
        self.pc.assign(self.mock_machine, self.service_1, AssignmentType.LXC)
        self.pc.assign(self.mock_machine_2, self.service_2, AssignmentType.KVM)
        self.pc.reset_assigned_deployed()
        self.assertEqual(len(self.pc.services()) - 2,
                         len(self.pc.unassigned_undeployed_services()))

    def test_reset_excepting_compute(self):
        for cc in self.pc.services():
            if cc.charm_name == 'nova-compute':
                continue
            self.pc.assign(self.mock_machine, cc, AssignmentType.LXC)

        self.pc.reset_assigned_deployed()
        self.assertEqual(len(self.pc.unassigned_undeployed_services()), 1)

    def test_unassigned_undeployed(self):
        all_charms = set(self.pc.services())
        self.pc.assign(self.mock_machine, self.service_2, AssignmentType.KVM)
        self.pc.assign(self.mock_machine, self.service_1, AssignmentType.KVM)
        self.pc.mark_deployed(self.mock_machine, self.service_2,
                              AssignmentType.KVM)

        self.assertTrue(self.service_2 not in
                        self.pc.unassigned_undeployed_services())
        self.assertTrue(self.service_1 not in
                        self.pc.unassigned_undeployed_services())
        self.assertTrue(self.pc.is_deployed(self.service_2))
        self.assertTrue(self.pc.is_assigned(self.service_1))

        self.assertEqual(len(all_charms) - 2,
                         len(self.pc.unassigned_undeployed_services()))

        n_k_as = self.pc.assignment_machine_count_for_service(self.service_2)
        self.assertEqual(n_k_as, 0)
        n_k_dl = self.pc.deployment_machine_count_for_service(self.service_2)
        self.assertEqual(n_k_dl, 1)
        n_nc_as = self.pc.assignment_machine_count_for_service(self.service_1)
        self.assertEqual(n_nc_as, 1)
        n_nc_dl = self.pc.deployment_machine_count_for_service(self.service_1)
        self.assertEqual(n_nc_dl, 0)

    def test_deployed_charms_starts_empty(self):
        "Initially there are no deployed charms"
        self.assertEqual(0, len(self.pc.deployed_services))

    def test_mark_deployed_unsets_assignment(self):
        "Setting a placement to deployed removes it from assignment dict"
        self.pc.assign(self.mock_machine, self.service_2, AssignmentType.KVM)
        self.assertEqual([self.service_2], self.pc.assigned_services)
        self.pc.mark_deployed(self.mock_machine, self.service_2,
                              AssignmentType.KVM)
        self.assertEqual([self.service_2], self.pc.deployed_services)
        self.assertEqual([], self.pc.assigned_services)

    def test_set_deployed_unsets_assignment_only_once(self):
        "Setting a placement to deployed removes it from assignment dict"
        self.pc.assign(self.mock_machine, self.service_1, AssignmentType.KVM)
        self.pc.assign(self.mock_machine_2, self.service_1,
                       AssignmentType.KVM)
        self.assertEqual([self.service_1], self.pc.assigned_services)
        ad = self.pc.get_assignments(self.service_1)
        dd = self.pc.get_deployments(self.service_1)
        from pprint import pformat
        print("Assignments is {}".format(pformat(ad)))
        print("Deployments is {}".format(pformat(dd)))
        self.assertEqual(set([self.mock_machine, self.mock_machine_2]),
                         set(ad[AssignmentType.KVM]))
        self.assertEqual(len(dd.items()), 0)

        self.pc.mark_deployed(self.mock_machine, self.service_1,
                              AssignmentType.KVM)
        self.assertEqual([self.service_1], self.pc.deployed_services)
        self.assertEqual([self.service_1], self.pc.assigned_services)
        ad = self.pc.get_assignments(self.service_1)
        dd = self.pc.get_deployments(self.service_1)
        self.assertEqual([self.mock_machine_2], ad[AssignmentType.KVM])
        self.assertEqual([self.mock_machine], dd[AssignmentType.KVM])

    def test_is_assigned_to_is_deployed_to(self):
        self.assertFalse(self.pc.is_assigned_to(self.service_2,
                                                self.mock_machine))
        self.assertFalse(self.pc.is_deployed_to(self.service_2,
                                                self.mock_machine))
        self.pc.assign(self.mock_machine, self.service_2, AssignmentType.LXC)
        self.assertFalse(self.pc.is_deployed_to(self.service_2,
                                                self.mock_machine))
        self.assertTrue(self.pc.is_assigned_to(self.service_2,
                                               self.mock_machine))
        self.pc.mark_deployed(self.mock_machine, self.service_2,
                              AssignmentType.LXC)
        self.assertTrue(self.pc.is_deployed_to(self.service_2,
                                               self.mock_machine))
        self.assertFalse(self.pc.is_assigned_to(self.service_2,
                                                self.mock_machine))

    def test_double_clear_ok(self):
        """clearing assignments for a machine that isn't assigned (anymore) is
        OK and should do nothing
        """
        self.pc.assign(self.mock_machine, self.service_2, AssignmentType.LXC)
        self.pc.clear_assignments(self.mock_machine)
        self.pc.clear_assignments(self.mock_machine)
        self.pc.clear_assignments(self.mock_machine_2)
