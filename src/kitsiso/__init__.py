"""Public API of the *kitsiso* package."""

__version__ = '0.2.0'

import os

import dcar

from ._notifier import Notifier, BUS_NAME, OBJ_PATH, INTERFACE
from ._notification import DEFAULT_TIMEOUT, NO_TIMEOUT, Urgency, Notification

__all__ = ['Notifier',
           'DEFAULT_TIMEOUT',
           'NO_TIMEOUT',
           'Urgency',
           'Notification',
           'send_notification']


def send_notification(summary, body=None, *, app_name=None, icon=None,
                      urgency=Urgency.NORMAL, timeout=DEFAULT_TIMEOUT):
    """Send a simple notification.

    This function does not instantiate :class:`Notifier`. It connects
    to the D-Bus on each call and disconnects after the notification was
    sent.

    :param str summary: a single line overview
    :param str body: multi-line body of text
    :param str app_name: the application name
    :param str icon: path to notification icon
    :param urgency: urgency level
    :type urgency: Urgency
    :param int timeout: notification timeout in seconds, :const:`NO_TIMEOUT`
                        or :const:`DEFAULT_TIMEOUT`
    """
    with dcar.Bus() as bus:
        bus.method_call(OBJ_PATH, INTERFACE, 'Notify', BUS_NAME,
                        signature='susssasa{sv}i',
                        args=(app_name or '', 0,
                              os.path.abspath(icon) if icon else '',
                              summary, body or '', [],
                              {'urgency': ('y', urgency.value)},
                              timeout * 1000 if timeout > 0 else timeout))
