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
