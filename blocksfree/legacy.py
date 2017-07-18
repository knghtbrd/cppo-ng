#!/usr/bin/env python3
# vim: set tabstop=4 shiftwidth=4 noexpandtab filetype=python:

# Copyright (C) 2013-2016  Ivan Drucker
# Copyright (C) 2017       T. Joseph Carter
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
#
#
# If interested, please see the file HISTORY.md for information about both the
# technical and licensing decisions that have gone into the rewriting of cppo.

"""cppo: Copy/catalog files from a ProDOS/DOS 3.3/ShrinkIt image/archive.

copy all files: cppo [options] imagefile target_directory
copy one file : cppo [options] imagefile /extract/path target_path
catalog image : cppo -cat [options] imagefile

options:
-shk: ShrinkIt archive as source (also auto-enabled by filename).
-ad : Netatalk-compatible AppleDouble metadata files and resource forks.
-e  : Nulib2-compatible filenames with type/auxtype and resource forks.
-uc : Copy GS/OS mixed case filenames as uppercase.
-pro: Adapt DOS 3.3 names to ProDOS and remove addr/len from file data.

/extract/path examples:
    /FULL/PRODOS/PATH (ProDOS image source)
    "MY FILENAME" (DOS 3.3 image source)
    Dir:SubDir:FileName (ShrinkIt archive source)

+ after a file name indicates a GS/OS or Mac OS extended (forked) file.
Wildcard matching (*) is not supported and images are not validated.
ShrinkIt support requires Nulib2. cppo requires Python 2.6+ or 3.0+."""

# cppo by Ivan X, ivan@ivanx.com, ivanx.com/appleii

# Does anyone want to rewrite/refactor this? It works, but it's a mess.

import sys
import os
import datetime
import shutil
import errno
import uuid  # for temp directory
import subprocess
#import tempfile  # not used, but should be for temp directory?
import struct
from binascii import a2b_hex, b2a_hex

from . import diskimg
from .logging import LOG

class Globals:
	pass

g = Globals()

g.image_data = b''
g.out_data = bytearray(b'')
g.ex_data = None

g.activeDirBlock = None
g.activeFileName = None
g.activeFileSize = None
g.activeFileBytesCopied = 0
g.resourceFork = 0
g.shk_hasrf = False

g.PDOSPATH = []
g.PDOSPATH_INDEX = 0
g.PDOSPATH_SEGMENT = None
g.DIRPATH = ""

g.target_name = None
g.target_dir = ""
g.appledouble_dir = None
g.image_file = None
g.extract_file = None

# runtime options
g.use_appledouble = False   # -ad  (AppleDouble headers + resource forks)
g.use_extended = False      # -e   (extended filenames + resource forks)
g.catalog_only = False      # -cat (catalog only, no extract)
g.casefold_upper = False    # -uc  (GS/OS mixed case filenames extract as uppercase)
g.src_shk = False           # -shk (ShrinkIt archive source)
g.prodos_names = False      # -pro (adapt DOS 3.3 names to ProDOS)
g.afpsync_msg = True        # -s   (sets False to suppress afpsync message at end)
g.extract_in_place = False  # -n   (don't create parent dir for SHK, extract files in place)
g.dos33 = False             #      (DOS 3.3 image source, selected automatically)

# functions

def pack_u24be(buf: bytearray, offset: int, val: int):
	lo16 = val & 0xffff
	hi8 = (val >> 16) & 0xff
	struct.pack_into('>BH', buf, offset, hi8, lo16)

def pack_u32be(buf: bytearray, offset: int, val: int):
	# Currently unused, will be needed for resource fork dates later
	struct.pack_into('>L', buf, offset, val)

def unpack_u16le(buf: bytes, offset: int = 0) -> int:
	return struct.unpack_from('<H', buf, offset)[0]

def unpack_u24le(buf: bytes, offset: int = 0) -> int:
	lo16, hi8 = struct.unpack_from('<HB', buf, offset)
	return lo16 | (hi8 << 16)


def date_prodos_to_unix(prodos_date: bytes) -> int:
	"""Returns a UNIX timestamp given a raw ProDOS date"""
	"""The ProDOS date consists of two 16-bit words stored little-
	endian.  We receive them as raw bytes with this layout:

	  mmmddddd yyyyyyym 00MMMMMM 000HHHHH

	where:

	  year     yyyyyyy
	  month    m mmm
	  day      ddddd
	  hour     HHHHH
	  minute   MMMMMM

	Some notes about that:

	- The high bit of the month is the low bit of prodos_date[1], the rest of
	  lower bits are found in prodos_date[0].
	- The two-digit year treats 40-99 as being 19xx, else 20xx.
	- ProDOS has only minute-precision for its timestamps.  Data regarding
	  seconds is lost.
	- ProDOS dates are naive in the sense they lack a timezone.  We (naively)
	  assume these timestamps are in local time.
	- The unused bits in the time fields are masked off, just in case they're
	  ever NOT zero.  2040 is coming.
	"""
	try:
		year = (prodos_date[1] & 0xfe)>>1
		year += 1900 if year >= 40 else 2000
		month = ((prodos_date[1] & 0x01)<<4) | ((prodos_date[0] & 0xe0)>>5)
		day = prodos_date[0] & 0x1f
		hour = prodos_date[3] & 0x1f
		minute = prodos_date[2] & 0x3f

		return int(datetime.datetime(year, month, day,
			hour, minute).timestamp())
	except:
		# <NO DATE> is always an option
		return None

APPLE_EPOCH_OFFSET = 946684800
"""The number of seconds between 1970-01-01 amd 2000-01-01"""
# $ date --date="2000-01-01 00:00:00 GMT" +%s
# 946684800

def date_unix_to_appledouble(unix_date):
	""" convert UNIX date to Apple epoch (2000-01-01) """
	# input: seconds since Unix epoch (1-Jan-1970 00:00:00 GMT)
	# output: seconds since Netatalk epoch (1-Jan-2000 00:00:00 GMT),
	#         in 4 bytes
	adDate = int(unix_date - APPLE_EPOCH_OFFSET)
	# Think: "UNIX dates have 30 years too many seconds to be Apple dates,
	# so we need to subtract 30 years' worth of seconds."
	if adDate < 0:
		adDate += 1<<32  # to get negative hex number
	return adDate.to_bytes(4, 'big')

# cppo support functions:
# arg1: directory block or [T,S] containing file entry, or shk file dir path
# arg2: file index in overall directory (if applicable), or shk file name

# returns byte position in disk image file
def getStartPos(arg1, arg2):
	if g.dos33:
		return (ts(arg1) + (35 * (arg2 % 7)) + 11)
	else:  # ProDOS
		return ( (arg1 * 512)
				+ (39 * ((arg2 + (arg2 > 11)) % 13))
				+ (4 if arg2 > 11 else 43) )

def getStorageType(arg1, arg2):
	start = getStartPos(arg1, arg2)
	firstByte = g.image_data[start]
	return (int(firstByte != 255)*2 if g.dos33 else (firstByte//16))

def getFileName(arg1, arg2):
	start = getStartPos(arg1, arg2)
	if g.dos33:
		fileNameLo = bytearray()
		fileNameHi = g.image_data[sli(start+3, 30)]
		for b in fileNameHi:
			fileNameLo.append(b & 0x7f)
		fileName = bytes(fileNameLo).rstrip()
	else:  # ProDOS
		firstByte = g.image_data[start]
		entryType = firstByte//16
		nameLength = firstByte - entryType*16
		fileName = g.image_data[sli(start+1, nameLength)]
		caseMask = getCaseMask(arg1, arg2)
		if caseMask and not g.casefold_upper:
			fileName = bytearray(fileName)
			for i in range(0, len(fileName)):
				if caseMask[i] == "1":
					fileName[i:i+1] = fileName[i:i+1].lower()
			fileName = bytes(fileName)
	return fileName

def getCaseMask(arg1, arg2):
	start = getStartPos(arg1, arg2)
	caseMaskDec = unpack_u16le(g.image_data, start + 28)
	if caseMaskDec < 32768:
		return None
	else:
		return format(caseMaskDec - 32768, '015b')

def getFileType(arg1, arg2):
	if g.src_shk:
		return arg2.split('#')[1][0:2]
	start = getStartPos(arg1, arg2)
	if g.dos33:
		d33fileType = g.image_data[start+2]
		if (d33fileType & 127) == 4:
			return '06'  # BIN
		elif (d33fileType & 127) == 1:
			return 'FA'  # INT
		elif (d33fileType & 127) == 2:
			return 'FC'  # BAS
		else:
			return '04'  # TXT or other
	else:  # ProDOS
		return b2a_hex(g.image_data[start+16:start+17]).decode()

def getAuxType(arg1, arg2):
	if g.src_shk:
		return arg2.split('#')[1][2:6]
	start = getStartPos(arg1, arg2)
	if g.dos33:
		fileType = getFileType(arg1, arg2)
		if fileType == '06':  # BIN (B)
			# file address is in first two bytes of file data
			fileTSlist = list(g.image_data[sli(start+0,2)])
			fileStart = list(g.image_data[sli(ts(fileTSlist)+12,2)])
			return (
					b2a_hex(g.image_data[sli(ts(fileStart)+1,1)]) +
					b2a_hex(g.image_data[sli(ts(fileStart),1)])
					).decode()
		elif fileType == 'FC':  # BAS (A)
			return '0801'
		elif fileType == 'FA':  # INT (I)
			return '9600'
		else:  # TXT (T) or other
			return '0000'
	else:  # ProDOS
		return format(unpack_u16le(g.image_data, start + 31), '04x')

def getKeyPointer(arg1, arg2):
	start = getStartPos(arg1, arg2)
	if g.dos33:
		return list(g.image_data[sli(start,2)])
	else:  # ProDOS
		return unpack_u16le(g.image_data, start + 17)

def getFileLength(arg1, arg2):
	start = getStartPos(arg1, arg2)
	if g.dos33:
		fileType = getFileType(arg1, arg2)
		fileTSlist = list(g.image_data[sli(start,2)])
		fileStart = list(g.image_data[sli(ts(fileTSlist)+12,2)])
		if fileType == '06':  # BIN (B)
			# file length is in second two bytes of file data
			file_size = unpack_u16le(g.image_data, ts(fileStart) + 2) + 4
		elif fileType == 'FC' or fileType == 'FA':  # BAS (A) or INT (I)
			# file length is in first two bytes of file data
			file_size = unpack_u16le(g.image_data, ts(fileStart)) + 2
		else:  # TXT (T) or other
			# sadly, we have to walk the whole file
			# length is determined by sectors in TSlist, minus wherever
			# anything after the first zero in the last sector
			file_size = 0
			lastTSpair = None
			prevTSpair = [0,0]
			nextTSlistSector = fileTSlist
			endFound = False
			while not endFound:
				pos = ts(nextTSlistSector)
				for tsPos in range(12, 256, 2):
					cur_ts_pair = list(g.image_data[sli(pos+tsPos,2)])
					if ts(cur_ts_pair) != 0:
						file_size += 256
						prevTSpair = cur_ts_pair
					else:
						lastTSpair = prevTSpair
						endFound = True
						break
				if not lastTSpair:
					nextTSlistSector = list(g.image_data[sli(pos+1,2)])
					if nextTSlistSector[0]+nextTSlistSector[1] == 0:
						lastTSpair = prevTSpair
						endFound = True
						break
			file_size -= 256
			pos = ts(prevTSpair)
			# now find out where the file really ends by finding the last 00
			for offset in range(255, -1, -1):
				#print("pos: {#b}".format(pos))
				if g.image_data[pos+offset] != 0:
					file_size += (offset + 1)
					break
	else:  # ProDOS
		file_size = unpack_u24le(g.image_data, start + 21)

	return file_size

def getCreationDate(arg1, arg2):
	#outputs prodos creation date/time as Unix time
	#  (seconds since Jan 1 1970 GMT)
	#or None if there is none
	if g.src_shk:
		return None
	elif g.dos33:
		return None
	else:  # ProDOS
		start = getStartPos(arg1, arg2)
		return date_prodos_to_unix(g.image_data[start+24:start+28])

def getModifiedDate(arg1, arg2):
	#outputs prodos modified date/time as Unix time
	#  (seconds since Jan 1 1970 GMT)
	#or None if there is none

	if g.src_shk:
		return int(os.path.getmtime(os.path.join(arg1, arg2)))
	elif g.dos33:
		return None
	else:  # ProDOS
		start = getStartPos(arg1, arg2)
		return date_prodos_to_unix(g.image_data[start+33:start+27])

def getVolumeName():
	return getWorkingDirName(2)

def getWorkingDirName(arg1, arg2=None):
	# arg1:block, arg2:casemask (optional)
	start = arg1 * 512
	firstByte = g.image_data[start+4]
	entryType = firstByte//16
	nameLength = firstByte - entryType*16
	workingDirName = g.image_data[sli(start+5, nameLength)]
	if entryType == 15:  # volume directory, get casemask from header
		caseMaskDec = unpack_u16le(g.image_data, start + 26)
		if caseMaskDec < 32768:
			caseMask = None
		else:
			caseMask = format(caseMaskDec - 32768,'015b')
	else:  # subdirectory, get casemask from arg2 (not available in header)
		caseMask = arg2
	if caseMask and not g.casefold_upper:
		workingDirName = bytearray(workingDirName)
		for i in range(0, len(workingDirName)):
			if caseMask[i] == "1":
				workingDirName[i:i+1] = workingDirName[i:i+1].lower()
		workingDirName = bytes(workingDirName)
	return workingDirName

def getDirEntryCount(arg1):
	if g.dos33:
		entryCount = 0
		nextSector = arg1
		while True:
			top = ts(nextSector)
			pos = top+11
			for e in range(0, 7):
				if g.image_data[pos] == 0:
					return entryCount  # no more file entries
				else:
					if g.image_data[pos] != 255:
						entryCount += 1  # increment if not deleted file
					pos += 35
			nextSector = list(g.image_data[sli(top+1,2)])
			if nextSector == [0,0]:  # no more catalog sectors
				return entryCount
	else:  # ProDOS
		start = arg1 * 512
		return unpack_u16le(g.image_data, start + 37)

def getDirNextChunkPointer(arg1):
	if g.dos33:
		start = ts(arg1)
		return list(g.image_data[sli(start+1,2)])
	else:  # ProDOS
		start = arg1 * 512
		return unpack_u16le(g.image_data, start + 2)

def toProdosName(name):
	i = 0
	if name[0] == '.':  # eliminate leading period
		name = name[1:]
	for c in name:
		if c != '.' and not c.isalnum():
			name = name[:i] + '.' + name[i+1:]
		i += 1
	name = name[:15]
	return name

def ts(track, sector=None):
	# returns offset; track and sector can be dec, or hex-ustr
	#   can also supply as [t,s] for convenience
	if sector == None:
		(track, sector) = track
	if isinstance(track, str):  # hex-ustr
		track = int(track, 16)
	if isinstance(sector, str):  # hex-ustr
		sector = int(sector, 16)
	return track*16*256 + sector*256

def sli(start, length=1, ext=None):
	"""return a slice object from an offset and length"""
	return slice(start, start + length, ext)

# --- main logic functions

def copyFile(arg1, arg2):
	#arg1/arg2:
	#  ProDOS  : directory block  / file index in overall directory
	#  DOS 3.3 : [track, sector]  / file index in overall VTOC
	#  ShrinkIt: directory path   / file name
	# copies file or dfork to g.out_data, rfork if any to g.ex_data
	g.activeFileBytesCopied = 0

	if g.src_shk:
		with open(os.path.join(arg1, arg2), 'rb') as infile:
			g.out_data += infile.read()
		if g.shk_hasrf:
			print("    [data fork]")
			if g.use_extended or g.use_appledouble:
				print("    [resource fork]")
				if g.ex_data == None:
					g.ex_data = bytearray(b'')
				with open(os.path.join(arg1, (arg2 + "r")), 'rb') as infile:
					g.ex_data += infile.read()
	else:  # ProDOS or DOS 3.3
		storageType = getStorageType(arg1, arg2)
		keyPointer = getKeyPointer(arg1, arg2)
		fileLen = getFileLength(arg1, arg2)
		if storageType == 1:  #seedling
			copyBlock(keyPointer, fileLen)
		elif storageType == 2:  #sapling
			processIndexBlock(keyPointer)
		elif storageType == 3:  #tree
			processMasterIndexBlock(keyPointer)
		elif storageType == 5:  #extended (forked)
			processForkedFile(keyPointer)
	if g.prodos_names:
		# remove address/length data from DOS 3.3 file data if ProDOS target
		if getFileType(arg1, arg2) == '06':
			g.out_data = g.out_data[4:]
		elif (getFileType(arg1, arg2) == 'FA'
				or getFileType(arg1, arg2) == 'FC'):
			g.out_data = g.out_data[2:]

def copyBlock(arg1, arg2):
	#arg1: block number or [t,s] to copy
	#arg2: bytes to write (should be 256 (DOS 3.3) or 512 (ProDOS),
	#      unless final block with less)
	#print(arg1 + " " + arg2 + " " + g.activeFileBytesCopied)
	if arg1 == 0:
		outBytes = bytes(arg2)
	else:
		outBytes = g.image_data[sli(ts(arg1) if g.dos33 else arg1*512, arg2)]
	if g.resourceFork > 0:
		if g.use_appledouble or g.use_extended:
			offset = (741 if g.use_appledouble else 0)
			if g.ex_data == None:
				g.ex_data = bytearray(b'')
			g.ex_data[
					g.activeFileBytesCopied + offset
					: g.activeFileBytesCopied + offset + arg2
					] = outBytes
	else:
		g.out_data[
				g.activeFileBytesCopied
				: g.activeFileBytesCopied + arg2
				] = outBytes
	g.activeFileBytesCopied += arg2

def process_dir(arg1, arg2=None, arg3=None, arg4=None, arg5=None):
	# arg1: ProDOS directory block, or DOS 3.3 [track,sector]
	# for key block (with directory header):
	#   arg2: casemask (optional), arg3:None, arg4:None, arg5:None
	# for secondary directory blocks (non-key block):
	#   arg2/3/4/5: for non-key chunks: entryCount, entry#,
	#   workingDirName, processedEntryCount

	entryCount = None
	e = None
	pe = None
	workingDirName = None

	if arg3:
		entryCount = arg2
		e = arg3
		workingDirName = arg4
		pe = arg5
	else:
		e = 0
		pe = 0
		entryCount = getDirEntryCount(arg1)
		if not g.dos33:
			workingDirName = getWorkingDirName(arg1, arg2).decode("L1")
			g.DIRPATH = g.DIRPATH + "/" + workingDirName
			if g.PDOSPATH_INDEX:
				if g.PDOSPATH_INDEX == 1:
					if ("/" + g.PDOSPATH_SEGMENT.lower()) != g.DIRPATH.lower():
						print("ProDOS volume name does not match disk image.")
						quit_now(2)
					else:
						g.PDOSPATH_INDEX += 1
						g.PDOSPATH_SEGMENT = g.PDOSPATH[g.PDOSPATH_INDEX]
			#else: print(g.DIRPATH)
	while pe < entryCount:
		if getStorageType(arg1, e) > 0:
			#print(pe, e, entryCount)
			processEntry(arg1, e)
			pe += 1
		e += 1
		if not (e + (0 if g.dos33 else (e>11)) ) % (7 if g.dos33 else 13):
			process_dir(
					getDirNextChunkPointer(arg1), entryCount, e,
					workingDirName, pe)
			break

def processEntry(arg1, arg2):
	# arg1=block number, [t,s] if g.dos33=True, or subdir name if g.src_shk=1
	# arg2=index number of entry in directory, or file name if g.src_shk=1

	#print(getFileName(arg1, arg2), getStorageType(arg1, arg2),
	#		getFileType(arg1, arg2), getKeyPointer(arg1, arg2),
	#		getFileLength(arg1, arg2), getAuxType(arg1, arg2),
	#		getCreationDate(arg1, arg2), getModifiedDate(arg1, arg2))

	eTargetName = None
	g.ex_data = None
	g.out_data = bytearray(b'')
	if g.src_shk:  # ShrinkIt archive
		g.activeFileName = (arg2 if g.use_extended else arg2.split('#')[0])
		if g.casefold_upper:
			g.activeFileName = g.activeFileName.upper()
		origFileName = g.activeFileName
	else:  # ProDOS or DOS 3.3 image
		g.activeFileName = getFileName(arg1 ,arg2).decode("L1")
		origFileName = g.activeFileName
		if g.prodos_names:
			g.activeFileName = toProdosName(g.activeFileName)
		g.activeFileSize = getFileLength(arg1, arg2)

	if (not g.PDOSPATH_INDEX or
		g.activeFileName.upper() == g.PDOSPATH_SEGMENT.upper()):

		# if ProDOS directory, not file
		if not g.src_shk and getStorageType(arg1, arg2) == 13:
			if not g.PDOSPATH_INDEX:
				g.target_dir = g.target_dir + "/" + g.activeFileName
			g.appledouble_dir = g.target_dir + "/.AppleDouble"
			if not g.catalog_only or os.path.isdir(g.target_dir):
				makedirs(g.target_dir)
			if (not g.catalog_only and g.use_appledouble
					and not os.path.isdir(g.appledouble_dir)):
				makedirs(g.appledouble_dir)
			if g.PDOSPATH_SEGMENT:
				g.PDOSPATH_INDEX += 1
				g.PDOSPATH_SEGMENT = g.PDOSPATH[g.PDOSPATH_INDEX]
			process_dir(getKeyPointer(arg1, arg2), getCaseMask(arg1, arg2))
			g.DIRPATH = g.DIRPATH.rsplit("/", 1)[0]
			if not g.PDOSPATH_INDEX:
				g.target_dir = g.target_dir.rsplit("/", 1)[0]
			g.appledouble_dir = g.target_dir + "/.AppleDouble"
		else:  # ProDOS or DOS 3.3 file either from image or ShrinkIt archive
			dirPrint = ""
			if g.DIRPATH:
				dirPrint = g.DIRPATH + "/"
			else:
				if g.src_shk:
					if "/".join(dirName.split('/')[3:]):
						dirPrint = ("/".join(dirName.split('/')[3:]) + "/")
			if (not g.extract_file or (
						os.path.basename(g.extract_file.lower())
						== origFileName.split('#')[0].lower())):
				filePrint = g.activeFileName.split("#")[0]
				print(
						dirPrint + filePrint
						+ ("+" if (g.shk_hasrf
							or (not g.src_shk
								and getStorageType(arg1, arg2) == 5))
							else "")
						+ ((" [" + origFileName + "] ")
							if (g.prodos_names
								and origFileName != g.activeFileName)
							else ""))
				if g.catalog_only:
					return
				if not g.target_name:
					g.target_name = g.activeFileName
				if g.use_extended:
					if g.src_shk:
						eTargetName = arg2
					else:  # ProDOS image
						eTargetName = (g.target_name + "#"
								+ getFileType(arg1, arg2).lower()
								+ getAuxType(arg1, arg2).lower())
				# touch(g.target_dir + "/" + g.target_name)
				if g.use_appledouble:
					makeADfile()
				copyFile(arg1, arg2)
				saveName = (g.target_dir + "/"
						+ (eTargetName if eTargetName else g.target_name))
				save_file(saveName, g.out_data)
				d_created = getCreationDate(arg1, arg2)
				d_modified = getModifiedDate(arg1, arg2)
				if not d_modified:
					d_modified = (d_created
							or int(datetime.datetime.today().timestamp()))
				if not d_created:
					d_created = d_modified
				if g.use_appledouble:  # AppleDouble
					# set dates
					ADfile_path = g.appledouble_dir + "/" + g.target_name
					g.ex_data[637:641] = date_unix_to_appledouble(d_created)
					g.ex_data[641:645] = date_unix_to_appledouble(d_modified)
					g.ex_data[645] = 0x80
					g.ex_data[649] = 0x80
					#set type/creator
					g.ex_data[653] = ord('p')
					g.ex_data[654:657] = bytes.fromhex(
							getFileType(arg1, arg2)
							+ getAuxType(arg1, arg2))
					g.ex_data[657:661] = b'pdos'
					save_file(ADfile_path, g.ex_data)
				touch(saveName, d_modified)
				if g.use_extended:  # extended name from ProDOS image
					if g.ex_data:
						save_file((saveName + "r"), g.ex_data)
						touch((saveName + "r"), d_modified)
				if (g.PDOSPATH_SEGMENT
						or (g.extract_file
							and (g.extract_file.lower()
								== origFileName.lower()))):
					quit_now(0)
				g.target_name = None
	#else print(g.activeFileName + " doesn't match " + g.PDOSPATH_SEGMENT)

def processForkedFile(arg1):
	# finder info except type/creator
	fInfoA_entryType = g.image_data[9]
	fInfoB_entryType = g.image_data[27]
	if fInfoA_entryType == 1:
		g.image_data[661:669], g.image_data[18:26]
	elif fInfoA_entryType == 2:
		g.image_data[669:685], g.image_data[10:26]
	if fInfoB_entryType == 1:
		g.image_data[661:669], g.image_data[36:44]
	elif fInfoB_entryType == 2:
		g.image_data[669:685], g.image_data[28:44]

	for f in (0, 256):
		g.resourceFork = f
		g.activeFileBytesCopied = 0
		forkStart = arg1 * 512  # start of Forked File key block
		#print("--" + forkStart)
		forkStorageType = g.image_data[forkStart+f]
		forkKeyPointer = unpack_u16le(g.image_data, forkStart + f + 1)
		forkFileLen = unpack_u24le(g.image_data, forkStart + f + 5)
		g.activeFileSize = forkFileLen
		if g.resourceFork > 0:
			rsrcForkLen = unpack_u24le(g.image_data, forkStart + f + 5)
			#print(">>>", rsrcForkLen)
			if g.use_appledouble or g.use_extended:
				print("    [resource fork]")
			if g.use_appledouble:
				pack_u24be(g.ex_data, 35, rsrcForkLen)
		else:
			print("    [data fork]")
		if forkStorageType == 1:  #seedling
			copyBlock(forkKeyPointer, forkFileLen)
		elif forkStorageType == 2:  #sapling
			processIndexBlock(forkKeyPointer)
		elif forkStorageType == 3:  #tree
			processMasterIndexBlock(forkKeyPointer)
	#print()
	g.resourceFork = 0

def processMasterIndexBlock(arg1):
	processIndexBlock(arg1, True)

def processIndexBlock(arg1, arg2=False):
	#arg1: indexBlock, or [t,s] of track/sector list
	#arg2: if True, it's a Master Index Block
	pos = 12 if g.dos33 else 0
	bytesRemaining = g.activeFileSize
	while g.activeFileBytesCopied < g.activeFileSize:
		if g.dos33:
			targetTS = list(g.image_data[sli(ts(arg1)+pos,2)])
			#print('{02x} {02x}'.format(targetTS[0], targetTS[1]))
			bytesRemaining = (g.activeFileSize - g.activeFileBytesCopied)
			bs = (bytesRemaining if bytesRemaining < 256 else 256)
			copyBlock(targetTS, bs)
			pos += 2
			if pos > 255:
				# continue with next T/S list sector
				processIndexBlock(list(g.image_data[sli(ts(arg1)+1,2)]))
		else:  # ProDOS
			# Note these are not consecutive bytes
			targetBlock = (g.image_data[arg1*512+pos] +
					g.image_data[arg1*512+pos+256]*256)
			if arg2:
				processIndexBlock(targetBlock)
			else:
				bytesRemaining = (g.activeFileSize - g.activeFileBytesCopied)
				bs = bytesRemaining if bytesRemaining < 512 else 512
				copyBlock(targetBlock, bs)
			pos += 1
			if pos > 255:
				break  # go to next entry in Master Index Block (tree)

def makeADfile():
	if not g.use_appledouble:
		return
	touch(g.appledouble_dir + "/" + g.target_name)
	g.ex_data = bytearray(741)
	# ADv2 header
	g.ex_data[sli(0x00,8)] = a2b_hex("0005160700020000")
	# number of entries
	g.ex_data[sli(0x18,2)] = a2b_hex("000D")
	# Resource Fork
	g.ex_data[sli(0x1a,12)] = a2b_hex("00000002000002E500000000")
	# Real Name
	g.ex_data[sli(0x26,12)] = a2b_hex("00000003000000B600000000")
	# Comment
	g.ex_data[sli(0x32,12)] = a2b_hex("00000004000001B500000000")
	# Dates Info
	g.ex_data[sli(0x3e,12)] = a2b_hex("000000080000027D00000010")
	# Finder Info
	g.ex_data[sli(0x4a,12)] = a2b_hex("000000090000028D00000020")
	# ProDOS file info
	g.ex_data[sli(0x56,12)] = a2b_hex("0000000B000002C100000008")
	# AFP short name
	g.ex_data[sli(0x62,12)] = a2b_hex("0000000D000002B500000000")
	# AFP File Info
	g.ex_data[sli(0x6e,12)] = a2b_hex("0000000E000002B100000004")
	# AFP Directory ID
	g.ex_data[sli(0x7a,12)] = a2b_hex("0000000F000002AD00000004")
	# dbd (second time) will create DEV, INO, SYN, SV~

def quit_now(exitcode=0):
	if (exitcode == 0 and g.afpsync_msg and
			g.use_appledouble and os.path.isdir("/usr/local/etc/netatalk")):
		print(
				"File(s) have been copied to the target directory. "
				"If the directory\n"
				"is shared by Netatalk, please type 'afpsync' now.")
	if g.src_shk:  # clean up
		for file in os.listdir('/tmp'):
			if file.startswith("cppo-"):
				shutil.rmtree('/tmp' + "/" + file)
	sys.exit(exitcode)

def to_sys_name(name):
	if os.name == 'nt':
		if name[-1] == '.':
			name += '-'
		name = name.replace('./', '.-/')
	return name

#---- IvanX general purpose functions ----#

def touch(file_path, modTime=None):
	# http://stackoverflow.com/questions/1158076/implement-touch-using-python
	#print(file_path)
	with open(to_sys_name(file_path), "ab"):
		os.utime(file_path, None if modTime is None else (modTime, modTime))

def mkdir(dirPath):
	try:
		os.mkdir(to_sys_name(dirPath))
	except FileExistsError:
		pass

def makedirs(dirPath):
	try:
		os.makedirs(to_sys_name(dirPath))
	except OSError as e:
		if e.errno != errno.EEXIST:
			raise

def load_file(file_path):
	with open(to_sys_name(file_path), "rb") as image_handle:
		return image_handle.read()

def save_file(file_path, fileData):
	with open(to_sys_name(file_path), "wb") as image_handle:
		image_handle.write(fileData)

def dopo_swap(image_data):
	# for each track,
	# read each sector in the right sequence to make
	# valid ProDOS blocks (sector pairs)
	dopo = bytearray(143360)
	for t in range(0, 35):
		for s in range(16):
			src = ts(t,s)
			dst = ts(t,s if s in (0,15) else 15-s)
			dopo[dst:dst+256] = image_data[src:src+256]
	return bytes(dopo)

#---- end IvanX general purpose functions ----#

def run_cppo():
	try:
		disk = diskimg.Disk(g.image_file)
	except IOError as e:
		LOG.critical(e)
		quit_now(2)

	# automatically set ShrinkIt mode if extension suggests it
	if g.src_shk or disk.ext in ('.shk', '.sdk', '.bxy'):
		if os.name == "nt":
			print("ShrinkIt archives cannot be extracted on Windows.")
			quit_now(2)
		else:
			try:
				with open(os.devnull, "w") as fnull:
					subprocess.call("nulib2", stdout = fnull, stderr = fnull)
				g.src_shk = True
			except Exception:
				print(
						"Nulib2 is not available; not expanding "
						"ShrinkIt archive.")
				quit_now(2)

	if g.src_shk:
		g.prodos_names = False
		unshkdir = ('/tmp' + "/cppo-" + str(uuid.uuid4()))
		makedirs(unshkdir)
		result = os.system(
				"/bin/bash -c 'cd " + unshkdir + "; "
				+ "result=$(nulib2 -xse " + os.path.abspath(disk.pathname)
				+ ((" " + g.extract_file.replace('/', ':'))
					if g.extract_file else "") + " 2> /dev/null); "
				+ "if [[ $result == \"Failed.\" ]]; then exit 3; "
				+ "else if grep -q \"no records match\" <<< \"$result\""
				+ " > /dev/null; then exit 2; else exit 0; fi; fi'")
		if result == 512:
			print(
					"File not found in ShrinkIt archive. "
					"Try cppo -cat to get the path,\n"
					"  and omit any leading slash or colon.")
			quit_now(1)
		elif result != 0:
			print(
					"ShrinkIt archive is invalid, "
					"or some other problem happened.")
			quit_now(1)
		if g.extract_file:
			g.extract_file = g.extract_file.replace(':', '/')
			extractPath = (unshkdir + "/" + g.extract_file)
			extractPathDir = os.path.dirname(extractPath)
			# move the extracted file to the root
			newunshkdir = ('/tmp' + "/cppo-" + str(uuid.uuid4()))
			makedirs(newunshkdir)
			for filename in os.listdir(extractPathDir):
				shutil.move(extractPathDir + "/" + filename, newunshkdir)
			shutil.rmtree(unshkdir)
			unshkdir = newunshkdir

		fileNames = [name for name in sorted(os.listdir(unshkdir))
					 if not name.startswith(".")]
		if g.extract_in_place:  # extract in place from "-n"
			curDir = True
		elif (len(fileNames) == 1 and
				os.path.isdir(unshkdir + "/" + fileNames[0])):
			curDir = True  # only one folder at top level, so extract in place
			volumeName = toProdosName(fileNames[0])
		elif (len(fileNames) == 1 and  # disk image, so extract in place
				fileNames[0][-1:] == "i"):
			curDir = True
			volumeName = toProdosName(fileNames[0].split("#")[0])
		else:  # extract in folder based on disk image name
			curDir = False
			volumeName = toProdosName(os.path.basename(disk.pathname))
			if volumeName[-4:].lower() in ('.shk', '.sdk', '.bxy'):
				volumeName = volumeName[:-4]
		if not g.catalog_only and not curDir and not g.extract_file:
			print("Extracting into " + volumeName)
		# recursively process unshrunk archive hierarchy
		for dirName, subdirList, fileList in os.walk(unshkdir):
			subdirList.sort()
			if not g.catalog_only:
				g.target_dir = (
						g.target_dir
						+ ("" if curDir else ("/" + volumeName))
						+ ("/" if dirName.count('/') > 2 else "")
						+ ("/".join(dirName.split('/')[3:])))  # chop tempdir
				if g.casefold_upper:
					g.target_dir = g.target_dir.upper()
				g.appledouble_dir = (g.target_dir + "/.AppleDouble")
				makedirs(g.target_dir)
				if g.use_appledouble:
					makedirs(g.appledouble_dir)
			for fname in sorted(fileList):
				if fname[-1:] == "i":
					# disk image; rename to include suffix and correct
					# type/auxtype
					imagePath = os.path.join(dirName, fname).split("#")[0]
					new_name = (
							imagePath
							+ ("" if os.path.splitext(imagePath.lower())[1]
								in ('.po', '.hdv') else ".PO") + "#e00005")
					os.rename(os.path.join(dirName, fname), new_name)
					fname = os.path.basename(new_name)
				g.shk_hasrf = False
				rfork = False
				if (fname[-1:] == "r"
						and os.path.isfile(os.path.join(dirName, fname[:-1]))):
					rfork = True
				elif (os.path.isfile(os.path.join(dirName, (fname + "r")))):
					g.shk_hasrf = True
				if not rfork:
					processEntry(dirName, fname)
		shutil.rmtree(unshkdir, True)
		quit_now(0)

	# end script if SHK

	g.image_data = load_file(disk.pathname)

	# detect if image is 2mg and remove 64-byte header if so
	if disk.ext in ('.2mg', '.2img'):
		g.image_data = g.image_data[64:]

	# handle 140k disk image
	if len(g.image_data) == 143360:
		LOG.debug("140k disk")
		prodos_disk = False
		fix_order = False
		# is it ProDOS?
		if g.image_data[sli(ts(0,0), 4)] == b'\x01\x38\xb0\x03':
			LOG.debug("detected ProDOS by boot block")
			if g.image_data[sli(ts(0,1)+3, 6)] == b'PRODOS':
				LOG.debug("order OK (PO)")
				prodos_disk = True
			elif g.image_data[sli(ts(0,14)+3, 6)] == b'PRODOS':
				LOG.debug("order needs fixing (DO)")
				prodos_disk = True
				fix_order = True
		# is it DOS 3.3?
		else:
			LOG.debug("it's not ProDOS")
			if g.image_data[ts(17,0)+3] == 3:
				vtocT, vtocS = g.image_data[sli(ts(17,0) + 1,2)]
				if vtocT < 35 and vtocS < 16:
					LOG.debug("it's DOS 3.3")
					g.dos33 = True
					# it's DOS 3.3; check sector order next
					if g.image_data[ts(17,14)+2] != 13:
						LOG.debug("order needs fixing (PO)")
						fix_order = True
					else:
						LOG.debug("order OK (DO)")
		# fall back on disk extension if weird boot block (e.g. AppleCommander)
		if not prodos_disk and not g.dos33:
			LOG.debug("format and ordering unknown, checking extension")
			if disk.ext in ('.dsk', '.do'):
				LOG.debug("extension indicates DO, changing to PO")
				fix_order = True
		if fix_order:
			LOG.debug("fixing order")
			g.image_data = dopo_swap(g.image_data)
			#print("saving fixed order file as outfile.dsk")
			#save_file("outfile.dsk", g.image_data)
			#print("saved")

		if not prodos_disk and not g.dos33:
			print("Warning: Unable to determine disk format, assuming ProDOS.")

	# enforce leading slash if ProDOS
	if (not g.src_shk and not g.dos33 and g.extract_file
			and (g.extract_file[0] not in ('/', ':'))):
		LOG.critical("Cannot extract {} from {}: "
				"ProDOS volume name required".format(
					g.extract_file, g.image_file))
		quit_now(2)

	if g.dos33:
		disk_name = (disk.diskname if disk.ext in ('.dsk', '.do', '.po')
				else disk.filename)
		if g.prodos_names:
			disk_name = toProdosName(disk_name)
		if not g.catalog_only:
			print(g.target_dir)
			g.target_dir = (g.extract_file if g.extract_file
					else (g.target_dir + "/" + disk_name))
			g.appledouble_dir = (g.target_dir + "/.AppleDouble")
			makedirs(g.target_dir)
			if g.use_appledouble:
				makedirs(g.appledouble_dir)
			if not g.extract_file:
				print("Extracting into " + disk_name)
		process_dir(list(g.image_data[sli(ts(17,0)+1,2)]))
		if g.extract_file:
			print("ProDOS file not found within image file.")
		quit_now(0)

	# below: ProDOS

	g.activeDirBlock = 0
	g.activeFileName = ""
	g.activeFileSize = 0
	g.activeFileBytesCopied = 0
	g.resourceFork = 0
	g.PDOSPATH_INDEX = 0
	g.prodos_names = False

	if g.extract_file:
		g.PDOSPATH = g.extract_file.replace(':', '/').split('/')
		g.extract_file = None
		if not g.PDOSPATH[0]:
			g.PDOSPATH_INDEX += 1
		g.PDOSPATH_SEGMENT = g.PDOSPATH[g.PDOSPATH_INDEX]
		g.appledouble_dir = (g.target_dir + "/.AppleDouble")
		if g.use_appledouble and not os.path.isdir(g.appledouble_dir):
			mkdir(g.appledouble_dir)
		process_dir(2)
		print("ProDOS file not found within image file.")
		quit_now(2)
	else:
		if not g.catalog_only:
			g.target_dir = (g.target_dir + "/" + getVolumeName().decode())
			g.appledouble_dir = (g.target_dir + "/.AppleDouble")
			if not os.path.isdir(g.target_dir):
				makedirs(g.target_dir)
			if g.use_appledouble and not os.path.isdir(g.appledouble_dir):
				makedirs(g.appledouble_dir)
		process_dir(2)
		quit_now(0)
