#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 20 14:42:48 2026

@author: winkle14
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import csd
from numpy.linalg import svd

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
# 1. FDD
# =========================
def compute_csd_matrix(data, fs, nperseg=4096):
    n_channels = data.shape[1]
    freqs = None

    S = []

    for i in range(n_channels):
        row = []
        for j in range(n_channels):
            f, Pxy = csd(data[:,i], data[:,j], fs=fs, nperseg=nperseg)
            row.append(Pxy)
        S.append(row)

    S = np.array(S)  # shape: (ch, ch, freq)
    S = np.transpose(S, (2,0,1))  # → (freq, ch, ch)

    return f, S


def fdd(data, fs):
    freqs, S = compute_csd_matrix(data, fs)

    singular_values = []
    singular_vectors = []

    for k in range(len(freqs)):
        U, s, Vh = svd(S[k,:,:])
        singular_values.append(s)
        singular_vectors.append(U)

    singular_values = np.array(singular_values)
    singular_vectors = np.array(singular_vectors)

    return freqs, singular_values, singular_vectors

# =========================
# 2. Peaks finden
# =========================
def find_peaks(freqs, sv, fmin=1, fmax=50, threshold=0.1):
    s1 = sv[:,0]

    mask = (freqs > fmin) & (freqs < fmax)
    f_sel = freqs[mask]
    s_sel = s1[mask]

    peaks = []

    for i in range(1, len(s_sel)-1):
        if s_sel[i] > s_sel[i-1] and s_sel[i] > s_sel[i+1]:
            if s_sel[i] > threshold * np.max(s_sel):
                peaks.append((f_sel[i], s_sel[i]))

    return peaks

# =========================
# 3. Modenformen extrahieren
# =========================
def extract_modes(peaks, freqs, singular_vectors):
    modes = []

    for f_peak, _ in peaks:
        idx = np.argmin(np.abs(freqs - f_peak))
        mode_shape = singular_vectors[idx][:,0]  # erster Singulärvektor
        modes.append((f_peak, mode_shape))

    return modes

# =========================
# 4. Plot
# =========================
def plot_fdd(freqs, sv):
    plt.figure(figsize=(10,5))
    plt.semilogy(freqs, sv[:,0], label="1. Singularwert")
    plt.xlim(0, 50)
    plt.xlabel("Frequenz [Hz]")
    plt.ylabel("Amplitude")
    plt.title("FDD Spectrum")
    plt.grid()
    plt.legend()
    plt.show()

# =========================
# 5. MAIN (Integration)
# =========================
if __name__ == "__main__":
    #from your_script import load_file  # dein vorheriges Script

    df, fs, header = load_file("Setup8_sensor1.bin")

    # nur relevante Kanäle (Acceleration oft besser für FDD)
    #data = df[["Ax","Ay","Az"]].values
    data = df[["Vz"]].values

    # Offset entfernen
    data = data - np.mean(data, axis=0)

    # FDD
    freqs, sv, U = fdd(data, fs)

    # Peaks
    peaks = find_peaks(freqs, sv)

    print("\nGefundene Eigenfrequenzen:")
    for f, amp in peaks:
        print(f"{f:.2f} Hz")

    # Modenformen
    modes = extract_modes(peaks, freqs, U)

    print("\nModenformen:")
    for f, mode in modes:
        print(f"\nMode bei {f:.2f} Hz:")
        print(mode)

    # Plot
    plot_fdd(freqs, sv)