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
Util functions

This module serves as a catch-all generally for functions that don't seem to
belong somewhere else.
"""

from typing import Callable, Iterator, Sequence

def seqsplit(seq: Sequence, num: int) -> Iterator[Sequence]:
	"""Returns a generator that yields num-sized slices of seq"""
	for i in range(0, len(seq), num):
		yield seq[i:i + num]

def hexchars(line):
	"""Return canonical-format hex values of sixteen bytes"""
	vals = [format(b, '02x') for b in line]
	return '  '.join(' '.join(part) for part in seqsplit(vals, 8))

def printables(line: bytes, mask_high: bool = False):
	"""Return ASCII printable string from bytes

	If mask_high is set, the high bit on a byte is ignored when testing it for
	printability.
	"""
	return ''.join(
			chr(c) if 0x20 <= c < 127 else '.' for c in [
				b & 0x7f if mask_high else b for b in line])


def gen_hexdump(
		buf: bytes,
		verbose: bool = False,
		mask_high: bool = False
		) -> Iterator[str]:
	"""Return an iterator of hexdump lines of a bytes object

	verbose=True outputs all data
	mask_high=True treats bytes as 7 bit for printability test

	Output is in "canonical" hex+ASCII format as produced by BSD hexdump(1)
	with the -C argument.  It should be very familiar to people who have used
	hexdumps before: 32 bit offset, space-delimited hex values of 16 bytes with
	an extra space in the middle, and character representations of those same
	bytes, either ASCII character if printable or dot (.) if nonprintable.  A
	final line contains total length.

	As with the unix command, output is empty on a zero-length byte object.
	"""
	buf = memoryview(buf)
	last = None
	outstar = True
	i = 0

	for i, line in enumerate(seqsplit(buf, 16)):
		if not verbose and line == last:
			if outstar:
				# Next line output will be if line != last
				outstar = False
				yield '*'
		else:
			# Set up for next line
			last, outstar = line, True
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
	"""Pass each line of a hexdump of buf to func (print by default)"""
	for line in gen_hexdump(buf, verbose, mask_high):
		func(line)
