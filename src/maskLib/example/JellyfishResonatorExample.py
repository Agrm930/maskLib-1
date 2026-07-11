#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 21 18:29:41 2022

@author: sasha

Generating file for a wafer of
"""


from dxfwrite import DXFEngine as dxf
from dxfwrite import const
from dxfwrite.vector2d import vadd

import maskLib.MaskLib as m
from maskLib.dcLib import ResistanceBarNegative
from maskLib.microwaveLib import CPW_launcher, CPW_straight
from maskLib.microwaveLib import waffle

from maskLib.utilities import doMirrored
from maskLib.markerLib import MarkerSquare, MarkerCross

from maskLib.resonatorLib import JellyfishResonator

# ===============================================================================
# wafer setup
# ===============================================================================

w = m.Wafer('JellyResExample','DXF/',7000,7000,padding=2500,waferDiameter=m.waferDiameters['2in'],sawWidth=200,
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
                 L_ws =       [320,305,290,280,265,250], #Lw the wiggle length of each resonator (sets the resonator frequency) (lo to high freq)
                 seps =       [200, 220,240,220,260,280],#resonator distance to cpw (sets each resonator's coupling)
                 indices =    [2,0,5,3,1,4], #these indices are chosen so no two adjacent resonators are close in frequency (to limit crosstalk)
                 res_spacing=1200 # how far apart the resonators are
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
        
        #write the resonators
        for i in range(6):
            # make a clone of s0 at varying distances along the main bus, some distance off to the side. 
            # alternate offseting left and right of the bus, and set the new direction to point away from the main bus
            s1 = s0.cloneAlongLast((xdist/2 + res_spacing*(-1.25+0.5*indices[i]),pow(-1,indices[i])*(half_trace + seps[i])),newDirection=(90+180*indices[i])%360)
            # this forms the jellyfish resonator. the capacitor is defined by w_cap and s_cap, similar to a cpw
            # the first two arguments are the width and height of the resonator. Weird things happen if the width is too small or height too short...
            # we specify the width of the inductor, and instead of giving a overall wire length, we set the number of turns, and the max wiggle length
            # wiggle length is half the distance from the the edge of one bend to the opposite side
            # we also want the wiggles to bunch near the capacitor (ialign) although this doesn't matter since we chose the height of the resonator to be exact
            JellyfishResonator(self,s1,500,412,None,r_ind=4,w_ind=3,w_cap=40,s_cap=20,maxWidth=L_ws[i]/2.,nTurns=19,ialign=const.TOP)
            #label the resonator for debugging
            self.add(dxf.text(str(i),vadd(s1.start,(360,80)),height=48,layer='FRAME'))
        
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