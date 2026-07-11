#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jul 5 2026

@author: Agrim, with Claude (Claude Code)

Layer dose table utilities for ebeam lithography on an Elionix.

The fab pipeline: the design DXF is converted to GDS (KLayout; every
non-empty layer reaches the GDS), then the Elionix CONV software combines
the GDS with a layer dose table (.ldt) into a .car job file. CONV rejects
GDS layers that are missing from the .ldt as well as dose-0 entries, so
layers that are drawn but not ebeam-written must be unselected in CONV --
export_wafer_ldt prints which those are.

GDS layer numbering: the DXF->GDS converter numbers layers 1-based in
wafer layer-table order, so GDS layer = wafer.layerNums[name] + 1
(verified against a converted GDS).

Layers classify into three roles (also used to color the 'layer dose
table' sheet that Sweep3D.export_workbook writes):

  green  -- written by ebeam: has an .ldt entry (per-dose sweep layers
            plus unswept families with a base dose)
  yellow -- drawn on the chip but written optically / for reference: in
            the GDS but NOT in the .ldt -> unselect in Elionix CONV
  red    -- holds no shapes on the chip (DXF bookkeeping, wafer-level
            layers, base layers of swept dose families) -> never reaches
            the GDS, nothing to do
"""

# status fill colors for the xlsx 'layer dose table' sheet
# (Excel's standard good / neutral / bad fills)
XLSX_GREEN, XLSX_YELLOW, XLSX_RED = 'C6EFCE', 'FFEB9C', 'FFC7CE'


def gds_layer_number(wafer, name):
    '''GDS layer number of a wafer layer after DXF->GDS conversion
    (1-based wafer layer-table index, see module docstring)'''
    return wafer.layerNums[name] + 1


def export_ldt(path, entries):
    '''
    Write an Elionix layer dose table (.ldt) for ebeam lithography.

    entries: iterable of (gds_layer_number, dose) pairs. The dose is
    written divided by 1000 with 3 decimals, per the Elionix format:

        Dosetable V1.0
        Dose Assignment by Layer
        (2 ,   0.400)
        ...

    Returns the path written.
    '''
    with open(path, 'w') as f:
        f.write('\nDosetable V1.0\nDose Assignment by Layer\n')
        for num, dose in sorted(entries):
            f.write('(%d ,   %.3f)\n' % (num, dose / 1000.0))
        f.write('\n')
    return path


def layer_dose_rows(wafer, sweep, base_doses, optical_layers=()):
    '''
    One row per wafer layer for the xlsx 'layer dose table' sheet:
    (name, gds_number, 'yes'/'no' in the .ldt, dose or None, status color).

    Built from the same sweep.ldt_entries call that generates the .ldt, so
    the sheet always matches the actual dose table.

    wafer          -- MaskLib Wafer with its layer table set up
    sweep          -- Sweep3D/Sweep2D (provides ldt_entries)
    base_doses     -- {LAYER_FAMILY: dose} for unswept ebeam layers
    optical_layers -- names of layers drawn on the chip but written
                      optically or kept for reference (the 'yellow' set)
    '''
    dose_by_gds = dict(sweep.ldt_entries(
        lambda name: gds_layer_number(wafer, name), base_doses))
    rows = []
    for name in wafer.layerNames:
        gds = gds_layer_number(wafer, name)
        if gds in dose_by_gds:
            color = XLSX_GREEN
        elif name in optical_layers:
            color = XLSX_YELLOW
        else:
            color = XLSX_RED
        rows.append((name, gds,
                     'yes' if gds in dose_by_gds else 'no',
                     dose_by_gds.get(gds), color))
    return rows


def export_ldt_array(path, wafer, sweep, base_doses, optical_layers=()):
    '''
    Write the .ldt for a dose-array ebeam job (doses from a Sweep3D/Sweep2D
    plus base_doses) and print which drawn-but-undosed ('yellow') layers
    must be unselected in the Elionix CONV software when it combines the
    GDS and this .ldt into the .car file.

    Array-specific: the doses come from a sweep. A future design with e.g.
    one qubit per chip would assemble its own (gds_layer, dose) entries and
    call the generic export_ldt directly.

    Arguments as in layer_dose_rows. Returns the path written.
    '''
    export_ldt(path, sweep.ldt_entries(
        lambda name: gds_layer_number(wafer, name), base_doses))
    print('Elionix dose table saved to', path)

    yellow = ['%s (gds %d)' % (r[0], r[1])
              for r in layer_dose_rows(wafer, sweep, base_doses, optical_layers)
              if r[4] == XLSX_YELLOW]
    if yellow:
        print('\x1b[33mNOT in the .ldt -- UNSELECT these in Elionix CONV '
              '(GDS + ldt -> .car):\n  %s\x1b[0m' % ', '.join(yellow))
    return path
