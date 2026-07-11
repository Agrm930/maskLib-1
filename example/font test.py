#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 3 2026

@author: Agrim, with Claude (Claude Code)

Font comparison test for chip labels.

Chip labels in 'junction array.py' are drawn by Chip.add_chip_label
(MaskLib.py), which converts text to polylines with ezdxf's text2path
using FontFace(family='Arial'). This script uses the same mechanism to
draw sample label text in several candidate fonts, one row per font, so
the outlines here are exactly what the mask would get.

Outputs:
    DXF/font_test.dxf -- one row per font (each on its own layer, so you
                         can toggle fonts on/off in your DXF viewer)
    DXF/font_test.png -- quick preview, no DXF viewer needed

To change the label font for real, edit the FontFace(family=...) line in
Chip.add_chip_label in src/maskLib/MaskLib.py.
"""

from ezdxf import path as ezpath  # noqa: F401  (text2path dependency)
from ezdxf.addons import text2path
from ezdxf.fonts.fonts import FontFace
from dxfwrite import DXFEngine as dxf

from maskLib.blockFont import block_text_rects

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import os
# output paths are relative to the repo root, so the script works no matter
# which directory it is run from (it now lives in example/)
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# sample text: a field label plus digits/letters used in labels & legend
SAMPLE = 'A0103 B1907 sfw=0.10um'
HEIGHT = 22          # same as the field label height in junction array.py
ROW_SPACING = 60     # vertical spacing between font rows in microns

# candidate fonts (standard on Windows; missing ones fall back silently --
# the duplicate check below catches that)
FONTS = [
    'Arial',            # current label font
    'Calibri',
    'Segoe UI',
    'Tahoma',
    'Verdana',
    'Times New Roman',
    'Georgia',
    'Consolas',         # monospaced
    'Courier New',      # monospaced
    'Lucida Console',   # monospaced
    'Cascadia Mono',    # monospaced
    'OCR A Extended',   # machine-readable style
]


def text_polylines(text, family, size):
    '''text -> list of point lists, exactly like Chip.add_chip_label'''
    paths = text2path.make_paths_from_str(text, font=FontFace(family=family), size=size)
    return [[(p.x, p.y) for p in path.flattening(0.01)] for path in paths]


drawing = dxf.drawing('DXF/font_test.dxf')
fig, ax = plt.subplots(figsize=(14, 0.45 * len(FONTS)))

signatures = {}   # outline fingerprint -> first font with that outline
for k, family in enumerate(FONTS):
    y = -k * ROW_SPACING
    polylines = text_polylines(SAMPLE, family, HEIGHT)

    # fingerprint the outlines: identical rows mean the font wasn't found
    # and ezdxf silently substituted the same fallback font
    sig = tuple(round(x, 3) for pts in polylines for xy in pts[:3] for x in xy)
    if sig in signatures:
        print('WARNING: %-16s renders identical to %s -- probably not installed'
              % (family, signatures[sig]))
    else:
        signatures[sig] = family

    layer = family.upper().replace(' ', '_')
    drawing.add_layer(layer, color=(k % 7) + 1)
    drawing.add(dxf.text(family, (-320, y), height=HEIGHT * 0.7, layer=layer))
    for pts in polylines:
        shifted = [(x, yy + y) for x, yy in pts]
        drawing.add(dxf.polyline(shifted, layer=layer, flags=1))
        ax.plot(*zip(*shifted), lw=0.7, color='k')
    ax.text(-20, y + HEIGHT / 2, family, ha='right', va='center', fontsize=9)

# block 5x7 font (maskLib.blockFont): characters built from disjoint
# rectangles -- no closed outline inside another (no donut/island problem
# for 0, B, A, D, 6, 8, 9 when shapes are filled downstream)
y = -len(FONTS) * ROW_SPACING
drawing.add_layer('BLOCK_5X7', color=1)
drawing.add(dxf.text('block 5x7', (-320, y), height=HEIGHT * 0.7, layer='BLOCK_5X7'))
for (rx, ry), rw, rh in block_text_rects(SAMPLE, HEIGHT, origin=(0, y)):
    pts = [(rx, ry), (rx + rw, ry), (rx + rw, ry + rh), (rx, ry + rh), (rx, ry)]
    drawing.add(dxf.polyline(pts, layer='BLOCK_5X7', flags=1))
    ax.fill(*zip(*pts), color='k', lw=0)
ax.text(-20, y + HEIGHT / 2, 'block 5x7', ha='right', va='center', fontsize=9)

drawing.save()
print('Saved DXF/font_test.dxf')

ax.set_aspect('equal')
ax.axis('off')
fig.tight_layout()
fig.savefig('DXF/font_test.png', dpi=200, bbox_inches='tight')
print('Saved DXF/font_test.png')
