#!/usr/bin/env python

# it2fss.py, version 0.5

from sys import argv, stderr, version_info
from math import floor, log2
from pytrax import impulsetracker


def die(msg):
    if isinstance(msg, BaseException):
        msg = str(msg)
    stderr.write(str(msg) + '\n')
    exit(1)


if version_info.major < 3:
    die('python3 only!')


if len(argv) == 2:
    MODULE = argv[1]
else:
    die('Usage: {} MODULE'.format(argv[0]))


NOTE_NAMES = ['a', 'A', 'b', 'c', 'C', 'd', 'D', 'e', 'f', 'F', 'g', 'G']
VALUE_NAMES = ['f', '8', '4', '2', '1']


# Calculates and returns the fSound Speed based on the tempo and speed of an ImpulseTracker Module.
def get_fsound_tempo(tempo: int, speed: int) -> int:
    return 2500 // tempo * speed


# Sets current row values.
# input:  an .it row
# output: cur_item (absolute note value. if not set, the script stops)
#         cur_instr (instrument value. if not set, the script stops (unless its a note cut)
#         cur_vol (volume value. if not set, it defaults to 64)
#         cur_cmd (command + value. if not set, it defaults to None)
def get_row_info(row):
    cur_item = None
    cur_instr = None
    cur_vol = None
    cur_cmd = None
    error_msg = "ERROR: There are rows with content but no note in your song."

    try:
        cur_item = row[0]['note']
        # check if the current note is a note cut (254) or not
        if cur_item != 254:
            try:
                cur_instr = row[0]['instrument']
            except:
                error_msg = "ERROR: There are notes in your song with no instrument assigned."
                die(error_msg)
        else:
            cur_instr = None
        try:
            cur_vol = row[0]['volpan']
        except:
            cur_vol = 64
        try:
            cur_cmd = row[0]['command']
        except:
            cur_cmd = None
    except:
        die(error_msg)

    return cur_item, cur_instr, cur_vol, cur_cmd


# returns a .fss string with linebreaks for one row of the .it file
# inputs: note (absolute IT note)
#         rows (the amount of empty rows until the next note happens (or end of song))
#         vol (the volume of the note)
#         instr (the instrument used for the note)
#         speed (None if there is no new speed to set, new speed value otherwise)
# output: string with .fss content
def note_format(note, rows, vol, instr, speed):
    # 64 values get mapped down to 16
    vol = round(vol/4)
    # dec values need to get converted to hex
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
        if speed is not None:
            if speed > 9:
                if int(str(speed)[1]) in [1, 2, 4, 8]:
                    print("Your song uses the speed value t{}. Keep in mind, that speed values with 1, 2, 4 or 8 at the 2nd position will result in pauses in your song.".format(speed))
            strings.append('t{}'.format(speed))
        if note == 254:
            strings.append('r-' + length)
        else:
            fs_note = note - 9
            octave = fs_note // 12
            if instr == 1:
                if not 1 <= octave <= 7:
                    die("ERROR: Your module file uses octaves below 2 or above 8.")
                name = NOTE_NAMES[fs_note % 12]
                strings.append(name + str(octave) + length + str(vol))
            elif instr == 2:
                strings.append('x-' + length + str(vol))
            # for kick and snare, only trigger them once, then set note to r-x
            # speed has to be set to None, to avoid multiple trigger of the same speed value
            elif instr == 3:
                strings.append('K-' + length)
                speed = None
                note = 254
            elif instr == 4:
                strings.append('S-' + length)
                speed = None
                note = 254
            else:
                die("ERROR: Your module file uses instruments higher than 4.")

    if strings:
        return '\n'.join(strings) + '\n'
    return ''


# calculates a new speed given either a Txx or a Axx effect with value
# returns the tempo and speed too, because those changed values will get reused later on
def calc_new_speed(cur_cmd, tempo: int, speed: int):
    new_speed = None
    if cur_cmd is not None:
        if cur_cmd.startswith("T"):
            tempo = int(cur_cmd[1:], 16)
            new_speed = get_fsound_tempo(tempo, speed)
        elif cur_cmd.startswith("A"):
            speed = int(cur_cmd[1:], 16)
            new_speed = get_fsound_tempo(tempo, speed)
    return tempo, speed, new_speed


# converts an .it module into a .fss file
def convert(module, filename):
    outfile = None
    try:
        outfile = open(filename, 'w')
        print(".fss file created.")
    except BaseException as ex:
        die(ex)

    length = 0
    tempo = module['inittempo']
    speed = module['initspeed']

    cur_item = None
    cur_instr = None
    cur_vol = None
    cur_cmd = None

    outfile.write('{}\n\n'.format(get_fsound_tempo(tempo, speed)))
    outfile.write('> generated by it2fss.py Ver 0.5\n\n')
    print("Header written.")

    print("Converting patterns.")
    for order in (x for x in module['orders']):
        # +++ Patterns
        if order == 254:
            pass
        # --- Pattern (End of Song, no matter if there are other patterns after)
        elif order == 255:
            tempo, speed, new_speed = calc_new_speed(cur_cmd, tempo, speed)
            outfile.write(note_format(cur_item, length, cur_vol, cur_instr, new_speed))
            break
        else:
            pattern = module['patterns'][order]
            pattern_comment_check = True
            for row in pattern[0]:
                if len(row) > 0:
                    if length == 0:
                        cur_item, cur_instr, cur_vol, cur_cmd = get_row_info(row)
                    else:
                        tempo, speed, new_speed = calc_new_speed(cur_cmd, tempo, speed)
                        outfile.write(note_format(cur_item, length, cur_vol, cur_instr, new_speed))
                        length = 0
                        cur_item, cur_instr, cur_vol, cur_cmd = get_row_info(row)
                    if pattern_comment_check:
                        outfile.write('> pattern {}\n'.format(order))
                        pattern_comment_check = False
                length += 1

    outfile.close()
    print("File sucessfully converted.")


module = impulsetracker.parse_file(MODULE, with_patterns=True)
convert(module, MODULE[:-3] + '.fss')
