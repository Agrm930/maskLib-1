# -*- coding: utf-8 -*-
"""
Created on Fri Jan  5 12:35:23 2018

@author: sasha
Edited by Agrim, 2026 (updated ezdxf font imports; moved deprecated functions to MaskLib_old.py)
"""
import math
import os

from dxfwrite import const
#force all 2D polylines by disabling 3D polyline flags
const.POLYLINE_3D_POLYLINE=0

from dxfwrite import DXFEngine as dxf

from dxfwrite.vector2d import vadd,midpoint,vmul_scalar,vsub
from dxfwrite.algebra import rotate_2d

import ezdxf
from ezdxf.addons import text2path
from ezdxf.math import Matrix44
# from ezdxf.gfxattribs import GfxAttribs
from ezdxf.tools import text
# from ezdxf.enums import MTextEntityAlignment
# (ezdxf.tools.fonts was removed in ezdxf v1.x -- font tools now live in ezdxf.fonts.fonts)

import math

from dxfwrite import const
#force all 2D polylines by disabling 3D polyline flags
const.POLYLINE_3D_POLYLINE=0

from dxfwrite import DXFEngine as dxf

from dxfwrite.vector2d import vadd,midpoint,vmul_scalar,vsub
from dxfwrite.algebra import rotate_2d

import ezdxf
from ezdxf.addons import text2path
from ezdxf.math import Matrix44
# from ezdxf.gfxattribs import GfxAttribs
from ezdxf.tools import text
# from ezdxf.enums import MTextEntityAlignment

import math

from dxfwrite import const
#force all 2D polylines by disabling 3D polyline flags
const.POLYLINE_3D_POLYLINE=0

from dxfwrite import DXFEngine as dxf

from dxfwrite.vector2d import vadd,midpoint,vmul_scalar,vsub
from dxfwrite.algebra import rotate_2d

import ezdxf
from ezdxf.addons import text2path
from ezdxf.math import Matrix44
# from ezdxf.gfxattribs import GfxAttribs
from ezdxf.tools import text
# from ezdxf.enums import MTextEntityAlignment
from dxfwrite import DXFEngine as engine

# ===============================================================================
#  LOOKUP DICTIONARIES FOR COMMON TERMS 
# ===============================================================================
waferDiameters = {'2in':50800,'3in':76200,'4in':101600,'6in':152400}
sawWidths = {'4A':101.6,'8A':203.2}

# NOTE: the deprecated module-level functions that used to live here
# (HiVisMarker09, curveAB, corner, transformedQuadrants, skewRect) were
# removed in 2026. Use markerLib.HiVisMarker09, utilities.curveAB,
# utilities.cornerRound, utilities.transformedQuadrants, and
# Entities.SkewRect instead (argument conventions differ slightly -- see
# each function's docstring). The old versions are preserved in
# MaskLib_old.py if you need to reference them.

# ===============================================================================
#  WAFER CLASS
#       master class designed to handle all layers, main dxf drawing and stores chips
# ===============================================================================
class Wafer:

    def __init__(self,name,path,chipWidth,chipHeight,waferDiameter=50800,padding=2500,sawWidth=203.2,frame=True,markers=True,solid=False,multiLayer=True,singleChipRow=False,singleChipColumn=False,centerChip=False,**kwargs):
        # initialize drawing
        self.fileName = name
        self.path = path
        self.drawing = dxf.drawing(path + name + '.dxf')
        
        #get rid of extra layers (we still want '0', and 'VIEWPORTS')
        self.drawing.tables.layers.clear()
        self.drawing.add_layer('0')
        self.drawing.add_layer('VIEWPORTS',color=8)
        
        # set default wafer properties
        self.waferDiameter = waferDiameter
        self.padding = padding
        self.sawWidth = sawWidth
        # if centerChip:
        #     self.chipX = -0.5*(chipWidth + sawWidth)
        #     self.chipY = -0.5*(chipHeight + sawWidth)
        # else:
        self.centerChip = centerChip
        self.chipX = chipWidth + sawWidth
        self.chipY = chipHeight + sawWidth
        self.frame = frame              #draw frame layer?
        self.markers = markers
        self.solid = solid              #draw things solid?
        self.multiLayer = multiLayer    #draw in multiple layers?
        self.singleChipRow = singleChipRow #draw only one row of chips? (horizontal row)
        self.singleChipColumn = singleChipColumn #draw only one column of chips? (vertical column)
        
        # initialize default layers
        self.layerNames = ['0']
        self.layerColors = {'0':7} #colors corresponding to layers
        self.layerNums = {'0':0} #colors corresponding to layers
        self.defaultLayer = '0' #default layer to draw chips on
        self.FRAME_LAYER = kwargs.get('FRAME_LAYER', ['WAFER_FRAME', 8, 1])  # default frame layer
        
        # initialize private variables
        self.chipPts = [] #chip offsets, measring from lower left corner
        self.chipColumns = [] #chip columns
        self.chips = [] #cached chip references
        self.defaultChip = None
        
        
        
    # for changing wafer properties later
    def setProperties(self,chipWidth,chipHeight,waferDiameter=50800,padding=2500,sawWidth=203.2,frame=True,markers=True,solid=False,multiLayer=True):
        # set the basic properties of the wafer
        self.waferDiameter = waferDiameter
        self.padding = padding
        self.sawWidth = sawWidth
        self.chipY = chipWidth + sawWidth
        self.chipX = chipHeight + sawWidth
        self.frame = frame              #draw frame layer?
        self.markers = markers
        self.solid = solid              #draw things solid?
        self.multiLayer = multiLayer    #draw in multiple layers?
    
    #copy properties from a parent wafer
    def copyPropertiesFrom(self,wafer):
        self.waferDiameter = wafer.waferDiameter
        self.padding = wafer.padding
        self.sawWidth = wafer.sawWidth
        self.chipY = wafer.chipY
        self.chipX = wafer.chipX
        self.frame = wafer.frame              #draw frame layer?
        self.markers = wafer.markers
        self.solid = wafer.solid              #draw things solid?
        self.multiLayer = wafer.multiLayer    #draw in multiple layers?
        
        self.layerColors = wafer.layerColors
        self.layerNums = wafer.layerNums
        self.layerNames = wafer.layerNames
        self.defaultLayer = wafer.defaultLayer 
        
        #ignore private vars
    
    def save(self):
        # stamp the creation/update date into the DXF header ($TDCREATE /
        # $TDUPDATE are stored as Julian dates; CAD programs show them as
        # the drawing's creation / last-saved time)
        import time
        julian_now = time.time() / 86400.0 + 2440587.5
        self.drawing.header['$TDCREATE'] = julian_now
        self.drawing.header['$TDUPDATE'] = julian_now
        self.drawing.save()
        print('Saved as: '+ '\x1b[36m' + self.path + self.fileName + '.dxf'+'\x1b[0m')
    
    def lyr(self,layerName):
        return self.multiLayer and layerName or '0'
    
    def bg(self,layerName=None):
        # return the fill color
        if layerName is None:
            return self.solid and const.BYLAYER or None
        else:
            return self.solid and self.layerColors[self.lyr(layerName)] or None
    
    def addLayer(self,layerName,layerColor):
        if layerName not in self.layerNames:
            self.layerNames.append(layerName)
            self.layerColors[layerName]=layerColor
            self.layerNums[layerName]=len(self.layerNames)-1

    def addLayerAt(self, layerName, layerColor, layerNumber=-1):
        if layerName in self.layerNames: return
        numLayers = len(self.layerNames)
        if layerNumber == -1: layerNumber = numLayers
        if layerNumber < numLayers: return
        fillerLayers = [f'{layerNum}' for layerNum in range(numLayers, layerNumber)]
        for fillerLayerName in fillerLayers:
            self.addLayer(fillerLayerName, -1)
        self.addLayer(layerName, layerColor)
    
    def setDefaultChip(self,chip=None):
        # update default chip and chip list
        
        if chip is None: 
            if self.defaultChip is None:
                self.defaultChip = Chip(self,'BLANK',self.defaultLayer)
                self.defaultChip.save(self)
            else:
                print('Default chip already set in '+self.fileName)
        else:
            self.defaultChip = chip
            self.defaultChip.save(self)
        
        #populate wafer with default chips
        if len(self.chips)>0:
            for i in range(len(self.chips)):
                self.chips[i]=self.defaultChip
        else:
            for i in range(len(self.chipPts)):
                self.chips.append(self.defaultChip)
    
    def init(self, FRAME_LAYER=None, MARKER_LAYER=['MARKERS',5,-1]):
        #self.frame and self.markers override presence/absence of FRAME_LAYER/MARKER_LAYER params
        #verify frame is off is multilayer is off
        if FRAME_LAYER is None:
            FRAME_LAYER = self.FRAME_LAYER
        self.frame = self.multiLayer and self.frame or 0
        #finish setup of DXF file
        if self.multiLayer:
            if self.frame:
                self.addLayerAt(*FRAME_LAYER)
            if self.markers:
                self.addLayerAt(*MARKER_LAYER)
        #add layers
        for layer in self.layerNames:
            self.drawing.add_layer(layer,color=self.layerColors[layer])
            
        #cache frame layer string
        fr = self.lyr(FRAME_LAYER[0])
        #draw wafer for debugging purposes
        if self.frame:
            self.drawing.add(dxf.circle(radius=self.waferDiameter/2,center=(0,0),layer=fr))
            self.drawing.add(dxf.circle(radius=self.waferDiameter/2-self.padding,center=(0,0),layer=fr))
        #determine number of chips, chip layout and coordinates
        nx=0
        ny=0
        if self.singleChipColumn:
            if self.singleChipRow:
                #only one chip on the wafer
                self.chipPts.append([-0.5*self.chipX,-0.5*self.chipY])
                self.chipColumns.append(1)
            else:
                #vertical column of chips, symmetric about X axis
                while((ny+1)*self.chipY)**2 + ((0.5)*self.chipX)**2 < (self.waferDiameter/2 - self.padding)**2:
                    self.chipPts.append([-0.5*self.chipX,ny*self.chipY])
                    self.chipPts.append([-0.5*self.chipX,(-ny-1)*self.chipY])
                    ny += 1
                self.chipColumns.append(2*ny)
                nx += 1
        elif self.singleChipRow:
            #horizontal row of chips, symmetric about Y axis
            while ((nx+1)*self.chipX)**2 + self.chipY**2 < (self.waferDiameter/2 - self.padding)**2:
                self.chipPts.append([nx*self.chipX,-0.5*self.chipY])
                self.chipPts.append([(-nx-1)*self.chipX,-0.5*self.chipY])
                self.chipColumns.append(1)
                nx += 1
        else:
            #grid of chips, symmetric about X and Y axis
            while ((nx+1)*self.chipX)**2 + self.chipY**2 < (self.waferDiameter/2 - self.padding)**2:
                ny=0
                while((ny+1)*self.chipY)**2 + ((nx+1)*self.chipX)**2 < (self.waferDiameter/2 - self.padding)**2:
                    self.chipPts.append([nx*self.chipX,ny*self.chipY])
                    self.chipPts.append([nx*self.chipX,(-ny-1)*self.chipY])
                    self.chipPts.append([(-nx-1)*self.chipX,ny*self.chipY])
                    self.chipPts.append([(-nx-1)*self.chipX,(-ny-1)*self.chipY])
                    ny += 1
                self.chipColumns.append(2*ny)
                nx += 1
        #sort chip indices left to right, then bottom to top
        self.chipPts.sort()
        print('Number of Chips: '+str(len(self.chipPts)))
        #reverse column counts to go from left to center
        self.chipColumns = self.chipColumns[::-1]
        
        self.setDefaultChip()
        
        #setup the viewport
        self.drawing.add_vport('*ACTIVE',ucs_icon=0,circle_zoom=1000,grid_on=1,center_point=(0,0),aspect_ratio=2*(self.waferDiameter))
    
    def initChipOnly(self,center=False, FRAME_LAYER=None, MARKER_LAYER=['MARKERS',5,-1]):
        if FRAME_LAYER is None:
            FRAME_LAYER = self.FRAME_LAYER
        #self.frame and self.markers override presence/absence of FRAME_LAYER/MARKER_LAYER params
        #initialize drawing assuming we only want to draw a single chip
        #verify frame is off is multilayer is off
        self.frame = self.multiLayer and self.frame or 0
        #finish setup of DXF file
        if self.multiLayer:
            if self.frame:
                self.addLayerAt(*FRAME_LAYER)
            if self.markers:
                self.addLayerAt(*MARKER_LAYER)
        #add layers
        for layer in self.layerNames:
            self.drawing.add_layer(layer,color=self.layerColors[layer])
        if center:
            self.chipPts =[[-self.chipX/2,-self.chipY/2]]
        else:
            # anchor the chip's bottom-left corner exactly at the DXF origin:
            # writeChip shifts every insert by +sawWidth/2 (chipSpace), which
            # centers a chip in its dicing cell on the full wafer but is an
            # unwanted offset in a standalone single-chip DXF
            self.chipPts =[[-self.sawWidth/2,-self.sawWidth/2]]
            
        # NOTE: no setDefaultChip() here -- Chip.save() sets the real chip as
        # default right after initChipOnly. Creating a BLANK default here only
        # polluted the standalone DXF with an unused CHIP_BLANK block whose
        # frame rectangle had the parent wafer's chip size, which showed up as
        # a phantom oversized outline in viewers that display all blocks (KLayout).

        #setup the viewport
        self.drawing.add_vport('*ACTIVE',ucs_icon=0,circle_zoom=1000,grid_on=1,center_point=(0,0),aspect_ratio=2*(max(self.chipX,self.chipY)))
    
    def SetupLayers(self,layers):
        #format: ['layername',color_int,layer_num (optional)]
        #first layer is default
        if self.multiLayer:
            for l in layers:
                if len(l) == 2: l.append(-1)
                self.addLayerAt(*l)
            self.defaultLayer=layers[0][0]
            
    
    #dicing saw border
    def DicingBorder(self,maxpts=0,minpts=0,thin=5,thick=20,short=40,long=100,dash=400,layer='MARKERS'):
        '''
        # maxpts:     where in chip list to stop putting a dicing border 
        # minpts:     where in chip list to start putting dicing border
        # thin:5      #thin section of crosshair
        # thick:20    #thick section of crosshair AND dash thickness
        # short:40    #short section of crosshair
        # long:100    #long section of crosshair
        # dash:400    #spacing between dashes
        '''
        if maxpts < 0:
            maxpts = len(self.chipPts)+maxpts
        
        #determine filling
        bg = self.bg(layer)
        offsetX = ((self.chipX-2*short-2*long)%(dash)+dash)/2
        offsetY = ((self.chipY-2*short-2*long)%(dash)+dash)/2
        border = dxf.block('DICINGBORDER')
        border.add(dxf.rectangle((0,0),short+thin,thin,bgcolor=bg))
        border.add(dxf.rectangle((short+thin,0),long,thick,bgcolor=bg))
        border.add(dxf.rectangle((0,thin),thin,short,bgcolor=bg))
        border.add(dxf.rectangle((0,thin+short),thick,long,bgcolor=bg))
        
        for x in range(int(short+long),int(self.chipX-short-long-dash),dash):
            border.add(dxf.rectangle((x+offsetX,0),thick,thick,bgcolor=bg))
        
        border.add(dxf.rectangle((self.chipX,0),-short-thin,thin,bgcolor=bg))
        border.add(dxf.rectangle((self.chipX-short-thin,0),-long,thick,bgcolor=bg))
        border.add(dxf.rectangle((self.chipX,thin),-thin,short,bgcolor=bg))
        border.add(dxf.rectangle((self.chipX,thin+short),-thick,long,bgcolor=bg))
        
        for y in range(int(short+long),int(self.chipY-short-long-dash),dash):
            border.add(dxf.rectangle((0,y+offsetY),thick,thick,bgcolor=bg))
        
        border.add(dxf.rectangle((0,self.chipY),short+thin,-thin,bgcolor=bg))
        border.add(dxf.rectangle((short+thin,self.chipY),long,-thick,bgcolor=bg))
        border.add(dxf.rectangle((0,-thin+self.chipY),thin,-short,bgcolor=bg))
        border.add(dxf.rectangle((0,-thin-short+self.chipY),thick,-long,bgcolor=bg))
        
        for x in range(int(short+long),int(self.chipX-short-long-dash),dash):
            border.add(dxf.rectangle((x+offsetX-thick,self.chipY),thick,-thick,bgcolor=bg))
        
        border.add(dxf.rectangle((self.chipX,self.chipY),-short-thin,-thin,bgcolor=bg))
        border.add(dxf.rectangle((self.chipX-short-thin,self.chipY),-long,-thick,bgcolor=bg))
        border.add(dxf.rectangle((self.chipX,-thin+self.chipY),-thin,-short,bgcolor=bg))
        border.add(dxf.rectangle((self.chipX,-thin-short+self.chipY),-thick,-long,bgcolor=bg))
        
        for y in range(int(short+long),int(self.chipY-short-long-dash),dash):
            border.add(dxf.rectangle((self.chipX,y+offsetY-thick),-thick,thick,bgcolor=bg))
        
        self.drawing.blocks.add(border)

        for index,pt in enumerate(self.chipPts):
            if (maxpts==0 or index<maxpts) and index>=minpts:
                self.drawing.add(dxf.insert('DICINGBORDER',insert=(pt[0],pt[1]),layer=self.lyr(layer)))
                
    def writeChip(self,chip,index):
        # #insert a chip at specified index
        # self.drawing.add(dxf.insert(chip.ID,insert=self.chipSpace(self.chipPts[index]),layer=self.lyr(chip.layer)))
        # If centerChip, offset so chip center is at chipPts[index]
        if getattr(self, 'centerChip', False):
            offset = (self.chipX / 2, self.chipY / 2)
            insert_pt = (self.chipPts[index][0] - offset[0], self.chipPts[index][1] - offset[1])
        else:
            insert_pt = tuple(self.chipPts[index])
        self.drawing.add(dxf.insert(chip.ID, insert=self.chipSpace(insert_pt), layer=self.lyr(chip.layer)))
        
    #write all chips in the chips buffer
    def populate(self):
        for i,chip in enumerate(self.chips):
            self.writeChip(chip,i)
    
    def setChipBuffer(self,chip,index):
        self.chips[index]=chip
    
    #define high visibility markers as blocks '00' - '09'
    def defineHiVisMarker09(self,width,layer):
        # deferred import: markerLib imports MaskLib, so a top-level import
        # here would be circular
        from maskLib.markerLib import HiVisMarker09
        for i in range(10):
            num = dxf.block('0'+str(i))
            HiVisMarker09(num,0,0,i,width,self.bg(layer))
            self.drawing.blocks.add(num)
    
    #draw a high visibility marker on each chip in the lower left corner
    def mark1000(self,markHeight,start,stop,layer):
        width = markHeight/4
        #default spacing is 
        for i in range(start,stop+1):
            n=i-start
            self.drawing.add(dxf.insert('0'+str(n//100),insert=self.chipSpace(vadd((width,width),self.chipPts[i])),layer=self.lyr(layer)))
            self.drawing.add(dxf.insert('0'+str(n%100//10),insert=self.chipSpace(vadd((width*5,width),self.chipPts[i])),layer=self.lyr(layer)))
            self.drawing.add(dxf.insert('0'+str(n%10),insert=self.chipSpace(vadd((width*9,width),self.chipPts[i])),layer=self.lyr(layer)))
    
    #return chip centered coordinates in wafer space
    def center(self,xy=(0,0)):
        return (xy[0]+self.chipX/2,xy[1]+self.chipY/2)

    def cx(self,x):
        return self.chipX/2 + x
    
    def cy(self,y):
        return self.chipY/2 + y
    
    #chip space:
    #coordinates centered on corner of actual chip
    def chipSpace(self,xy):
        return (xy[0]+self.sawWidth/2,xy[1]+self.sawWidth/2)
    
    #shortcut for add function
    def add(self,obj):
        self.drawing.add(obj)
    
    # --------------------------  Common layer setup functions  ----------------------------------
    
    def setupJunctionLayers(self,JLAYER='JUNCTION',jcolor=1,ULAYER='UNDERCUT',ucolor=2,bandaid=False,BLAYER='BANDAID',bcolor=3):
        #add correct layers to wafer, and cache layer
        self.addLayer(JLAYER,jcolor)
        self.JLAYER=JLAYER
        self.addLayer(ULAYER,ucolor)
        self.ULAYER=ULAYER
        if bandaid:
            self.addLayer(BLAYER,bcolor)
            self.BLAYER=BLAYER
    
    def setupJunctionAngles(self,JANGLES=[0,90]):
        '''
        Angles are defined as the angle in degrees *from which the evaporation is coming*.
        For example, if the first evaporation comes from the East, and the second from the north,
        the angles would be [0,90]. Add more angles to the list as needed.
        '''
        self.JANGLES = [angle % 360 for angle in JANGLES]
        
    def setupManhattanJAngles(self,JANGLE1=0,flip=False):
        '''
        Sets up angles specifically for manhattan junction (Angle 2 is 90 deg CW or CCW from angle 1)
        '''
        JANGLE2 = JANGLE1 + 90
        if flip:
            JANGLE2 = JANGLE1 - 90
        self.setupJunctionAngles(self,[JANGLE1 % 360,JANGLE2 % 360])
        
    def setupXORlayer(self,XLAYER='XOR',xcolor=6):
        '''
        Sets a layer for XOR operations on all other layers. 
        OUT = ( LAYER1 or LAYER2 ... or LAYERN ) xor XLAYER 
        '''
        self.XLAYER=XLAYER
        self.addLayer(XLAYER, xcolor)
       
    def setupAirbridgeLayers(self,BRLAYER='BRIDGE',RRLAYER='TETHER',brcolor=36,rrcolor=41):
        #add correct layers to wafer, and cache layer
        self.addLayer(BRLAYER,brcolor)
        self.BRLAYER=BRLAYER
        self.addLayer(RRLAYER,rrcolor)
        self.RRLAYER=RRLAYER        
# ===============================================================================
#  CHIP CLASS  
#       basic class with a blank chip
# ===============================================================================
        
import ezdxf
from ezdxf.addons import text2path
# NOTE: ezdxf reorganized its font tools in v1.0 and later removed the old path:
#   old (removed):  from ezdxf.tools.fonts import FontFace
#   new:            from ezdxf.fonts.fonts import FontFace  (public API)
# (ezdxf.fonts.font_face.FontFace also works but is the internal module path)
from ezdxf.fonts.fonts import FontFace
from maskLib.utilities import snap_to_grid

class Chip:
    def __init__(self, wafer, chipID, layer, structures=None, defaults=None, FRAME_NAME='703/0', grid_size_small=.005, grid_size_large=.050,centerChip=True):
        self.wafer = wafer
        self.width = wafer.chipX - wafer.sawWidth
        self.height = wafer.chipY - wafer.sawWidth
        self.chipID = chipID  # String (usually)
        self.centerChip = centerChip
        self.ID = 'CHIP_' + str(chipID)
        self.solid = wafer.solid
        self.frame = wafer.frame
        self.layer = layer
        
        self.grid_size_small = grid_size_small  # nm, default 5
        self.grid_size_large = grid_size_large  # nm, default 100

        if defaults is None:
            self.defaults = {}
        else:
            self.defaults = defaults.copy()
        # Setup centering
        self.center = (self.width / 2, self.height / 2)
        # Initialize the block
        self.chipBlock = dxf.block(self.ID)
        
        if centerChip:
            self.origin_offset = (-self.width / 2, -self.height / 2)
        else:
            self.origin_offset = (0, 0)

        # Setup structures
        if structures is not None:
            self.structures = structures
            
        # Add a debug frame for actual chip area
        if wafer.frame:
            # Frame at (0,0) - self.add() will apply origin_offset for centering
            self.add(dxf.rectangle((0, 0), self.width, self.height, layer=wafer.lyr(FRAME_NAME)))

    def add_structure(self, structure):
        self.structures.append(structure)

    def draw(self):
        for structure in self.structures:
            structure.draw(self)

    # def add_chip_label(self, text, position, height=10, layer='TEXT'):
    #     # Define font properties
    #     font_face = FontFace(family='Arial')
        
    #     # Convert text to paths
    #     paths = text2path.make_paths_from_str(text, font=font_face, size=height)
    #     for path in paths:
    #         points = list(path.flattening(0.01))  # Flatten the path to get the points
    #         self.wafer.drawing.add(dxf.polyline(points, layer=layer))
    # GOODONEdef add_chip_label(self, text, position, height=10, layer='TEXT'):
    #     font_face = FontFace(family='Arial')
    #     paths = text2path.make_paths_from_str(text, font=font_face, size=height)
    #     for path in paths:
    #         points = list(path.flattening(0.01))
    #         self.chipBlock.add(dxf.polyline(points, layer=layer)) # Add to chipBlock instead of wafer.drawing
    def add_chip_label(self, text, position, height=10, layer='98/0'):
        font_face = FontFace(family='Arial')
        paths = text2path.make_paths_from_str(text, font=font_face, size=height)
        
        # Calculate the bounding box of the text paths
        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')

        for path in paths:
            for point in path.flattening(0.01):
                min_x = min(min_x, point.x)
                min_y = min(min_y, point.y)
                max_x = max(max_x, point.x)
                max_y = max(max_y, point.y)

        text_width = max_x - min_x
        text_height = max_y - min_y

        # Calculate the offset to center the text at the position
        offset_x = position[0] - text_width / 2
        offset_y = position[1] - text_height / 2

        for path in paths:
            points = list(path.flattening(0.01))
            # Apply the offset to each point in the path
            offset_points = [(point.x + offset_x, point.y + offset_y) for point in points]
            self.chipBlock.add(dxf.polyline(offset_points, layer=layer, flags=1))

    def save(self, wafer, drawCopyDXF=False, dicingBorder=True, center=False, FRAME_LAYER=['703/0', 8, -1], MARKER_LAYER=['MARKERS', 5, -1], fileName=None):
        # fileName overrides the copy DXF's file name (default: wafer name + chip ID)
        wafer.drawing.blocks.add(self.chipBlock)
        if drawCopyDXF:
            # Make a copy DXF with only the chip
            if fileName is None:
                fileName = wafer.fileName + '_' + self.ID
            temp_wafer = Wafer(fileName, wafer.path, 10, 10)
            # Height and width don't matter since the next line copies all settings
            temp_wafer.copyPropertiesFrom(wafer)
            temp_wafer.drawing.blocks.add(self.chipBlock)
            temp_wafer.initChipOnly(center=center, FRAME_LAYER=FRAME_LAYER, MARKER_LAYER=MARKER_LAYER)
            if dicingBorder:
                temp_wafer.DicingBorder()
            temp_wafer.setDefaultChip(self)
            temp_wafer.populate()
            temp_wafer.save()
        return self

    def add(self, obj, structure=None, length=None, offsetVector=None, absolutePos=None, angle=0, newDir=None, use_large_grid=True):
        # Snap points and origin to grid if present
        gs = self.grid_size_large if use_large_grid else self.grid_size_small
        if hasattr(obj, 'points') and obj.points is not None:
            obj.points = [snap_to_grid((pt[0] + self.origin_offset[0], pt[1] + self.origin_offset[1]), gs) for pt in obj.points]
        if hasattr(obj, 'origin') and obj.origin is not None:
            obj.origin = snap_to_grid((obj.origin[0] + self.origin_offset[0], obj.origin[1] + self.origin_offset[1]), gs)
        self.chipBlock.add(obj)
        # Snap points and origin if present
        # gs = self.grid_size_large if use_large_grid else self.grid_size_small
        # if hasattr(obj, 'points') and obj.points is not None:
        #     obj.points = [snap_to_grid(pt, gs) for pt in obj.points]
        # if hasattr(obj, 'origin') and obj.origin is not None:
        #     obj.origin = snap_to_grid(obj.origin, gs)
        # self.chipBlock.add(obj)
        def struct():
            if isinstance(structure, Structure):
                return structure
            elif isinstance(structure, tuple):
                return Structure(self, structure)
            else:
                return self.structures[structure]
        if length is not None:
            struct().shiftPos(length, angle=angle, newDir=newDir)
        elif offsetVector is not None:
            struct().translatePos(vector=offsetVector, angle=angle, newDir=newDir)
        elif absolutePos is not None:
            struct().updatePos(newStart=absolutePos, angle=angle, newDir=newDir)

    # Return chip centered coordinates in chip space
    def centered(self, xy=(0, 0)):
        return (xy[0] + self.center[0], xy[1] + self.center[1])

    # Return chip centered x coordinate in chip space
    def cx(self, x):
        return self.center[0] + x

    # Return chip centered y coordinate in chip space
    def cy(self, y):
        return self.center[1] + y

    # Chip space:
    # Coordinates centered on corner of actual chip
    def chipSpace(self, xy):
        return (xy[0] + self.wafer.sawWidth / 2, xy[1] + self.wafer.sawWidth / 2)

    # Get structure by index
    def structure(self, i):
        return self.structures[i]

    # Get structure start by index
    def getStart(self, i):
        return self.structures[i].start

    # Get structure direction by index
    def getDir(self, i):
        return self.structures[i].direction

    # Get background color from layer
    def bg(self, layerName=None):
        return self.wafer.bg(layerName)

    # Get layer from wafer 
    def lyr(self, layerName):
        return self.wafer.lyr(layerName)

# ===============================================================================
#  STRUCTURE CLASS  
#       Coordinate system. keeps track of current location and direction, as well as any defaults
# ===============================================================================    

class Structure:
    #start = current coordinates, direction is angle of +x axis in degrees
    
    def __init__(self,chip,start=(0,0),direction=0,defaults=None,current_length=0.0):
        self.chip = chip #parent block reference
        self.start = start
        self.direction = direction #in degrees
        self.last = start
        self.last_direction = direction #in degrees
        self.current_length = current_length #for keeping track of length
        self.last_length = current_length
        if defaults is None:
            self.defaults = chip.defaults.copy()
        else:
            self.defaults = defaults.copy()
        
    def zeroLength(self):
        self.current_length=0.0
    
    def updatePos(self,newStart=(0,0), angle=0, newDir=None): #set exact start position, add angle to direction, or set new direction
        self.last = self.start
        self.last_direction = self.direction
        self.start = newStart
        if newDir is not None:
            self.direction = newDir
        else:
            self.direction = self.direction + angle
            
    def translatePos(self,vector=(0,0), angle=0, newDir=None): 
        #move by a specified vector, set new direction
        self.updatePos(newStart = self.getPos(vector),angle=angle,newDir=newDir)
    
    def shiftPos(self, distance, angle=0, newDir=None):
        #move by a specified distance, set new direction
        self.updatePos(newStart = vadd(self.start,rotate_2d((distance,0),math.radians(self.direction))),angle=angle,newDir=newDir)
        
    def getPos(self,vector=None,distance=None,angle=0):
        #return global position from local position based on current location and direction
        if vector is not None:
            return vadd(self.start,rotate_2d(vector,math.radians(self.direction)))
        elif distance is not None:
            return vadd(self.start,rotate_2d((distance,0),math.radians(angle+self.direction)))
        else:
            return self.start
        
    def getLastPos(self,vector=None,distance=None,angle=0):
        #return global position from local position based on previous location and direction
        if vector is not None:
            return vadd(self.last,rotate_2d(vector,math.radians(self.last_direction)))
        elif distance is not None:
            return vadd(self.last,rotate_2d((distance,0),math.radians(angle+self.last_direction)))
        else:
            return self.last
        
    def getGlobalPos(self,pos=(0,0)):
        #return local position from global position based on current location and direction
        localPos = vsub(pos,self.start)
        return rotate_2d(localPos,-math.radians(self.direction))
    
    def getLastGlobalPos(self,pos=(0,0)):
        #return local position from global position based on previous location and direction
        localPos = vsub(pos,self.last)
        return rotate_2d(localPos,-math.radians(self.last_direction))
    
    def clone(self,defaults=None):
        return Structure(self.chip,start=self.start,direction=self.direction,defaults=defaults is not None and defaults or self.defaults)
    
    def cloneAlong(self,vector=None,distance=None,angle=0,newDirection=0,defaults=None):
        return Structure(self.chip,start=self.getPos(vector=vector,distance=distance,angle=angle),direction=self.direction+newDirection,defaults=defaults is not None and defaults or self.defaults)
    
    def cloneAlongLast(self,vector=None,distance=None,angle=0,newDirection=0,defaults=None):
        return Structure(self.chip,start=self.getLastPos(vector=vector,distance=distance,angle=angle),direction=self.direction+newDirection,defaults=defaults is not None and defaults or self.defaults)

# ===============================================================================
#  BEGIN CUSTOM CLASS DEFINITIONS        
# ===============================================================================
#  7mm CHIP CLASS  
#       chip with 8 structures corresponding to the launcher positions
#       NOTE: chip size still needs to be set in the wafer settings, this just determines structure location
# ===============================================================================

class Chip7mm(Chip):
    def __init__(self,wafer,chipID,layer,structures=None,defaults=None):
        Chip.__init__(self,wafer,chipID,layer,structures=structures)
        self.defaults = {'w':10, 's':5, 'radius':25,'r_out':0,'r_ins':0}
        if defaults is not None:
            #self.defaults = defaults.copy()
            for d in defaults:
                self.defaults[d]=defaults[d]
        if structures is not None:
            #override default structures
            self.structures = structures
        else:
            self.structures = [#hardwired structures
                    Structure(self,start=(500,self.height/2),direction=0,defaults=self.defaults),
                    Structure(self,start=(500,700),direction=45,defaults=self.defaults),
                    Structure(self,start=(2500,500),direction=90,defaults=self.defaults),
                    Structure(self,start=(4500,500),direction=90,defaults=self.defaults),
                    Structure(self,start=(self.width-500,700),direction=135,defaults=self.defaults),
                    Structure(self,start=(self.width-500,self.height/2),direction=180,defaults=self.defaults),
                    Structure(self,start=(self.width-500,self.height-700),direction=225,defaults=self.defaults),
                    Structure(self,start=(4500,self.height-500),direction=270,defaults=self.defaults),
                    Structure(self,start=(2500,self.height-500),direction=270,defaults=self.defaults),
                    Structure(self,start=(500,self.height-700),direction=315,defaults=self.defaults)]
        if wafer.frame:
            self.add(dxf.rectangle(self.center,6000,6000,layer=wafer.lyr('FRAME'),halign = const.CENTER,valign = const.MIDDLE,linetype='DOT'))
            
# ===============================================================================
#  10mm CHIP CLASS  
#       chip with 8 structures corresponding to the launcher positions
#       NOTE: chip size still needs to be set in the wafer settings, this just determines structure location
# ===============================================================================

class Chip10mm(Chip):
    def __init__(self,wafer,chipID,layer,structures=None,defaults=None):
        Chip.__init__(self,wafer,chipID,layer,structures=structures)
        self.defaults = {'w':10, 's':5, 'radius':25,'r_out':0,'r_ins':0}
        if defaults is not None:
            #self.defaults = defaults.copy()
            for d in defaults:
                self.defaults[d]=defaults[d]
        if structures is not None:
            #override default structures
            self.structures = structures
        else:
            self.structures = [#hardwired structures
                    #TODO update these for 10mm IBM board
                    Structure(self,start=(500,self.height/2),direction=0,defaults=self.defaults),
                    Structure(self,start=(500,700),direction=45,defaults=self.defaults),
                    Structure(self,start=(2500,500),direction=90,defaults=self.defaults),
                    Structure(self,start=(4500,500),direction=90,defaults=self.defaults),
                    Structure(self,start=(self.width-500,700),direction=135,defaults=self.defaults),
                    Structure(self,start=(self.width-500,self.height/2),direction=180,defaults=self.defaults),
                    Structure(self,start=(self.width-500,self.height-700),direction=225,defaults=self.defaults),
                    Structure(self,start=(4500,self.height-500),direction=270,defaults=self.defaults),
                    Structure(self,start=(2500,self.height-500),direction=270,defaults=self.defaults),
                    Structure(self,start=(500,self.height-700),direction=315,defaults=self.defaults)]
        if wafer.frame:
            self.add(dxf.rectangle(self.center,6000,6000,layer=wafer.lyr('FRAME'),halign = const.CENTER,valign = const.MIDDLE,linetype='DOT'))

# ===============================================================================
#  LARGE MARKER CHIP CLASS  
#       chip with large centered rectangle for high visibility
#       NOTE: ribs enabled greatly increases file size
# ===============================================================================

class MarkerLarge(Chip):
    filling = 0
    def __init__(self,wafer,chipID,layer,filling,ribs=0):
        Chip.__init__(self,wafer,chipID,layer)
        self.filling = filling
        if ribs>0:
            for i in range(int(self.height/ribs)):
                self.add(dxf.rectangle((self.cx(-self.width*filling/2),i*ribs),self.width*filling,ribs/2,bgcolor = wafer.bg(layer)))
        else:
            self.add(dxf.rectangle((self.cx(-self.width*filling/2),0),self.width*filling,self.height,bgcolor = wafer.bg(layer)))
        
# ===============================================================================
#  BLANK CENTERED WR10 CHIP CLASS  
#       chip with a rectangle marking dimensions of wr10 waveguide
# ===============================================================================

class BlankCenteredWR10(Chip):
    def __init__(self,wafer,chipID,layer,offset=(0,0)):
        Chip.__init__(self,wafer,chipID,layer)
        self.center = self.centered(offset)
        if wafer.frame:
            self.add(dxf.rectangle(self.centered((-1270,-635)),2540,1270,layer=wafer.lyr('FRAME')))  

# ===============================================================================
# CHIP CLASS FOR LINCOLN LABS DESIGNS
# ===============================================================================

class ChipLL_2port(Chip):
    def __init__(self,wafer,chipID,layer,structures=None,defaults=None, FRAME_NAME='FRAME'):
        Chip.__init__(self,wafer,chipID,layer,structures=structures, FRAME_NAME=FRAME_NAME)
        self.defaults = {'w':10, 's':6, 'radius':50,'r_out':0,'r_ins':0}
        if defaults is not None:
            #self.defaults = defaults.copy()
            for d in defaults:
                self.defaults[d]=defaults[d]
        if structures is not None:
            #override default structures
            self.structures = structures
        else:
            self.structures = [#hardwired structures
            Structure(self,start=(self.width/2, 100),direction=90,defaults=self.defaults),
            Structure(self,start=(self.width/2, self.height-100),direction=-90,defaults=self.defaults),
            ]

class ChipLL_6port(Chip):
    def __init__(self,wafer,chipID,layer,structures=None,defaults=None, FRAME_NAME='FRAME'):
        Chip.__init__(self,wafer,chipID,layer,structures=structures, FRAME_NAME=FRAME_NAME)
        self.defaults = {'w':10, 's':6, 'radius':50,'r_out':0,'r_ins':0}
        if defaults is not None:
            #self.defaults = defaults.copy()
            for d in defaults:
                self.defaults[d]=defaults[d]
        if structures is not None:
            #override default structures
            self.structures = structures
        else:
            self.structures = [#hardwired structures
            Structure(self,start=(100,1200),direction=0,defaults=self.defaults),
            Structure(self,start=(100,self.height-1200),direction=0,defaults=self.defaults),
            Structure(self,start=(self.width/2,self.height-100),direction=-90,defaults=self.defaults),
            Structure(self,start=(self.width-100,self.height-1200),direction=180,defaults=self.defaults),
            Structure(self,start=(self.width-100,1200),direction=180,defaults=self.defaults),
            Structure(self,start=(self.width/2,100),direction=90,defaults=self.defaults),
            ]

class ChipLL_20port(Chip):
    def __init__(self,wafer,chipID,layer,structures=None,defaults=None, FRAME_NAME='FRAME'):
        Chip.__init__(self,wafer,chipID,layer,structures=structures, FRAME_NAME=FRAME_NAME)
        self.defaults = {'w':10, 's':6, 'radius':50,'r_out':0,'r_ins':0}
        if defaults is not None:
            #self.defaults = defaults.copy()
            for d in defaults:
                self.defaults[d]=defaults[d]
        if structures is not None:
            #override default structures
            self.structures = structures
        else:
            self.structures = [#hardwired structures
            Structure(self,start=(100,700),direction=0,defaults=self.defaults),
            Structure(self,start=(100,1900),direction=0,defaults=self.defaults),
            Structure(self,start=(100,3100),direction=0,defaults=self.defaults),
            Structure(self,start=(100,4300),direction=0,defaults=self.defaults),

            Structure(self,start=(625, self.height-25),direction=-90,defaults=self.defaults),
            Structure(self,start=(1375,self.height-100),direction=-90,defaults=self.defaults),
            Structure(self,start=(2125,self.height-100),direction=-90,defaults=self.defaults),
            Structure(self,start=(2875,self.height-100),direction=-90,defaults=self.defaults),
            Structure(self,start=(3625,self.height-100),direction=-90,defaults=self.defaults),
            Structure(self,start=(4375,self.height-25),direction=-90,defaults=self.defaults),

            Structure(self,start=(self.width-100,4300),direction=180,defaults=self.defaults),
            Structure(self,start=(self.width-100,3100),direction=180,defaults=self.defaults),
            Structure(self,start=(self.width-100,1900),direction=180,defaults=self.defaults),
            Structure(self,start=(self.width-100,700),direction=180,defaults=self.defaults),

            Structure(self,start=(4375,25),direction=90,defaults=self.defaults),
            Structure(self,start=(3625,100),direction=90,defaults=self.defaults),
            Structure(self,start=(2875,100),direction=90,defaults=self.defaults),
            Structure(self,start=(2125,100),direction=90,defaults=self.defaults),
            Structure(self,start=(1375,100),direction=90,defaults=self.defaults),
            Structure(self,start=(625,25),direction=90,defaults=self.defaults),
            ]


# ===============================================================================
#  END CLASS DEFINITIONS   
# ===============================================================================
