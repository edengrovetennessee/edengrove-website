#!/usr/bin/env bash
# The Census shapefiles the basemap is drawn from. ~45MB unpacked, so they
# are fetched rather than committed; map-build-detail.py reads them from
# data/tiger/ (or $TIGER).
#
#   bash data/map-fetch-tiger.sh && python3 data/map-build-detail.py
set -euo pipefail
cd "$(dirname "$0")"; mkdir -p tiger && cd tiger
B=https://www2.census.gov/geo/tiger/TIGER2023
get(){ f=$(basename "$1"); [ -f "$f" ] || curl -fsS -o "$f" "$1"; 
       d="${f%.zip}"; [ -d "$d" ] || { mkdir -p "$d"; unzip -oq "$f" -d "$d"; }; echo "  $d"; }
get "$B/PRISECROADS/tl_2023_47_prisecroads.zip"      # interstates + highways
get "$B/PLACE/tl_2023_47_place.zip"                  # city limits
for c in 47037 47187; do                             # Davidson, Williamson
  get "$B/ROADS/tl_2023_${c}_roads.zip"              # the residential texture
  get "$B/LINEARWATER/tl_2023_${c}_linearwater.zip"  # rivers and creeks
done
for c in 47037 47187 47021 47119; do                 # + Cheatham, Maury
  get "$B/AREAWATER/tl_2023_${c}_areawater.zip"      # lakes and river polygons
done
get "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip"
echo "done"
