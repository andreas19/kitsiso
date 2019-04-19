"""Public API of the *kitsiso* package."""

__version__ = '0.0.5'

import os

from jeepney import new_method_call
from jeepney.integrate.blocking import connect_and_authenticate

from ._notifier import Notifier, _addr
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

    This funcition does not instantiate :class:`Notifier`. It connects
    to the D-Bus on each call and disconnects after the notification was
    sent.

    :param str summary: a single line overview
    :param str body: multi-line body of text
    :param str app_name: the application name
    :param str icon: path to notification icon
    :param urgency: urgency level
    :type urgency: Urgency
    :param int timeout: notification timeout in milliseconds
    """
    conn = None
    try:
        conn = connect_and_authenticate()
        msg = new_method_call(_addr, 'Notify', 'susssasa{sv}i',
                              (app_name or '', 0,
                               os.path.abspath(icon) if icon else '',
                               summary, body or '', [],
                               {'urgency': ('y', urgency.value)}, timeout))
        conn.send_and_get_reply(msg)
    finally:
        if conn:
            conn.sock.close()
