#!/usr/bin/env bash

VOLUME=("/data" "/books" "/data/calibre" "/backup")

for EVOL in "${VOLUME[@]}"; do
    btrfs filesystem defrag -czstd -r "${EVOL}"
done
