#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created 2026

@author: Agrim

QubitLibExample: a 'qubit zoo' chip demonstrating the main functions in
maskLib.qubitLib, one of each with a text label.

Run from the repo root:
    masklib\\Scripts\\python.exe example\\QubitLibExample.py
Output: DXF/QubitLibExample*.dxf

Not shown here: Snailmon3D, Fluxonium3D, add_dose_array, add_JJ_dose_array --
those are whole-chip generators with many hardcoded positions, best used by
copying and editing their source.
"""
from dxfwrite import DXFEngine as dxf

import maskLib.MaskLib as m
from maskLib.qubitLib import TransmonPad, Transmon3D, Xmon, Elephantmon, Hamburgermon
from maskLib.junctionLib import ManhattanJunction, DolanJunction

# ===============================================================================
# wafer setup
# ===============================================================================

w = m.Wafer('QubitLibExample', 'DXF/', 7000, 7000, padding=2500,
            waferDiameter=m.waferDiameters['2in'], sawWidth=200,
            frame=1, solid=0, multiLayer=1)

w.SetupLayers([
    ['BASEMETAL', 4],
    ['MARKERS', 2],
    ])

# junction functions draw on wafer.JLAYER / wafer.ULAYER -- this creates
# the JUNCTION and UNDERCUT layers and points the wafer at them
w.setupJunctionLayers()

# Hamburgermon defines its metal through an XOR layer
w.setupXORlayer()

w.init()
w.DicingBorder()


# ===============================================================================
# demo chip
# ===============================================================================
class QubitZoo(m.Chip):
    def __init__(self, wafer, chipID, layer):
        # centerChip=False: keep one corner-based coordinate system for all
        # entity types (see CLAUDE.md pitfalls)
        m.Chip.__init__(self, wafer, chipID, layer,
                        defaults={'w': 10, 's': 6, 'radius': 50,
                                  'r_out': 5, 'r_ins': 5, 'curve_pts': 30},
                        centerChip=False)

        def label(text, pos):
            self.add(dxf.text(text, pos, height=80, layer='MARKERS'))

        # LAYER CONVENTION: do NOT pass layer= to these composite functions --
        # it collides with the junction internals. Metal shapes are drawn on
        # layer '0', which per the DXF block rules inherits the chip's layer
        # (BASEMETAL) when the chip block is inserted into the wafer. The
        # junction parts land on JUNCTION/UNDERCUT (from setupJunctionLayers).

        # --- TransmonPad: single pad, with contact tab (left) or slot (right)
        TransmonPad(self, (800, 1000), padwidth=250, padheight=250, tab=True)
        TransmonPad(self, (2000, 1000), padwidth=250, padheight=250, tab=False,
                    flipped=True)
        label('TransmonPad (tab / slot)', (600, 1300))

        # --- Transmon3D, Manhattan junction (the default junctionClass)
        # position = where the junction goes; pads grow outward from there.
        # NOTE: padw2/padh2 (right pad) do NOT default to padw/padh -- set both!
        Transmon3D(self, (3500, 2200), padw=800, padh=150, padw2=800, padh2=150,
                   leadw=85, leadh=20, separation=20)
        label('Transmon3D + ManhattanJunction', (2400, 2450))

        # --- Transmon3D, Dolan junction
        # junctionl (the gap the junction must span) is passed through kwargs
        Transmon3D(self, (3500, 3400), padw=800, padh=150, padw2=800, padh2=150,
                   leadw=85, leadh=20, separation=20,
                   junctionClass=DolanJunction, junctionl=20)
        label('Transmon3D + DolanJunction', (2400, 3650))

        # --- Xmon: cross-shaped planar qubit, junction location jj_loc in [0,11]
        Xmon(self, (1200, 5000), xmonw=25, xmonl=150, xmon_gapw=20, xmon_gapl=30,
             jj_loc=6)
        label('Xmon', (1000, 5500))

        # --- Elephantmon: planar pads in a ground cutout, Dolan junction
        # (takes a Structure object rather than a tuple)
        Elephantmon(self, m.Structure(self, start=(3000, 4700)),
                    tpad_width=200, tpad_height=300, tpad_gap=100, tpad_gap_gnd=50)
        label('Elephantmon', (3000, 5500))

        # --- Hamburgermon: planar qubit drawn on the XOR layer
        Hamburgermon(self, (4800, 4500))
        label('Hamburgermon', (4900, 5500))


zoo = QubitZoo(w, 'QUBITZOO', w.defaultLayer)
zoo.save(w, drawCopyDXF=True, dicingBorder=False)
w.setDefaultChip(zoo)

w.populate()
w.save()
