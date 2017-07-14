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

from abc import ABCMeta, abstractmethod
from typing import Optional

# Rationale:
#
# The buffers we will work with most commonly represent 140k disk images.  For
# that, it'd make a lot of sense to simply use a bytearray.  It's built in to
# the language and pretty efficient for an interpreted OO construct.  But even
# ProDOS disk images can be 32M in size.
#
# Well that's fine, because most systems have 1G or more of RAM, plus swap, you
# might say.  And that's true, they do have that much RAM.  Only on an embedded
# system like the Raspberry Pi, they may not have much or any swap.  And while
# ProDOS volumes will never be larger than 32M, GS/OS supports other
# filesystems
#
# HFS is even commonly used.  It's true that HFS support has not been something
# you could expect from AppleCommander, to say nothing of cppo, but we ought to
# consider the possibility for the future.  As of this writing, we cannot
# really guarantee that your host operating system can handle HFS completely.
# How do you access resource fork on Linux?  How do you access any of it on
# Windows?  Can Apple OSes officially carrying the designation "macOS" even
# open old HFS volumes read-only anymore?  They haven't had read-write access
# for some time now.

class BufferType(metaclass=ABCMeta):
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
		"""Return len(self)"""
		pass

	@property
	def changed(self):
		"""Returns True if buffer has been altered

		Always returns false for read-only buffers
		"""
		return False

	@abstractmethod
	def read(
			self,
			start: int = 0,
			count: Optional[int] = None,
			limit: bool = True
			) -> bytearray:
		"""Return bytearray of count bytes from buffer beginning at start

		Should raise IndexError if an attempt to read past the end of the
		buffer is made.
		"""
		pass

	def write(
			self,
			buf: bytes,
			start: int,
			count: Optional[int] = None,
			limit: bool = True
			) -> None:
		"""Writes bytes to buffer beginning at start

		Raises NotImplementedError unless implemented by subclass
		"""
		raise NotImplementedError('buffer does not support writing')

	def resize(self, size: int) -> None:
		"""Resize buffer to size

		Raises NotImplementedError unless implemented by subclass
		"""
		raise NotImplementedError('buffer does not support writing')

	@property
	def locked(self) -> bool:
		"""Returns True for read-only buffers.

		Returns True unless writing is implemented by subclass
		"""
		return True
