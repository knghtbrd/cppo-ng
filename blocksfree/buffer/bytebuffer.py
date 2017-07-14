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

from typing import Optional, Union
from .buffertype import BufferType

class ByteBuffer(BufferType):
	"""ByteBuffer(bytes_or_int[, changed[, locked]]) -> ByteBuffer

	Create a BufferType object in memory.  If an int is provided, the buffer
	will be zero-filled.  If it is a bytes-type object, the object will be
	copied into the buffer.
	"""

	def __init__(
			self,
			bytes_or_int: Union[bytes,int],
			changed: bool = False,
			locked: bool = False
			) -> None:
		self._buf = bytearray(bytes_or_int)
		self._changed = changed
		self._locked = locked

	def __len__(self) -> int:
		"""Return len(self)"""
		return len(self._buf)

	def read(
			self,
			start: int = 0,
			count: Optional[int] = None,
			limit: bool = True
			) -> bytearray:
		"""Return bytearray of count bytes from buffer beginning at start

		By default, an IndexError will be raised if you read past the end of
		the buffer.  Pass limit=False if reads outside the buffer should just
		return trncated or empty results as with python slicing
		"""
		if count is None:
			count = len(self)
		try:
			assert(start >= 0)
			assert(count >= 0)
			if limit == True:
				assert(start + count <= len(self._buf))
		except AssertionError:
			raise IndexError('buffer read with index out of range')
		return bytes(self._buf[start:start + count])

	def write(
			self,
			buf: bytes,
			start: int,
			count: Optional[int] = None,
			limit: bool = True
			) -> None:
		"""Writes bytes to buffer beginning at start

		If count is not supplied, the entire bytes-like object will be written
		to the buffer.  An IndexError will be raised if the write would extend
		past the end of the buffer.  Pass limit=False
		"""
		if self.locked:
			raise BufferError('cannot write to locked buffer')

		if not count:
			count = len(buf)
		try:
			assert(start >= 0)
			assert(count >= 0)
			if limit == True:
				assert(start + count <= len(self._buf))
		except AssertionError:
			raise IndexError('buffer write with index out of range')

		self._buf[start:start+count] = buf
		self._changed = True

	def resize(self, size):
		"""Resize buffer to size

		If size is larger than len(self), the buffer is appended with zero
		bytes.  If it is smaller, the buffer will be truncated.
		"""
		if self.locked:
			raise BufferError('cannot write to locked buffer')

		if size <= len(self._buf):
			del self._buf[size:]
		else:
			self._buf.append(bytes(size - len(self._buf)))
		self._changed = True

	@property
	def locked(self):
		"""Returns True for read-only buffers."""
		return self._locked

	@locked.setter
	def locked(self, value: bool) -> None:
		self._locked = value
