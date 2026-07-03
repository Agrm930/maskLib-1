# -*- coding: utf-8 -*-
"""
Created on Thu Aug 8 15:11:27 2024

@author: chuyao and paul 
"""
import sys
import os
current_dir = os.getcwd()
file_dir = os.path.dirname(__file__)

import maskLib
from dxfwrite.vector2d import vadd,midpoint,vmul_scalar,vsub
import math
import sys, subprocess, os, time
import numpy as np
from dxfwrite import DXFEngine as dxf
from dxfwrite import const
from dxfwrite.entities import Polyline
import ezdxf
import datetime

#from pya import Layout

import maskLib.MaskLib as m
from maskLib.Entities import SolidPline
from maskLib.utilities import cornerRound   
from dxfwrite.entities import Polyline
import maskLib.microwaveLib as mw
from maskLib.utilities import curveAB
from maskLib.markerLib import AlphaNumStr

from maskLib.markerLib import MarkerSquare, MarkerCross
from maskLib.utilities import doMirrored

def est_exposure_time(exposed_area, avg_dose, beam_current=5):
    """
    Estimate exposure time in minutes given the exposed area, average dose, and beam current.

    Args:
        exposed_area (float): area to be exposed in um^2
        avg_dose (float): average dose in uC/cm^2
        beam_current (float): beam current in nA, typically 5 nA
    """
    total_charge = avg_dose * exposed_area / (1e4)**2 # uC

    exposure_time = total_charge / (beam_current * 1e-3) / 60 # min

    return exposure_time

def round_sf(value, n):
    """
    Round a value to n significant figures
    
    Args:
        value (float): value to round
        n (int): number of significant figures
    """
    try:
        rounded_val = round(value, -int(np.floor(np.log10(abs(value)))) + (n - 1))
        # if rounded_val has >= n digits to the left of the decimal point, return int
        if len(str(rounded_val).split('.')[0]) >= n:
            rounded_val = int(rounded_val)
        return rounded_val
    except:
        return value


def grid_from_row(row, no_row):
    return [row for _ in range(no_row)]

def grid_from_column(column, no_column, no_row):
    return [[column[i] for _ in range(no_column)] for i in range(no_row)]

def grid_from_entry(entry, no_row, no_column):
    return [entry * np.ones(no_column) for _ in range(no_row)]

# A JJ chain method for designs from the Chakram/Shankar Labs
def JJ_chain(chip, structure, n_junc=3, JJlength=1.5, JJwidth=1.08, bridgewidth=1.78, gap=None, undercut=0.2, leadW=1, shiftL=0.5, bgcolor=None, CW=True, 
             leadundercut=True, Jlayer=None, Ulayer=None, Slayer='SHIFT', bridgelayer='BRIDGE',
             **kwargs):
    # print(JJlength,"jjchain")
    def struct():
        if isinstance(structure, m.Structure):
            return structure
        elif isinstance(structure, tuple):
            return m.Structure(chip, structure)
        else:
            return chip.structure(structure)


    if bgcolor is None:
        bgcolor = chip.wafer.bg()

    struct().translatePos((0, -JJwidth/2))

    for n in range(n_junc):
        undercutstruct = struct().clone()

        if n> 0:
            chip.add(dxf.rectangle(struct().getPos((0, JJwidth/2-bridgewidth/2)), gap, bridgewidth,
                                   rotation=struct().direction, bgcolor=bgcolor, 
                                #    layer="BRIDGE",
                                   layer=bridgelayer
                                   ),
                                   structure=structure, length= gap)
        
        undercutstruct.translatePos((gap if n>0 else 0, JJwidth/2), angle=0)

        mw.CPW_straight(chip, undercutstruct, w = JJwidth, s = undercut, length = JJlength, layer = Ulayer, rotation = struct().direction)
        
        chip.add(dxf.rectangle(struct().getPos((0, 0)), JJlength, JJwidth,
                                rotation=struct().direction, bgcolor=bgcolor, layer=Jlayer),
                                structure=structure, length= JJlength)
    
    # draw undercut at the corners of the array, where they meet the leads
    if leadundercut:
        undercutstruct = struct().clone()
        undercutstruct.translatePos((0, JJwidth/2), angle=0)
        mw.CPW_straight(chip, undercutstruct, w = leadW, s = undercut+JJwidth/2-leadW/2, length = shiftL, layer = Slayer, rotation = struct().direction)
        undercutstruct.translatePos((-n_junc*JJlength-(n_junc-1)*gap-shiftL, 0), angle=0)
        mw.CPW_straight(chip, undercutstruct, w = leadW, s = undercut+JJwidth/2-leadW/2, length = -shiftL, layer = Slayer, rotation = struct().direction)    

def junction_chain(chip, structure, n_junc_array=None, w=None, s=None, gap=None,
                   bgcolor=None, CW=True, finalpiece=True, Jlayer=None,
                   Ulayer=None, **kwargs):
    def struct():
        if isinstance(structure, m.Structure):
            return structure
        elif isinstance(structure, tuple):
            return m.Structure(chip, structure)
        else:
            return chip.structure(structure)

    if w is None:
        try:
            w = struct().defaults['w']
        except KeyError:
            print('\x1b[33mw not defined in ', chip.chipID)
    if s is None:
        try:
            s = struct().defaults['s']
        except KeyError:
            print('\x1b[33ms not defined in ', chip.chipID)
    if bgcolor is None:
        bgcolor = chip.wafer.bg()

    struct().translatePos((0, -s/2))

    # undercut amount = 0.3 approximate, set to 0.2 per UT-Austin practices
    UNDERCUT = 0.2

    for count, n in enumerate(n_junc_array):
        undercut = struct().clone()
        # undercut on outside of JJ array
        undercut.translatePos((0, s/2), angle=0)

        mw.CPW_straight(chip, undercut, w = s, s = UNDERCUT, length = n*gap + (n-1)*w, 
                        layer = Ulayer, rotation = struct().direction)

        chip.add(dxf.rectangle(struct().getPos((0, 0)), gap, s,
                                   rotation=struct().direction, bgcolor=bgcolor, layer=Ulayer),
                                   structure=structure, length= gap)
        for i in range(n-1):
            chip.add(dxf.rectangle(struct().getPos((0, 0)), w, s,
                                   rotation=struct().direction, bgcolor=bgcolor, layer=Jlayer),
                                   structure=structure, length= w)

            chip.add(dxf.rectangle(struct().getPos((0, 0)), gap, s,
                                   rotation=struct().direction, bgcolor=bgcolor, layer=Ulayer),
                                   structure=structure, length= gap)
        if len(n_junc_array) >= 1:

            if CW:
                if count % 2 == 0:
                    factor = -2
                    direction = -1
                else:
                    factor = 0
                    direction = 3
            else:
                if count % 2 == 0:
                    factor = 0
                    direction = 3
                else:
                    factor = -2
                    direction = -1

            if count + 1 < len(n_junc_array):
                chip.add(dxf.rectangle(struct().getPos((0, factor*s)), w + gap, 3 * s, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Jlayer))
                chip.add(dxf.rectangle(struct().getPos((w + gap, factor*s)), UNDERCUT, 3 * s, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Ulayer))
                chip.add(dxf.rectangle(struct().getPos((0, abs(direction)*s)), w + gap + UNDERCUT, UNDERCUT, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Ulayer))
                chip.add(dxf.rectangle(struct().getPos((0, factor*s-UNDERCUT)), w + gap + UNDERCUT, UNDERCUT, rotation=struct().direction,
                        bgcolor=bgcolor, layer=Ulayer))
                chip.add(dxf.rectangle(struct().getPos((-UNDERCUT, (factor+1)*s+UNDERCUT)), UNDERCUT, s-2*UNDERCUT, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Ulayer))
                struct().translatePos((0, direction * s), angle=180)

                # undercut.translatePos((0, s/2))
                # chip.add(dxf.rectangle(undercut.getPos((0, 0)), w+gap+UNDERCUT, UNDERCUT,
                #                    rotation=undercut.direction, bgcolor=bgcolor, layer=Ulayer),
                #                    structure=structure, length= gap)

            elif finalpiece:
                chip.add(dxf.rectangle(struct().getPos((0, factor*s)), w + gap, 3 * s, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Jlayer))
                chip.add(dxf.rectangle(struct().getPos((w + gap, factor*s)), UNDERCUT, 3 * s, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Ulayer))
                chip.add(dxf.rectangle(struct().getPos((-UNDERCUT, (factor+1)*s)), UNDERCUT, s, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Ulayer))
                struct().translatePos((0, direction * s), angle=180)
    

    struct().translatePos((0, +s/2))

# A small JJ method for designs from the Chakram/Shankar Labs
def smallJJ(chip, structure, gap=0.48, leadW = 1, fingerL=1.5, bigfingerW=0.41, smallfingerW=0.21, bridgeW=0.91, bridgeL=0.48, undercut=0.2, shiftL=0.5, **kwargs):

    # Jlayer="SJJLAYER", Ulayer='SULAYER', Slayer='SHIFT',
    Jlayer = kwargs.get('Jlayer', 'SJJLAYER')
    Ulayer = kwargs.get('Ulayer', 'SULAYER')
    Slayer = kwargs.get('Slayer', 'SHIFT')
    smallfingerlayer = kwargs.get('smallfingerlayer', 'SMALLFINGER')
    bridgelayer = kwargs.get('bridgelayer', 'BRIDGE')
    bigfingerlayer = kwargs.get('bigfingerlayer', 'BIGFINGER')    
    smallfingerW = kwargs.get('smallfingerwidth', smallfingerW)
    bigfingerW = kwargs.get('bigfingerwidth', smallfingerW+0.2)
    bridgeW = kwargs.get('bridgewidth', bridgeW)
    bridgeL = kwargs.get('bridgelength', bridgeL)
    #bridgelayer = kwargs.get('bridgelayer', bridgelayer)

    #locals().update(kwargs)

    undercutstruct = structure.clone()
    startX=0
    startY=leadW/2
    #finger length 1.36 # specified by LL # can be changed for UTA
    # chip.add(dxf.rectangle(structure.getPos((startX+bridgeL/2, startY-smallfingerW/2)), fingerL, smallfingerW,
    #                     rotation=structure.direction, bgcolor=chip.wafer.bg(), layer=Jlayer))
    # chip.add(dxf.rectangle(structure.getPos((startX-bridgeL/2, startY-bridgeW/2)), gap, bridgeW,
    #                     rotation=structure.direction, bgcolor=chip.wafer.bg(), layer=Ulayer))
    # #structure.translatePos((fingerL + gap, j_length/2), angle=0)
    # chip.add(dxf.rectangle(structure.getPos((startX-bridgeL/2, startY-bigfingerW/2)), -fingerL, bigfingerW,
    #                     rotation=structure.direction, bgcolor=chip.wafer.bg(), layer=Jlayer))
    
    #print locals dictionary

    chip.add(dxf.rectangle(structure.getPos((startX+bridgeL/2+fingerL, startY-smallfingerW/2)), -fingerL, smallfingerW,
                        rotation=structure.direction, bgcolor=chip.wafer.bg(), layer=smallfingerlayer))
    chip.add(dxf.rectangle(structure.getPos((startX+bridgeL/2, startY-bridgeW/2)), -bridgeL, bridgeW,
                        rotation=structure.direction, bgcolor=chip.wafer.bg(), layer=bridgelayer))
    #structure.translatePos((fingerL + gap, j_length/2), angle=0)
    chip.add(dxf.rectangle(structure.getPos((startX-bridgeL/2, startY-bigfingerW/2)), -fingerL, bigfingerW,
                        rotation=structure.direction, bgcolor=chip.wafer.bg(), layer=bigfingerlayer))



    # do undercut for U layer 
    undercutstruct.translatePos((startX+bridgeL/2, leadW/2), angle=0)
    # mw.CPW_taper(chip, undercut, length=0.5, w1 = j_length, w0 = leadW, s0 = bridgeW, s1 = bridgeW, layer = Ulayer)
    mw.CPW_straight(chip, undercutstruct, w = smallfingerW, s = undercut, length = fingerL, layer = Ulayer)
    undercutstruct_big = structure.clone()
    undercutstruct_big.translatePos((startX-bridgeL/2, leadW/2), angle=0)
    mw.CPW_straight(chip, undercutstruct_big, w = bigfingerW, s = undercut, length = -fingerL, layer = Ulayer)
    mw.CPW_straight(chip, undercutstruct, w = smallfingerW+2*undercut, s = leadW/2-smallfingerW/2-undercut, length = -shiftL, layer = Slayer)
    mw.CPW_straight(chip, undercutstruct_big, w = bigfingerW+2*undercut, s = leadW/2-bigfingerW/2-undercut, length = shiftL, layer = Slayer)

    # # do second undercut near bridge
    # if gap < bridgeW:
    #     undercutstruct.translatePos((-(bridgeW-gap), 0), angle=0)
    #     mw.CPW_straight(chip, undercutstruct, w = undercut, s = (leadW - j_length)/2, length = (bridgeW-gap), layer = Ulayer)

def smallJ(chip, structure, start, j_length, Jlayer, Ulayer, gap=0.14, lead = 1, ubridge_width=0.3, **kwargs):

    x, y = start

    tmp = round(200 * (lead - j_length) / 2) / 200 # rounding to make sure it falls in 5nm grid

    j_quad = dxf.polyline(points=[[x, y], [x+0.5, y-tmp], [x+0.5, y-tmp-j_length], [x, y-lead], [x, y]], bgcolor=chip.wafer.bg(), layer=Jlayer)
    j_quad.close()
    chip.add(j_quad)

    # u_quad = dxf.polyline(points=[[x, y], [x+0.5, y-tmp], [x+0.5, y-tmp-j_length], [x, y-lead], [x, y]], bgcolor=chip.wafer.bg(), layer=Ulayer)
    # u_quad.close()
    # chip.add(u_quad)

    structure.translatePos((0.5, - j_length/2), angle=0)

    undercut = structure.clone()
    
    finger_length = 1.5 #1.36 # specified by LL # can be changed for UTA I suppose.
    chip.add(dxf.rectangle(structure.getPos((0, 0)), finger_length, j_length,
                        rotation=structure.direction, bgcolor=chip.wafer.bg(), layer=Jlayer))
    chip.add(dxf.rectangle(structure.getPos((finger_length, -ubridge_width-lead/2 +j_length/2)), gap, 2*ubridge_width + lead,
                        rotation=structure.direction, bgcolor=chip.wafer.bg(), layer=Ulayer))
    structure.translatePos((finger_length + gap, j_length/2), angle=0)

    # do undercut for U layer 
    undercut.translatePos((-0.5, j_length/2), angle=0)
    mw.CPW_taper(chip, undercut, length=0.5, w1 = j_length, w0 = lead, s0 = ubridge_width, s1 = ubridge_width, layer = Ulayer)
    mw.CPW_straight(chip, undercut, w = j_length, s = ubridge_width, length = finger_length, layer = Ulayer)

    # do second undercut near bridge
    if gap < ubridge_width:
        undercut.translatePos((-(ubridge_width-gap), 0), angle=0)
        mw.CPW_straight(chip, undercut, w = j_length+2*ubridge_width, s = (lead - j_length)/2, length = (ubridge_width-gap), layer = Ulayer)

# make leads with half a loop to be connected to the JJ objects from either side. "start" is the center of the loop.
def half_loop_leads(chip, structure, start=(0,0), yflip=False,leadL=100, leadW=1, loopW=15, looplength_R=5, looplength_L=7, contactpads=True, contactW=20, contactL=10, wedgeL=10, 
                    shift=True, shiftW=0.5, layer='LOOP', shiftlayer='SHIFT', **kwargs):    
    # Create a template structure for the loop
    loop_structure = structure.clone()
    
    # If we're flipping, rotate the structure 180 degrees
    if yflip:
        loop_structure.translatePos(start, angle=180)
    else:
        loop_structure.translatePos(start)
    
    # Calculate the starting point based on whether we have contact pads
    if contactpads:
        if yflip:
            drawstart = loop_structure.getPos((0, -leadL - leadW - loopW/2 + contactL + wedgeL))
        else:
            drawstart = loop_structure.getPos((0, leadL + leadW + loopW/2 - contactL - wedgeL))
        leadL_adjusted = leadL - contactL - wedgeL
    else:
        if yflip:
            drawstart = loop_structure.getPos((0, -leadL - leadW - loopW/2))
        else:
            drawstart = loop_structure.getPos((0, leadL + leadW + loopW/2))
        leadL_adjusted = leadL
        
    # Create the core loop points - these will be the same regardless of orientation
    loop_points = [
        (drawstart[0] - leadW/2, drawstart[1]),
        (drawstart[0] - leadW/2, drawstart[1] + (-1 if yflip else 1) * leadL_adjusted),
        (drawstart[0] - leadW - loopW/2, drawstart[1] + (-1 if yflip else 1) * leadL_adjusted),
        (drawstart[0] - leadW - loopW/2, drawstart[1] + (-1 if yflip else 1) * (leadL_adjusted + looplength_L)),
        (drawstart[0] - loopW/2, drawstart[1] + (-1 if yflip else 1) * (leadL_adjusted + looplength_L)),
        (drawstart[0] - loopW/2, drawstart[1] + (-1 if yflip else 1) * (leadL_adjusted + leadW)),
        (drawstart[0] + loopW/2, drawstart[1] + (-1 if yflip else 1) * (leadL_adjusted + leadW)),
        (drawstart[0] + loopW/2, drawstart[1] + (-1 if yflip else 1) * (leadL_adjusted + looplength_R)),
        (drawstart[0] + leadW + loopW/2, drawstart[1] + (-1 if yflip else 1) * (leadL_adjusted + looplength_R)),
        (drawstart[0] + leadW + loopW/2, drawstart[1] + (-1 if yflip else 1) * leadL_adjusted),
        (drawstart[0] + leadW/2, drawstart[1] + (-1 if yflip else 1) * leadL_adjusted),
        (drawstart[0] + leadW/2, drawstart[1])
    ]
    
    # Add contact pads if needed
    if contactpads:
        if yflip:
            loop_points += [
                (drawstart[0] + contactW/2, drawstart[1] - wedgeL),
                (drawstart[0] + contactW/2, drawstart[1] - contactL - wedgeL),
                (drawstart[0] - contactW/2, drawstart[1] - contactL - wedgeL),
                (drawstart[0] - contactW/2, drawstart[1] - wedgeL)
            ]
        else:
            loop_points += [
                (drawstart[0] + contactW/2, drawstart[1] + wedgeL),
                (drawstart[0] + contactW/2, drawstart[1] + contactL + wedgeL),
                (drawstart[0] - contactW/2, drawstart[1] + contactL + wedgeL),
                (drawstart[0] - contactW/2, drawstart[1] + wedgeL)
            ]
    
    # Create and add the loop
    loop = dxf.polyline(points=loop_points, bgcolor=chip.wafer.bg(), layer=layer)
    loop.close()
    chip.add(loop)
    
    # Add shift lines if needed
    if shift:
        shift_structure = structure.clone()
        shift_structure.translatePos(start)
        
        if yflip:
            mw.Strip_straight(chip, (shift_structure.getPos((-loopW/2, -(loopW-shiftW)/2))), 
                            length=loopW, w=shiftW, layer=shiftlayer)
            mw.Strip_straight(chip, (shift_structure.getPos((-loopW/2-leadW, -leadW-(loopW+shiftW)/2))), 
                            length=(loopW+leadW)/2, w=shiftW, layer=shiftlayer)
            mw.Strip_straight(chip, (shift_structure.getPos((leadW/2, -leadW-(loopW+shiftW)/2))), 
                            length=(loopW+leadW)/2, w=shiftW, layer=shiftlayer)
        else:
            mw.Strip_straight(chip, (shift_structure.getPos((-loopW/2, (loopW-shiftW)/2))), 
                            length=loopW, w=shiftW, layer=shiftlayer)
            mw.Strip_straight(chip, (shift_structure.getPos((-loopW/2-leadW, leadW+(loopW+shiftW)/2))), 
                            length=(loopW+leadW)/2, w=shiftW, layer=shiftlayer)
            mw.Strip_straight(chip, (shift_structure.getPos((leadW/2, leadW+(loopW+shiftW)/2))), 
                            length=(loopW+leadW)/2, w=shiftW, layer=shiftlayer)

# Optimized half_loop_leads2 using structure for transformations
def half_loop_leads2(chip, structure, start=(0,0), yflip=False, leadL=100, leadW=1, loopW=15, 
                    loopLength=17, looplength_R=5, looplength_L=7, contactpads=True, contactW=20, 
                    contactL=10, wedgeL=10, shift=True, shiftW=0.5, shiftlayer='SHIFT', layer='LOOP',
                    contact_to_probe_leads=True, contact_to_probe_leads_Length=10, **kwargs):
    # Create template structure and position/rotate it appropriately
    loop_structure = structure.clone()
    
    if yflip:
        loop_structure.translatePos(start, angle=180)
    else:
        loop_structure.translatePos(start)
    
    # Calculate the starting point based on whether we have contact pads
    if contactpads:
        if yflip:
            drawstart = loop_structure.getPos((0, -leadL - leadW - loopW/2 + contactL + wedgeL))
        else:
            drawstart = loop_structure.getPos((0, leadL + leadW + loopLength/2 - contactL - wedgeL))
        leadL_adjusted = leadL - contactL - wedgeL
    else:
        if yflip:
            drawstart = loop_structure.getPos((0, -leadL - leadW - loopW/2))
        else:
            drawstart = loop_structure.getPos((0, leadL + leadW + loopLength/2))
        leadL_adjusted = leadL
        
    # Create the core loop points
    loop_points = [
        (drawstart[0] - leadW/2, drawstart[1]),
        (drawstart[0] - leadW/2, drawstart[1] + (-1 if yflip else 1) * leadL_adjusted),
        (drawstart[0] - leadW - loopW/2, drawstart[1] + (-1 if yflip else 1) * leadL_adjusted),
        (drawstart[0] - leadW - loopW/2, drawstart[1] + (-1 if yflip else 1) * (leadL_adjusted + looplength_L)),
        (drawstart[0] - loopW/2, drawstart[1] + (-1 if yflip else 1) * (leadL_adjusted + looplength_L)),
        (drawstart[0] - loopW/2, drawstart[1] + (-1 if yflip else 1) * (leadL_adjusted + leadW)),
        (drawstart[0] + loopW/2, drawstart[1] + (-1 if yflip else 1) * (leadL_adjusted + leadW)),
        (drawstart[0] + loopW/2, drawstart[1] + (-1 if yflip else 1) * (leadL_adjusted + looplength_R)),
        (drawstart[0] + leadW + loopW/2, drawstart[1] + (-1 if yflip else 1) * (leadL_adjusted + looplength_R)),
        (drawstart[0] + leadW + loopW/2, drawstart[1] + (-1 if yflip else 1) * leadL_adjusted),
        (drawstart[0] + leadW/2, drawstart[1] + (-1 if yflip else 1) * leadL_adjusted),
        (drawstart[0] + leadW/2, drawstart[1])
    ]
    
    # Add contact pads with appropriate configuration
    if contactpads:
        if contact_to_probe_leads:
            if yflip:
                loop_points += [
                    (drawstart[0] + contactW/2, drawstart[1] - wedgeL),
                    (drawstart[0] + contactW/2, drawstart[1] - contactL - wedgeL),
                    (drawstart[0] + leadW/2, drawstart[1] - contactL - wedgeL),
                    (drawstart[0] + leadW/2, drawstart[1] - contactL - wedgeL - contact_to_probe_leads_Length),
                    (drawstart[0] - leadW/2, drawstart[1] - contactL - wedgeL - contact_to_probe_leads_Length),
                    (drawstart[0] - leadW/2, drawstart[1] - contactL - wedgeL),
                    (drawstart[0] - contactW/2, drawstart[1] - contactL - wedgeL),
                    (drawstart[0] - contactW/2, drawstart[1] - wedgeL)
                ]
            else:
                loop_points += [
                    (drawstart[0] + contactW/2, drawstart[1] + wedgeL),
                    (drawstart[0] + contactW/2, drawstart[1] + contactL + wedgeL),
                    (drawstart[0] + leadW/2, drawstart[1] + contactL + wedgeL),
                    (drawstart[0] + leadW/2, drawstart[1] + contactL + wedgeL + contact_to_probe_leads_Length),
                    (drawstart[0] - leadW/2, drawstart[1] + contactL + wedgeL + contact_to_probe_leads_Length),
                    (drawstart[0] - leadW/2, drawstart[1] + contactL + wedgeL),
                    (drawstart[0] - contactW/2, drawstart[1] + contactL + wedgeL),
                    (drawstart[0] - contactW/2, drawstart[1] + wedgeL)
                ]
        else:
            if yflip:
                loop_points += [
                    (drawstart[0] + contactW/2, drawstart[1] - wedgeL),
                    (drawstart[0] + contactW/2, drawstart[1] - contactL - wedgeL),
                    (drawstart[0] - contactW/2, drawstart[1] - contactL - wedgeL),
                    (drawstart[0] - contactW/2, drawstart[1] - wedgeL)
                ]
            else:
                loop_points += [
                    (drawstart[0] + contactW/2, drawstart[1] + wedgeL),
                    (drawstart[0] + contactW/2, drawstart[1] + contactL + wedgeL),
                    (drawstart[0] - contactW/2, drawstart[1] + contactL + wedgeL),
                    (drawstart[0] - contactW/2, drawstart[1] + wedgeL)
                ]
    
    # Create and add the loop
    loop = dxf.polyline(points=loop_points, bgcolor=chip.wafer.bg(), layer=layer)
    loop.close()
    chip.add(loop)
    
    # Add shift lines if needed
    if shift:
        shift_structure = structure.clone()
        shift_structure.translatePos(start)
        
        if yflip:
            mw.Strip_straight(chip, (shift_structure.getPos((-loopW/2, -(loopW-shiftW)/2))), 
                            length=loopW, w=shiftW, layer=shiftlayer)
            mw.Strip_straight(chip, (shift_structure.getPos((-loopW/2-leadW, -leadW-(loopW+shiftW)/2))), 
                            length=(loopW+leadW)/2, w=shiftW, layer=shiftlayer)
            mw.Strip_straight(chip, (shift_structure.getPos((leadW/2, -leadW-(loopW+shiftW)/2))), 
                            length=(loopW+leadW)/2, w=shiftW, layer=shiftlayer)
        else:
            mw.Strip_straight(chip, (shift_structure.getPos((-loopW/2, (loopW-shiftW)/2))), 
                            length=loopW, w=shiftW, layer=shiftlayer)
            mw.Strip_straight(chip, (shift_structure.getPos((-loopW/2-leadW, leadW+(loopW+shiftW)/2))), 
                            length=(loopW+leadW)/2, w=shiftW, layer=shiftlayer)
            mw.Strip_straight(chip, (shift_structure.getPos((leadW/2, leadW+(loopW+shiftW)/2))), 
                            length=(loopW+leadW)/2, w=shiftW, layer=shiftlayer)

# Optimized leads_for_tmon_dosearray_custom using structure abstraction
def leads_for_tmon_dosearray_custom(chip, structure, start=(0,0), leadLpadtocontact=100, 
                                  leadLcontacttoJJ=50, leadW=1, startshifty=1.5, 
                                  contactW=20, contactL=10, wedgeL=10, layer='lead', 
                                  toporbottom='top', **kwargs):
    lead_structure = structure.clone()
    lead_structure.translatePos(start)
    
    if toporbottom == 'top':
        drawstart = lead_structure.getPos((0, 0))
        lead_points = [(drawstart[0] - leadW/2, drawstart[1])]
        lead_points += [
            (drawstart[0] - leadW/2, drawstart[1]-leadLpadtocontact),
            (drawstart[0] - contactW/2, drawstart[1]-leadLpadtocontact),
            (drawstart[0] - contactW/2, drawstart[1]-leadLpadtocontact - contactL),
            (drawstart[0] - leadW/2, drawstart[1]-leadLpadtocontact - contactL- wedgeL),
            (drawstart[0] - leadW/2, drawstart[1]-leadLpadtocontact - contactL- wedgeL - leadLcontacttoJJ),
            (drawstart[0] + leadW/2, drawstart[1]-leadLpadtocontact - contactL- wedgeL - leadLcontacttoJJ),
            (drawstart[0] + leadW/2, drawstart[1]-leadLpadtocontact - contactL- wedgeL),
            (drawstart[0] + contactW/2, drawstart[1]-leadLpadtocontact - contactL),
            (drawstart[0] + contactW/2, drawstart[1]-leadLpadtocontact),
            (drawstart[0] + leadW/2, drawstart[1]-leadLpadtocontact),
            (drawstart[0] + leadW/2, drawstart[1])
        ]
        lead = dxf.polyline(points=lead_points, bgcolor=chip.wafer.bg(), layer=layer)
        lead.close()
        chip.add(lead)
    elif toporbottom == 'bottom':
        # Use structure rotation instead of duplicating code
        bottom_structure = lead_structure.clone()
        bottom_structure.translatePos((0, 0), angle=180)  # Rotate 180 degrees
        
        drawstart = bottom_structure.getPos((0, 0))
        lead_points = [(drawstart[0] - leadW/2, drawstart[1])]
        lead_points += [
            (drawstart[0] - leadW/2, drawstart[1]+leadLpadtocontact),
            (drawstart[0] - contactW/2, drawstart[1]+leadLpadtocontact),
            (drawstart[0] - contactW/2, drawstart[1]+leadLpadtocontact + contactL),
            (drawstart[0] - leadW/2, drawstart[1]+leadLpadtocontact + contactL+ wedgeL),
            (drawstart[0] - leadW/2, drawstart[1]+leadLpadtocontact + contactL+ wedgeL + leadLcontacttoJJ),
            (drawstart[0] + leadW/2, drawstart[1]+leadLpadtocontact + contactL+ wedgeL + leadLcontacttoJJ),
            (drawstart[0] + leadW/2, drawstart[1]+leadLpadtocontact + contactL+ wedgeL),
            (drawstart[0] + contactW/2, drawstart[1]+leadLpadtocontact + contactL),
            (drawstart[0] + contactW/2, drawstart[1]+leadLpadtocontact),
            (drawstart[0] + leadW/2, drawstart[1]+leadLpadtocontact),
            (drawstart[0] + leadW/2, drawstart[1])
        ]
        lead = dxf.polyline(points=lead_points, bgcolor=chip.wafer.bg(), layer=layer)
        lead.close()
        chip.add(lead)
    else:
        print('toporbottom must be top or bottom')

# Enhanced shunted_loop_leads using structure abstraction
def shunted_loop_leads(chip, structure, start=(0,0), leadL=100, leadW=1, loopW=15, loopL=17, 
                      contactpads=True, contactW=20, contactL=10, wedgeL=10, shift=True, 
                      shiftW=0.5, layer='LOOP', **kwargs):
    loop_structure = structure.clone()
    loop_structure.translatePos(start)
    
    drawstart = loop_structure.getPos((0, leadL + leadW + loopW/2))
    
    # Outer loop
    loop_points = [
        (drawstart[0] - leadW/2, drawstart[1]), 
        (drawstart[0] - leadW/2, drawstart[1]-leadL), 
        (drawstart[0] - leadW - loopW/2, drawstart[1]-leadL), 
        (drawstart[0] - leadW - loopW/2, drawstart[1]-leadL - loopL), 
        (drawstart[0] - leadW/2, drawstart[1]- leadL - loopL), 
        (drawstart[0] - leadW/2, drawstart[1]- leadL - loopL - leadL),
        (drawstart[0] + leadW/2, drawstart[1]- leadL - loopL - leadL),
        (drawstart[0] + leadW/2, drawstart[1]- leadL - loopL),
        (drawstart[0] + leadW + loopW/2, drawstart[1]- leadL - loopL),
        (drawstart[0] + leadW + loopW/2, drawstart[1]- leadL),
        (drawstart[0] + leadW/2, drawstart[1]-leadL),
        (drawstart[0] + leadW/2, drawstart[1])
    ]
    
    loop = dxf.polyline(points=loop_points, bgcolor=chip.wafer.bg(), layer=layer)
    loop.close()
    chip.add(loop)

    # Inner loop
    loop_points2 = [
        (drawstart[0] - leadW/2, drawstart[1] - leadL - leadW),
        (drawstart[0] - leadW/2 - loopW/2 + leadW/2, drawstart[1] - leadL - leadW),
        (drawstart[0] - leadW/2 - loopW/2 + leadW/2, drawstart[1] - leadL - loopL + leadW),
        (drawstart[0] + loopW/2, drawstart[1] - leadL - loopL + leadW),
        (drawstart[0] + loopW/2, drawstart[1] - leadL - leadW)
    ]

    loop2 = dxf.polyline(points=loop_points2, bgcolor=chip.wafer.bg(), layer=layer)
    loop2.close()
    chip.add(loop2)

# Add structure support for add_imported_polyLine
def add_imported_polyLine(chip, structure, file_name, scale=1.0, rename_dict=None):
    """
    Add imported polyline with structure support for positioning and rotation
    """
    start = structure.getPos((0, 0))
    rotation = structure.direction
    
    doc = ezdxf.readfile(file_name)
    doc.header['$INSUNITS'] = 13 
    msp = doc.modelspace()

    for entity in msp:
        if entity.dxf.layer in rename_dict:
            layer_updated = rename_dict[entity.dxf.layer]
        else:
            layer_updated = entity.dxf.layer

        if entity.dxftype() != 'POLYLINE':
            print(f'Unsupported entity type: {entity.dxftype()}, skipping. Only POLYLINE supported')
            continue
        
        pts = list(entity.points())
        pts = [vmul_scalar(pt, scale) for pt in pts]
        
        # Apply rotation if needed
        if rotation != 0:
            rotation_rad = rotation * math.pi / 180
            pts = [
                (p[0] * math.cos(rotation_rad) - p[1] * math.sin(rotation_rad),
                 p[0] * math.sin(rotation_rad) + p[1] * math.cos(rotation_rad))
                for p in pts
            ]
        
        # Shift points to start
        pts = [vadd(start, pt) for pt in pts]
        
        try:
            pts.append(pts[0])
        except:
            continue
            
        poly = dxf.polyline(
            points=pts,
            color=entity.dxf.color,
            layer=layer_updated,
            bgcolor=chip.wafer.bg(layer_updated)
        )
        poly.POLYLINE_CLOSED = True
        poly.close()

        chip.add(poly)

# checker_board for resolution tests
def checker_board(chip, structure, start, num, square_size, layer=None):
    # Convert to use structure for positioning and rotation
    for i in range(num):
        for j in range(num):
            if (i+j) % 2 == 0:
                chip.add(dxf.rectangle(structure.getPos((start[0] + i * square_size, start[1] + j * square_size)), 
                                      square_size, square_size,
                                      rotation=structure.direction, bgcolor=chip.wafer.bg(), layer=layer))

# clover_leaf for 4-pt_probe measurement
def clover_leaf(chip, structure, start, diameter, layer=None, ptDensity=64, sf=1.05, ground_plane=True):
    # Use structure for positioning and rotation
    def get_pos(x, y):
        return structure.getPos((start[0] + x, start[1] + y))
    
    size = diameter/2

    if ground_plane:
        poly = dxf.polyline(points=[], bgcolor=chip.wafer.bg(), layer=layer)

        ## first quadrant
        # big circle
        poly.add_vertices(curveAB(get_pos(size/10, size), get_pos(size, size/10), ptDensity=ptDensity))
        # small circle
        poly.add_vertices(curveAB(get_pos(size/4, size/10), get_pos(size/4, -size/10), 
                                  ptDensity=ptDensity, clockwise=False, angleDeg=180))

        ## second quadrant
        # big circle
        poly.add_vertices(curveAB(get_pos(size, -size/10), get_pos(size/10, -size), ptDensity=ptDensity))

        # finish 1st poly object
        poly.add_vertices([
            get_pos(size/10, -sf*size), 
            get_pos(sf*size, -sf*size), 
            get_pos(sf*size, sf*size), 
            get_pos(size/10, sf*size)
        ])

        poly.close()
        chip.add(poly)

        # second poly object
        poly = dxf.polyline(points=[get_pos(size/10, -size)], bgcolor=chip.wafer.bg(), layer=layer)

        # small circle
        poly.add_vertices(curveAB(get_pos(size/10, -size/4), get_pos(-size/10, -size/4), 
                                  ptDensity=ptDensity, clockwise=False, angleDeg=180))

        ## third quadrant
        # big circle
        poly.add_vertices(curveAB(get_pos(-size/10, -size), get_pos(-size, -size/10), ptDensity=ptDensity))
        # small circle
        poly.add_vertices(curveAB(get_pos(-size/4, -size/10), get_pos(-size/4, size/10), 
                                  ptDensity=ptDensity, clockwise=False, angleDeg=180))

        ## fourth quadrant
        # big circle
        poly.add_vertices(curveAB(get_pos(-size, size/10), get_pos(-size/10, size), ptDensity=ptDensity))
        # small circle
        poly.add_vertices(curveAB(get_pos(-size/10, size/4), get_pos(size/10, size/4), 
                                  ptDensity=ptDensity, clockwise=False, angleDeg=180))

        # finish 2nd poly object
        poly.add_vertices([
            get_pos(size/10, sf*size), 
            get_pos(-sf*size, sf*size), 
            get_pos(-sf*size, -sf*size), 
            get_pos(size/10, -sf*size)
        ])

        poly.close() 
        chip.add(poly)
    else:
        poly = dxf.polyline(points=[], bgcolor=chip.wafer.bg(), layer=layer)        
        
        ## first quadrant
        # big circle
        poly.add_vertices(curveAB(get_pos(size/10, size), get_pos(size, size/10), ptDensity=ptDensity))
        # small circle
        poly.add_vertices(curveAB(get_pos(size/4, size/10), get_pos(size/4, -size/10), 
                                  ptDensity=ptDensity, clockwise=False, angleDeg=180))

        ## second quadrant
        # big circle
        poly.add_vertices(curveAB(get_pos(size, -size/10), get_pos(size/10, -size), ptDensity=ptDensity))
        # small circle
        poly.add_vertices(curveAB(get_pos(size/10, -size/4), get_pos(-size/10, -size/4), 
                                  ptDensity=ptDensity, clockwise=False, angleDeg=180))

        ## third quadrant
        # big circle
        poly.add_vertices(curveAB(get_pos(-size/10, -size), get_pos(-size, -size/10), ptDensity=ptDensity))
        # small circle
        poly.add_vertices(curveAB(get_pos(-size/4, -size/10), get_pos(-size/4, size/10), 
                                  ptDensity=ptDensity, clockwise=False, angleDeg=180))

        ## fourth quadrant
        # big circle
        poly.add_vertices(curveAB(get_pos(-size, size/10), get_pos(-size/10, size), ptDensity=ptDensity))
        # small circle
        poly.add_vertices(curveAB(get_pos(-size/10, size/4), get_pos(size/10, size/4), 
                                  ptDensity=ptDensity, clockwise=False, angleDeg=180))

        poly.close() 
        chip.add(poly)

# Flux Transformer drawing methods with structure pattern
def flux_transformer(chip, structure, 
                    large_rect_length=5000,
                    large_rect_width=2250,
                    small_rect_length=2500,
                    small_rect_width=100,
                    conductor_width=10,
                    Y_offset=0,
                    X_offset=0,
                    outer_radius=20,
                    inner_radius=10,
                    layer='FT'):
    """
    Draws the flux transformer with a large rectangle and a smaller finger-like
    rectangle, then applies fillets to both paths.
    Now uses structure for positioning and rotation.
    """
    startpoint = structure.getPos((0, 0))
    
    FT_outer, FT_outer_quadrants, FT_outer_clockwises = generate_ft_coordinates(
        large_rect_length, large_rect_width, small_rect_length, small_rect_width, 
        conductor_width, Y_offset, X_offset, outer_radius, inner_radius, outer=True
    )
    FT_inner, FT_inner_quadrants, FT_inner_clockwises = generate_ft_coordinates(
        large_rect_length, large_rect_width, small_rect_length, small_rect_width, 
        conductor_width, Y_offset, X_offset, outer_radius, inner_radius, outer=False
    )

    # Handle rotation by creating rotated points if needed
    if structure.direction != 0:
        # The filleted polylines are already created with the structure position as origin
        # We just need to handle rotation if the structure has been rotated
        rotation_rad = structure.direction * math.pi / 180
        transform_points = lambda pts: [
            (startpoint[0] + (p[0]*math.cos(rotation_rad) - p[1]*math.sin(rotation_rad)),
             startpoint[1] + (p[0]*math.sin(rotation_rad) + p[1]*math.cos(rotation_rad)))
            for p in pts
        ]
        
        # Apply rotation transformation to the points
        FT_outer = transform_points(FT_outer)
        FT_inner = transform_points(FT_inner)
        
        # Add polylines directly without using structure's position
        add_fillet_polyline(chip, FT_outer, FT_outer_quadrants, 
                          FT_outer_clockwises, (0, 0), 
                          outer_radius, inner_radius, layer)
        
        add_fillet_polyline(chip, FT_inner, FT_inner_quadrants, 
                          FT_inner_clockwises, (0, 0), 
                          inner_radius, outer_radius, layer)
    else:
        # No rotation needed, use the original approach
        add_fillet_polyline(chip, FT_outer, FT_outer_quadrants, 
                          FT_outer_clockwises, startpoint, 
                          outer_radius, inner_radius, layer)
        
        add_fillet_polyline(chip, FT_inner, FT_inner_quadrants, 
                          FT_inner_clockwises, startpoint, 
                          inner_radius, outer_radius, layer)

