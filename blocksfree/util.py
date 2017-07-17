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
"""
Utility functions for blocksfree.

This module serves as a catch-all generally for functions that don't seem to
belong somewhere else.
"""

from typing import Callable, Iterator, Sequence

def seqsplit(seq: Sequence, num: int) -> Iterator[Sequence]:
	"""Return a sequence in num-sized pieces.

	Args:
		seq: A sequence type (bytes, list, etc.)
		num: The maximum length of sequence desired

	Yields:
		The next num items from seq or as many as remain.  The last sequence we
		yield may be shorter than mum elements.
	"""
	for i in range(0, len(seq), num):
		yield seq[i:i + num]

def hexchars(line: bytes) -> str:
	"""Return a canonical byte hexdump string of byte values.

	NB: This function will be memory intensive if called on large objects.  It
	is actually intended to be called on at most 16 bytes at a time to produce
	a data for a single line of a canonical hexdump.

	Args:
		line: a bytes-like object to be dumped

	Returns:
		A string containing a canonical-style hex dump of byte values with
		space delimiters in groups of eight.  The format has this pattern:

		## ## ## ## ## ## ## ##  ## ## ## ## ## ## ## ##  ## ## ##...

		The string will not be padded to a fixed length.
	"""
	vals = [format(b, '02x') for b in line]
	return '  '.join(' '.join(part) for part in seqsplit(vals, 8))

def printables(line: bytes, mask_high: bool = False) -> str:
	r"""Return ASCII printable string from bytes for hexdump.

	Args:
		line: The bytes to convert to ASCII
		mask_high: True to mask away high bit before testing printability

	Returns:
		String of printable ASCII characters equal to the number of bytes in
		line.  All non-printable characters will be replaced by a dot (.) in
		the style of a canonical hexdump.

		If mask_high is True, the high bit of each character will be ignored.
		In that case b'\x41' and b'\xc1' will both produce 'A'.
	"""
	ascii_ = []
	for char in line:
		if mask_high:
			char = char & 0x7f
		ascii_.append(chr(char) if 0x20 <= char < 0x7f else '.')
	return ''.join(ascii_)


def hexdump_gen(
		buf: bytes,
		verbose: bool = False,
		mask_high: bool = False
		) -> Iterator[str]:
	"""Yield lines of a hexdump of a bytes-like object.

	Args:
		buf: A bytes-like object to be hexdumped
		verbose: Include full output rather than collapsing duplicated lines
		mask_high: Strip high bit of each byte for testing printable characters
			(see printables() above)

	Yields:
		For a zero-length buf, nothing.

		With verbose, lines of at most 16 bytes in the format:
			'<offset>  <hex bytes>  |<ASCII bytes>|'
		The last line provides the total number of bytes in the buffer:
			'<offset>'

		With not verbose, repeated lines whose data is the same as the line
		just printed are compressed.  Unique lines are as before:
			'<offset>  <hex bytes>  |<ASCII bytes>|'
		All lines whose bytes are identical to the previously printed line will
		be compressed to a line containing an asterisk:
			'*'
		The last line provides the total number of bytes in the buffer:
			'<offset>'

		The <offset> format is 8 hex digits with no prefix.  Individual bytes
		in <hex bytes> are 2 hex digits with no prefix, see hexchars() for the
		precise format.  The <ASCII bytes> format is described for the function
		printables() and is bracketed by two pipe (|) characters as shown here.
	"""
	buf = memoryview(buf)
	last = None
	outstar = True
	i = 0

	for i, line in enumerate(seqsplit(buf, 16)):
		if not verbose and line == last:
			if outstar:
				outstar = False  # Ensure we yield only one star
				yield '*'
		else:
			last = line
			outstar = True  # This line is not a star
			yield "{:07x}0  {:48}  |{:16}|".format(
					i, hexchars(line), printables(line, mask_high))

	if last is not None:
		yield format(i * 16 + len(last), '08x')

def hexdump(
		buf: bytes,
		verbose: bool = False,
		mask_high: bool = False,
		func: Callable[[str], None] = print
		) -> None:
	"""Perform func for each line of a hexdump of buf.

	Exists as a means to temporarily dump binary data to stdout to assist with
	debugging stubborn code.  For other uses, it probably makes more sense to
	call hexdump_gen() directly.  Do use this function for other purposes, set
	func to something other than its default of the print function.  func()
	will be passed each line of output as generated by hexdump_gen().  This is
	memory-efficient for sizable buffers, but it is not fast as func is
	effectively called for each sixteen bytes of buf.

	See hexdump_gen for a more information about the other arguments to this
	function and the format of the strings func will receive.

	Args:
		buf: the bytes-like object to be hexdumped
		verbose: True if we should not compress duplicate output
		mask_high: True high bit should be stripped for ASCII printability
		func: The function to be called with each line from hexdump_gen
	"""
	for line in hexdump_gen(buf, verbose, mask_high):
		func(line)

gen_hexdump = hexdump_gen  # TODO(tjcarter): Fix blocksfree.buffer and remove
