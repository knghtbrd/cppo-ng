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
"""Read/Write BufferType that lives in memory"""


from typing import Dict, List, Optional, Union
from .buffertype import BufferType
from .. import util

class ByteBuffer(BufferType):
	"""ByteBuffer(bytes_or_int[, changed[, locked]]) -> ByteBuffer

	Create a BufferType object in memory.  If an int is provided, the buffer
	will be zero-filled.  If it is a bytes-type object, the object will be
	copied into the buffer.
	"""

	def __init__(
			self,
			bytes_or_int: Union[bytes, int],
			changed: bool = False,
			locked: bool = False
			) -> None:
		self._buf = bytearray(bytes_or_int)
		self._changed = changed
		self._locked = locked

	def __len__(self) -> int:
		"""Implement len(self)"""
		return len(self._buf)

	@property
	def changed(self):
		"""Return True if buffer has been altered

		Returns:
			Always False for read-only buffers
		"""
		return self._changed

	def read(self, start: int, count: int) -> bytes:
		"""Return count bytes from buffer beginning at start

		Args:
			start: Starting position of bytes to return
			count: Number of bytes to return

		Returns:
			bytes object of the requested length copied from buffer

		Raises:
			IndexError if attempt to read outside the buffer is made
		"""
		try:
			assert start >= 0
			assert count >= 0
			assert start + count <= len(self._buf)
		except AssertionError:
			raise IndexError('buffer read with index out of range')
		return bytes(self._buf[start:start + count])

	def read1(self, offset: int) -> int:
		"""Return single byte from buffer as int

		Args:
			offset: The position of the requested byte in the buffer

		Returns:
			int value of the requested byte

		Raises:
			IndexError if attempt to read outside the buffer is made
		"""
		try:
			assert 0 <= offset <= len(self._buf)
		except AssertionError:
			raise IndexError('buffer read with index out of range')
		return self._buf[offset]

	def write(
			self,
			buf: bytes,
			start: int,
			count: Optional[int] = None
			) -> None:
		"""Write given bytes-like object to buffer at start

		Args:
			buf: The bytes-like object to write
			start: Offset to where in buffer it should be written
			count: Length to write (default: length of buf)

		Raises:
			IndexError if attempt to read outside the buffer is made
		"""
		if self.locked:
			raise BufferError('cannot write to locked buffer')

		if not count:
			count = len(buf)
		try:
			assert start >= 0
			assert count >= 0
			assert start + count <= len(self._buf)
		except AssertionError:
			raise IndexError('buffer write with index out of range')

		self._buf[start:start+count] = buf
		self._changed = True

	def resize(self, size: int) -> None:
		r"""Resize a given buffer

		Resizes the current buffer in place.  If size < len(self), the buffer
		will be truncated.  If size > len(self), the buffer will be extended.
		The newly added bytes will be b'\x00'

		Args:
			size: New size of buffer

		Raises:
			BufferError if buffer is locked
		"""
		if self.locked:
			raise BufferError('cannot write to locked buffer')

		if size <= len(self._buf):
			del self._buf[size:]
		else:
			self._buf.append(bytes(size - len(self._buf)))
		self._changed = True

	@property
	def locked(self) -> bool:
		"""Determine writability of buffer

		Returns:
			True if buffer has been locked to prevent writing
		"""
		return self._locked

	@locked.setter
	def locked(self, value: bool) -> None:
		self._locked = value

	def __repr__(self):
		"""Return repr(self)

		This will be a very long string for any buffer of non-trivial length
		"""
		return 'ByteBuffer({_buf}, {_changed}, {_locked})'.format_map(
				vars(self))

	def __str__(self) -> str:
		"""Implement str(self)"""
		return '<ByteBuffer of {} bytes>'.format(len(self._buf))

	def hexdump(self, *args: List, **kwargs: Dict) -> None:
		"""Performas a canonical hexdump of self.

		Args:
			Any for blocksfree.util.hexdump, see that function for details.
		"""
		util.hexdump(self._buf, *args, **kwargs)
