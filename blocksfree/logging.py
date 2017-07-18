# vim: set tabstop=4 shiftwidth=4 noexpandtab filetype=python:

# Copyright (C) 2017  T. Joseph Carter
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

"""BlocksFree LoggingAdapter using str.format and textwrap.dedent

Traditionally Python has used a % operator on strings to perform a somewhat
printf-like string formatting operation.  It has limitations and str.format was
made to replace it.  The old way isn't deprecated yet, and it won't be removed
any time soon, but str.format is how new code should work.

The issue is that Python's logging module is used by old and new code alike,
and so calls to the basic logger require the use of %-style format strings in
order to work with new and old code alike, forcing you to use the less flexible
"old way".

There isn't a perfectly clean solution to this--either you need ugliness in
each logging call, or you need a bit different ugliness up front to hide the
mess.

Details are at the bottom of this section of the Logging Cookbook:

https://docs.python.org/howto/logging-cookbook.html\
#use-of-alternative-formatting-styles

The next issue was that multi-line strings either break code indentation flow,
or they have to deal with indentation.  If you don't have a special case for
the first line, textwrap.dedent works great for that.  In order to avoid the
special case, just use a line continuation immediately after your opening
quotes.  Another imperfect solution, but it does the job.
"""

import sys
import logging
import textwrap
from typing import List, Dict

# pylint: disable=too-few-public-methods,missing-docstring
class Message(object):
	def __init__(self, fmt: str, args: List) -> None:
		self.fmt = fmt
		self.args = args

	def __str__(self) -> str:
		return self.fmt.format(*self.args)
# pylint: enable=too-few-public-methods,missing-docstring

class StyleAdapter(logging.LoggerAdapter):
	"""Return a LoggerAdapter that uses str.format expansions in log messages

	StyleAdapter wraps the standard logger (e.g. logging.getLogger) so that it
	appears to take str.format strings rather than the classic str % tuple
	strings.

	Args:
		logger: A logging.Logger instance/logging channel
		extra: A context object (see the Python logging cookbook)
	"""

	def __init__(self, logger: logging.Logger, extra=None) -> None:
		super(StyleAdapter, self).__init__(logger, extra or {})

	def log(self, level: int, msg: str, *args: List, **kwargs: Dict) -> None:
		"""Logs msg.format(*args) at the given level

		Effectively functions as if we were subclassing logging.Logger's log
		method to change arg convention from msg % args to msg.format(*args).
		See the documentation for the standard logging module for more info.

		Additionally can perform textwrap.dedent() on msg before logging if
		dedent=True.

		Args:
			level: Integer logging level
			msg: A log message in the form of a str.format format string
			dedent: Whether to dedent format string
			args/kwargs: Positional and keyword arguments passed to _log
		"""
		if self.isEnabledFor(level):
			if kwargs.get('dedent', False):
				msg = textwrap.dedent(msg)
			msg, kwargs = self.process(msg, kwargs)
			# pylint: disable=protected-access
			self.logger._log(level, Message(str(msg), args), (), **kwargs)
			# pylint: enable=protected-access

LOG = StyleAdapter(logging.getLogger(__name__))

# Set up our logging facility
# FIXME(tjcarter): get rid of log, let caller handle where it's going
log = LOG
_HANDLER = logging.StreamHandler(sys.stdout)
_FORMATTER = logging.Formatter('{message}', style='{')
_HANDLER.setFormatter(_FORMATTER)
LOG.logger.addHandler(_HANDLER)
LOG.setLevel(logging.DEBUG)
