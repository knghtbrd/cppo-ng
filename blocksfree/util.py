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

from typing import Sequence, Iterator

def seqsplit(seq: Sequence, num: int) -> Iterator[Sequence]:
	"""Returns a generator that yields num-sized slices of seq"""
	for i in range(0, len(seq), num):
		yield seq[i:i + num]

def hexdump(
		buf: bytes,
		striphigh: bool = False,
		wordsize: int = 2,
		sep: str = ' ',
		sep2: str = '  '
		) -> str:
	"""return a multi-line debugging hexdump of a bytes object"""
	'''Format is configurable but defaults to that of xxd:

	########: #### #### #### ####  #### #### #### #### |................|

	wordsize is the number of bytes between separators
	sep is the separator between words
	sep2 is the midline separator
	striphigh considers 0xa0-0xfe to be printable ASCII (as on Apple II)
	'''
	out = []
	hlen = 32 + len(sep2) + (16//wordsize-2) * len(sep)
	wordlen = wordsize * 2
	for i, vals in enumerate(seqsplit(buf, 16)):
		hexs = sep2.join([
			sep.join(seqsplit(b2a_hex(x).decode(), wordlen))
			for x in seqsplit(vals,8)
			])
		if striphigh:
			vals = [x & 0x7f for x in vals]
		chars = ''.join([
			chr(x) if x >= 0x20 and x < 0x7f else '.'
			for x in vals
			])
		out.append('{i:07x}0: {hexs:{hlen}} |{chars}|'.format(**locals()))
	return '\n'.join(out)
