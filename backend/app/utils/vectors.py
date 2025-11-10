"""Vector generation utilities for tags and colors using hashing and binning."""
from __future__ import annotations

import colorsys
from typing import Iterable, List

import mmh3
import numpy as np

# === CONFIG ===
TAG_DIM = 4096  # tune as needed (1024–4096 is common)

# 12 hue bins (30° each). Order matters—used for one-hot queries.
COLOR_BINS = [
    "red",
    "orange",
    "yellow",
    "chartreuse",
    "green",
    "teal",
    "cyan",
    "sky",
    "blue",
    "indigo",
    "violet",
    "magenta",
]
COLOR_DIM = len(COLOR_BINS)


# ========== TAGS ==========
def tag_vector(tags: Iterable[str], dim: int = TAG_DIM) -> List[float]:
    """
    Multi-hot hashing trick over `dim` bins, L2-normalized for cosine similarity.

    Args:
        tags: Iterable of tag strings
        dim: Dimension of output vector (default 4096)

    Returns:
        L2-normalized vector as list of floats
    """
    v = np.zeros(dim, dtype=np.float32)
    for t in tags:
        if not t:
            continue
        idx = mmh3.hash(t.strip().lower(), signed=False) % dim
        v[idx] += 1.0
    n = np.linalg.norm(v)
    return (v / n).tolist() if n else v.tolist()


# ========== COLORS ==========
def _hex_to_hue_deg(hex_code: str) -> float:
    """
    Convert '#RRGGBB' to hue degrees [0, 360).

    Args:
        hex_code: Color in format '#RRGGBB'

    Returns:
        Hue in degrees [0, 360)

    Raises:
        ValueError: If hex code is malformed
    """
    s = hex_code.lstrip("#")
    if len(s) != 6:
        raise ValueError(f"Bad hex color: {hex_code}")
    r = int(s[0:2], 16) / 255.0
    g = int(s[2:4], 16) / 255.0
    b = int(s[4:6], 16) / 255.0
    h, _, _ = colorsys.rgb_to_hsv(r, g, b)  # h in [0,1)
    return h * 360.0


def nearest_color_bin_index(hex_code: str) -> int:
    """
    Map a hex color to one of the 12 hue bins by simple 30° ranges.

    Args:
        hex_code: Color in format '#RRGGBB'

    Returns:
        Index into COLOR_BINS (0-11)

    Raises:
        ValueError: If hex code is malformed
    """
    h = _hex_to_hue_deg(hex_code)
    return int(h // 30) % COLOR_DIM


def color_vector(hex_colors: Iterable[str], dim: int = COLOR_DIM) -> List[float]:
    """
    Count colors per hue bin, L2-normalized for cosine similarity.

    Args:
        hex_colors: Iterable of hex color strings ('#RRGGBB')
        dim: Dimension of output vector (default 12)

    Returns:
        L2-normalized vector as list of floats
    """
    v = np.zeros(dim, dtype=np.float32)
    for hx in hex_colors:
        try:
            v[nearest_color_bin_index(hx)] += 1.0
        except Exception:
            # skip malformed hex codes
            continue
    n = np.linalg.norm(v)
    return (v / n).tolist() if n else v.tolist()


# ========== QUERY HELPERS ==========
def color_query_one_hot(name_or_hex: str) -> List[float]:
    """
    Build a one-hot color query vector (e.g., user clicks 'blue' or passes '#3B82F6').

    Args:
        name_or_hex: Either a color name from COLOR_BINS or hex code '#RRGGBB'

    Returns:
        One-hot vector as list of floats

    Raises:
        ValueError: If color name is not in COLOR_BINS or hex is malformed
    """
    q = np.zeros(COLOR_DIM, dtype=np.float32)
    if name_or_hex.startswith("#"):
        q[nearest_color_bin_index(name_or_hex)] = 1.0
    else:
        try:
            idx = COLOR_BINS.index(name_or_hex.strip().lower())
        except ValueError:
            raise ValueError(
                f"Unknown color bin '{name_or_hex}'. Valid: {COLOR_BINS}"
            )
        q[idx] = 1.0
    return q.tolist()
