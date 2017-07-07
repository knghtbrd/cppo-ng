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

import sys
import logging
import textwrap

### LOGGING
# *sigh* No clean/simple way to use str.format() type log strings without
# jumping through a few hoops

class Message(object):
	def __init__(self, fmt, args):
		self.fmt = fmt
		self.args = args

	def __str__(self):
		return self.fmt.format(*self.args)

class StyleAdapter(logging.LoggerAdapter):
	def __init__(self, logger, extra=None):
		super(StyleAdapter, self).__init__(logger, extra or {})

	def log(self, level, msg, *args, **kwargs):
		if self.isEnabledFor(level):
			msg, kwargs = self.process(textwrap.dedent(msg), kwargs)
			self.logger._log(level, Message(str(msg), args), (), **kwargs)

log = StyleAdapter(logging.getLogger(__name__))


# Set up our logging facility
_handler = logging.StreamHandler(sys.stdout)
_formatter = logging.Formatter('%(message)s')
_handler.setFormatter(_formatter)
log.logger.addHandler(_handler)
log.setLevel(logging.DEBUG)
