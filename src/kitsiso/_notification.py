"""Notification module."""
from contextlib import suppress
from enum import Enum

__all__ = ['DEFAULT_TIMEOUT', 'NO_TIMEOUT', 'Urgency', 'Notification']

DEFAULT_TIMEOUT = -1
NO_TIMEOUT = 0


class Urgency(Enum):
    """Urgency levels for notifications: LOW, NORMAL, CRITICAL."""

    LOW = 0
    NORMAL = 1
    CRITICAL = 2


class Notification:
    """Class for a notification.

    An instance of this class has the following r/w attributes:

      * summary
      * body
      * icon
      * urgency
      * timeout

    :param str summary: a single line overview
    :param str body: multi-line body of text
    :param str icon: path to notification icon
    :param urgency: urgency level
    :type urgency: Urgency
    :param int timeout: notification timeout in seconds, :const:`NO_TIMEOUT`
                        or :const:`DEFAULT_TIMEOUT`
    """

    def __init__(self, summary, body=None, *, icon=None,
                 urgency=Urgency.NORMAL,
                 timeout=DEFAULT_TIMEOUT):
        self._id = 0
        self.summary = summary
        self.body = body
        self.icon = icon
        self.urgency = urgency
        self.timeout = timeout
        self._actions = {}
        self._hints = {}
        self._closed_handler = None

    def add_action(self, key, name, func, args=(), kwargs={}):  # noqa: B006
        """Add an action.

        An action is mostly shown as a button in the notification.

        :param str key: must be unique for one notification
        :param str name: will be shown in the notification
        :param func: callback function `func(*args, **kwargs)`
                     (should return quickly)
        :type func: callable or None
        :param args: arguments for the callback function
        :type args: tuple
        :param kwargs: keyword arguments for the callback function
        :type kwargs: dict
        """
        self._actions[key] = (key, name, func, args, kwargs)

    def del_action(self, key):
        """Delete an action."""
        with suppress(KeyError):
            del self._actions[key]

    def clear_actions(self):
        """Clear all actions."""
        self._actions.clear()

    def add_hint(self, name, signature, value):
        """Add a hint.

        Hints are defined in the `specification <https://people.gnome.org
        /~mccann/docs/notification-spec/notification-spec-latest.html
        #hints>`_.

        The *urgency* hint will be ignored (use the parameter or
        the attribute `urgency`).

        The signature must be given as defined in the D-Bus specification:

        =======  =====
        Type     Code
        =======  =====
        boolean    b
        byte       y
        int        i
        string     s
        =======  =====

        :param str name: name of the hint
        :param str signature: D-Bus signature of the value type
        :param value: the value
        """
        self._hints[name] = (signature, value)

    def del_hint(self, name):
        """Delete a hint."""
        with suppress(KeyError):
            del self._hints[name]

    def clear_hints(self):
        """Clear all hints."""
        self._hints.clear()

    def closed(self, func, args=(), kwargs={}):  # noqa: B006
        """Set a function that is envoked when the notification is closed.

        The the first argument to the function ``func`` is of type ``int``
        and indicates the reason the notification was closed:

        ===  =====
         1   the notification expired
         2   the notification was dismissed by the user
         3   the notification was closed with :meth:`Notifier.close`
         4   undefined/reserved reasons
        ===  =====

        :param func: the function `func(reason, *args, **kwargs)`
                     (should return quickly)
        :param args: arguments for the function
        :type args: tuple
        :param kwargs: keyword arguments for the function
        :type kwargs: dict
        """
        self._closed_handler = (func, args, kwargs)

    def copy(self):
        """Make a copy of this notification."""
        n = Notification(self.summary, self.body, icon=self.icon,
                         urgency=self.urgency, timeout=self.timeout)
        n._actions = self._actions.copy()
        n._hints = self._hints.copy()
        n._closed_handler = self._closed_handler
        return n

    def _get_actions(self):
        lst = []
        for action in self._actions.values():
            lst.append(action[0])
            lst.append(action[1])
        return lst

    def _get_hints(self):
        self._hints['urgency'] = ('y', self.urgency.value)
        return self._hints

    def __repr__(self):
        return '<Notification:%d:%r>' % (self._id, self.summary[:30])
