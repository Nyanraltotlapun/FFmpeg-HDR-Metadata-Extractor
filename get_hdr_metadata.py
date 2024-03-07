#!/usr/bin/python3

# FFmpeg HDR Metadata Extractor is an HDR metadata extractor that uses ffprobe output.
#     Copyright (C) 2024  Kirill Harmatulla Shakirov
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <https://www.gnu.org/licenses/>.


import subprocess
import json
import argparse

x265_valid_color_matrix = [
    "gbr", "bt709", "unknown", "reserved", "fcc", "bt470bg", "smpte170m", "smpte240m", "ycgco",
    "bt2020nc", "bt2020c", "smpte2085", "chroma-derived-nc", "chroma-derived-c", "ictcp"
]

x265_color_matrix_mapping = {"bt2020_ncl": "bt2020nc", "bt2020_cl": "bt2020c"}

# aomenc --help
# https://ffmpeg.org/ffmpeg-codecs.html
libaom_valid_matrix_coefficients = [
    "bt709", "fcc73", "bt470bg", "bt601", "smpte240", "ycgco",
    "bt2020ncl", "bt2020cl", "smpte2085", "chromncl", "chromcl", "ictcp"
]

libaom_matrix_coefficients_mapping = {
    "fcc": "fcc73",
    "smpte240m": "smpte240",
    "bt2020nc": "bt2020ncl",
    "bt2020_ncl": "bt2020ncl",
    "bt2020c": "bt2020cl",
    "bt2020_cl": "bt2020cl",
    "chroma-derived-nc": "chromncl",
    "chroma-derived-c": "chromcl"
}


def libaom_get_matrix_coefficients(color_space: str) -> str | None:
    if color_space in libaom_valid_matrix_coefficients:
        return color_space
    elif color_space in libaom_matrix_coefficients_mapping:
        return libaom_matrix_coefficients_mapping[color_space]

    return None


# https://gitlab.com/AOMediaCodec/SVT-AV1/-/blob/master/Docs/Parameters.md
libsvtav1_color_primaries_mapping = {
    "bt709": 1,
    "bt470m": 4,
    "bt470bg": 5,
    "bt601": 6,
    "smpte240": 7,
    "film": 8,
    "bt2020": 9,
    "xyz": 10,
    "smpte431": 11,
    "smpte432": 12,
    "ebu3213": 22
}


def libsvtav1_get_cp_code(color_primaries: str) -> int:
    # 2: unspecified, default
    return libsvtav1_color_primaries_mapping.get(color_primaries, 2)


# 2: unspecified, default
# https://gitlab.com/AOMediaCodec/SVT-AV1/-/blob/master/Docs/Parameters.md
libsvtav1_transfer_characteristics_mapping = {
    "bt709": 1,
    "bt470m": 4,
    "bt470bg": 5,
    "bt601": 6,
    "smpte240": 7,
    "linear": 8,
    "log100": 9,
    "log100-sqrt10": 10,
    "iec61966": 11,
    "bt1361": 12,
    "srgb": 13,
    "bt2020-10": 14,
    "bt2020-12": 15,
    "smpte2084": 16,
    "smpte428": 17,
    "hlg": 18
}


def libsvtav1_get_tch_code(transfer_characteristics: str) -> int:
    # 2: unspecified, default
    return libsvtav1_transfer_characteristics_mapping.get(transfer_characteristics, 2)


class MDItem:
    def __init__(self, raw_val: str):
        self.raw_value: str = raw_val
        val_list = raw_val.split("/")
        self.numerator: int = int(val_list[0])
        self.denominator: int = int(val_list[1])
        self.float_value = self.numerator / self.denominator

    def __str__(self) -> str:
        return self.raw_value

    # *If your data for colors is not divided by /50000 or luminescence not divided by 10000 and have been simplified,
    # you will have to expand it back out to the full ratio. For example if yours lists 'red_x': '17/25',
    # 'red_y': '8/25' you will have to divide 50000 by the current denominator (25) to get the ratio (2000)
    # and multiply that by the numerator (17 and 8) to get the proper R(34000,16000).
    def expand_to_ratio(self, denominator: int) -> int:
        return int(self.numerator * (denominator / self.denominator))


class MDItemColorXY:
    def __init__(self, side_data: dict, prefix: str):
        self.prefix: str = prefix
        self.x_data = MDItem(side_data[prefix + "_x"])
        self.y_data = MDItem(side_data[prefix + "_y"])

    def __str__(self) -> str:
        return f"{self.prefix}_x: {self.x_data}\n{self.prefix}_y: {self.y_data}"

    def to_x265(self) -> str:
        return f"({self.x_data.expand_to_ratio(50000)},{self.y_data.expand_to_ratio(50000)})"

    def to_libsvtav1(self) -> str:
        return f"({round(self.x_data.float_value, 4):.4f},{round(self.y_data.float_value, 4):.4f})"


class MasteringDisplayData:
    def __init__(self, side_data: dict):
        self.red = MDItemColorXY(side_data, "red")
        self.green = MDItemColorXY(side_data, "green")
        self.blue = MDItemColorXY(side_data, "blue")
        self.white_point = MDItemColorXY(side_data, "white_point")
        self.min_luminance = MDItem(side_data["min_luminance"])
        self.max_luminance = MDItem(side_data["max_luminance"])

    def __str__(self) -> str:
        return f"{self.red}\n{self.green}\n{self.blue}\n{self.white_point}\n" + \
            f"min_luminance: {self.min_luminance}\nmax_luminance{self.max_luminance}"

    def to_x265_params(self) -> str:
        return f"display=G{self.green.to_x265()}B{self.blue.to_x265()}R{self.red.to_x265()}" + \
            f"WP{self.white_point.to_x265()}" + \
            f"L({self.max_luminance.expand_to_ratio(10000)},{self.min_luminance.expand_to_ratio(10000)})"

    def to_libsvtav1_params(self) -> str:
        return f"mastering-display=G{self.green.to_libsvtav1()}B{self.blue.to_libsvtav1()}" + \
            f"R{self.red.to_libsvtav1()}WP{self.white_point.to_libsvtav1()}" + \
            f"L({round(self.max_luminance.float_value, 4):.4f},{round(self.min_luminance.float_value, 4):.4f})"


class ContentLightLevelData:
    def __init__(self, side_data: dict):
        self.max_content: int = side_data["max_content"]
        self.max_average: int = side_data["max_average"]

    def __str__(self) -> str:
        return f"max_content: {self.max_content}, max_average {self.max_average}"

    # This data, as well as the Content light level <max_content>,<max_average> of 0,0
    # will be fed into the encoder command options.
    # max-cll=1000,239
    def to_x265_params(self) -> str:
        return f"max-cll={self.max_content},{self.max_average}"

    def to_libsvtav1_params(self) -> str:
        return f"content-light={self.max_content},{self.max_average}"


class ColorData:
    def __init__(self, frame_data: dict):
        self.pix_fmt = frame_data["pix_fmt"]
        self.color_space = frame_data["color_space"]
        self.color_primaries = frame_data["color_primaries"]
        self.color_transfer = frame_data["color_transfer"]

    def __str__(self) -> str:
        return "pix_fmt: " + self.pix_fmt + "\ncolor_space: " + self.color_space + \
            "\ncolor_primaries: " + self.color_primaries + "\ncolor_transfer: " + self.color_transfer

    def to_ffmpeg_options(self) -> str:
        return f"-pix_fmt {self.pix_fmt} -colorspace {self.color_space} " + \
            f"-color_trc {self.color_transfer} -color_primaries {self.color_primaries}"

    def to_x265_params(self) -> str:
        if self.color_space in x265_valid_color_matrix:
            return f"colormatrix={self.color_space}"
        elif self.color_space in x265_color_matrix_mapping:
            return f"colormatrix={x265_color_matrix_mapping[self.color_space]}"
        return ""

    # matrix-coefficients=<arg> Matrix coefficients (CICP) of input content:
    # identity, bt709, unspecified, fcc73, bt470bg, bt601, smpte240,
    # ycgco, bt2020ncl, bt2020cl, smpte2085, chromncl, chromcl, ictcp
    def to_libaom_av1_params(self) -> str:
        res = f"color-primaries={self.color_primaries}:transfer-characteristics={self.color_transfer}"
        mc = libaom_get_matrix_coefficients(self.color_space)
        if mc is not None:
            res += f":matrix-coefficients={mc}"
        return res

    # From Fastfix
    # if (fastflix.current_video.color_space and "bt2020" in fastflix.current_video.color_space):
    #             svtav1_params.append(f"matrix-coefficients=9")
    def to_libsvtav1_params(self) -> str:
        res = f"color-primaries={libsvtav1_get_cp_code(self.color_primaries)}"
        res += f":transfer-characteristics={libsvtav1_get_tch_code(self.color_transfer)}"
        if "bt2020" in self.color_space:
            res += ":matrix-coefficients=9"
        return res


def parse_frame_data(frame_data: dict):
    color_params = ["pix_fmt", "color_space", "color_primaries", "color_transfer"]

    missing_params = [x for x in color_params if x not in frame_data.keys()]
    if len(missing_params) != 0:
        print(f"Missing {missing_params} parameters in frame metadata!")
        print("Probably not an HDR stream!")
        print("Exit!")
        return

    color_data = ColorData(frame_data)
    print("Color Data:")
    print(color_data)
    print("")

    x265_params: str = color_data.to_x265_params()
    libaom_av1_params: str = color_data.to_libaom_av1_params()
    libsvtav1_params: str = color_data.to_libsvtav1_params()

    side_data_list = frame_data["side_data_list"]
    for side_data in side_data_list:
        if side_data["side_data_type"] == "Mastering display metadata":
            mastering_display_data = MasteringDisplayData(side_data)
            x265_params += ":" + mastering_display_data.to_x265_params()
            libsvtav1_params += ":" + mastering_display_data.to_libsvtav1_params()
            print("Mastering display metadata:")
            print(mastering_display_data)
            print("")

        elif side_data["side_data_type"] == "Content light level metadata":
            content_light_level_data = ContentLightLevelData(side_data)
            x265_params += ":" + content_light_level_data.to_x265_params()
            libsvtav1_params += ":" + content_light_level_data.to_libsvtav1_params()
            print("Content light level metadata:")
            print(content_light_level_data)
            print("")

    print(f"\nFFmpeg options: {color_data.to_ffmpeg_options()}\n")
    print(f"x265 params: {x265_params}\n")
    print(f"libsvtav1 params: {libsvtav1_params}\n")
    print(f"libaom-av1 params: {libaom_av1_params}\n")

    print("Done!")


if __name__ == '__main__':

    # Initialize arguments parser
    parser = argparse.ArgumentParser(
        prog="get_hdr_metadata.py",
        description="This program parse HDR metadata from ffprobe output and generates ffmpeg parameters based on it.",
        epilog="Have a nice day!")

    parser.add_argument("-i", "--input-file",
                        action="store",
                        default=None,
                        help="video file name from which hdr metadata needs to be extracted.",
                        required=True)

    parser.add_argument("-s", "--input-stream",
                        action="store",
                        type=int,
                        default=0,
                        help="video stream number in the input file, default 0.",
                        required=False)

    parser.add_argument("-e", "--ffprobe-binary",
                        action="store",
                        default="ffprobe",
                        help="specify ffprobe binary to use, default - \"ffprobe\".",
                        required=False)

    arguments = parser.parse_args()

    print(f"Reading data from file: {arguments.input_file}")
    print(f"Stream: {arguments.input_stream}")
    print("")

    # https://codecalamity.com/encoding-uhd-4k-hdr10-videos-with-ffmpeg/
    # https://www.reddit.com/r/AV1/comments/yb0eck/getting_accurate_hdr_data_from_h264_265_to_encode/
    # https://www.reddit.com/r/AV1/comments/ut2y4l/svtav1_hdr_encoding_libsvtav1_with_ffmpeg/

    #    -hide_banner -loglevel warning Don’t display what we don’t need
    #    -select_streams v We only want the details for the video (v) stream
    #    -print_format json Make it easier to parse
    #    -read_intervals "%+#1" Only grab data from the first frame
    #    -show_entries ... Pick only the relevant data we want
    #    -i GlassBlowingUHD.mp4 input (-i) is our Dobly Vision demo file
    ffprobe_cmd: list[str] = [arguments.ffprobe_binary, "-hide_banner", "-loglevel", "warning",
                              "-select_streams", str(arguments.input_stream),
                              "-print_format", "json", "-show_frames", "-read_intervals", "%+#1",
                              "-show_entries",
                              "stream=codec_type:" +
                              "frame=pix_fmt,color_space,color_primaries,color_transfer,side_data_list",
                              "-i", arguments.input_file]

    try:
        result = subprocess.run(ffprobe_cmd, capture_output=True, encoding="UTF-8")
        if result.returncode == 0 and result.stdout is not None:
            metadata = json.loads(result.stdout)

            stream_codec_type = metadata["streams"][0]["codec_type"]
            if stream_codec_type == "video":

                parse_frame_data(metadata["frames"][0])
            else:
                print(f"Selected stream type is \"{stream_codec_type}\"")
                print("Not a video stream!")
                print("Exit!")

        else:
            print("Error executing ffprobe binary!")
            print(result.stderr)
            print("Exit!")

    except FileNotFoundError as err:
        print("Cannot find ffprobe binary!")
        print("Try to specify it thru -e command line argument.")
        print(err)
        print("Exit!")
    except Exception as ex:
        print("Unknown error!")
        print(ex)
        print("Exit!")
