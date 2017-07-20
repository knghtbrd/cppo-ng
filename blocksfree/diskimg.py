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

import os
import struct
from .buffer.bytebuffer import ByteBuffer

# FIXME Move to_sys_name
from . import legacy

class Disk:
	def __init__(self, name=None):
		if name is not None:
			self.pathname = name
			self.path, self.filename = os.path.split(name)
			self.diskname, self.ext = os.path.splitext(self.filename)
			self.ext = os.path.splitext(name)[1].lower()
			# FIXME: Handle compressed images?
			with open(legacy.to_sys_name(name), "rb") as f:
				self.buffer = ByteBuffer(f.read())
