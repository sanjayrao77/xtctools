# xtc tools, uploader

## Overview

This tool lets you send files to your XTEINK X3 (or X4) over wifi.

Upload progress is printed to the console, allowing you to see how long it will take.

You can enable the device mode by selecting "Sync/APP" from the home screen,
then selecting "Upload from Network (PC)" from the menu.

Once in the correct device mode, you can use this xteuploader.py tool.

## Installation

You should be able to download xteuploader.py directly from here.

This requires Python version 3, but has no unusual python requirements.

## Quick start

First, download xteuploader.py from here. Try running it. If Python 3 is installed
and working, xteuploader.py should ask for an IP address for the device.

Now, place your XTEINK X3 or X4 in the correct mode by selecting "Sync/APP" from the
home screen, then selecting "Upload from Network (PC)" from the menu. You may need
to enter wifi credentials first.

xteuploader.py was asking for an IP address. You can take this address from your
device's screen. At the bottom of the screen should be a message like "4. For
file management, open 192.168.1.214 in a web browser". In the example, the
program wants "192.168.1.214."

After entering the IP address (or hostname), xteuploader.py will list the contents
of the top directory and print usage information.

## Directory listing

You can use "ls [REMOTE\_DIRECTORY]" to list the contents of a directory.

E.g.:
```
xteuploader.py 192.168.1.214 ls
xteuploader.py 192.168.1.214 ls /
xteuploader.py 192.168.1.214 ls Dickens
xteuploader.py 192.168.1.214 ls Dickens/New
```

## Uploading

You can use "xteuploader.py (HOSTNAME) upload (FILENAME) (DEVICE\_DIRECTORY)" to upload a file to a directory on the device.
The file will be saved with the same name.

To upload the file under a different name, you can run
"xteuploader.py (HOSTNAME) upload (LOCAL\_FILENAME) (DEVICE\_DIRECTORY) (DEVICE\_FILENAME)" instead.

E.g.:
```
xteuploader.py 192.168.1.214 upload /tmp/DombeyAndSon.xtch Dickens
xteuploader.py 192.168.1.214 upload /tmp/DombeyAndSon.xtch Dickens dombey.xtch
```

By default, xteuploader.py will print the progress of the upload, using my http
upload code. My X3 is not fast, and can take several minutes to upload a large
book.
