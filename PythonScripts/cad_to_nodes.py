"""
Convert AutoCAD exported coordinate data (test.txt) to nodes_Field.txt and
lines_Field.txt formats.

Input  : tab-separated AutoCAD export with Lines and Points
Outputs:
  nodes_Field_new.txt  ->  NodeID  X  Y  Z  SensorID  SetupID
  lines_Field_new.txt  ->  NodeID_Start  NodeID_End

Columns extracted from test.txt (0-indexed):
  Name       -> col 1
  End X/Y/Z  -> cols 11,12,13
  Start X/Y/Z-> cols 32,33,34
  Pos X/Y/Z  -> cols 39,40,41  (Point objects)
"""

import csv
import os
import sys

# ── paths ──────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_FILE  = os.path.join(BASE_DIR, "Node_Coordinates", "test.txt")
OUTPUT_FILE = os.path.join(BASE_DIR, "Node_Coordinates", "nodes_Field_new.txt")
LINES_FILE  = os.path.join(BASE_DIR, "Node_Coordinates", "lines_Field_new.txt")

# ── column indices (0-based) ───────────────────────────────────────────────────
COL_NAME  = 1
COL_END_X, COL_END_Y, COL_END_Z   = 11, 12, 13
COL_SX,    COL_SY,    COL_SZ      = 32, 33, 34
COL_PX,    COL_PY,    COL_PZ      = 39, 40, 41


def parse_coord(value: str):
    """Return float or None for empty / non-numeric cells."""
    try:
        return float(value.strip())
    except (ValueError, AttributeError):
        return None


def collect_coords_and_lines(filepath: str):
    """
    Read all unique (X, Y, Z) node coordinates and line connections from test.txt.

    Returns:
        coords : sorted list of unique (X, Y, Z) tuples
        raw_lines : list of ((sx,sy,sz), (ex,ey,ez)) for each CAD Line
    """
    coords: set[tuple[float, float, float]] = set()
    raw_lines: list[tuple] = []

    with open(filepath, encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh, delimiter="\t")
        next(reader)  # skip header row

        for row in reader:
            while len(row) <= max(COL_END_Z, COL_SZ, COL_PZ):
                row.append("")

            name = row[COL_NAME].strip().lower()

            if name == "line":
                sx, sy, sz = parse_coord(row[COL_SX]), parse_coord(row[COL_SY]), parse_coord(row[COL_SZ])
                ex, ey, ez = parse_coord(row[COL_END_X]), parse_coord(row[COL_END_Y]), parse_coord(row[COL_END_Z])
                if None not in (sx, sy, sz, ex, ey, ez):
                    coords.add((sx, sy, sz))
                    coords.add((ex, ey, ez))
                    raw_lines.append(((sx, sy, sz), (ex, ey, ez)))

            elif name == "point":
                x, y, z = parse_coord(row[COL_PX]), parse_coord(row[COL_PY]), parse_coord(row[COL_PZ])
                if None not in (x, y, z):
                    coords.add((x, y, z))

    sorted_coords = sorted(coords, key=lambda c: (c[2], c[1], c[0]))
    return sorted_coords, raw_lines


def build_coord_index(coords: list) -> dict:
    """Return a dict mapping (X,Y,Z) -> NodeID."""
    return {coord: idx for idx, coord in enumerate(coords)}


def write_nodes(coords: list[tuple[float, float, float]], filepath: str):
    """Write nodes in the nodes_Field.txt format."""
    with open(filepath, "w", encoding="utf-8", newline="\n") as fh:
        for node_id, (x, y, z) in enumerate(coords):
            sensor_id = 0
            setup_id  = 0
            def fmt(v):
                return str(int(v)) if v == int(v) else f"{v:.4f}".rstrip("0").rstrip(".")
            line = "\t".join([str(node_id), fmt(x), fmt(y), fmt(z),
                              str(sensor_id), str(setup_id)])
            fh.write(line + "\n")
    print(f"Wrote {len(coords)} nodes -> {filepath}")


def write_lines(raw_lines: list, coord_index: dict, filepath: str):
    """Write line connections as NodeID pairs, deduplicating reversed duplicates."""
    seen: set[tuple[int, int]] = set()
    pairs: list[tuple[int, int]] = []

    for (start, end) in raw_lines:
        nid_s = coord_index.get(start)
        nid_e = coord_index.get(end)
        if nid_s is None or nid_e is None:
            continue
        if nid_s == nid_e:
            continue  # zero-length line, skip
        key = (min(nid_s, nid_e), max(nid_s, nid_e))
        if key not in seen:
            seen.add(key)
            pairs.append((nid_s, nid_e))

    # Sort by first node ID, then second
    pairs.sort(key=lambda p: (min(p), max(p)))

    with open(filepath, "w", encoding="utf-8", newline="\n") as fh:
        for nid_s, nid_e in pairs:
            fh.write(f"{nid_s}\t{nid_e}\n")
    print(f"Wrote {len(pairs)} lines  -> {filepath}")


if __name__ == "__main__":
    if not os.path.isfile(INPUT_FILE):
        sys.exit(f"Input file not found: {INPUT_FILE}")

    coords, raw_lines = collect_coords_and_lines(INPUT_FILE)
    print(f"Found {len(coords)} unique node positions.")
    print(f"Found {len(raw_lines)} CAD lines.")

    coord_index = build_coord_index(coords)
    write_nodes(coords, OUTPUT_FILE)
    write_lines(raw_lines, coord_index, LINES_FILE)

    # Preview nodes
    print("\nFirst 10 nodes:")
    print("NodeID\tX\tY\tZ\tSensorID\tSetupID")
    with open(OUTPUT_FILE) as fh:
        for i, line in enumerate(fh):
            if i >= 10:
                break
            print(line, end="")

    # Preview lines
    print("\nFirst 10 lines:")
    print("Start\tEnd")
    with open(LINES_FILE) as fh:
        for i, line in enumerate(fh):
            if i >= 10:
                break
            print(line, end="")
