"""This module contains classes for drawing"""

from schlib import *

class Point:
    x = 0
    y = 0

    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

    def Sub (self, p):
        return Point (self.x - p.x, self.y-p.y)

class DrawBase(object):

    key = ' '
    unit=0
    demorgan=0
    pensize=10
    fill="N"

    def __init__(self, s=None):
        self.key = ' '
        self.unit=0
        self.demorgan=0
        self.pensize=10
        self.fill="N"

    def getvalues (self):
        values = [] 
        return values

    def get_element (self):
        return [self.key, dict(zip(Component._KEYS[self.key], self.getvalues() )) ]

class Pin:

    orientation = "L"
    align = " "

    def __init__(self):
        self.unit = 0
        self.convert = 0

        self.name=""
        self.number=""
        self.pos = Point()
        self.length = 100
        self.orientation="L"
        self.sizenum = 50
        self.sizename = 50
        self.type = "I"
        self.shape = " "
        self.visible = True

    def getvalues (self):
        values = [] 
        values.append (self.name)
        values.append (self.number)
        values.append (str(self.pos.x))
        values.append (str(self.pos.y))
        values.append (str(self.length))
        values.append (self.orientation)
        values.append (str(self.sizename))
        values.append (str(self.sizenum))
        values.append (str(self.unit))
        values.append (str(self.convert))
        values.append (self.type)
        values.append (self.shape)
        return values

    def is_output(self):
        return self.type in ['O','B','T','C','E']

    def is_input(self):
        return self.type in ['I','B']

class Arc:
    unit=0
    demorgan=0
    pensize=10
    fill="N"

    pos=Point()
    radius=0
    arcstart=0
    arcend=0
    start=Point()
    end=Point()

    def __init__(self, s=None):
        if s:
            self.parse (s)

    def getvalues (self):
        values = []
        values.append (str(int(self.pos.x)))
        values.append (str(int(self.pos.y)))
        values.append (str(int(self.radius)))
        values.append (str(int(self.arcstart)))
        values.append (str(int(self.arcend)))
        values.append (str(self.unit))
        values.append (str(self.demorgan))
        values.append (str(int(self.pensize)))
        values.append (self.fill)
        values.append (str(int(self.start.x)))
        values.append (str(int(self.start.y)))
        values.append (str(int(self.end.x)))
        values.append (str(int(self.end.y)))
        return values

    def parse (self, s):
        tokens = s.split()
        self.pos.x = int(tokens[1])
        self.pos.y = int(tokens[2])
        self.radius= int(tokens[3])
        self.arcstart = int(tokens[4])
        self.arcend= int(tokens[5])
        self.unit=int(tokens[6])
        self.demorgan=int(tokens[7])
        self.pensize=int(tokens[8])
        self.fill = tokens[9]
        self.start.x = int(tokens[10])
        self.start.y = int(tokens[11])
        self.end.x = int(tokens[12])
        self.end.y = int(tokens[13])

    def SetParams (self, unit, variant, pensize, fill, startpos, endpos, pos, radius, startangle, endangle):
        self.unit = unit     
        self.demorgan = variant
        self.pensize = pensize
        self.fill = fill

        self.pos = pos
        self.radius = radius
        self.arcstart = startangle * 10
        self.arcend = endangle * 10
        self.start = startpos
        self.end = endpos

    def get_element (self):
        return ['A', dict(zip(Component._ARC_KEYS, self.getvalues() )) ]


class Circle (DrawBase):

    def __init__(self, s = None):
        super(Circle, self).__init__()
        self.key = 'C'    

class PolyLine:

    def __init__(self, s=None):
        self.unit=0
        self.demorgan=0
        self.pensize=10
        self.fill="N"

        self.point_count =0
        self.points = []

        if s:
            self.parse (s)

    def parse (self, s):
        # e.g "P 2 0 1 8 -300 -200 0 -200 N"
        tokens = s.split()
        self.point_count=int(tokens[1])
        self.unit=int(tokens[2])
        self.demorgan=int(tokens[3])
        self.pensize=int(tokens[4])
        for j in range(0, self.point_count):
            pt = Point(int (tokens[5+j*2]), int(tokens[6+j*2]))
            self.points.append(pt)
        self.fill = tokens[-1]

    def SetParams (self, unit, variant, pensize, fill, pts):
        self.unit = unit     
        self.demorgan = variant
        self.pensize = pensize
        self.fill = fill

        self.point_count = len(pts)
        self.points = pts

    def getvalues (self):
        values = []
        values.append (str(self.point_count))
        values.append (str(self.unit))
        values.append (str(self.demorgan))
        values.append (str(self.pensize))

        pts=[]
        for p in self.points:
            pts.append (str(int(round(p.x))))
            pts.append (str(int(round(p.y))))
        values.append (pts)
        values.append (self.fill)

        return values

    def get_element (self):
        return ['P', dict(zip(Component._POLY_KEYS, self.getvalues() )) ]


class Rect:
    unit = 0
    demorgan = 1
    pensize = 10
    fill = "N"

    p1 = Point()
    p2 = Point()

    def __init__(self):
        pass

    def getvalues (self):
        values = []
        values.append (str(self.p1.x))
        values.append (str(self.p1.y))
        values.append (str(self.p2.x))
        values.append (str(self.p2.y))
        values.append (str(self.unit))
        values.append (str(self.demorgan))
        values.append (str(self.pensize))
        values.append (self.fill)
        return values


# "P 2 0 1 8 -300 -200 0 -200 N"
def parse_polyline (s):
    tokens = s.split()
    poly = PolyLine()
    poly.point_count=int(tokens[1])
    poly.unit=int(tokens[2])
    poly.demorgan=int(tokens[3])
    poly.pensize=int(tokens[4])
    for j in range(0,poly.point_count):
        pt = Point(int (tokens[5+j*2]), int(tokens[6+j*2]))
        poly.points.append(pt)
    poly.fill = tokens[-1]

    return poly

def parse_arc (s):
    tokens = s.split()
    arc = Arc()
    arc.pos.x = int(tokens[1])
    arc.pos.y = int(tokens[2])
    arc.radius= int(tokens[3])
    arc.arcstart = int(tokens[4])
    arc.arcend= int(tokens[5])
    arc.unit=int(tokens[6])
    arc.demorgan=int(tokens[7])
    arc.pensize=int(tokens[8])
    arc.fill = tokens[9]
    arc.start.x = int(tokens[10])
    arc.start.y = int(tokens[11])
    arc.end.x = int(tokens[12])
    arc.end.y = int(tokens[13])

    return arc
