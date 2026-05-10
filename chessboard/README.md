# xtc tools, chessboard

## Overview

This tool lets you convert common FEN-format chessboards to XTH format, suitable for an XTEINK X3 or X4.
These files can be set to your "power-off" screen, visible when your device is off.

After an XTH file is made, you can upload it to your device using my xteuploader.py or by copying
it to your sd card.

Note: I've only tested this on an X3. The X4 output may need to be fixed.

## Installation

You should be able to download chessboard.py directly from here.

This requires Python version 3, but has no unusual python requirements.

## Quick start

First, download chessboard.py from here.

Then, try running:
```
chessboard.py --x3 --landscape "4k3/p2q1p2/1pQp2rp/6p1/1B6/3n4/PP3PPP/2R3K1 w - -" chess.x3.xth
chessboard.py --x4 --landscape "4k3/p2q1p2/1pQp2rp/6p1/1B6/3n4/PP3PPP/2R3K1 w - -" chess.x4.xth
```

This should create a chess.xth file suitable for the XTEINK X3 and X4.

Note: I've only tested this on an X3. The X4 output may need to be fixed.

## Uploading

You can use "xteuploader.py (HOSTNAME) upload (FILENAME) (DEVICE\_DIRECTORY)" to upload the xth file to your device.

E.g.:
```
xteuploader.py 192.168.1.214 upload chess.x3.xth / poweroff.xth
```

## Power-off screen

You can enter the "Folder" view by selecting "Folder" from the main menu.

Within the "Folder" view, when an XTH file is highlighted, you can long-press the Select button to see a menu.
On that menu is the option "Set as Power-off Screen." Selecting that will make the file visible whenever
the device is powered off.
