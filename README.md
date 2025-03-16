# FFmpeg HDR Metadata Extractor

**FFmpeg HDR Metadata Extractor** is a HDR metadata extractor that uses **ffprobe** in order to retrieve HDR metadata from file, and generates ffmpeg parameters based on it.
Specifically it generates command line parameters for three codecs available in FFmpeg:
- x265
- libsvtav1
- libaom_av1

# Pre requirements
In order to use this python script you need **python** version 3+ and **ffprobe** binary installed somewhere on your system.
## Linux
In **Linux** **ffprobe** usually came with **ffmpeg** package in your distribution.
## Windows
In **Windows**, you should search and install **ffmpeg** package by yourself, good starting point is ffmpeg official site: https://ffmpeg.org/download.html

# Usage
```
get_hdr_metadata.py [-h] -i INPUT_FILE [-s INPUT_STREAM] [-e FFPROBE_BINARY]

options:
  -h, --help            show this help message and exit
  -i INPUT_FILE, --input-file INPUT_FILE
                        video file name from which hdr metadata needs to be extracted.
  -s INPUT_STREAM, --input-stream INPUT_STREAM
                        video stream number in the input file, default 0.
  -e FFPROBE_BINARY, --ffprobe-binary FFPROBE_BINARY
                        specify ffprobe binary to use, default - "ffprobe".
```

On Windows you probably need to specify exact ffprobe.exe binary location.
For example: `python get_hdr_metadata.py -e "C:\ffmpeg\ffprobe.exe" -i test.mkv`
