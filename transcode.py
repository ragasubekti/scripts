import os
import subprocess
import sqlite3
import concurrent.futures
import logging
import argparse
import threading
from pathlib import Path

SUPPORTED_EXTENSIONS = (".mp4", ".mkv", ".webm")
DEFAULT_BITRATE = 3

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

thread_local = threading.local()


def get_thread_local_connection():
    if not hasattr(thread_local, "connection"):
        thread_local.connection = sqlite3.connect(
            "transcoded_videos.db", check_same_thread=False)
    return thread_local.connection


def connect_to_db():
    return get_thread_local_connection()


def create_table_if_not_exists(conn):
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS transcoded_videos (source_file TEXT, target_file TEXT, source_modified_time TIMESTAMP)"
    )


def insert_transcoded_video(conn, source_file, target_file):
    cursor = conn.cursor()
    source_modified_time = os.path.getmtime(source_file)
    cursor.execute(
        "INSERT OR REPLACE INTO transcoded_videos (source_file, target_file, source_modified_time) VALUES (?, ?, ?)",
        (source_file, target_file, source_modified_time)
    )
    conn.commit()


def check_if_transcoded(conn, video_file):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT source_modified_time FROM transcoded_videos WHERE source_file = ?", (video_file,))
    result = cursor.fetchone()
    if result is not None:
        source_modified_time = os.path.getmtime(video_file)
        return result[0] >= source_modified_time
    return False


def check_video(video_file):
    ffprobe_command = ["ffprobe", "-v", "error", "-i", video_file]
    returncode = subprocess.run(ffprobe_command).returncode
    return returncode == 0


def get_bitrate(video_file, dev_null):
    ffprobe_command = ["ffprobe", "-hide_banner",
                       "-i", video_file, "-show_format"]
    output = subprocess.check_output(ffprobe_command, stderr=dev_null)

    for line in output.splitlines():
        if b"duration=" in line:
            logger.info(f'[DURATION]\t: {float(line.split(b"=")[1])}')

        if b"bit_rate=" in line:
            bitrate = float(line.split(b"=")[1]) / 1024 / 1024
            return bitrate
    return None


def ffmpeg_cmd(video_file, output_file, bitrate, hwaccel=True):
    cmd = [
        "ffmpeg", "-hide_banner", "-v", "error", "-stats", "-y",
    ]

    if hwaccel:
        cmd.extend([
            "-hwaccel", "vaapi", "-vaapi_device", "/dev/dri/renderD128",
            "-i", str(video_file),
            "-vf", 'format=nv12,hwupload,scale_vaapi=w=-2:h=1080',
            "-vcodec", "h264_vaapi",
        ])
    else:
        cmd.extend([
            "-i", str(video_file),
            "-vf", "scale=-2:min(1080\,trunc(ih/2)*2)",
            "-vcodec", "libx264",
        ])

    cmd.extend([
        "-acodec", "copy", "-b:v", f"{bitrate}M",
        str(output_file)
    ])

    return cmd


def transcode_video_real(video_file, output_file, bitrate, dev_null):
    output_dir = output_file.parent
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"[SOURCE]\t: {video_file}")
    logger.info(f"[OUTPUT]\t: {output_file}")

    logger.info(f'[FFMPEG]\t: Trying with VAAPI')
    command = ffmpeg_cmd(video_file, str(output_file), bitrate, True)
    returncode = subprocess.run(command).returncode

    if returncode != 0:
        logger.info(f'[FFMPEG]\t: Retrying with CPU')
        retry_cmd = ffmpeg_cmd(video_file, str(output_file), bitrate, False)
        retry = subprocess.run(retry_cmd).returncode

        if retry != 0:
            logger.error(f'[FAIL]\t: {video_file}')
            return

    conn = connect_to_db()
    insert_transcoded_video(conn, video_file, str(output_file))


def process_video(video_file, source_dir, output_dir, bitrate, dev_null, conn):
    try:  # Convert to Path object
        if not video_file.suffix.lower() in SUPPORTED_EXTENSIONS:
            return

        output_file = output_dir / video_file.relative_to(source_dir)
        output_file = output_file.with_suffix(".mp4")

        source_modified_time = video_file.stat().st_mtime

        if check_if_transcoded(conn, str(video_file)):
            return

        if output_file.exists():
            output_modified_time = output_file.stat().st_mtime
            if output_modified_time >= source_modified_time:
                return

        if check_video(str(video_file)):
            source_bitrate = (
                bitrate if video_file.suffix.lower() == ".webm" else get_bitrate(video_file, dev_null)
            )

            logger.info(f"[SOURCE_BITRATE]\t: {source_bitrate}")
            transcode_video_real(str(video_file), output_file, min(
                source_bitrate, bitrate), dev_null)
    except Exception as e:
        logger.error(f"[ERROR]\t: {video_file} __ {e}")


def transcode_videos(source_dir, output_dir, bitrate, db_connection):
    create_table_if_not_exists(db_connection)
    dev_null = open(os.devnull, 'w')
    max_workers = min(4, os.cpu_count() or 1)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        source_dir = Path(source_dir)
        output_dir = Path(output_dir)

        for root, _, files in os.walk(source_dir):
            video_files = [Path(root) / file for file in files]
            executor.map(process_video, video_files, [source_dir] * len(video_files), [output_dir] * len(video_files), [
                         bitrate] * len(video_files), [dev_null] * len(video_files), [db_connection] * len(video_files))


def main():
    parser = argparse.ArgumentParser(
        description="Transcode videos recursively")
    parser.add_argument("source", help="Source directory")
    parser.add_argument("output", help="Output directory")
    parser.add_argument(
        "--bitrate", type=int, default=DEFAULT_BITRATE, help="Target bitrate (default: 3)")
    args = parser.parse_args()

    db_connection = connect_to_db()

    transcode_videos(args.source, args.output, args.bitrate, db_connection)


if __name__ == "__main__":
    main()
