"""
GUI application to convert AutoCAD exported coordinate data (test.txt)
to nodes_Field.txt and lines_Field.txt formats.
"""

import csv
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# ── column indices (0-based) ───────────────────────────────────────────────────
COL_NAME  = 1
COL_END_X, COL_END_Y, COL_END_Z = 11, 12, 13
COL_SX,    COL_SY,    COL_SZ    = 32, 33, 34
COL_PX,    COL_PY,    COL_PZ    = 39, 40, 41


# ── core logic ─────────────────────────────────────────────────────────────────

def parse_coord(value):
    try:
        return float(value.strip())
    except (ValueError, AttributeError):
        return None


def collect_coords_and_lines(filepath):
    coords = set()
    raw_lines = []

    with open(filepath, encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh, delimiter="\t")
        next(reader)

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


def build_coord_index(coords):
    return {coord: idx for idx, coord in enumerate(coords)}


def fmt(v):
    return str(int(v)) if v == int(v) else f"{v:.4f}".rstrip("0").rstrip(".")


def write_nodes(coords, filepath):
    with open(filepath, "w", encoding="utf-8", newline="\n") as fh:
        for node_id, (x, y, z) in enumerate(coords):
            line = "\t".join([str(node_id), fmt(x), fmt(y), fmt(z), "0", "0"])
            fh.write(line + "\n")
    return len(coords)


def write_lines(raw_lines, coord_index, filepath):
    seen = set()
    pairs = []

    for (start, end) in raw_lines:
        nid_s = coord_index.get(start)
        nid_e = coord_index.get(end)
        if nid_s is None or nid_e is None or nid_s == nid_e:
            continue
        key = (min(nid_s, nid_e), max(nid_s, nid_e))
        if key not in seen:
            seen.add(key)
            pairs.append((nid_s, nid_e))

    pairs.sort(key=lambda p: (min(p), max(p)))

    with open(filepath, "w", encoding="utf-8", newline="\n") as fh:
        for nid_s, nid_e in pairs:
            fh.write(f"{nid_s}\t{nid_e}\n")
    return len(pairs)


# ── GUI ────────────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CAD → Nodes & Lines Converter")
        self.resizable(False, False)
        self.configure(padx=20, pady=20, bg="#f0f0f0")

        # ── styles ──
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TLabel",  background="#f0f0f0", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10), padding=6)
        style.configure("TEntry",  font=("Segoe UI", 10), padding=4)
        style.configure("Header.TLabel", font=("Segoe UI", 13, "bold"), background="#f0f0f0")
        style.configure("Log.TLabel", font=("Consolas", 9), background="#f0f0f0")

        # ── header ──
        ttk.Label(self, text="AutoCAD → nodes_Field / lines_Field",
                  style="Header.TLabel").grid(row=0, column=0, columnspan=3,
                                              pady=(0, 16), sticky="w")

        # ── input file ──
        ttk.Label(self, text="Archivo de entrada (.txt):").grid(
            row=1, column=0, sticky="w", pady=4)
        self.input_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.input_var, width=48).grid(
            row=1, column=1, padx=8)
        ttk.Button(self, text="Buscar…", command=self.browse_input).grid(
            row=1, column=2)

        # ── output folder ──
        ttk.Label(self, text="Carpeta de salida:").grid(
            row=2, column=0, sticky="w", pady=4)
        self.outdir_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.outdir_var, width=48).grid(
            row=2, column=1, padx=8)
        ttk.Button(self, text="Buscar…", command=self.browse_outdir).grid(
            row=2, column=2)

        # ── nodes filename ──
        ttk.Label(self, text="Nombre archivo nodos:").grid(
            row=3, column=0, sticky="w", pady=4)
        self.nodes_name_var = tk.StringVar(value="nodes_Field_new.txt")
        ttk.Entry(self, textvariable=self.nodes_name_var, width=48).grid(
            row=3, column=1, padx=8)

        # ── lines filename ──
        ttk.Label(self, text="Nombre archivo líneas:").grid(
            row=4, column=0, sticky="w", pady=4)
        self.lines_name_var = tk.StringVar(value="lines_Field_new.txt")
        ttk.Entry(self, textvariable=self.lines_name_var, width=48).grid(
            row=4, column=1, padx=8)

        # ── separator ──
        ttk.Separator(self, orient="horizontal").grid(
            row=5, column=0, columnspan=3, sticky="ew", pady=14)

        # ── convert button ──
        ttk.Button(self, text="Convertir", command=self.run_conversion,
                   style="TButton").grid(row=6, column=0, columnspan=3)

        # ── log area ──
        self.log_frame = tk.Frame(self, bg="#1e1e1e", bd=1, relief="sunken")
        self.log_frame.grid(row=7, column=0, columnspan=3,
                            pady=(14, 0), sticky="ew")
        self.log_text = tk.Text(
            self.log_frame, height=8, width=68,
            bg="#1e1e1e", fg="#cccccc",
            font=("Consolas", 9), relief="flat",
            state="disabled", wrap="word"
        )
        self.log_text.pack(padx=6, pady=6)

    # ── helpers ──

    def browse_input(self):
        path = filedialog.askopenfilename(
            title="Seleccionar archivo de entrada",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            self.input_var.set(path)
            # auto-fill output folder with input file's directory
            if not self.outdir_var.get():
                self.outdir_var.set(os.path.dirname(path))

    def browse_outdir(self):
        path = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if path:
            self.outdir_var.set(path)

    def log(self, msg, color="#cccccc"):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.configure(state="disabled")
        self.log_text.see("end")

    def clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    # ── conversion ──

    def run_conversion(self):
        input_path = self.input_var.get().strip()
        outdir     = self.outdir_var.get().strip()
        nodes_name = self.nodes_name_var.get().strip()
        lines_name = self.lines_name_var.get().strip()

        self.clear_log()

        # validation
        if not input_path or not os.path.isfile(input_path):
            messagebox.showerror("Error", "Selecciona un archivo de entrada válido.")
            return
        if not outdir:
            messagebox.showerror("Error", "Selecciona una carpeta de salida.")
            return
        if not nodes_name:
            messagebox.showerror("Error", "Ingresa el nombre del archivo de nodos.")
            return
        if not lines_name:
            messagebox.showerror("Error", "Ingresa el nombre del archivo de líneas.")
            return

        nodes_path = os.path.join(outdir, nodes_name)
        lines_path = os.path.join(outdir, lines_name)

        try:
            self.log(f"Leyendo: {input_path}")
            coords, raw_lines = collect_coords_and_lines(input_path)
            self.log(f"  → {len(coords)} posiciones únicas de nodos")
            self.log(f"  → {len(raw_lines)} líneas CAD")

            idx = build_coord_index(coords)

            n_nodes = write_nodes(coords, nodes_path)
            self.log(f"\n✔ Nodos escritos ({n_nodes})")
            self.log(f"  {nodes_path}")

            n_lines = write_lines(raw_lines, idx, lines_path)
            self.log(f"\n✔ Líneas escritas ({n_lines})")
            self.log(f"  {lines_path}")

            self.log("\n¡Conversión completada!")
            messagebox.showinfo("Listo", f"Conversión completada.\n\n"
                                         f"Nodos : {nodes_path}\n"
                                         f"Líneas: {lines_path}")

        except Exception as exc:
            self.log(f"\n✘ Error: {exc}")
            messagebox.showerror("Error durante conversión", str(exc))


if __name__ == "__main__":
    app = App()
    app.mainloop()
