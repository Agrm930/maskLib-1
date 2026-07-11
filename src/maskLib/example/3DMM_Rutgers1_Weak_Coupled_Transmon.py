#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 17 13:52:03 2021

@author: sasha
"""
import numpy as np

from dxfwrite import DXFEngine as dxf
from dxfwrite import const

import maskLib.MaskLib as m
from maskLib.microwaveLib import Strip_straight
from maskLib.junctionLib import setupJunctionLayers,setupManhattanJAngles,JProbePads
from maskLib.junctionLib import ManhattanJunction
from maskLib.qubitLib import Transmon3D, qubit_defaults


from maskLib.markerLib import MarkerSquare, MarkerCross
from maskLib.utilities import doMirrored

# ===============================================================================
# wafer setup
# ===============================================================================

w = m.Wafer('3DMultimodeExample','DXF/',32000,2000,padding=2500,waferDiameter=m.waferDiameters['4in'],sawWidth=200,#sawWidth=m.sawWidths['8A'],
                frame=1,solid=0,multiLayer=1,singleChipColumn=True)
#set wafer properties
# w.frame: draw frame layer?
# w.solid: draw things solid?
# w.multiLayer: draw in multiple layers?
# w.singleChipColumn: only make one column of chips?

w.SetupLayers([
    ['BASEMETAL',4],
    ['DICEBORDER',5],
    ['MARKERS',3]
    ])

#setup junction layers
setupJunctionLayers(w)

#initialize the wafer (remember to finalize any wafer properties like layers before initializing!)
w.init()


#do dicing border (by default located on layer 'MARKERS', so let's put it on layer 'DICEBORDER' instead)
w.DicingBorder(layer='DICEBORDER')

#do optical markers
#(note: mirrorX and mirrorY are true by default, but I've exposed them here to demonstrate how they work)
doMirrored(MarkerCross, w, (16000,16000),(200,200), 5,layer='MARKERS',mirrorX=True,mirrorY=True)

#do ebeam markers 
markerpts = [(15000,15000),(14000,14000),(13000,13000),(12000,12000)]
for pt in markerpts:
    #(note: mirrorX and mirrorY are true by default)
    doMirrored(MarkerSquare, w, pt, 80,layer='MARKERS')

# ===============================================================================
# chip class definition
# ===============================================================================
class MultimodeTransmon3D(m.Chip):
    def __init__(self,wafer,chipID,layer,jfingerw,chip_id_loc=(6100,0),defaults=None,**kwargs):
        m.Chip.__init__(self,wafer,chipID,layer,defaults={'w':200,'r_out':10,'r_ins':0})
        #self.defaults = {'w':200,'r_out':10,'r_ins':0}
        if defaults is not None:
            for d in defaults:
                self.defaults[d]=defaults[d]
        
        #define the transmon (transmon pads and manhattan junction)
        #these numbers copied from Kevin's files
        jpos =self.centered((-self.width/2 + 2960+58-210-250+500+790+1102+100+648-750-500,0))
        Transmon3D(self, jpos,padh=200,padw=4950-750-500,padw2=750+750+500,leadw=85,leadw2=85,leadh=20,separation=20,jfingerw=jfingerw,**kwargs)
        
        #define the alignment mark
        Strip_straight(self,self.centered((-1300-1600+3808+790+943.75,0)),100,w=2000)
        #or to just use primitives, you could use: 
        #self.add(dxf.rectangle(self.centered((-1300-1600+3808+790+943.75,0)),100,2000,valign=const.MIDDLE,bgcolor=wafer.bg()))
        
        #add chip name to frame layer
        self.add(dxf.text(str(self.chipID),chip_id_loc,height=200,layer='FRAME'))
        
# ===============================================================================
# generate chips
# ===============================================================================
# junc_ws = np.array([175,178,180,180,182,185,190,200,205,215,225,235,105,95,145,155])/1000
junc_ws = np.ones(len(w.chips))*175/1000

        
        
#this will set the default chip for the wafer, filling the chip buffer with this chip
#Let's make this a transmon without rounded edges:
w.setDefaultChip(MultimodeTransmon3D(w,'3DMM2_CHIP_DEFAULT',w.defaultLayer,jfingerw=junc_ws[0],defaults={'r_out':0,'r_ins':0},jpadr=0,
                                     **qubit_defaults['sharp_jContactTab']))

#this goes through the chip buffer and sets each entry to a new chip we define.
#Note: the CHIPID has to be unique for each chip 
for i in range(1,len(w.chips)):
    w.setChipBuffer(MultimodeTransmon3D(w,'3DMM2_CHIP'+str(i),w.defaultLayer,jfingerw=junc_ws[i]).save(w), i)
    #Note: You need to generate the chip, then call chip.save(wafer) to make sure the chip is written to the wafer block list!
    #alternative example:
    #temp_chip = MultimodeTransmon3D(w,'3DMM2_CHIP'+str(i),w.defaultLayer,jfingerw=junc_ws[i])
    #temp_chip.save(w)
    #wafer.chips[i]=temp_chip
    
#Let's also save a dxf of just one of the chips but without the dicing border 
#(this will technically overwrite the block list with itself, so best to do this when you set the chip buffer)
w.chips[15].save(w,drawCopyDXF=True,dicingBorder=False)
    

# Now that all chips are saved in the blocks section, write instances of the chips at the right spots on the wafer
w.populate()
w.save()