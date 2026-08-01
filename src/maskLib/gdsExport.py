#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jul 5 2026

@author: Agrim, with Claude (Claude Code)

DXF -> GDS conversion using the KLayout Python module ('pip install
klayout') -- the same engine as the KLayout GUI, so results match a manual
conversion exactly, but with one crucial improvement: the GDS layer
numbers are set EXPLICITLY from the wafer layer table instead of relying
on KLayout's automatic assignment. That guarantees the GDS numbering
always matches the .ldt dose table (see maskLib.layerDoseTable).

Only layers that contain shapes exist in a GDS file (GDS has no layer
table), so empty layers -- e.g. base layers of swept dose families --
vanish in conversion automatically.

Also home to the klayout-Layout export helpers used by write-file
assembly scripts (2026-07-30, hoisted from jj_master's PEC array
designs): write_layout (one Layout -> GDS + OASIS + optional .ldt) and
split_layout (one master Layout -> a copy holding only the given GDS
layer numbers, e.g. to split a write into a designs file and a labels
file).
"""


def dxf_to_gds(dxf_path, gds_path, gds_layer_numbers, keep_layers=None):
    '''
    Convert a DXF file to GDS, renumbering layers by name.

    dxf_path          -- input DXF
    gds_path          -- output GDS
    gds_layer_numbers -- {layer_name: gds_layer_number}; for a maskLib
                         wafer build it as
                         {name: gds_layer_number(wafer, name)
                          for name in wafer.layerNames}
    keep_layers       -- optional set of layer names; if given, every other
                         layer is dropped from the GDS. Use to split one
                         DXF into per-mask GDS files (e.g. one per
                         photolithography step).

    Layer names found in the DXF but missing from the mapping are left to
    KLayout's automatic numbering, with a loud warning -- their numbers
    are NOT guaranteed to match the .ldt. Returns gds_path.
    '''
    import klayout.db as kdb   # deferred: maskLib itself must not require klayout

    layout = kdb.Layout()
    layout.read(dxf_path)

    if keep_layers is not None:
        keep = set(keep_layers)
        for i in list(layout.layer_indexes()):
            if layout.get_info(i).name not in keep:
                layout.delete_layer(i)

    unmapped = []
    for i in layout.layer_indexes():
        info = layout.get_info(i)
        if not info.name:
            continue   # already numeric (e.g. DXF layer '0' comes in as 0/0)
        if info.name in gds_layer_numbers:
            layout.set_info(i, kdb.LayerInfo(gds_layer_numbers[info.name], 0,
                                             info.name))
        elif any(not cell.shapes(i).is_empty() for cell in layout.each_cell()):
            # only shape-holding layers matter: empty ones (e.g. dxfwrite's
            # VIEWPORTS bookkeeping layer) never reach the GDS at all
            unmapped.append(info.name)
    if unmapped:
        print('\x1b[31mWARNING: DXF layers not in the mapping, GDS numbers '
              'NOT guaranteed to match the .ldt: %s\x1b[0m'
              % ', '.join(unmapped))

    layout.write(gds_path)
    return gds_path


def write_layout(layout, path_stem, formats=('gds', 'oas'), ldt_entries=None,
                 quiet=False):
    '''
    Write one klayout Layout under every requested format, plus its dose
    table if given.

    layout      -- a klayout.db.Layout, fully assembled
    path_stem   -- output path WITHOUT extension; each format appends its
                   own (path/to/chip -> chip.gds, chip.oas, chip.ldt)
    formats     -- iterable of klayout-writable extensions. The default
                   writes both GDS (what Elionix CONV consumes) and OASIS
                   (~30x smaller twin of the same layout; klayout picks
                   the format from the extension).
    ldt_entries -- optional iterable of (gds_layer_number, dose_uC_cm2)
                   pairs, passed to maskLib.layerDoseTable.export_ldt.
                   The caller owns the convention that every entry
                   matches a GDS layer.

    Returns the list of paths written, ldt last.
    '''
    import os

    paths = []
    for ext in formats:
        p = path_stem + '.' + ext.lstrip('.')
        layout.write(p)
        paths.append(p)
    if ldt_entries is not None:
        from maskLib.layerDoseTable import export_ldt
        paths.append(export_ldt(path_stem + '.ldt', ldt_entries))
    if not quiet:
        print('  %s: %s' % (os.path.basename(path_stem),
                            ' / '.join('%s %.1f MB' % (os.path.splitext(p)[1][1:],
                                                       os.path.getsize(p) / 1e6)
                                       for p in paths)))
    return paths


def strip_zero_dose(layout, ldt_entries, min_dose=0.5):
    '''
    Drop zero-dose layers from a (Layout, ldt entries) pair before export.

    A dvals ladder that includes relative dose 0 is the correct way to
    let a PEC engine assign "write nothing here" (regions whose demand
    is met entirely by backscatter from neighbours) -- but the Elionix
    hates layers with dose zero, so they must not reach the machine.
    This is the post-processing step: any layer whose dose is below
    min_dose uC/cm2 (default 0.5, i.e. anything that would print as
    0.000 in the 3-decimal ldt) is removed from BOTH the layout copy and
    the entries. Skipping a zero-dose layer loses nothing physically:
    dose 0 and "not written" are the same exposure.

    ldt_entries -- iterable of (gds_layer_number, dose_uC_cm2)

    Returns (stripped_layout, kept_entries, dropped_entries); the input
    layout is untouched. Feed the first two to write_layout, and log the
    third so travelers record what was dropped.
    '''
    entries = [(int(n), float(d)) for n, d in ldt_entries]
    dropped = [(n, d) for n, d in entries if d < min_dose]
    kept = [(n, d) for n, d in entries if d >= min_dose]
    keep_nums = {n for n, _ in kept}
    return split_layout(layout, keep_nums), kept, dropped


def split_layout(layout, keep_layers):
    '''
    A copy of a klayout Layout holding ONLY the given GDS layer numbers.

    The master layout is untouched: the copy keeps the full cell
    hierarchy and instances, with every layer whose number is not in
    keep_layers deleted (its shapes with it). Cells left empty by the
    deletion still exist but contain nothing, which GDS/OASIS writers
    handle fine.

    Use to split one master write file into sequential-write parts (all
    dose layers vs the label layers, one photolitho step per file, ...)
    without rebuilding the geometry per part:

        master = ...                      # one assembled Layout
        designs = split_layout(master, range(10, 1418))
        labels  = split_layout(master, (2, 3))

    keep_layers -- iterable of GDS layer NUMBERS (datatype ignored)

    Returns the new Layout.
    '''
    keep = set(int(n) for n in keep_layers)
    ly = layout.dup()
    for i in list(ly.layer_indexes()):
        if ly.get_info(i).layer not in keep:
            ly.delete_layer(i)
    return ly
