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

"""Abstract base class for disk image buffers

The buffers we will work with most commonly represent 140k disk images.  For
that, it'd make a lot of sense to simply use a bytearray.  It's built in to
the language and pretty efficient for an interpreted OO construct.  But even
ProDOS disk images can be 32M in size.

Well that's fine, because most systems have 1G or more of RAM, plus swap, you
might say.  And that's true, they do have that much RAM.  Only on an embedded
system like the Raspberry Pi, they may not have much or any swap.  And while
ProDOS volumes will never be larger than 32M, GS/OS supports other
filesystems

HFS is even commonly used.  It's true that HFS support has not been something
you could expect from AppleCommander, to say nothing of cppo, but we ought to
consider the possibility for the future.  As of this writing, we cannot
really guarantee that your host operating system can handle HFS completely.
How do you access resource fork on Linux?  How do you access any of it on
Windows?  Can Apple OSes officially carrying the designation "macOS" even
open old HFS volumes read-only anymore?  They haven't had read-write access
for some time now.
"""

from abc import ABCMeta, abstractmethod
from typing import Optional


class BufferType(object, metaclass=ABCMeta):
	"""Abstract class that describes a BufferType.

	Read-only BufferType subclasses must implement read and __len__, as well as
	provide an __init__ that establishes the buffer to be read.

	Read-write subclasses will also implement write, locked, and changed.

	If the size of the buffer may be changed (files rather than block devices),
	subclasses would implement resize.
	"""

	def __enter__(self) -> 'BufferType':
		return self

	def __exit__(self, exc_type, exc_value, traceback) -> None:
		pass

	@abstractmethod
	def __len__(self) -> int:
		"""Implement len(self)

		Subclasses must provide an implementation for this method.
		"""
		pass

	@property
	def changed(self):
		"""Return True if buffer has been altered

		Returns:
			Always False for read-only buffers
		"""
		return False

	@abstractmethod
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
		pass

	@abstractmethod
	def read1(self, offset: int) -> int:
		"""Return single byte from buffer as int

		Args:
			offset: The position of the requested byte in the buffer

		Returns:
			int value of the requested byte

		Raises:
			IndexError if attempt to read outside the buffer is made
		"""
		pass

	def write(
			self,
			buf: bytes,
			start: int,
			count: Optional[int] = None
			) -> None:
		"""Write given bytes-like object to buffer at start

		Subclasses should raise IndexError if an attempt to write outside the
		buffer is made.

		Args:
			buf: The bytes-like object to write
			start: Offset to where in buffer it should be written
			count: Length to write (default: length of buf)

		Raises:
			NotImplementedEror unless implemented by subclass
		"""
		raise NotImplementedError('buffer does not support writing')

	def resize(self, size: int) -> None:
		r"""Resize a given buffer

		Resizes the current buffer in place.  If size < len(self), the buffer
		will be truncated.  If size > len(self), the buffer will be extended.
		The newly added bytes will be b'\x00'

		Args:
			size: New size of buffer

		Raises:
			NotImplementedError unless implemented by subclass
		"""
		raise NotImplementedError('buffer does not support writing')

	@property
	def locked(self) -> bool:
		"""Determine writability of buffer

		Returns:
			True unless writing is implemented by subclass
		"""
		return True
