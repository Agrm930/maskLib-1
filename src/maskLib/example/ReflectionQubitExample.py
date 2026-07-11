# -*- coding: utf-8 -*-
"""
Created on Fri Aug 31 16:45:06 2018

@author: slab
"""

import maskLib.MaskLib as m
from maskLib.microwaveLib import CPW_straight,CPW_taper,CPW_bend,CPW_launcher,Strip_straight,waffle
import numpy as np
from dxfwrite import const
from dxfwrite import DXFEngine as dxf
from dxfwrite.vector2d import vadd

from maskLib.utilities import doMirrored
from maskLib.markerLib import MarkerSquare
from maskLib.Entities import RoundRect

from maskLib.junctionLib import setupJunctionLayers, JProbePads, ManhattanJunction
from maskLib.qubitLib import Hamburgermon

# ===============================================================================
# wafer setup
# ===============================================================================

w = m.Wafer('ReflectionQubitExample','DXF/',7000,7000,waferDiameter=m.waferDiameters['2in'],sawWidth=m.sawWidths['8A'],
                frame=1,solid=0,multiLayer=1)
# w.frame: draw frame layer?
# w.solid: draw things solid?
# w.multiLayer: draw in multiple layers?

#[string layername,int color]
w.SetupLayers([
    ['BASEMETAL',4],
    ['EMARKER',3]
    ])

setupJunctionLayers(w)

#initialize the wafer
w.init()

#do dicing border
w.DicingBorder()

#do global p80 eBeam markers
markerpts = [(16000,x) for x in range(13000,16000,1000)]
for pt in markerpts:
    #(note: mirrorX and mirrorY are true by default)
    doMirrored(MarkerSquare, w, pt, 80,layer='EMARKER')

#=============================
class ReflectionPurcellQubit(m.Chip7mm):
    def __init__(self,wafer,chipID,layer,jfingerw=0.0,padwidth=150,padradius=5,**kwargs):
        m.Chip7mm.__init__(self,wafer,chipID,layer,defaults={'w':11, 's':5, 'radius':180,'r_out':5,'r_ins':5})
        #do local p80 ebeam markers
        doMirrored(MarkerSquare, self, (3250,3250), 80,layer='EMARKER',chipCentered=True)
        
        for s in self.structures:
            s.shiftPos(340)
        
        '''
        #by default the corner structures are angled to match the pads
        self.structures[4].shiftPos(0,angle=-45)
        #make a reference to structure #4 so we don't confuse it for a variable
        s4 = self.structures[4]
        '''
        
        #this code is copied closely from Jeronimo's file
        s4 = m.Structure(self,self.chipSpace((5883,1000)),direction=90)
        
        CPW_launcher(self,s4,l_taper=400,padw=234,pads=100,l_pad=400,l_gap=434)
        CPW_straight(self, s4, 429)
        CPW_taper(self, s4, 10, w0=11, s0=5, w1=11, s1=10.625)
        CPW_taper(self, s4, 30,11,10.625,44.75,10.625)
        CPW_taper(self, s4, 10, 44.75, 10.625, 60, 3)
        CPW_straight(self,s4, 2790, w=60, s=3)
        CPW_bend(self,s4,CCW=False,w=60,s=3)
        CPW_straight(self,s4,200,w=60,s=3)
        CPW_bend(self,s4,CCW=False,w=60,s=3)
        CPW_straight(self,s4,1934.5, 60, 3)
        CPW_taper(self,s4, 40,w0=60, s0=3, w1=3, s1=47)
        CPW_straight(self,s4, 2300,3, 47)
        CPW_bend(self,s4,w=3,s=47)
        CPW_straight(self,s4,200,3,47)
        CPW_bend(self,s4,w=3,s=47)
        CPW_straight(self,s4,4000,3, 47)
        CPW_bend(self,s4,CCW=False,w=3,s=47)
        CPW_straight(self,s4,200,3,47)
        CPW_bend(self,s4,CCW=False,w=3,s=47)
        CPW_straight(self,s4,169,3,47)
        CPW_taper(self,s4,39.884, 3, 47, 60, 3)
        CPW_straight(self,s4, 3800, 60, 3)
        CPW_bend(self,s4,w=60,s=3)
        CPW_straight(self,s4,200,w=60,s=3)
        CPW_bend(self,s4,w=60,s=3)
        CPW_straight(self,s4,934.5, 60, 3)
        CPW_taper(self,s4, 40,60, 3, 3, 47)
        CPW_straight(self,s4, 3300, 3, 47)
        CPW_bend(self,s4,CCW=False,w=3,s=47)
        CPW_straight(self,s4,200,3,47)
        CPW_bend(self,s4,CCW=False,w=3,s=47)
        CPW_straight(self,s4, 3934.5, 3, 47)
        CPW_taper(self,s4, 50.15, 3, 47, 11, 5)
        CPW_bend(self,s4,angle=180,w=11,s=5,radius=210.5)
        CPW_straight(self,s4, 361.77, 11, 5)
        CPW_taper(self,s4, 100, 11, 5, 59, 26.818) #capacitor
        CPW_straight(self,s4, 25, 59, 26.818) #capacitor
        Strip_straight(self,s4, 5, 2*56.318) #capacitor
        CPW_straight(self,s4, 25, 59, 26.818) #capacitor
        CPW_taper(self,s4, 100,  59, 26.818, 11, 5)
        CPW_straight(self,s4, 1514 + 114.2, 11, 5)
        CPW_bend(self,s4,angle=180,CCW=False,w=11,s=5,radius=210.5)
        CPW_straight(self,s4, 2175.01, 11, 5)
        CPW_bend(self,s4,angle=180,w=11,s=5,radius=210.5)
        CPW_straight(self,s4, 3098, 11, 5)

        Hamburgermon(self, s4,qbunthick=120,qbunr=59.9,qccap_padl=170,qccapl=120,jfingerw=jfingerw,**kwargs)
        
        #this is for the test junctions on the left
        
        #cutout
        self.add(RoundRect(self.chipSpace((650,2375)),670,2275+300,1,valign=const.MIDDLE))#note we are purposefully not setting the bgcolor
        #contact pads
        for y in range(5):
            for x in range(2):
                pos = self.chipSpace((830+300*x,3180+170-500*y))
                #notice we're calling the probepads and manhattan functions with the position tuple instead of a structure class.
                JProbePads(self,pos,rotation=90,padwidth=padwidth,padradius=padradius,layer=self.wafer.XLAYER,**kwargs)
                ManhattanJunction(self,pos,rotation=90,jfingerw=jfingerw,**kwargs)
                
                #optionally, we can do the same with structures:
                #s1 = m.Structure(self,pos,direction=90)
                #JProbePads(self,s1,padwidth=padwidth,padradius=padradius,layer=self.wafer.XLAYER,**kwargs)
                #ManhattanJunction(self,s1,jfingerw=jfingerw,**kwargs)
                
                
   

#define the chip        
reflectionQubit01 = ReflectionPurcellQubit(w,'QCHIP1','BASEMETAL',jfingerw=0.12)
#perforate the ground plane to trap flux vortices
waffle(reflectionQubit01, 211.3, width=50,bleedRadius=1,padx=700,layer='MARKERS')
#save the chip to the wafer, and also make a copy dxf of just this chip with dicing border included
reflectionQubit01.save(w,drawCopyDXF=True,dicingBorder=True)

for i in range(8,16):
    w.chips[i]=reflectionQubit01

# write all chips
w.populate()
w.save()
