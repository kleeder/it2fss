# it2fss

Converter which takes single-channel ImpulseTracker modules as input and outputs a fSound .fss file, for use with fsound.exe.
fSound is available [here](https://kleeder.de/files/botbFiles.php). This converter aims for the version called "fsound.zip".
The [Pytrax/impulsetracker-parser library](https://github.com/ramen/pytrax) is used and
slightly modified to work with Python 3.

Improved version of: https://gist.github.com/jangler/9565970

-------

## Features
- Squarewaves of any volume and pitch are supported.
- White Noise of any volume is supported.
- Tempo Changes are supported. (Txx with values bigger <= 20 and Axx).
- Kick and Snare Samples are supported.
- Only use an instrument setting, volume or effect along with a note, otherwise it will throw an error.


-------

## Installation
- download/clone repo 
- make sure Python 3 is installed
- write your song using the test.it (follow the limits listed below)
- convert your song with
  ```bash
   python it2fss.py test.it
  ```

-------

## Limitations
- Square Waves can be produced between C-2 and B-8 (C-1 to B-7 in fSound), using Instrument 1.
- White Noise is always the same pitch, using Instrument 2.
- Kick uses Instrument 3 and Snare uses Instrument 4.
- Make sure to set an instrument for every note you put in.


- Square and Noise have volume control. v00 is lowest, v64 is highest.
- The values get mapped to the 16 available sound values in fSound (0-F).
- Non-set volume gets mapped to f (loudest).
-------
## Version history

* 0.5: Massive Refactoring; added Axx support; sample-mapping via instrument, not octave;
       Volume is now mapped from 0-64 values, non-set-volume doesn't map to None anymore
* 0.4.1: Fixed a bug where consecutive drum notes would be combined into one
* 0.4: Added Tempo Change Support
* 0.3: Added Sample and Volume Support
* 0.2: Fixed a bug that occurred when translating a single IT note into
       multiple FSS notes.
* 0.1: Initial creation of program.