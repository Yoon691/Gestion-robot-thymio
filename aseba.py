import dbus
import time
from dbus.mainloop.glib import DBusGMainLoop
import dbus.mainloop.glib
from gi.repository import GObject as gobject
import sys
from optparse import OptionParser

gobject.threads_init()
dbus.mainloop.glib.threads_init()
                 
class AsebaException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
        
        
        
        

class Aseba(object):

    NB_EVTS_FREQ = 10 # nb of events to be received before computing frequency

    def __init__(self, system_bus = False, dummy = False):
        self.dummy = dummy

        self.callbacks = {}
        self._events_last_evt = {}
        self._events_periods = {}
        self.events_freq = {}
        self.colors = {"BLACK": 150,"WHITE":900, "GREY": 512}
        self.state = 0 
        self.interval = 5        
        self.system = 4        
        self.wordlen = 2 

        if not dummy:
            DBusGMainLoop(set_as_default=True)
            # init 
            if system_bus:
                self.bus = dbus.SystemBus()
            else:
                self.bus = dbus.SessionBus()

            try:
                self.network = dbus.Interface(
                        self.bus.get_object('ch.epfl.mobots.Aseba', '/'), 
                        dbus_interface='ch.epfl.mobots.AsebaNetwork')
            except dbus.exceptions.DBusException:
                raise AsebaException("Can not connect to Aseba DBus services! "
                                     "Is asebamedulla running?")


            # Configure event management
            eventfilter = self.network.CreateEventFilter()
            self.events = dbus.Interface(
                        self.bus.get_object('ch.epfl.mobots.Aseba', eventfilter), 
                        dbus_interface='ch.epfl.mobots.EventFilter')
            self.dispatch_handler = self.events.connect_to_signal('Event', self._dispatch_events)

    def clear_events(self):
        """ Use DBus introspection to get the list of event filters, and remove them.
        """
        try:
            introspect = dbus.Interface(
                        self.bus.get_object('ch.epfl.mobots.Aseba', "/events_filters"), 
                        dbus_interface=dbus.INTROSPECTABLE_IFACE)
            interface = introspect.Introspect()
        except dbus.exceptions.DBusException:
            # /events_filters not yet created -> no events to delete
            return

        import xml.etree.ElementTree as ET
        root = ET.fromstring(interface)
        for n in root.iter("node"):
            if 'name' in n.attrib:
                evtfilter = dbus.Interface(
                        self.bus.get_object('ch.epfl.mobots.Aseba', "/events_filters/%s" % n.attrib['name']), 
                        dbus_interface='ch.epfl.mobots.EventFilter')
                evtfilter.Free()

    def __enter__(self):
        self.run()
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def run(self):
        # run event loop
        self.loop = gobject.MainLoop()
        self.loop.run()

    def close(self):
        self.loop.quit()
        if not self.dummy:
            self.dispatch_handler.remove()
            self.events.Free()

    def dbus_reply(self):
        # correct replay on D-Bus, ignore
        pass

    def dbus_error(self, e):
        assert(not self.dummy)

        # there was an error on D-Bus, stop loop
        self.close()
        raise Exception('dbus error: %s' % str(e))

    def get_nodes_list(self):
        if self.dummy: return []

        dbus_array = self.network.GetNodesList()
        size = len(dbus_array)
        return [str(dbus_array[x]) for x in range(0,size)]

    def set(self, node, var, value):
        if self.dummy: return
        self.network.SetVariable(node, var, value)

    def get(self, node, var):
        if self.dummy: return [0] * 10
        dbus_array = self.network.GetVariable(node, var)
        size = len(dbus_array)
        if (size == 1):
            return int(dbus_array[0])
        else:
            return [int(dbus_array[x]) for x in range(0,size)]

    def send_event(self, event_id, event_args):

        if isinstance(event_id, str):
            return self.send_event_name(event_id, event_args)

        if self.dummy: return

        # events are sent asynchronously
        self.network.SendEvent(event_id, 
                               event_args,
                               reply_handler=self.dbus_reply,
                               error_handler=self.dbus_error,
                               signature='as')


    def send_event_name(self, event_name, event_args):
        if self.dummy: return

        # events are sent asynchronously
        self.network.SendEventName(event_name, 
                                   event_args,
                                   reply_handler=self.dbus_reply,
                                   error_handler=self.dbus_error)


    def load_scripts(self, path):
        """ Loads a given Aseba script (aesl) on the Aseba network.
        """
        if self.dummy: return
        self.network.LoadScripts(path)

    def _dispatch_events(self, *args):
        id, name, vals = args

        key = None

        if name in self.callbacks:
            key = name
        elif id in self.callbacks:
            # event registered from ID, not from name
            key = id

        if key:
            self.callbacks[key](vals)

            # update frequency for this event
            now = time.time()
            self._events_periods[key].append(now - self._events_last_evt[key])
            self._events_last_evt[key] = now
            if len(self._events_periods[key]) == Aseba.NB_EVTS_FREQ:
                self.events_freq[key] = 1. / (sum(self._events_periods[key]) / float(Aseba.NB_EVTS_FREQ))
                self._events_periods[key] = []

    def on_event(self, event_id, cb):
        """
        Subscribe to an Aseba event

        :param event_id: the event name or the event numerical ID
        :param cb: the callback function that will be called with the content of the event as parameter
        """
        if self.dummy: return

        self.callbacks[event_id] = cb
        self._events_last_evt[event_id] = time.time()
        self._events_periods[event_id] = []
        self.events_freq[event_id] = 0.

        if isinstance(event_id, str):
            self.events.ListenEventName(event_id)
        else:
            self.events.ListenEvent(event_id)