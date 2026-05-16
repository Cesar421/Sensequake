#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 20 14:39:44 2026

@author: winkle14
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt
from scipy.fft import rfft, rfftfreq

# =========================
# 1. 24-bit Decoder
# =========================
def read_int24_le(data):
    b = np.frombuffer(data, dtype=np.uint8)
    b = b.reshape(-1, 3)

    vals = (b[:,0].astype(np.int32) |
           (b[:,1].astype(np.int32) << 8) |
           (b[:,2].astype(np.int32) << 16))

    # Sign extension
    mask = 1 << 23
    vals = (vals ^ mask) - mask

    return vals

# =========================
# 2. Datei einlesen
# =========================
def load_file(filename):
    with open(filename, "rb") as f:
        data = f.read()

    # Header finden
    header_end = data.find(b"\r\n\r\n") + 4
    header = data[:header_end].decode("ascii")
    binary = data[header_end:]

    # Samplingrate extrahieren
    fs = None
    for line in header.splitlines():
        if "Sampling Frequency" in line:
            fs = float(line.split(":")[1])
    
    if fs is None:
        raise ValueError("Samplingrate nicht gefunden!")

    # Daten dekodieren
    values = read_int24_le(binary)
    samples = values.reshape(-1, 6)

    df = pd.DataFrame(samples, columns=["Vx","Vy","Vz","Ax","Ay","Az"])

    return df, fs, header

# =========================
# 3. FFT Analyse
# =========================
def compute_fft(signal, fs):
    N = len(signal)
    f = rfftfreq(N, 1/fs)
    spectrum = np.abs(rfft(signal)) / N
    return f, spectrum

# =========================
# 4. dominante Frequenz finden
# =========================
def dominant_frequency(signal, fs, fmin=0.5, fmax=100):
    f, spec = compute_fft(signal, fs)

    mask = (f >= fmin) & (f <= fmax)
    f_sel = f[mask]
    spec_sel = spec[mask]

    idx = np.argmax(spec_sel)
    return f_sel[idx], spec_sel[idx]

# =========================
# 5. RMS berechnen
# =========================
def rms(x):
    return np.sqrt(np.mean(x**2))

# =========================
# 6. Analyse durchführen
# =========================
def analyze(df, fs):
    results = {}

    print("\n=== Schwingungsanalyse ===\n")

    for col in df.columns:
        sig = df[col].values

        # Offset entfernen
        sig = sig - np.mean(sig)

        # Kennwerte
        r = rms(sig)
        f_dom, amp = dominant_frequency(sig, fs)

        results[col] = {
            "RMS": r,
            "Dominant Frequency": f_dom,
            "Amplitude": amp
        }

        print(f"{col}:")
        print(f"  RMS: {r:.2f}")
        print(f"  Dominante Frequenz: {f_dom:.2f} Hz")
        print()

    return results

# =========================
# 7. Plot
# =========================
def plot_signals(df, fs):
    t = np.arange(len(df)) / fs

    plt.figure(figsize=(12,8))

    for i, col in enumerate(df.columns):
        plt.subplot(3,2,i+1)
        plt.plot(t, df[col])
        plt.title(col)
        plt.xlabel("Zeit [s]")

    plt.tight_layout()
    plt.show()

def plot_fft(df, fs):
    plt.figure(figsize=(12,8))

    for i, col in enumerate(df.columns):
        sig = df[col].values - np.mean(df[col].values)
        f, spec = compute_fft(sig, fs)

        plt.subplot(3,2,i+1)
        plt.semilogy(f, spec)
        plt.xlim(0, 100)
        plt.title(col + " FFT")
        plt.xlabel("Hz")

    plt.tight_layout()
    plt.show()

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    filename = "/media/winkle14/Extreme SSD/openBridge/bautzen02/Setup1_sensor1.bin"

    df, fs, header = load_file(filename)

    print("Samplingrate:", fs)
    print("Samples:", len(df))

    results = analyze(df, fs)

    plot_signals(df, fs)
    plot_fft(df, fs)