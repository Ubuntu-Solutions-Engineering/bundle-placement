# Copyright 2015 Canonical, Ltd.
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

from urwid import Divider, Pile, Text, WidgetWrap

from bundleplacer.maas import satisfies
from bundleplacer.state import ServiceState
from bundleplacer.ui.simple_service_widget import SimpleServiceWidget

log = logging.getLogger('bundleplacer.ui')


class ServicesList(WidgetWrap):

    """A list of services with flexible display options.

    Note that not all combinations of display options make sense. YMMV.

    controller - a PlacementController

    display_controller - a PlacerView

    machine - a machine instance to query for constraint checking. If
    None, no constraint checking is done. If set, only services whose
    constraints are satisfied by 'machine' are shown.

    ignore_assigned - bool, whether or not to display services that
    have already been assigned to a machine (but not yet deployed)

    ignore_deployed - bool, whether or not to display services that
    have already been deployed

    deployed_only - bool, only show deployed services

    show_constraints - bool, whether or not to display the constraints
    for the various services

    show_type - string, one of 'all', 'required' or 'non-required',
    controls which service states should be shown. default is 'all'.

    trace_updates - bool, enable verbose update logging

    """

    def __init__(self, placement_controller, display_controller,
                 machine=None, ignore_assigned=False,
                 ignore_deployed=False, assigned_only=False,
                 deployed_only=False, show_type='all',
                 show_constraints=False, show_placements=False,
                 title="Services", trace_updates=False):
        self.placement_controller = placement_controller
        self.display_controller = display_controller
        self.service_widgets = []
        self.machine = machine
        self.ignore_assigned = ignore_assigned
        self.ignore_deployed = ignore_deployed
        self.assigned_only = assigned_only
        self.deployed_only = deployed_only
        self.show_type = show_type
        self.show_constraints = show_constraints
        self.show_placements = show_placements
        self.title = title
        self.trace = trace_updates
        w = self.build_widgets()
        self.update()
        super().__init__(w)

    def selectable(self):
        # overridden to ensure that we can arrow through the buttons
        # shouldn't be necessary according to documented behavior of
        # Pile & Columns, but discovered via trial & error.
        return True

    def build_widgets(self):
        widgets = []
        if self.title:
            widgets = [Text(self.title), Divider(' ')]
        widgets += self.service_widgets
        self.service_pile = Pile(widgets)
        return self.service_pile

    def focus_top_or_next(self):
        return self._setfocus(top=False)

    def focus_top(self):
        return self._setfocus(top=True)

    def _setfocus(self, top):
        try:
            if top:
                self.service_pile.focus_position = 0
            else:
                pos = self.service_pile.focus_position
                if pos + 1 >= len(self.service_widgets):
                    return False
                self.service_pile.focus_position = pos + 1
        except IndexError:
            log.debug("caught indexerror in servicescolumn.focus_next")
            return False
        return True

    def focused_service_widget(self):
        if len(self.service_widgets) > 0:
            return self.service_pile.focus
        return None

    def find_service_widget(self, s):
        return next((sw for sw in self.service_widgets if
                     sw.service.service_name == s.service_name),
                    None)

    def update(self):

        def trace(service, s):
            if self.trace:
                log.debug("{}: {} {}".format(self.title, service, s))

        for s in self.placement_controller.services():
            if self.machine:
                pc = self.placement_controller
                if not satisfies(self.machine, s.constraints)[0] \
                   or not (pc.is_assigned_to(s, self.machine) or
                           pc.is_deployed_to(s, self.machine)):
                    self.remove_service_widget(s)
                    trace(s, "removed because machine doesn't match")
                    continue

            if self.ignore_assigned and self.assigned_only:
                raise Exception("Can't both ignore and only show assigned.")

            if self.ignore_assigned:
                pc = self.placement_controller
                n = pc.assignment_machine_count_for_service(s)
                if n == s.required_num_units() \
                   and not s.allow_multi_units \
                   and self.placement_controller.is_assigned(s):
                    self.remove_service_widget(s)
                    trace(s, "removed because max units are "
                          "assigned")
                    continue
            elif self.assigned_only:
                if not self.placement_controller.is_assigned(s):
                    self.remove_service_widget(s)
                    trace(s, "removed because it is not assigned and "
                          "assigned_only is True")
                    continue

            if self.ignore_deployed and self.deployed_only:
                raise Exception("Can't both ignore and only show deployed.")

            if self.ignore_deployed:
                pc = self.placement_controller
                n = pc.deployment_machine_count_for_service(s)
                if n == s.required_num_units() \
                   and self.placement_controller.is_deployed(s):
                    self.remove_service_widget(s)
                    trace(s, "removed because the required number of units"
                          " has been deployed")
                    continue
            elif self.deployed_only:
                if not self.placement_controller.is_deployed(s):
                    self.remove_service_widget(s)
                    continue

            state, _, _ = self.placement_controller.get_service_state(s)
            if self.show_type == 'required':
                if state != ServiceState.REQUIRED:
                    self.remove_service_widget(s)
                    continue
            elif self.show_type == 'non-required':
                if state == ServiceState.REQUIRED:
                    self.remove_service_widget(s)
                    trace(s, "removed because show_type is 'non-required' and"
                          "state is REQUIRED.")
                    continue
                assigned_or_deployed = (
                    self.placement_controller.is_assigned(s) or
                    self.placement_controller.is_deployed(s))
                if not s.allow_multi_units and assigned_or_deployed:
                    self.remove_service_widget(s)
                    trace(s, "removed because it doesn't allow multiple units"
                          " and is not assigned or deployed.")
                    continue

            sw = self.find_service_widget(s)
            if sw is None:
                sw = self.add_service_widget(s)
                trace(s, "added widget")
            sw.update()

        self.sort_service_widgets()

    def add_service_widget(self, service):
        sw = SimpleServiceWidget(service, self.placement_controller,
                                 self.display_controller,
                                 show_placements=self.show_placements)
        self.service_widgets.append(sw)
        options = self.service_pile.options()
        self.service_pile.contents.append((sw, options))

        # NOTE: see the + 1: indexing in remove_service_widget if you
        # re-add this divider. it should then be +2.

        # self.service_pile.contents.append((AttrMap(Padding(Divider('\u23bc'),
        #                                                    left=2, right=2),
        #                                            'label'), options))
        return sw

    def remove_service_widget(self, service):
        sw = self.find_service_widget(service)

        if sw is None:
            return
        self.service_widgets.remove(sw)
        sw_idx = 0
        for w, opts in self.service_pile.contents:
            if w == sw:
                break
            sw_idx += 1

        c = self.service_pile.contents[:sw_idx] + \
            self.service_pile.contents[sw_idx + 1:]
        self.service_pile.contents = c

    def sort_service_widgets(self):
        def keyfunc(sw):
            s = sw.service
            if s.subordinate:
                skey = 'z'
            else:
                skey = s.service_name
            return skey
        self.service_widgets.sort(key=keyfunc)

        def wrappedkeyfunc(t):
            mw, options = t
            if not isinstance(mw, SimpleServiceWidget):
                return 'A'
            return keyfunc(mw)

        self.service_pile.contents.sort(key=wrappedkeyfunc)

    def select_service(self, service_name):
        idx = 0
        for w, opts in self.service_pile.contents:
            if w.service.service_name == service_name:
                self.service_pile.focus_position = idx
                return
            idx += 1
