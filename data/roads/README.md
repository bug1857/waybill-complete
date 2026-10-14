# Pinned Jaipur and Monaco roads

Map data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright),
distributed by [Geofabrik](https://download.geofabrik.de/), licensed under
[ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/).
This small derived extract is included so Free hosting does not download or
preprocess an entire Indian region on every build. It contains mapped roads,
not traffic observations or courier orders.

## Sources and checksums

| Input | SHA-256 |
| --- | --- |
| [Northern Zone, 12 October 2026](https://download.geofabrik.de/asia/india/northern-zone-261012.osm.pbf) | `12d993b3e8affd7784e28e0c9d85453281201a6210bfce8e869c682e5fff5a52` |
| [Monaco, 1 September 2026](https://download.geofabrik.de/europe/monaco-260901.osm.pbf) | `f2d904ee0aa156a2252c39c0ab80ca7b3fafb28da6a84b909084a26f068ac962` |
| Jaipur crop | `203351a54d050a413f2488adb0c775b75f0d6c953c546be7c7eebd0902803357` |
| Bundled `monaco-jaipur-release.osm.pbf` | `3a31b6f8f58812732870d619f7e5de5c34dbc62b15ae4c5d77e10ed797f52b09` |

The Northern Zone download also matched Geofabrik's published MD5
`a227a114543f5bfce966491a733df6dd`. The bundled PBF is 7,359,430 bytes.
Jaipur's input snapshot contains OSM data through 12 October 2026;
Monaco retains its September snapshot. The API's dataset fingerprint records
the combined checksum, pinned OSRM image, car profile and MLD algorithm.

## Reproduce the extraction

Using Osmium 1.18.0 / libosmium 2.22.0, download and verify the sources above,
then run (output files must not already exist):

```sh
osmium extract -s complete_ways -b 75.45,26.70,76.05,27.15 \
  northern-zone-261012.osm.pbf -o jaipur-northern-261012.osm.pbf
osmium check-refs jaipur-northern-261012.osm.pbf
osmium merge monaco-260901.osm.pbf jaipur-northern-261012.osm.pbf \
  -o monaco-jaipur-release.osm.pbf
sha256sum monaco-jaipur-release.osm.pbf
```

The crop contains 800,412 nodes and 142,986 ways; all way-node references passed.
`complete_ways` preserves whole ways and their nodes, including nodes beyond
the crop, but does not promise reference-complete relations. The combined
file has 842,115 nodes and 149,235 ways. A differently serialized PBF can have
a different file checksum; update the pinned build/fingerprint only after
revalidating the new input.

## Supported stop coordinates

Jaipur: latitude **26.72–27.13**, longitude **75.50–76.02**. This includes the
city centre, Amer, airport and Dahmi Kalan/western outskirts, not all Rajasthan.
The crop has a buffer beyond these bounds. The POI fetch remains a smaller
city-centre query. Monaco: latitude 43.725–43.752, longitude 7.405–7.44.
All stops in a road request must belong to one supported area. Mixed areas
and outside stops are rejected before OSRM; geographic estimates remain
explicitly selectable. Roads can extend beyond the stop boundary because
the source ways are complete. Car-access tags and map completeness are not
field-verified; route geometry is road-snapped, not live GPS or traffic.
