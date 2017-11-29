"""This module contains classes for drawing"""

from enum import Enum
from schlib import *


NoFill = 'N'
Foreground = 'F'
Background = 'f'

AlignLeft = "L"
AlignCenter = "C"
AlignRight = "R"

AlignTop = "T"
AlignBottom = "B"

# convert pin orientation from KiCad directions to symgen directions
def kicad_to_symgen_dir (direction):
    if direction=="R":
        return "L"
    elif direction=="L":
        return "R"
    elif direction=="U":
        return "B"
    elif direction=="D":
        return "T"

# convert pin orientation from symgen directions to KiCad directions
def symgen_to_kicad_dir (direction):
    if direction=="R":
        return "L"
    elif direction=="L":
        return "R"
    elif direction=="B":
        return "U"
    elif direction=="T":
        return "D"

# convert kicad to symgen
def get_pin_type (_type, shape):

    flags = ""
    result = _type
    if result == "W":
        flags += "P"
        result = "I"
    elif result == "w":
        flags += "P"
        result = "O"

    if "C" in shape:
        flags += "C"
    if "F" in shape:
        flags += "F"
    if "L" in shape:
        flags += "L"
    if "V" in shape:
        flags += "V"
    if "N" in shape:
        flags += "N"
    if "X" in shape:
        flags += "X"
    if "I" in shape:
        flags = "~" + flags

    result = flags + result

    return result

def TextLength (s, fontsize):
    return fontsize * len(get_chars(s))

class Point:
    #x = 0
    #y = 0

    def __init__(self, px=0, py=0):
        self.x = px
        self.y = py

    def Sub (self, p):
        return Point (self.x - p.x, self.y-p.y)

    def Add (self, p):
        return Point (self.x + p.x, self.y + p.y)

    def __str__(self):
        return "P(%r, %r)" % (self.x, self.y)
    __repr__ = __str__

class Rectangle:

    def __init__(self, pos=None, size=None):
        if pos:
            self.pos = Point(pos.x, pos.y)
        else:
            self.pos = Point()

        if size:
            self.size = Point(size.x, size.y)
        else:
            self.size = Point()

    def center(self):
        return Point ( (self.pos.x + self.size.x) / 2, (self.pos.y - self.size.y) / 2)
    
    def left(self):
        return self.pos.x

    def top(self):
        return self.pos.y

    def right(self):
        return self.pos.x + self.size.x

    def bottom(self):
        return self.pos.y - self.size.y

    def __str__(self):
        return "R(%r, %r, %r, %r)" % (self.pos.x, self.pos.y, self.size.x, self.size.y)
    __repr__ = __str__


class BoundingBox(object):

    pmin = Point()
    pmax = Point()

    def __init__(self, p_min = None, p_max = None):
        self.pmin = Point()
        self.pmax = Point()
        self.valid = False
        if p_min:
            self.pmin.x = p_min.x
            self.pmin.y = p_min.y
            self.pmax.x = p_max.x
            self.pmax.y = p_max.y
            self.valid = True

    def extend (self, p):
        if self.valid:
            self.pmin.x = min(self.pmin.x, p.x)
            self.pmin.y = min(self.pmin.y, p.y)
            self.pmax.x = max(self.pmax.x, p.x)
            self.pmax.y = max(self.pmax.y, p.y)
        else:
            self.pmin.x = p.x
            self.pmin.y = p.y
            self.pmax.x = p.x
            self.pmax.y = p.y
            self.valid = True

    def __add__(self, other):
        if other == 0:
            return BoundingBox(self.pmin, self.pmax)
        return BoundingBox(
                Point (min(self.pmin.x, other.pmin.x), min(self.pmin.y, other.pmin.y)),
                Point (max(self.pmax.x, other.pmax.x), max(self.pmax.y, other.pmax.y)) )
    __radd__ = __add__

    def __repr__(self):
        return "BoundingBox(%r, %r, %r, %r)" % (
                self.pmin.x, self.pmax.x, self.pmin.y, self.pmax.y)

    __str__ = __repr__

    @property
    def width(self):
        return self.pmax.x - self.pmin.x
    @property
    def height(self):
        return self.pmax.y - self.pmin.y
    @property
    def centerx(self):
        return (self.pmax.x + self.pmin.x) / 2
    @property
    def centery(self):
        return (self.pmax.y + self.pmin.y) / 2

class DrawBase(object):

    key = ' '
    unit=0
    demorgan=1
    pensize=10
    fill = NoFill

    def __init__(self, s=None):
        self.key = ' '
        self.unit=0
        self.demorgan=1
        self.pensize=10
        self.fill=NoFill

    def parse (self, s):
        pass

    def get_values (self):
        values = [] 
        return values

    def get_element (self):
        return [self.key, dict(zip(Component._KEYS[self.key], self.get_values() )) ]

    def get_bounds (self):
        bb = BoundingBox(Point(),Point())
        return bb

class Pin (DrawBase):

    def __init__(self, s=None):
        self.unit = 0
        self.demorgan = 0

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

        # extra stuff
        self.qualifiers = ""
        self.align = ""

        super(Pin, self).__init__()
        self.key = 'X'
        if s:
            self.parse (s)

    def get_values (self):
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
        values.append (str(self.demorgan))
        values.append (self.type)
        values.append (self.shape)
        return values

    # parse, get_bounds

    def is_output(self):
        return self.type in ['O','B','T','C','E']

    def is_input(self):
        return self.type in ['I','B'] and not 'W' in self.shape.upper()

    def get_string (self):
        if self.shape == " " :
            return "SPC %s" % (kicad_to_symgen_dir(self.orientation))
        else:
            s = "%s %s %s %s%s" % (self.number, self.name, get_pin_type (self.type, self.shape), kicad_to_symgen_dir(self.orientation), 
                                 "" if self.align == "L" else self.align)
            if self.qualifiers:
                s += '"'+self.qualifiers+'"'
            return s


    def __str__(self):
        return self.get_string()
    __repr__ = __str__

class Arc (DrawBase):

    pos=Point()
    radius=0
    arcstart=0
    arcend=0
    start=Point()
    end=Point()

    def __init__(self, s=None):
        super(Arc, self).__init__()
        self.key = 'A'
        if s:
            self.parse (s)

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

    def get_values (self):
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

    def get_bounds (self):
        bb = BoundingBox(Point(),Point())
        # todo: maybe not right?
        bb.extend (self.start)
        bb.extend (self.end)
        return bb


class Circle (DrawBase):
    center = Point()
    radius = 0

    def __init__(self, s = None):
        super(Circle, self).__init__()
        self.key = 'C'
        if s:
            self.parse (s)


    def parse (self, s):
        tokens = s.split()
        self.center.x = int(tokens[1])
        self.center.y = int(tokens[2])
        self.radius = int(tokens[3])
        self.unit = int(tokens[4])
        self.demorgan = int(tokens[5])
        self.pensize = int(tokens[6])
        self.fill = tokens[7]

    def get_values(self):
        # ['posx','posy','radius','unit','convert','thickness','fill']
        values = []
        values.append (str(int(self.center.x)))
        values.append (str(int(self.center.y)))
        values.append (str(int(self.radius)))
        values.append (str(int(self.unit)))
        values.append (str(int(self.demorgan)))
        values.append (str(int(self.pensize)))
        values.append (self.fill)
        return values

    def get_bounds (self):
        bb = BoundingBox(Point(),Point())
        bb.extend (Point (self.center.x - self.radius, self.center.x - self.radius))
        bb.extend (Point (self.center.x + self.radius, self.center.x + self.radius))
        return bb

class PolyLine (DrawBase):

    def __init__(self, s=None):
        super(PolyLine, self).__init__()
        self.key = 'P'

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

    def get_values (self):
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

    def get_bounds (self):
        bb = BoundingBox(Point(),Point())
        for p in self.points:
            bb.extend (p)
        return bb

    def get_point_list (self):
        pts=[]
        for p in self.points:
            pts.append (str(int(round(p.x))))
            pts.append (str(int(round(p.y))))
        return pts

class Rect (DrawBase):

    p1 = Point()
    p2 = Point()

    def __init__(self, s=None):
        super(Rect, self).__init__()
        self.key = 'S'
        if s:
            self.parse (s)

    def SetParams (self, unit, variant, pensize, fill, p1, p2):
        self.unit = unit     
        self.demorgan = variant
        self.pensize = pensize
        self.fill = fill

        self.p1 = p1
        self.p2 = p2

    def parse (self, s):
        tokens = s.split()
        self.p1.x = int(tokens[1])
        self.p1.y = int(tokens[2])
        self.p2.x = int(tokens[3])
        self.p2.y = int(tokens[4])
        self.unit = int(tokens[5])
        self.demorgan = int(tokens[6])
        self.pensize= int(tokens[7])
        self.fill = tokens[8]

    def get_values (self):
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

    def get_bounds (self):
        bb = BoundingBox(Point(),Point())
        bb.extend (self.p1)
        bb.extend (self.p2)
        return bb


class Text (DrawBase):

    # ['direction','posx','posy','text_size','text_type','unit','convert','text', 'italic', 'bold', 'hjustify', 'vjustify']

    value = "~"  # text
    pos = Point()
    angle = 0.0  # direction
    text_size = 50
    visible = True  # text_type
    horiz_alignment = "C"   # L C R
    vert_alignment = "C"    # T C B
    italic = False
    bold = False

    def __init__(self, s = None):
        super(Text, self).__init__()
        self.key = 'T'
        if s:
            self.parse (s)

    def parse (self, s):
        tokens = s.split()
        self.angle = float(tokens[1])/10.0
        self.pos.x = int(tokens[2])
        self.pos.y = int(tokens[3])
        self.text_size = int(tokens[4])
        self.visible = True if tokens[5]=="0" else False
        self.unit = int(tokens[6])
        self.demorgan = int(tokens[7])
        self.value = tokens[8]
        self.italic = True if tokens[9]=="Italic" else False
        self.bold = True if tokens[10]=="1" else False
        self.horiz_alignment = tokens[11]
        self.vert_alignment = tokens[12]

        #self.pensize= int(tokens[7])
        #self.fill = tokens[8]

    def get_values (self):
        values = []
        values.append (str(int(self.angle*10.0)))
        values.append (str(int(self.pos.x)))
        values.append (str(int(self.pos.y)))
        values.append (str(self.text_size))
        values.append ("0" if self.visible else "1")
        values.append (str(self.unit))
        values.append (str(self.demorgan))
        values.append ('"' + self.value + '"')      # quotes, escaping
        values.append ("Italic" if self.italic else "Normal")
        values.append ("1" if self.bold else "0")
        values.append (self.horiz_alignment)
        values.append (self.vert_alignment)
        return values

    def get_bounds (self):
        bb = BoundingBox(Point(),Point())
        # todo: need to adjust for alignment, angle
        bb.extend (self.pos)
        bb.extend (self.pos.Add (self.text_size * len(self.value), self.text_size) )
        return bb

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
