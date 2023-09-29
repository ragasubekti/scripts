import os
import subprocess
import sqlite3
from colorama import Fore, Back, Style


def connect_to_db():
    conn = sqlite3.connect("transcoded_videos.db")
    return conn


def create_table_if_not_exists(conn):
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS transcoded_videos (source_file TEXT, target_file TEXT)")


def insert_transcoded_video(conn, source_file, target_file):
    c = conn.cursor()

    c.execute(
        "INSERT INTO transcoded_videos (source_file, target_file) VALUES (?, ?)",
        (source_file, target_file),
    )

    conn.commit()


def check_if_transcoded(conn, video_file):
    c = conn.cursor()

    c.execute("SELECT 1 FROM transcoded_videos WHERE source_file = ?", (video_file,))

    result = c.fetchone()

    return result is not None


def check_video(video_file):
    check = ["ffprobe", "-v", "error", "-i", video_file]
    returncode = subprocess.run(check).returncode

    return returncode == 0


def get_bitrate(video_file):
    command = ["ffprobe", "-hide_banner", "-i", video_file, "-show_format"]
    dev_null = open(os.devnull, 'w')
    output = subprocess.check_output(command, stderr=dev_null)

    for line in output.splitlines():
        if b"bit_rate=" in line:
            bitrate = float(line.split(b"=")[1]) / 1024 / 1024
            print(Back.WHITE + Fore.BLACK +  "[BITRATE]" + Style.RESET_ALL, end="")
            print(f"\t{bitrate}")
            return bitrate
    return None


def ffmpeg_cmd(video_file, output_file, bitrate, hwaccel=True):
    if hwaccel:
        return [
            "ffmpeg", "-hide_banner",
            "-v", "error",
            "-stats", "-y",
            "-hwaccel", "vaapi", "-vaapi_device", "/dev/dri/renderD128",
            "-i", video_file,
            "-vf", 'format=nv12,hwupload,scale_vaapi=w=-2:h=1080',
            "-acodec", "copy", "-b:v", f"{bitrate}M",
            "-vcodec", "h264_vaapi",
            output_file
        ]
    else:
        return [
            "ffmpeg", "-hide_banner",
            "-v", "error",
            "-stats", "-y",
            "-i", video_file,
            "-vf",  "scale=-2:min(1080\,trunc(ih/2)*2)",
            "-acodec", "copy", "-b:v", f"{bitrate}M",
            "-vcodec", "libx264",
            output_file
        ]


def transcode_video(video_file, output_file, bitrate):
    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    print(Back.WHITE + Fore.BLACK +  "[SOURCE] " + Style.RESET_ALL, end="")
    print(f"\t{video_file}")
    print(Back.WHITE + Fore.BLACK +  "[OUTPUT]" + Style.RESET_ALL, end="")
    print(f"\t{output_file}")

    print(Back.GREEN + Fore.WHITE + '[FFMPEG]' + Style.RESET_ALL, end="")
    print(f"\tProcessing file with VAAPI")

    command = ffmpeg_cmd(video_file, output_file, bitrate, True)

    returncode = subprocess.run(command).returncode

    if returncode != 0:
        print(Back.BLUE + Fore.WHITE +
              '[FFMPEG]' + Style.RESET_ALL, end="")
        print(f"\tRetrying processing file with CPU")

        retry_cpu = ffmpeg_cmd(video_file, output_file, bitrate, False)
        retry = subprocess.run(retry_cpu).returncode

        if retry != 0:
            print(Back.RED + Fore.WHITE +
                  '[FAIL]' + Style.RESET_ALL, end="")
            print(f"\tFailed to process {video_file}")
            return

    conn = connect_to_db()
    insert_transcoded_video(conn, video_file, output_file)
    conn.close()


def transcode_videos_recursively(source_dir, output_dir, bitrate):
    supported_ext = (".mp4", ".mkv", ".webm")
    with connect_to_db() as conn:
        create_table_if_not_exists(conn)

        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if file.endswith(supported_ext):
                    video_file = os.path.join(root, file)
                    output_file = os.path.join(
                        output_dir, os.path.relpath(video_file, source_dir))

                    output_file = os.path.splitext(output_file)[0] + ".mp4"
                    # continue

                    if check_if_transcoded(conn, video_file):
                        continue

                    if check_video(video_file):
                        source_bitrate = 3 if file.endswith(
                            ".webm") else get_bitrate(video_file)
                        transcode_video(video_file, output_file, min(
                            source_bitrate, bitrate))


if __name__ == "__main__":
    source_dir = "/media/h"
    output_dir = "/media/httr"

    bitrate = int("3")

    transcode_videos_recursively(source_dir, output_dir, bitrate)
