#!/usr/bin/env bash

ACCEPTED_FORMAT=(mp4 webm mkv)
SOURCE_DIRECTORY=$1
TARGET_DIRECTORY=$2

! [[ $1 ]] && echo "Source Directory Required" && exit 1

find_cmd_params() {
    local _iname=""

    for _format in "${ACCEPTED_FORMAT[@]}"; do
        ! [[ $_format = "${ACCEPTED_FORMAT[0]}" ]] && _iname="${_iname} -o"

        _iname="${_iname} -iname \"*.${_format}\""
    done

    echo $_iname
}

transcode_ffmpeg() {
    # ffmpeg -i $1
    exit 0
}

get_files() {
    ! [[ -d $SOURCE_DIRECTORY  ]] && exit 2
    _params=$(find_cmd_params)

    find "${SOURCE_DIRECTORY}" ${_params} -print0 | xargs -0 -I {} bash -c 'transcode_ffmpeg "$@"' _ {}
}



get_files
