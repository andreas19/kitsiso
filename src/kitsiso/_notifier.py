"""Notifier module."""
import asyncio
import os
import threading

from jeepney.bus_messages import MatchRule, message_bus
from jeepney.integrate.asyncio import connect_and_authenticate, Proxy
from jeepney.low_level import MessageType, HeaderFields
from jeepney.wrappers import DBusAddress, new_method_call, new_method_return

__all__ = ['Notifier']

_addr = DBusAddress('/org/freedesktop/Notifications',
                    'org.freedesktop.Notifications',
                    'org.freedesktop.Notifications')


class Notifier:
    """Class for sending notifications and handling actions and close events.

    Starts an event loop which can be closed with :meth:`quit`.

    :param str app_name: the application name
    :param str app_icon: path to default notification icon
    """

    def __init__(self, app_name=None, app_icon=None):
        self._notifications = {}
        self._app_name = app_name
        self._app_icon = app_icon
        self._start_evt = threading.Event()
        self._thread = threading.Thread(target=self._start, daemon=True)
        self._thread.start()
        self._start_evt.wait()

    def _start(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._transport, self._proto = self._loop.run_until_complete(
            connect_and_authenticate())
        self._proto.router.on_unhandled = self._on_unhandled
        self._subscribe_signal('ActionInvoked', self._action_handler)
        self._subscribe_signal('NotificationClosed', self._closed_handler)
        self._start_evt.set()
        try:
            self._loop.run_forever()
        finally:
            self._transport.close()
            self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            self._loop.close()

    def _on_unhandled(self, msg):
        if (msg.header.message_type == MessageType.method_call and
                msg.header.fields.get(HeaderFields.interface) ==
                'org.freedesktop.DBus.Introspectable' and
                msg.header.fields.get(HeaderFields.member) == 'Introspect'):
            ret_msg = new_method_return(msg, 's', ('<node></node>',))
            ret_msg.header.fields[HeaderFields.destination] =\
                msg.header.fields.get(HeaderFields.sender)
            self._proto.send_message(ret_msg)

    def quit(self):
        """Close event loop and connection to D-Bus.

        After this method is called the Notifier object
        cannot be used anymore.
        """
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(0.5)

    async def _send_message(self, msg):
        return await self._proto.send_message(msg)

    def _send_and_get_reply(self, msg):
        reply = asyncio.run_coroutine_threadsafe(
            self._send_message(msg), self._loop)
        return reply.result()

    def get_capabilities(self):
        """Get server capabilities.

        :return: list with server capabilities
        :rtype: list[str]
        """
        msg = new_method_call(_addr, 'GetCapabilities')
        return self._send_and_get_reply(msg)[0]

    def get_server_information(self):
        """Get server information.

        :return: (name, vendor, version, spec_version)
        :rtype: tuple(str)
        """
        msg = new_method_call(_addr, 'GetServerInformation')
        return self._send_and_get_reply(msg)

    def notify(self, noti):
        """Send notification.

        :param noti: the notification
        :type noti: Notification
        """
        icon = noti.icon or self._app_icon
        timeout = noti.timeout * 1000 if noti.timeout > 0 else noti.timeout
        msg = new_method_call(_addr, 'Notify', 'susssasa{sv}i',
                              (self._app_name or '', noti._id,
                               os.path.abspath(icon) if icon else '',
                               noti.summary, noti.body or '',
                               noti._get_actions(),
                               noti._get_hints(),
                               timeout))
        reply = self._send_and_get_reply(msg)
        noti._id = reply[0]
        self._notifications[noti._id] = noti

    def close(self, noti):
        """Close notification.

        :param noti: the notification
        :type noti: Notification
        """
        msg = new_method_call(_addr, 'CloseNotification', 'u', (noti._id,))
        self._send_and_get_reply(msg)

    def _closed_handler(self, data):
        noti_id, reason = data
        noti = self._notifications.pop(noti_id, None)
        if noti and noti._closed_handler:
            func, args, kwargs = noti._closed_handler
            func(reason, *args, **kwargs)

    def _action_handler(self, data):
        noti_id, action_key = data
        noti = self._notifications.get(noti_id, None)
        if noti and action_key in noti._actions:
            _, _, callback, args, kwargs = noti._actions[action_key]
            if callback:
                callback(*args, **kwargs)

    def _subscribe_signal(self, member, callback):
        match_rule = MatchRule(type='signal',
                               path=_addr.object_path,
                               sender=_addr.bus_name,
                               interface=_addr.interface,
                               member=member)
        bus = Proxy(message_bus, self._proto)
        self._proto.router.subscribe_signal(callback=callback,
                                            path=_addr.object_path,
                                            interface=_addr.interface,
                                            member=member)
        self._loop.run_until_complete(bus.AddMatch(match_rule))
