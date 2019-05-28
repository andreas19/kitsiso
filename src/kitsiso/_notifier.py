"""Notifier module."""
import os

import dcar

__all__ = ['Notifier']

BUS_NAME = 'org.freedesktop.Notifications'
OBJ_PATH = '/org/freedesktop/Notifications'
INTERFACE = 'org.freedesktop.Notifications'


class Notifier:
    """Class for sending notifications and handling actions and close events.

    If ``bus=None`` a bus object will be created and connected.
    It can be closed with :meth:`quit`.

    :param str app_name: the application name
    :param str app_icon: path to default notification icon
    :param dcar.Bus bus: a bus object
    """

    def __init__(self, app_name=None, app_icon=None, bus=None):
        self._notifications = {}
        self._app_name = app_name
        self._app_icon = app_icon
        if bus:
            self._bus = bus
            self._new_bus = False
        else:
            self._bus = dcar.Bus()
            self._new_bus = True
        if not self._bus.connected:
            self._bus.connect()
        self._subscribe_signal('ActionInvoked', self._action_handler)
        self._subscribe_signal('NotificationClosed', self._closed_handler)
        self._bus.register_method('/', 'org.freedesktop.DBus.Introspectable',
                                  'Introspect', self._introspect)

    def _introspect(self, bus, msg):
        bus.method_return(msg.serial, msg.sender, signature='s',
                          args=('<node></node>',))

    def quit(self):
        """Close D-Bus connection.

        If a :class:`dcar.Bus` object was passed in on instantiation
        as the ``bus`` parameter, this method does nothing.
        """
        if self._new_bus:
            self._bus.disconnect()

    def get_capabilities(self):
        """Get server capabilities.

        :return: list with server capabilities
        :rtype: list[str]
        """
        return self._bus.method_call(OBJ_PATH, INTERFACE,
                                     'GetCapabilities', BUS_NAME)[0]

    def get_server_information(self):
        """Get server information.

        :return: (name, vendor, version, spec_version)
        :rtype: tuple(str)
        """
        return self._bus.method_call(OBJ_PATH, INTERFACE,
                                     'GetServerInformation', BUS_NAME)

    def notify(self, noti):
        """Send notification.

        :param noti: the notification
        :type noti: Notification
        """
        icon = noti.icon or self._app_icon
        timeout = noti.timeout * 1000 if noti.timeout > 0 else noti.timeout
        noti._id = self._bus.method_call(OBJ_PATH, INTERFACE, 'Notify',
                                         BUS_NAME, signature='susssasa{sv}i',
                                         args=(self._app_name or '',
                                               noti._id,
                                               os.path.abspath(icon)
                                               if icon else '',
                                               noti.summary,
                                               noti.body or '',
                                               noti._get_actions(),
                                               noti._get_hints(),
                                               timeout))[0]
        self._notifications[noti._id] = noti

    def close(self, noti):
        """Close notification.

        :param noti: the notification
        :type noti: Notification
        """
        self._bus.method_call(OBJ_PATH, INTERFACE, 'CloseNotification',
                              BUS_NAME, signature='u', args=(noti._id,))

    def _closed_handler(self, msg):
        noti_id, reason = msg.args
        noti = self._notifications.pop(noti_id, None)
        if noti and noti._closed_handler:
            func, args, kwargs = noti._closed_handler
            func(reason, *args, **kwargs)

    def _action_handler(self, msg):
        noti_id, action_key = msg.args
        noti = self._notifications.get(noti_id, None)
        if noti and action_key in noti._actions:
            _, _, callback, args, kwargs = noti._actions[action_key]
            if callback:
                callback(*args, **kwargs)

    def _subscribe_signal(self, signal_name, callback):
        match_rule = dcar.MatchRule(OBJ_PATH, INTERFACE, signal_name)
        self._bus.register_signal(match_rule, callback)
