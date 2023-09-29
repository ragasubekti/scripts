#!/usr/bin/env bash

ACCEPTED_FORMAT=(mp4 webm mkv)
SOURCE_DIRECTORY=$1
TARGET_DIRECTORY=$2

! [[ $1 ]] && echo "Source Directory Required" && exit 1

find_cmd_params() {
    local _iname=""

    for _format in "${ACCEPTED_FORMAT[@]}"; do
        ! [[ $_format = "${ACCEPTED_FORMAT[0]}" ]] && _iname="${_iname} -o"

        _iname="${_iname} -iname *.${_format}"
    done

    echo $_iname
}

transcode_ffmpeg() {
    local _input=$1
    local _filename=$(basename "$_input")

    # Q: Do we really need to specify the VAAPI device?

    ffmpeg \
        -hide_banner \
        -v fatal \
        -stats \
        -hwaccel vaapi \
        -hwaccel_device /dev/dri/renderD128 \
        -i "${_input}" \
        -c:v h265_vaapi \
        "${TARGET_DIRECTORY}/${_filename}"
}

export -f transcode_ffmpeg

get_files() {
    ! [[ -d "${SOURCE_DIRECTORY}"  ]] && exit 2
    _params=$(find_cmd_params)

    find "${SOURCE_DIRECTORY}" ${params} -print0 | xargs -0 -I {} bash -c 'transcode_ffmpeg "$@"' _ {}
}

get_files
