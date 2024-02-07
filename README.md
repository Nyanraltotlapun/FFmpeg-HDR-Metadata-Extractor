# FFmpegHDRMetadata

**FFmpegHDRMetadata** is a HDR metadata extractor that uses **ffprobe** in order to retrive HDR metadata from file, and generates ffmpeg parameters based on it.
Specifically it generates comman line parameter for tree codecs available in FFmpeg:
- x265
- libsvtav1
- libaom_av1
