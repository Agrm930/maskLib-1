# -*- coding: utf-8 -*-
"""
Created on Mon Apr  6 11:53:13 2020

@author: sasha
"""
from dxfwrite import DXFEngine as dxf
from dxfwrite.algebra import rotate_2d
from dxfwrite.vector2d import vadd,midpoint,vmul_scalar,vsub
import math
import numpy as np

# ===============================================================================
#  UTILITY FUNCTIONS  
# ===============================================================================
     

def curveAB(a,b,clockwise=True,angleDeg=90,ptDensity=120):
    # generate a segmented curve from A to B specified by angle. Point density = #pts / revolution
    # return list of points
    # clockwise can be boolean {1,0} or sign type {1,-1}
    
    if clockwise == 0:
        clockwise = -1
        
    angle = math.radians(angleDeg)
    segments = int(angle/(2*math.pi) *ptDensity)
    center = vadd(midpoint(a,b),vmul_scalar(rotate_2d(vsub(b,a),-clockwise*math.pi/2),0.5/math.tan(angle/2)))
    points = []
    for i in range(segments+1):
        points.append(vadd(center,rotate_2d(vsub(a,center),-clockwise*i*angle/segments)))
    return points

def cornerRound(vertex,quadrant,radius,clockwise=True,ptDensity=120):
    #quadrant corresponds to quadrants 1-4
    #generate a curve to replace the vertex
    ptA = vadd(vertex,rotate_2d((0,radius),quadrant * math.pi/2))
    ptB = vadd(vertex,rotate_2d((0,radius),(quadrant+1) * math.pi/2))

    return clockwise>0 and curveAB(ptA,ptB,1,ptDensity=ptDensity) or curveAB(ptB,ptA,-1,ptDensity=ptDensity)

def transformedQuadrants(vflip=False,hflip=False):
    #return quadrant list with vertical and horizontal flips applied. Updated to match dxfwrite style
    # default quadrants:
        
    #    ^y
    #  2 | 1
    #  --+--->x
    #  3 | 4
    
    return vflip==False and (hflip==False and [0,1,2,3,4] or [0,2,1,4,3]) or (hflip==False and [0,4,3,2,1] or [0,3,4,1,2])

def kwargStrip(kwargs,keys=['layer']):
    # return kwargs with only entries specified by keys
    return {k:kwargs[k] for k in keys if k in kwargs}


def doMirrored(func,canvas,pos,*args,**kwargs):
    #experimental- executes function 'func' with second argument mirrored around x and y
    # mirrorX : mirrors along X axis (1,0)
    # mirrorY : mirrors along Y axis (0,1)
    
    if not isinstance(pos, tuple):
        print('\x1b[33mError:\x1b[0m Bad position args passed to doMirrorred()!')
        return
    #assign unlisted default args
    kwargs = { **{'mirrorX':True,'mirrorY':True}, **kwargs}
    #assign args and sanitize kwargs
    mirrorX = kwargs.pop('mirrorX')
    mirrorY = kwargs.pop('mirrorY')
    
    func(canvas,(pos[0],pos[1]),*args,**kwargs)
    if mirrorY:
        func(canvas,(pos[0],-pos[1]),*args,**kwargs)
    if mirrorX:
        func(canvas,(-pos[0],pos[1]),*args,**kwargs)
    if mirrorY and mirrorX:
        func(canvas,(-pos[0],-pos[1]),*args,**kwargs)

def snap_to_grid(pt, grid=None):
    """
    Snap a point or array of points to the nearest grid.
    Supports scalars, tuples, lists, or numpy arrays.
    Always returns floats for tuples/lists.
    If grid is None or 0, returns the original point (no snapping).
    """
    if grid is None or grid == 0:
        return pt
    arr = np.asarray(pt, dtype=float)
    snapped = np.round(arr / grid) * grid
    if isinstance(pt, (tuple, list)):
        return tuple(snapped.tolist())
    elif np.isscalar(pt):
        return float(snapped)
    else:
        return snapped