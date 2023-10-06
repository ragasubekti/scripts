from genericpath import isfile
import os
import shutil
from mutagen.id3 import ID3, APIC, TIT2, TALB, TRCK, ID3NoHeaderError, PictureType
from mutagen import flac, File

import subprocess

def copy_and_tag_audio_folder(input_folder, output_folder):
    input_folder = input_folder.strip()
    output_folder = output_folder.strip()

    if not os.path.exists(input_folder) or not os.path.isdir(input_folder):
        print("Invalid input folder path or folder does not exist.")
        return

    for root, subfolders, files in os.walk(input_folder):
        for subfolder in subfolders[:]:
            subfolder_path = os.path.join(root, subfolder)
            output_subfolder = os.path.join(output_folder, os.path.relpath(subfolder_path, input_folder))
            os.makedirs(output_subfolder, exist_ok=True)

            for file_name in os.listdir(subfolder_path):
                source_file = os.path.join(subfolder_path, file_name)

                if os.path.isfile(source_file):
                    target_file = os.path.join(output_subfolder, file_name)
                    
                    os.makedirs(os.path.dirname(target_file), exist_ok=True)
                    
                    try:
                        if os.path.exists(target_file):
                            os.remove(target_file)  # Remove existing file
                        shutil.copy(source_file, target_file)
                        print("Copying {}".format(source_file))
                    except PermissionError as e:
                        print(f"Permission error: {e}")
                        continue

            tag_audio_folder(output_subfolder)

def convert_wav_to_flac(input_wav, output_flac):
    try:
        subprocess.run(['ffmpeg', '-y','-i', input_wav, '-c:a', 'flac', output_flac], check=True)
        os.remove(input_wav)
    except subprocess.CalledProcessError as e:
        print(f"Error converting WAV to FLAC: {e}")

def tag_audio_folder(folder_path):
    cover_image = find_cover_image(folder_path)

    audio_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('wav', 'mp3'))]

    if not audio_files:
        return

    audio_files.sort()

    for track_number, file_name in enumerate(audio_files, start=1):

        file_path = os.path.join(folder_path, file_name)
        track_name = os.path.splitext(file_name)[0]
        album_name = os.path.basename(folder_path)
        
        if file_name.lower().endswith('.wav'):
            # Convert WAV to FLAC
            flac_file = os.path.splitext(file_path)[0] + '.flac'
            convert_wav_to_flac(file_path, flac_file)
            file_path = flac_file
        
        try:
            if file_path.lower().endswith('.flac'):
                audio = flac.FLAC(file_path)  # Use FLAC class for FLAC files
            else:
                audio = ID3(file_path)
        except ID3NoHeaderError:
            audio = ID3()

        try:
            if file_path.lower().endswith('.flac'):
                # Use FLAC metadata for FLAC files
                audio['TITLE'] = track_name
                audio['ALBUM'] = album_name
                audio['TRACKNUMBER'] = str(track_number)
                
                if cover_image:
                    pic = flac.Picture()
                    pic.type = 3
                    pic.mime = 'image/jpeg'  # Ensure that 'mime' is a string

                    with open(cover_image, 'rb') as cover_file:
                        pic.data = cover_file.read()
                    audio.add_picture(pic)
            else:
                # Use ID3 tags for other formats
                audio.add(TIT2(encoding=3, text=track_name))
                audio.add(TALB(encoding=3, text=album_name))
                audio.add(TRCK(encoding=3, text=str(track_number)))

                if cover_image:
                    with open(cover_image, 'rb') as cover_file:
                        cover_data = cover_file.read()
                        audio['APIC'] = APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=cover_data)

            audio.save(file_path)

        except Exception as e:
            print(f"Error tagging file: {file_path} - {e}")


        print(f"Tagging file: {file_path}")
        print(f"Album: {album_name}")
        print(f"Track: {track_name}")
        print(f"Track Number: {track_number}")
        print(f"Cover Image: {cover_image}")
        print("-" * 40)

def find_cover_image(folder_path):
    cover_extensions = ('jpg', 'jpeg', 'webp',  'png')
    
    folder_path = u'{}'.format(folder_path)
    
    
    for cover_ext in cover_extensions:
        cover_name = f'cover.{cover_ext}'
        cover_path = os.path.join(folder_path, cover_name)

        if os.path.isfile(cover_path):
            print(f"Cover image found: {cover_path}")
            return cover_path

    print("Cover image not found.")
    return None



if __name__ == "__main__":
    input_folder = input("Enter the input folder path: ").strip()

    if not input_folder:
        print("Invalid input folder path.")
    else:
        parent_folder = os.path.dirname(input_folder)
        output_folder = os.path.join(parent_folder, "{}.tagged".format(os.path.basename(input_folder)))
        copy_and_tag_audio_folder(input_folder, output_folder)
        print("Copying and tagging completed successfully.")