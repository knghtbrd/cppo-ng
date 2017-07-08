import os
import struct
from collections import namedtuple

# FIXME Move to_sys_name
from . import legacy

### NEW DISK CLASSES

TWOIMG_V1_UNPACK = (
		'<'              # use little-endian numbers
		'4s'             # magic string '2IMG'
		'4s'             # creator string
		'H'              # header length
		'H'              # 2mg version
		'L'              # image format
		'L'              # flags (we unpack it into "vol")
		'L'              # number of 512 blocks
		'L'              # image data offset
		'L'              # image data length
		'L'              # comment offset
		'L'              # comment length
		'L'              # creator private use offset
		'L'              # creator private use length
		'16x'            # reserved for future use
		)
TWOIMG_V1_ATTRS = (
		'magic', 'creator', 'hdr_len', 'version',
		'img_fmt', 'flags', 'num_blocks',
		'data_offset', 'data_len',
		'comment_offset', 'comment_len',
		'creator_offset', 'creator_len'
		)

TwoImgV1 = namedtuple('TwoImgV1', TWOIMG_V1_ATTRS)

class Disk:
	def __init__(self, name=None):
		if name is not None:
			self.pathname = name
			self.path, self.filename = os.path.split(name)
			self.diskname, self.ext = os.path.splitext(self.filename)
			self.ext = os.path.splitext(name)[1].lower()
			# FIXME: Handle compressed images?
			with open(legacy.to_sys_name(name), "rb") as f:
				self.image = f.read()

			if self.ext in ('.2mg', '.2img'):
				self._parse_2mg()

	def _parse_2mg(self):
		self.twoimg = None
		self.twoimg_comment = None
		self.twoimg_creator = None
		self.twoimg_locked = None
		hdr = TwoImgV1(*struct.unpack_from(TWOIMG_V1_UNPACK, self.image))
		if hdr.magic == b'2IMG':
			self._raw_twoimg = self.image[:hdr.hdr_len]
			if hdr.version == 1:
				if hdr.hdr_len == 64:
					# Extract comment (if it exists and is valid)
					if hdr.comment_offset and hdr.comment_len:
						self.twoimg_comment = self.image[
								hdr.comment_offset
								: hdr.comment_offset + hdr.comment_len]
						if len(self.twoimg_comment) != hdr.comment_len:
							log.warn('invalid 2mg comment: {} bytes '
									'(expected {} bytes)'.format(
										len(self.twoimg_comment),
										hdr.comment_len))
							self.twoimg_comment = None

					# Extract creator area (if it exists and is valid)
					if hdr.creator_offset and hdr.creator_len:
						self.twoimg_creator = self.image[
								hdr.creator_offset
								: hdr.creator_offset + hdr.creator_len]
						if len(self.twoimg_creator) != hdr.creator_len:
							log.warn('invalid 2mg creator: {} bytes '
									'(expected {} bytes)'.format(
										len(self.twoimg_creator),
										hdr.creator_len))
							self.twoimg_creator = None

					self.twoimg_locked = bool(hdr.flags & 0x80000000)

					self.twoimg = hdr
				else:
					log.warn('2mg header length: {} (expected 64 '
							'for version 1)'.format(hdr.hdr_len))
			else:
				log.warn('2mg version unsupported: {} (only support '
						'version 1)'.format(hdr.version))
		else:
			log.warn('2mg header not found: magic is {}'.format(hdr.magic))
			self._raw_twoimg = None

