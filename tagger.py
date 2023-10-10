import os
import shutil
import sqlite3
import subprocess

from mutagen.id3 import ID3, APIC, TIT2, TALB, TRCK, ID3NoHeaderError, PictureType
from mutagen import flac
from datetime import datetime


def create_database(database_path):
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audio_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file TEXT NOT NULL,
            target_file TEXT NOT NULL,
            album_title TEXT,
            is_audio_file INTEGER,
            is_tagged INTEGER,
            created_at TEXT,
            modified_at TEXT,
            tag_data TEXT
        )
    ''')
    conn.commit()
    conn.close()


def insert_record(database_path, source_file, target_file, album_title, is_audio_file, is_tagged, tag_data):
    created_at = modified_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO audio_files (source_file, target_file, album_title, is_audio_file, is_tagged, created_at, modified_at, tag_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (source_file, target_file, album_title, is_audio_file, is_tagged, created_at, modified_at, tag_data))
    conn.commit()
    conn.close()


def update_record(database_path, target_file, is_tagged, tag_data, modified_file_name):
    try:
        modified_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE audio_files
            SET is_tagged = ?, modified_at = ?, tag_data = ?, target_file = ?
            WHERE target_file = ?
        ''', (is_tagged, modified_at, tag_data, modified_file_name, target_file))
        print([database_path, is_tagged, modified_at,
              tag_data, modified_file_name, target_file])
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(e)
        raise e


def copy_and_tag_audio_folder(input_folder, output_folder, database_path):
    input_folder = input_folder.strip()
    output_folder = output_folder.strip()

    if not os.path.exists(input_folder) or not os.path.isdir(input_folder):
        print("Invalid input folder path or folder does not exist.")
        return

    create_database(database_path)

    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    for root, subfolders, files in os.walk(input_folder):
        for subfolder in subfolders[:]:
            subfolder_path = os.path.join(root, subfolder)
            output_subfolder = os.path.join(
                output_folder, os.path.relpath(subfolder_path, input_folder)
            )
            os.makedirs(output_subfolder, exist_ok=True)

            is_file_copied = False

            for file_name in os.listdir(subfolder_path):
                source_file = os.path.join(subfolder_path, file_name)

                if os.path.isfile(source_file):
                    target_file = os.path.join(output_subfolder, file_name)

                    os.makedirs(os.path.dirname(target_file), exist_ok=True)
                    print(source_file)
                    # exit(1)
                    cursor.execute(
                        'SELECT id FROM audio_files WHERE source_file = ?', (source_file,))
                    existing_record = cursor.fetchone()

                    if existing_record:
                        print(f"File already copied: {source_file}")
                        is_file_copied = True
                        continue

                    try:
                        if os.path.exists(target_file):
                            os.remove(target_file)
                        shutil.copy(source_file, target_file)

                        print("Copying {}".format(source_file))
                        print("***"*8)

                        is_audio_file = file_name.lower().endswith(("wav", "mp3", "flac", "webm"))
                        tag_data = None

                        insert_record(database_path, source_file, target_file,
                                      subfolder, is_audio_file, False, tag_data)
                    except PermissionError as e:
                        print(f"Permission error: {e}")
                        continue

            if not is_file_copied:
                tag_audio_folder(output_subfolder, database_path)


def convert_format(input, output, is_flac=True):
    try:
        if is_flac:
            cmd = [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-i",
                input,
                "-c:a",
                "flac",
                output,
            ]
        else:
            cmd = [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-i",
                input,
                "-c:a",
                "libmp3lame",
                "-q:a",
                "2",
                output,
            ]

        subprocess.run(
            cmd,
            check=True,
        )
        os.remove(input)
    except subprocess.CalledProcessError as e:
        print(f"Error converting format: {e}")


def tag_audio_folder(folder_path, database_path):
    cover_image = find_cover_image(folder_path)

    valid_extensions = (".wav", ".mp3", ".webm", ".flac")
    audio_files = [
        f for f in os.listdir(folder_path) if os.path.splitext(f.lower())[1] in valid_extensions
    ]

    if not audio_files:
        return

    audio_files.sort()

    for track_number, file_name in enumerate(audio_files, start=1):
        file_path = os.path.join(folder_path, file_name)
        original_file_path = file_path

        track_name = os.path.splitext(file_name)[0]
        album_name = os.path.basename(folder_path)

        if file_name.lower().endswith(".wav"):
            flac_file = os.path.splitext(file_path)[0] + ".flac"
            convert_format(file_path, flac_file, True)
            file_path = flac_file
        elif file_name.lower().endswith(".webm"):
            mp3_file = os.path.splitext(file_path)[0] + ".mp3"
            convert_format(file_path, mp3_file, False)
            file_path = mp3_file

        try:
            if file_path.lower().endswith(".flac"):
                audio = flac.FLAC(file_path)  # Use FLAC class for FLAC files
            else:
                audio = ID3(file_path)
        except ID3NoHeaderError:
            audio = ID3()

        try:
            if file_path.lower().endswith(".flac"):
                # Use FLAC metadata for FLAC files
                audio["TITLE"] = track_name
                audio["ALBUM"] = album_name
                audio["TRACKNUMBER"] = str(track_number)

                if cover_image:
                    pic = flac.Picture()
                    pic.type = 3
                    pic.mime = "image/jpeg"  # Ensure that 'mime' is a string

                    with open(cover_image, "rb") as cover_file:
                        pic.data = cover_file.read()
                    audio.add_picture(pic)
            else:
                # Use ID3 tags for other formats
                audio.add(TIT2(encoding=3, text=track_name))
                audio.add(TALB(encoding=3, text=album_name))
                audio.add(TRCK(encoding=3, text=str(track_number)))

                if cover_image:
                    with open(cover_image, "rb") as cover_file:
                        cover_data = cover_file.read()
                        audio["APIC"] = APIC(
                            encoding=3,
                            mime="image/jpeg",
                            type=3,
                            desc="Cover",
                            data=cover_data,
                        )

            audio.save(file_path)

            if "APIC" in audio:
                audio["APIC"] = None

            tag_data = str(audio)

            update_record(database_path, original_file_path,
                          True, tag_data, file_path)

        except Exception as e:
            print(f"Error tagging file: {file_path} - {e}")

        print(f"Tagging file: {file_path}")
        print(f"Album: {album_name}")
        print(f"Track: {track_name}")
        print(f"Track Number: {track_number}")
        print(f"Cover Image: {cover_image}")
        print("-" * 40)


def find_cover_image(folder_path):
    cover_extensions = ("jpg", "jpeg", "webp", "png")

    folder_path = "{}".format(folder_path)

    for cover_ext in cover_extensions:
        cover_name = f"cover.{cover_ext}"
        cover_path = os.path.join(folder_path, cover_name)

        if os.path.isfile(cover_path):
            print(f"Cover image found: {cover_path}")
            return cover_path

    print("Cover image not found.")
    return None


if __name__ == "__main__":
    input_folder = "/mnt/d/media/audiobooks".strip()
    database_path = "/mnt/d/media/audiobooks/audio_files.db"

    if not input_folder:
        print("Invalid input folder path.")
    else:
        parent_folder = os.path.dirname(input_folder)
        output_folder = os.path.join(
            parent_folder, "{}_tagged".format(os.path.basename(input_folder))
        )
        copy_and_tag_audio_folder(input_folder, output_folder, database_path)
        print("Copying and tagging completed successfully.")
