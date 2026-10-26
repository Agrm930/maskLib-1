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


def grow_convex_polygon(points, d):
    '''
    Offset a convex polygon by d with mitred corners: d > 0 grows it
    outward, d < 0 shrinks it inward, d = 0 returns it unchanged.
    Straight-through corners (parallel neighbouring edges) are dropped
    first. When shrinking collapses a short edge, that edge is dropped and
    its neighbours meet in a point instead of crossing over.
    points -- [(x, y), ...] in order (either winding)
    '''
    if d == 0:
        return list(points)

    def _cross(a, b, c):
        return (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
    points = [q for i, q in enumerate(points)
              if abs(_cross(points[i - 1], q, points[(i + 1) % len(points)])) > 1e-12]
    n = len(points)
    area2 = sum(points[i][0] * points[(i + 1) % n][1] - points[(i + 1) % n][0] * points[i][1]
                for i in range(n))
    sgn = 1 if area2 > 0 else -1          # CCW -> outward normal is (dy, -dx)
    lines = []                            # each edge shifted by d along its outward normal
    for i in range(n):
        (x1, y1), (x2, y2) = points[i], points[(i + 1) % n]
        dx, dy = x2 - x1, y2 - y1
        L = (dx * dx + dy * dy) ** 0.5
        nx, ny = sgn * dy / L, -sgn * dx / L
        lines.append(((x1 + d * nx, y1 + d * ny), (dx, dy)))

    def meet(a, b):                       # intersection of shifted edge lines a and b
        (px, py), (ux, uy) = a
        (qx, qy), (vx, vy) = b
        t = ((qx - px) * vy - (qy - py) * vx) / (ux * vy - uy * vx)
        return (px + t * ux, py + t * uy)

    while True:
        out = [meet(lines[i - 1], lines[i]) for i in range(len(lines))]
        # edge i runs out[i] -> out[i+1]; reversed direction = collapsed edge
        flipped = [i for i in range(len(lines))
                   if (out[(i + 1) % len(lines)][0] - out[i][0]) * lines[i][1][0]
                   + (out[(i + 1) % len(lines)][1] - out[i][1]) * lines[i][1][1] < 0]
        if not flipped:
            return out
        assert len(lines) - len(flipped) >= 3, 'grow_convex_polygon: shrink collapses the polygon'
        lines = [l for i, l in enumerate(lines) if i not in flipped]
