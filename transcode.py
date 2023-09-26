import os
import subprocess
import sqlite3


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


def get_bitrate(video_file):
    command = ["ffprobe", "-hide_banner", "-i", video_file, "-show_format"]
    output = subprocess.check_output(command)

    for line in output.splitlines():
        if b"bit_rate=" in line:
            bitrate = float(line.split(b"=")[1]) / 1024 / 1024
            print("[bitrate] ", bitrate)
            return bitrate
    return None


def transcode_video(video_file, output_file, bitrate):
    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    command = [
        "ffmpeg", "-hide_banner",
        "-v", "fatal",
        "-stats", "-y",
        "-hwaccel", "vaapi", "-vaapi_device", "/dev/dri/renderD128",
        "-i", video_file,
        "-vf", 'format=nv12,hwupload,scale_vaapi=w=-2:h=1080',
        "-acodec", "copy", "-b:v", f"{bitrate}M",
        "-vcodec", "h264_vaapi",
        output_file
    ]

    print(command)

    subprocess.run(command)

    conn = connect_to_db()

    insert_transcoded_video(conn, video_file, output_file)

    conn.close()


def transcode_videos_recursively(source_dir, output_dir, bitrate):
    conn = connect_to_db()
    create_table_if_not_exists(conn)

    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.endswith(".mp4") or file.endswith(".mkv"):
                video_file = os.path.join(root, file)
                output_file = os.path.join(
                    output_dir, os.path.relpath(video_file, source_dir)
                )

                if check_if_transcoded(conn, video_file):
                    continue
                source_bitrate = get_bitrate(video_file)

                transcode_video(video_file, output_file,
                                min(source_bitrate, bitrate))

    conn.close()


if __name__ == "__main__":
    source_dir = "/media/h"
    output_dir = "/media/httr"

    bitrate = int("3")

    transcode_videos_recursively(source_dir, output_dir, bitrate)
