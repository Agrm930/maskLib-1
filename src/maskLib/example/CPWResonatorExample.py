#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 21 18:29:41 2022

@author: sasha

Generating file for a wafer of
"""
import numpy as np

from dxfwrite import DXFEngine as dxf
from dxfwrite import const
from dxfwrite.vector2d import vadd

import maskLib.MaskLib as m
from maskLib.dcLib import ResistanceBarNegative
from maskLib.microwaveLib import CPW_launcher, CPW_straight, CPW_stub_open, CPW_stub_short, CPW_stub_round, CPW_bend, CPW_wiggles
from maskLib.microwaveLib import waffle

from maskLib.utilities import doMirrored
from maskLib.markerLib import MarkerSquare, MarkerCross

from maskLib.resonatorLib import JellyfishResonator

# ===============================================================================
# wafer setup
# ===============================================================================

w = m.Wafer('CPWResExample','DXF/',7000,7000,padding=2500,waferDiameter=m.waferDiameters['2in'],sawWidth=200,
                frame=1,solid=0,multiLayer=1)
#set wafer properties
# w.frame: draw frame layer?
# w.solid: draw things solid?
# w.multiLayer: draw in multiple layers?

# I set saw width to a round number (200 um) to make dicing easier

w.SetupLayers([
    ['BASEMETAL',4],
    ['BUSMAIN',3],
    ['XOR',5],
    ['SECONDLAYER',6],
    ['MARKERS',2]
    ])


#initialize the wafer
w.init()

#write the dicing border
w.DicingBorder()

class ResonatorChip6(m.Chip7mm):
    def __init__(self,wafer,chipID,layer,
                 total_lengths = [4300,4200,4100,4000,3900,3800],#total cpw length (sets the resonator frequency) (lo to high freq)
                 seps =       [7+4]*6,# resonator distance to cpw (sets each resonator's coupling)
                 indices =    [2,0,5,3,1,4], #these indices are chosen so no two adjacent resonators are close in frequency (to limit crosstalk)
                 res_spacing=1300 # how far apart the resonators are
                 ):
        m.Chip7mm.__init__(self,wafer,chipID,layer,defaults={'w':10, 's':6, 'radius':300,'r_out':10,'r_ins':10,'curve_pts':30})
        
        for s in self.structures:
            #move away from edge of chip
            s.shiftPos(340)
            
        #optical markers
        doMirrored(MarkerCross, self, (2900,2900),linewidth=5, chipCentered=True,layer='MARKERS')
        
        half_trace = self.defaults['w']/2 + self.defaults['s']
                
        CPW_launcher(self,0,padw=250,pads=80,r_ins=30,r_out=30,l_taper=400,layer='BUSMAIN')
        CPW_launcher(self,5,padw=250,pads=80,r_ins=30,r_out=30,l_taper=400,layer='BUSMAIN')        
        
        #calculate separation between the two structures
        xdist = self.structures[5].start[0] - self.structures[0].start[0]
        CPW_straight(self,0,xdist,layer='BUSMAIN')
        
        #make local copy of s0
        s0  = self.structures[0]
        
        #CPW resonator parameters
        coupler_length=180  #length of inductive coupler overlap
        straight_length=62  #length of straight cpw before meanders start
        straight_length2=94 #length of straight cpw after meanders
        pincer_tee_r=5        
        
        #inductively coupled lambda/4 cpw resonators
        for i in range(6):
            s1 = s0.cloneAlongLast((xdist/2 + res_spacing*(-1+indices[i]//2)-coupler_length/2,pow(-1,indices[i])*(half_trace + seps[i] + half_trace)))
            s1.defaults['s']=10
            s1.defaults['radius']=50
            s1.defaults['r_ins']=10
            s1.defaults['r_out']=20
            CPW_stub_short(self, s1, flipped=True)
            CPW_straight(self, s1, coupler_length)
            CPW_bend(self, s1, CCW=indices[i]%2)
            CPW_straight(self,s1,straight_length)
            CPW_bend(self,s1,CCW=indices[i]%2)
            CPW_straight(self,s1,coupler_length/2)#unsure the length here
            CPW_wiggles(self, s1, length=total_lengths[i]-1.5*coupler_length-straight_length - straight_length2-np.pi*s1.defaults['radius'], nTurns=4,start_bend=False,CCW=indices[i]%2)
            CPW_straight(self,s1,straight_length2-pincer_tee_r)
            #cap the cpw with a rounded capacitor
            CPW_stub_round(self,s1)
        
        #resistance bars on unused area of chip
        ResistanceBarNegative(self,m.Structure(self,self.centered((0,-3000))))
        ResistanceBarNegative(self,m.Structure(self,self.centered((0,3000))))

ResonatorChip = ResonatorChip6(w,'RESONATORS','BASEMETAL')
waffle(ResonatorChip, 171.3, width=20,bleedRadius=1,padx=700,layer='MARKERS')
ResonatorChip.save(w,drawCopyDXF=True,dicingBorder=False,center=True)

#global optical markers
doMirrored(MarkerCross, w, (15000,15000),linewidth=5, layer='MARKERS')


for i in range(len(w.chips)):
    #set the chip buffer
    w.setChipBuffer(ResonatorChip, i)
    #add large number labels
    w.add(dxf.text(str(i),vadd(w.chipPts[i],(5500,5800)),height=600,layer='BASEMETAL'))

# write all chips
w.populate()
w.save()