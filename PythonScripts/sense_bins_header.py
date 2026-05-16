import os
import re
import pandas as pd

# =========================
# 1. Header lesen
# =========================
def read_header(filename):
    with open(filename, "rb") as f:
        data = f.read()

    end = data.find(b"\r\n\r\n") + 4
    return data[:end].decode("ascii", errors="ignore")


# =========================
# 2. Header parsen
# =========================
def parse_header(header):
    info = {}
    for line in header.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            info[key.strip()] = value.strip()
    return info


# =========================
# 3. Dateien finden
# =========================
def find_files(setup="Setup8"):
    pattern = re.compile(rf"{setup}_sensor(\d+)\.bin")
    files = []

    for f in os.listdir("."):
        m = pattern.match(f)
        if m:
            sensor_id = int(m.group(1))
            files.append((sensor_id, f))

    files.sort()
    return [f for _, f in files]


# =========================
# 4. Tabelle erstellen
# =========================
def build_dataframe(files):
    rows = []

    for f in files:
        header = read_header(f)
        parsed = parse_header(header)
        parsed["File"] = f
        rows.append(parsed)

    df = pd.DataFrame(rows)
    df = df.set_index("File")

    return df


# =========================
# 5. Unterschiede markieren
# =========================
def highlight_differences(df):
    def highlight(col):
        # Referenz = erster Wert
        ref = col.iloc[0]
        return ["background-color: yellow" if v != ref else "" for v in col]

    return df.style.apply(highlight, axis=0)


# =========================
# 6. MAIN
# =========================
if __name__ == "__main__":
    setup = "Setup8"

    files = find_files(setup)

    if not files:
        print("Keine Dateien gefunden!")
        exit()

    df = build_dataframe(files)

    print("\n=== Header Tabelle ===\n")
    print(df)

    # Styling (nur in Notebook sichtbar)
    styled = highlight_differences(df)

    # Excel Export mit Markierungen
    output_file = f"{setup}_header_comparison.xlsx"
    styled.to_excel(output_file, engine="openpyxl")

    print(f"\nExcel-Datei gespeichert: {output_file}")