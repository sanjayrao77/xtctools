# xtc tools

## Overview

These tools allow you to copy formatted pages from an Android ereader app
and use them to build xtc-format ebooks for XTEINK devices (X3 and X4).

I use this to take portrait pages from an Android tablet (I've used Amazon Fire HD 8 and 10),
then cut and stitch those portrait pages to make landscape pages for my X3.

My Fire HD 8 is 800x1280 and the X3 is 792x528, so there's a natural match of
about 2 output pages for every input page without scaling. My Fire HD 10 also works (1200x1080)
and gives me more control for removing side margins, though the output *is* scaled.

This should also work for capturing landscape pages (from a 2:1 phone for example)
and stitching them together for the X3/X4. I haven't tested this.

These tools could also be used to convert PDF files, but the print would be really small.

## License

In the USA it is *illegal* to use this to copy an entire DRM-encumbered book. Other regions may
also outlaw this.
In the USA it *is legal* to copy small portions of a DRM-encumbered book for fair-use
purposes.

This code is licensed under the GPLv2. The GPL license text is widely available
and should be downloadable above (on github).

Please don't use these tools to violate anyone's copyright. I use them to
copy public-domain books from Project Gutenberg. I like the formatting and OpenDyslexic font in Amazon's Android app.

## Warning

These tools are sloooooow. They are written in python for cross-platform compatiblity and are not designed to be fast.
But, they're fast enough to be sufferable on a Raspberry Pi 4. Converting the long novel, "Barnaby Rudge," took about 4 hours
to capture 3500 ereader-pages to storage and another 8 hours to convert them to xtch. A real computer could do it quicker, but
the python code is really inefficient.


#### started at 1:23

I suggest starting by converting a short story or a single chapter and seeing how everything works.

These tools are also mostly untested. Doing anything with them may take some debugging. I've only used them
on Linux.

## Installation

You should be able to download adbcapture.py, xtchbuilder.py and xtcviewer.py directly from here.

They all require Python, version 3, but have no unusual python requirements. They use tkinter,
but that should already be installed on major systems.

You'll need adb, the Android Debug Bridge, installed to use adbcapture.py.

I've only tested this on Linux, so they may require modification to run on other systems.
It should be possible to get it working on Windows and Mac as well.

## ADB

ADB is a tool provided by Google for communicating with Android devices. It's
often included in Android Studio. On a Raspberry Pi, you can simply do "apt-get
install adb" to install it.

For ADB to work, the device must be connected to a host computer, the device
must have "Developer Mode" enabled, the host computer must be approved on the
device, and the host computer must give read/write access to the user account.

Getting ADB to work is outside the scope of these instructions. However, if running "adb devices"
works, then that should mean adb is functioning well enough adbcapture.py.

On my Raspberry Pi 4, I think I just did "apt-get install adb" and everything worked after
enabling it on the device and approving the connection.

## Quick start

First check that "adb" is working on your system. An "adb devices" should list one device without
any warnings.

Now, download adbcapture.py, xtchbuilder.py and xtcviewer.py from here.

Run adbcapture.py and go through the first few steps. This verifies that adb is working.

Now, open an ereader on your Android device and capture a few pages with adbcapture.py. You can press
"Start" to begin and "Stop" after a few pages.

With the cap\*.png files saved, you can run xtchbuilder.py to build an xtc file and then xtcviewer.py
to view it on your desktop.

To transfer the xtc file to your ereader, copy it to its sdcard.

## PNG format

adbcapture.py will save files to PNG format, greyscale. This is an efficient way to store and/or archive
the pages. You should be able to load these into other programs.

It uses a subset of PNG, so they should be able to load into other programs just fine, but only this
subset of PNG is supported by xtchbuilder.py. If you edit these PNG files, you should save them to PGM
for xtchbuilder.py to be able to read them.

## PGM format

xtchbuilder.py uses PGM format natively. It also supports a special subset of PNG, as used by adbcapture.py.
If you modify any of adbcapture.py's PNG files, you should convert them to PGM so xtchbuilder.py can read them.

Note that PGM files are substantially larger than PNG and take more storage space.

## X3

I only have an X3. I've tested this on my X3 and it works for me.

I guessed how an X4 might work and have support for that in xtchbuilder.py, but it's quite likely that I
guessed wrong about some of it. Support for the X4 should be possible, but it's not tested.

## X4

I don't have an X4 to test this, but it's possible this works for the X4.

xtchbuilder.py has support for 480x800 resolution, and it's possible that's all that's needed for the X4.

## Scaling

If input and output dimensions are very close, xtchbuilder.py will use padding and trimming to fit images,
rather than scaling. Thus, the 800x1280 output of the Amazon Fire HD 8 can be used to make pages for the X3's 792x528 by
trimming 4 pixels from either side.

## Features

adbcapture.py will page through and capture pages, saving them in an efficient format. If it gets to the end
of the book, where pages stop flipping, it will stop.

xtchbuilder.py has many features. The GUI should describe them, but amongst other features, it can auto-crop,
add progress bars (chapter progress and book progress) and supports chapters.

xtcviewer.py can load xtc/xtch ebooks and lets you view them on your computer. This is mainly meant for quality
control but it could also be used to read books on a traditional computer.

## Compression

I added RLE and zlib compression support to xtchbuilder.py and xtcviewer.py. These compression methods are
*not* supported by any firmware. They *can* be used for testing or to store books for desktop viewing with xtcviewer.py.

The results I see are that zlib works well for compressing entire pages, not surprisingly. But, assuming
that's hard on an ESP32 and that the ESP32 would have an easier time decompressing individual rows, the zlib
compression in xtchbuilder.py will compress each row separately. Using this compression, it's still effective,
but not as good as RLE, in my testing.

The RLE compression works very well. Files are smaller than the line-at-a-time zlib compression. Also, the
decode is very efficient and small. I'll see if I can get this added to an alternate firmware. You can search for
"class RLE" in the python to see the code. It's not large.

I wouldn't be surprised if RLE decompression is faster than uncompressed
images. There is significantly less (less than half) the IO from the sdcard as the
images are smaller, and it takes very few instructions to decode. On the other
hand, maybe this isn't at all how the hardware works.

## Options for xtchbuilder.py

### xtchbuild.cfg

This configuration file stores all your settings. If no existing file is found in your input directory, a new one is created in
your output directory. You may want to move this file to your input directory for archiving.

### cap-cover.png

Most input filenames are expected to be in the format of capXXXX.pgm or capXXXX.png, where XXXX are digits.
The number 0 is reserved for the book cover, which is defaulted to scaling rather than splitting.

As a shortcut, you can use the filenames cap-cover.png and cap-cover.pgm instead of cap0000.png.

You can select this cover page as index 0. This may override any cap0000.png file.

Note that adbcapture.py has a step/button for saving this file.

### Step 1. Select directories

#### Input directory

This is the directory that includes all the capXXXX.png files from adbcapture.py. If an xtchbuild.cfg file
is found in this directory, this is the one used.

#### Output directory

This is where the final .xtc and .xtch files are created. If no xtchbuild.cfg is found elsewhere, a new
one is created in this directory.

### Step 2. Enter book info

These fields (title, author, publisher, language) are stored in the xtc file. They can also be used to
set the filename for the output xtc file.

### Step 3. Select filename format

This lets you choose the filename for the xtc file created. It currently has "AUTHOR - TITLE.FORMAT.xtc(h)", "TITLE.FORMAT.xtc(h)", and "output.FORMAT.xtc(h)"
as options.

### Step 4. Select page decorations

#### Status line

You can choose to add a progress bar along the bottom of the page. This takes 3 pixels plus whitespace padding.

The bar on the left is for chapter progress and the bar on the right is for book progress.

#### Padding above status line, in display pixels

This adds whitespace above any progress bars.

#### Padding below status line, in display pixels

This adds whitespace below any progress bars.

This was necessary on my X3, with the bezel obscuring the screen for a few pixels.

#### Top padding

If your bezel obscures the top of the screen, this adds whitespace to make everything visible.

#### Bottom padding

If you bezel obscures the bottom of the screen, this adds whitespace to make everything visible.

This setting is only used on pages without a progress bar. For pages with a progress bar, you should
set "Padding below status line."

### Step 5. Input page defaults

#### Global scaling option

The default option is to split input cap images into landscape pages for the ereader.

If you only want to scale the input into scaled output (without splitting), you can set that here.

This option is only the default mode; you can override this for individual pages.

#### Global crop values

Most pages have a header and footer. You can crop all of them by setting crop values here.

You can also do this in the next step if you don't know what values you want yet.

These values are only the default values; you can override these for individual pages.

### Step 6. Format input pages

#### Page number and left/right buttons

This lets you page through the input pages.

#### Split page to fit reader screen

This is the normal intended use. Input pages are split into multiple pages to fit the ereader
screen.

#### Scale full page to fit full reader screen

This is useful for covers and illustrations. When set, this page will not be split or decorated.
It will be sized to preserve aspect ratio.

This is the default for the cap-cover.png page.

#### Scale page and keep progress bar

This is the same as above, but uses the book-wide progress bar settings. If the book doesn't have
a progress bar then this is exactly the same as above.

#### Omit this page

This input page will not be included in the xtc file. This is useful for tables of contents and similar.

#### Global crop values

These are the same values from Step 5. When you set them here, you'll see red marks to denote the crops.
Any part of the page outside these red marks will be excluded.

These values set the default values for all pages

#### Crop this page override

These crop values will override the global crop values, setting values just for this page. These also
draw red crop marks.

Note that any empty field will still use the global values. So, if you have a page that wants to be
cropped exactly, you may want to enter a value for all fields (even if 0) in case the global values
are changed later.

### Step 7. Review page spacing

#### This many pixels will be duplicated on both reader pages

If an input page is split and whitespace isn't found in this space, then this many pixels will be placed on
both pages as an overlap.

If whitespace is found in this space, the page will be split on that whitespace without an overlap.

#### Linespacing in output

When stitching an input page after another, how many rows of whitespace should be placed between them,
in ereader pixels.

#### Chapter search size

Pages that start chapters often have more whitespace at the top. This setting should be larger than the whitespace
above a normal page (after cropping) and less than the whitespace above a chapter start page (after cropping).
This can be useful when adding chapters.
This is used in Step 8.

### Step 8. Edit chapters

#### Page number and left/right buttons

This lets you page through the input pages.

#### Add a new chapter

This lets you switch from updating an existing chapter to adding a new chapter.

#### Select a chapter to edit it

If you select an existing chapter, the UI can be used to modify that chapter (instead of adding a new one).

#### Delete chapter

This lets you delete an existing chapter or clear the field values (if adding a new chapter).

#### Start chapter search

If you don't know the page number of the next chapter, you can press "Start chapter search." This will walk
through the pages (you can watch the progress above) looking for pages with extra top margin. The margin
threshhold is set in "Step 7: Chapter search size". If a page margin is greater than this size, the search
will stop on this page.

You can stop the search by pressing the Stop button.

#### Chapter text

This is the chapter text to be included in the xtc file. There is a limit of 80 characters.

Practically, you should keep this under about 15 characters as they won't fit well on the ereader screen.

#### Capture page index

This is the page number of the input page. You can click on a preview image to enter this value.

#### Page offset

You can specify where on the input page the chapter actually starts. You should choose the top of "Chapter XX"
if present on the page.

You can enter this value by clicking on the preview image. A green line will be drawn to reflect your selection.

#### Add chapter

This adds a new chapter at the end of the list with the current values.

#### Update chapter

This updates the existing chapter with the new values

### Select output format

#### Bit depth for XTC file

You can choose 1-bit XTC or 2-bit XTCH output.

The 2-bit files are larger but look better.

#### Display of reader

You can choose X3 or X4 resolutions. I haven't tested an X4 so maybe that doesn't work.

#### Display orientation

By default, the output page is readable with the front buttons on the right-hand side.

If you prefer having the front buttons on the left-hand side, you can select that here.

Note, these values are for the X3. It's possible the X4 is reversed; I don't know.

#### Page compression

See the note on Compression above.

You should select "None" here if you want to read on normal devices.

### Step 10. Build XTC file

If all the values are set (inputdir, outputdir, etc.) you can press "Start" to start making the file.

The builder will pass through the input files twice. On the first pass, you'll see previews of the input
pages. Half-way through, you'll see previews of both the input and output pages.

This is very slow. You can use the --clibuild mode to run this in a shell.

### Command-line interface build: --clibuild

Instead of Step 10, you can do the final step from the command line.

You'll want to specify a complete xtchbuild.cfg file at the same time.

E.g.:
```
$ ./xtchbuilder.py --config=barnabyrudge/xtchbuild.cfg --clibuild
```

This will print its progress as it goes.

## Forking

I made these so I could read Dickens novels on my X3 and that's about all I want to do. (The built-in reader
choked on these enormous epubs and I don't blame it.)

I'll fix bugs if they're obvious but I don't have any interest in much further work on this. I might add a feature
if it's particularly useful but generally I'm not interested.

If you want to fork these programs, please do. All the source is right here.

## Personal note

I wrote 95% of this while waiting for my X3 to arrive. I'm glad I did.
I used "XtcFormat.md" as a reference and found it very good.

I'm using the firmware that came with the X3 and I'm satisfied with it, when used with these programs.

If the hardware is reliable, then I would highly recommend anyone to get an X3 or X4.
