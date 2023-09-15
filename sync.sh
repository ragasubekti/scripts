#!/usr/bin/env bash

! [[ $1 ]] && echo "Specify the device bruh" && exit 1

SDCARD_PATH=$(adb -s "$1" shell ls /storage | sed '1p;d')

adbsync \
    --adb-option "s" "$1" \
    --show-progress \
    --exclude "*.mp4" \
    --exclude "*.wav" \
    --exclude "*.mp3" \
    --exclude "*.flac" \
    --exclude "*.webm" \
    --exclude "Android/*" \
    pull \
    "/storage/emulated/0/" \
    "/backup/android/sdcard"

if ! [[ $SDCARD_PATH = "emulated" ]] && ! [[ $SDCARD_PATH = "self" ]]; then
    adbsync \
        --adb-option "s" "$1" \
        --show-progress \
        --exclude "Android/*" \
        --exclude "Audiobooks/*" \
        pull \
        "/storage/${SDCARD_PATH}/" \
        "/backup/android/external_sd"
fi