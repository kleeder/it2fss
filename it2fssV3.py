#!/usr/bin/env python

"""
it2fss.py, version 0.3
----------------------

Python 3 only.

This script converts single-channel Impulse Tracker module into a FSS text file
for use with fsound.exe. Tempo Effect command is supported.
Kick and Snare Samples are supported!

To make white noise, use note value C-0 or everything else except C-1 to B-9.
Kick Sample is triggered with F-1 and Snare with F-9.

Make sure to use the Volume Column for every note. Volumes 0 to 15 are mapped
to 0 to F and everything above 15 is also mapped to F.

White Noise and Square Wave need to have a specific volume. That means, if you
leave the column empty for notes in this octaves, they are converted to "None"
and might cause errors.
Kick and Snare Samples don't have volume control, so feel free to leave the
volume column empty on that rows, it won't have any effects.

The only supported effect is Txx. Every other effect will be ignored!
Tempo Slides are not supported, all values <20 will just be interpreted as BPM<32.
Only use the effect along with a note, otherwise it will be ignored.

Version history
---------------

* 0.4: Added Tempo Change Support
* 0.3: Added Sample and Volume Support
* 0.2: Fixed a bug that occurred when translating a single IT note into
       multiple FSS notes.
* 0.1: Initial creation of program.
"""

from sys import argv, stderr, version_info

def die(msg):
    if isinstance(msg, BaseException):
        msg = str(msg)
    stderr.write(str(msg) + '\n')
    exit(1)

if version_info.major < 3:
    die('python3 only!')

from collections import namedtuple
from math import floor, log2
from struct import unpack_from

if len(argv) == 2:
    MODULE = argv[1]
else:
    die('Usage: {} MODULE'.format(argv[0]))

Module = namedtuple('Module', ('speed', 'tempo', 'orders', 'patterns', 'patternsVol', 'patternsCmdVal'))

NOTE_NAMES = ['a', 'A', 'b', 'c', 'C', 'd', 'D', 'e', 'f', 'F', 'g', 'G']
VALUE_NAMES = ['f', '8', '4', '2', '1']

def note_format(note, rows, vol, cmdVal, speed):
    if vol != None:
        if vol == 10:
            vol = "a"
        elif vol == 11:
            vol = "b"
        elif vol == 12:
            vol = "c"
        elif vol == 13:
            vol = "d"
        elif vol == 14:
            vol = "e"
        elif vol >= 15:
            vol = "f"

    lengths = []
    while rows > 0:
        power = min(4, floor(log2(rows)))
        lengths.append(VALUE_NAMES[power])
        rows -= 2 ** power

    strings = []

    for length in lengths:
        if cmdVal != None:
            temp = '{}\n\n'.format(2500 // cmdVal * speed)
            strings.append('t' + temp)
        if note is not None:
            if note < 120:
                fs_note = note - 9
                octave = fs_note // 12
                if 1 <= octave <= 7:
                    name = NOTE_NAMES[fs_note % 12]
                    strings.append(name + str(octave) + length + str(vol))
                elif octave == 0:
                    strings.append('K-' + length)
                elif octave == 8:
                    strings.append('S-' + length)
                else:
                    strings.append('x-' + length + str(vol))
            else:
                strings.append('r-' + length)
        else:
            strings.append('r-' + length)

    if strings:
        return '\n'.join(strings) + '\n'
    return ''

def read_orders(data):
    ordnum = unpack_from('H', data, 0x20)[0]
    return unpack_from('B' * ordnum, data, 0xC0)

def pattern_offsets(data):
    ordnum, insnum, smpnum, patnum = unpack_from('HHHH', data, 0x20)
    offset = 0xC0 + ordnum + insnum * 4 + smpnum * 4
    return unpack_from('I' * patnum, data, offset)

def read_pattern(data, offset):
    _, rows = unpack_from('HH', data, offset)
    offset += 8

    prev_maskvar, prev_note, prev_ins = ([0] * 64 for i in range(3))
    prev_vol, prev_cmd, prev_cmdval = ([0] * 64 for i in range(3))
    items = [[None for y in range(rows)] for x in range(4)]
    itemsVol = [[None for y in range(rows)] for x in range(4)]
    itemsCmdVal = [[None for y in range(rows)] for x in range(4)]

    for row in range(rows):
        while True:
            channelvariable = unpack_from('B', data, offset)[0]
            offset += 1
            if channelvariable == 0:
                break  # end of row
            channel = (channelvariable - 1) & 63
            if channelvariable & 128:
                maskvar = unpack_from('B', data, offset)[0]
                offset += 1
            else:
                maskvar = prev_maskvar[channel]
            prev_maskvar[channel] = maskvar

            if maskvar & 1:
                note = unpack_from('B', data, offset)[0]
                prev_note[channel] = note
                offset += 1
            else:
                note = None

            if maskvar & 2:
                ins = unpack_from('B', data, offset)[0]
                prev_ins[channel] = ins
                offset += 1
            else:
                ins = None

            if maskvar & 4:
                vol = unpack_from('B', data, offset)[0]
                prev_vol[channel] = vol
                offset += 1
            else:
                vol = None

            if maskvar & 8:
                cmd, cmdval = unpack_from('BB', data, offset)
                prev_cmd[channel], prev_cmdval[channel] = cmd, cmdval
                offset += 2
            else:
                cmd, cmdval = None, None

            if maskvar & 16:
                note = prev_note[channel]
            if maskvar & 32:
                ins = prev_ins[channel]
            if maskvar & 64:
                vol = prev_vol[channel]
            if maskvar & 128:
                cmd = prev_cmd[channel]
                cmdval = prev_cmdval[channel]

            if channel < 4:
                items[channel][row] = note
                itemsVol[channel][row] = vol
                if cmd == 20:
                    itemsCmdVal[channel][row] = cmdval
                else:
                    itemsCmdVal[channel][row] = None

    return items, itemsVol, itemsCmdVal

def read_patterns(data):
    offsets = pattern_offsets(data)
    patterns = []
    patternsVol = []
    patternsCmdVal = []
    for offset in offsets:
        pattern, patternVol, patternCmdVal = read_pattern(data, offset)
        patterns.append(pattern)
        patternsVol.append(patternVol)
        patternsCmdVal.append(patternCmdVal)
    return tuple(patterns), tuple(patternsVol), tuple(patternsCmdVal)

def read_module(filename):
    try:
        with open(filename, 'rb') as f:
            data = f.read()
    except BaseException as ex:
        die(ex)

    if data[:4].decode('ascii') != 'IMPM':
        die("Invalid IT module: '{}'".format(filename))

    speed, tempo = unpack_from('BB', data, 0x32)
    orders = read_orders(data)
    patterns, patternsVol, patternsCmdVal = read_patterns(data)
    return Module(speed, tempo, orders, patterns, patternsVol, patternsCmdVal)

def convert(module, filename):
    try:
        outfile = open(filename, 'w')
    except BaseException as ex:
        die(ex)

    outfile.write('{}\n\n'.format(2500 // module.tempo * module.speed))
    outfile.write('> generated by it2fss.py Ver 0.4\n\n')

    item = 255
    length = 0
    vol = 0
    cmdVal = module.tempo

    for order in (x for x in module.orders if x != 255):
        pattern = module.patterns[order]
        patternVol = module.patternsVol[order]
        patternCmdVal = module.patternsCmdVal[order]
        outfile.write('> pattern {}\n'.format(order))
        for row in range(len(pattern[0])):
            cur_item = pattern[0][row]
            cur_vol = patternVol[0][row]
            cur_cmdVal = patternCmdVal[0][row]
            if cur_item is not None and cur_item != item or cur_item is not None and cur_vol != vol:
                outfile.write(note_format(item, length, vol, cmdVal, module.speed))
                length = 0
                item = cur_item
                vol = cur_vol
                cmdVal = cur_cmdVal
            length += 1
        outfile.write('\n')

    if item:
        outfile.write(note_format(item, length, vol, cmdVal, module.tempo))

    outfile.close()

module = read_module(MODULE)
convert(module, MODULE + '.fss')
