# -*- coding: utf-8 -*-

from  math import *
from schlib import *
from str_utils import *
from sym_drawing import *


def draw_text (comp, unit, variant, pos, s, fontsize, align_horiz = AlignLeft, align_vert = AlignBottom):

    chars = get_chars (s)
    s = ""
    for char in chars :
        if char in ["&xdtri;", "&xrtri;", "&circ;", "&st;"]:
            #
            if s != "":
                text = Text()        
                text.value = s
                text.unit = unit
                text.demorgan = variant
                text.pos = pos
                text.text_size = fontsize
                text.bold = True if fontsize > 50 else False
                text.horiz_alignment = align_horiz
                text.vert_alignment = align_vert
                comp.drawOrdered.append (text.get_element())
                pos.x += fontsize * len(s)
                s = ""

            if char == "&xdtri;":
                # white down-pointing triangle
                # unicode U+025BD
                poly = PolyLine ()
                poly.unit = unit
                poly.demorgan = variant
                poly.pensize = 0
                poly.points.append (Point (0,fontsize).Add (pos))
                poly.points.append (Point (fontsize,fontsize).Add (pos))
                poly.points.append (Point (fontsize/2,0).Add (pos))
                poly.points.append (Point (0,fontsize).Add (pos))
                poly.point_count = len(poly.points)
                comp.drawOrdered.append( poly.get_element() )
                pos.x += fontsize + 10
            elif char == "&xrtri;":
                # white right-pointing triangle
                # unicode U+025B7
                poly = PolyLine ()
                poly.unit = unit
                poly.demorgan = variant
                poly.pensize = 0
                poly.points.append (Point (0,0).Add (pos))
                poly.points.append (Point (0,fontsize).Add (pos))
                poly.points.append (Point (fontsize,fontsize/2).Add (pos))
                poly.points.append (Point (0,0 ).Add (pos))
                poly.point_count = len(poly.points)
                comp.drawOrdered.append( poly.get_element() )
                pos.x += fontsize + 15
            elif char == "&circ;":
                circle = Circle()
                circle.center = Point (pos.x + fontsize/2, pos.y+fontsize/2)
                circle.radius = fontsize/2
                circle.unit = unit
                circle.demorgan = variant
                circle.pensize = 0
                comp.drawOrdered.append( circle.get_element() )
                pos.x += fontsize + 10
            elif char == "&st;":
                # schmitt trigger
                # also Unicode U+238E Hysteresis symbol
                poly = PolyLine ()
                poly.unit = unit
                poly.demorgan = variant
                poly.pensize = 0
                poly.points.append (Point (0,0).Add (pos))
                poly.points.append (Point (30,0).Add (pos))
                poly.points.append (Point (40,50).Add (pos))
                poly.points.append (Point (50,50).Add (pos))
                poly.points.append (Point (20,50).Add (pos))
                poly.points.append (Point (10,0).Add (pos))
                poly.point_count = len(poly.points)
                comp.drawOrdered.append( poly.get_element() )
                pos.x += fontsize + 10
        else:
            if char.startswith ("&"):
                if char == "&xrtri;":
                    char = u'\u25B7'
                    char = char.encode('utf-8')
                elif char == "&ge;":
                    char = u'\u2265'
                    char = char.encode('utf-8')
                elif char == "&amp;":
                    char = '&'
                else:
                    char = '?'
                #char = u'\ufffd'

            s += char
    #
    if s!= "":
        text = Text()        
        text.value = s
        text.unit = unit
        text.demorgan = variant
        text.pos = pos
        text.text_size = fontsize
        text.bold = True if fontsize > 50 else False
        text.horiz_alignment = align_horiz
        text.vert_alignment = align_vert
        comp.drawOrdered.append (text.get_element())
        pos.x += fontsize + 10

class Gate:

    fill = Background
    pensize = 10

    num_inputs = 0
    offsets = []
    #pin_len = 150

    num_outputs = 1

    width = 300
    height = 300

    qualifiers = ""

    def __init__(self, num_inputs):
        self.num_inputs = num_inputs
        self.size_x_by_2 = self.width / 2

    def set_size (self, width, height):
        self.width = width
        self.height = height
        self.size_x_by_2 = width / 2

    def get_input_positions (self):
        return [], []

    def get_output_positions (self):
        return []

    def get_center (self):
        return Point (0,0)

    def add_gate_graphic (self, comp, unit, variant):
        pass

    def add_drawings (self, comp, unit, variant, drawings):
        for drawing in drawings:
            if drawing.startswith ("A"):
                arc=Arc(drawing)
                arc.unit = unit
                arc.demorgan = variant
                arc.pensize = self.pensize
                #arc.fill = self.fill
                comp.drawOrdered.append(arc.get_element())
            elif drawing.startswith ("P"):
                poly = PolyLine (drawing)
                poly.unit = unit
                poly.demorgan = variant
                poly.pensize = self.pensize
                #poly.fill = self.fill
                comp.drawOrdered.append(poly.get_element())
            ## todo, rect etc

    def r_pythagoras (self, x, h):
        return sqrt (h*h - x*x)

    def pythagoras (self, a, b):
        return sqrt (a*a + b*b)

    def circle_center (self, p1, p2, p3):
        mr = (p2.y-p1.y)/(p2.x-p1.x)
        mt = (p3.y-p2.y)/(p3.x-p2.x)
        x = mr*mt*(p3.y-p1.y) + mr*(p2.x+p3.x) - mt * (p1.x+p2.x)
        x = x / (2 * (mr-mt))
        y = -(x- (p1.x+p2.x)/2) / mr + (p1.y+p2.y) / 2
        radius = self.pythagoras (p1.x-x, p1.y-y)
        return Point (x,y), radius
    #
    def circle_center_2 (self, a1, a2, radius):
        radsq = radius * radius
        q = sqrt(((a2.x - a1.x) * (a2.x - a1.x)) + ((a2.y - a1.y) * (a2.y - a1.y)))
        
        x3 = (a1.x + a2.x) / 2
        x = x3 + sqrt(radsq - ((q / 2) * (q / 2))) * ((a1.y - a2.y) / q)

        y3 = (a1.y + a2.y) / 2
        y = y3 + sqrt(radsq - ((q / 2) * (q / 2))) * ((a2.x - a1.x) / q)

        return Point (x,y)

    def make_arc (self, pts, angle1, angle2, curpos, offset, r, reverso = 0):
        a = angle1
        # //PointF curpos = new PointF(x1, y1);
        newPos = Point()

        # resolution is 50 mil
        step = degrees(asin(50 / float(r)))
        
        temp=[]
        while a < angle2:
            newPos = Point(
                (int)(cos(radians(a)) * r + offset.x),
                (int)(sin(radians(a)) * r + offset.y))

            # module.Borders.Add(new fp_line(curpos, newPos, layer, 0.15f));
            temp.append (newPos)
            curpos = newPos
            # //a += MathUtil.DegToRad(0.5);
            a += step

        a = angle2
        newPos = Point(
            (int)(cos(radians(a)) * r + offset.x),
            (int)(sin(radians(a)) * r + offset.y))
        #module.Borders.Add(new fp_line(curpos, newPos, layer, 0.15f))
        temp.append (newPos)
        curpos = newPos

        if reverso:
            temp.reverse()
        pts.extend(temp)
        return curpos, pts

    def adjust_origin (self, pts, origin):
        result = []

        for p in pts:
            result.append (Point (p.x - origin.x, p.y-origin.y))
        return result

class AndGate (Gate):

    def __init__(self, num_inputs):
        Gate.__init__(self, num_inputs)

    def get_input_positions(self):
        if self.num_inputs==2:
            inputs_pos = [Point(-self.size_x_by_2,100), Point(-self.size_x_by_2,-100)]
            self.offsets = [0,0]
        elif self.num_inputs==3:
            inputs_pos = [Point(-self.size_x_by_2,100), Point(-self.size_x_by_2,0), Point(-self.size_x_by_2,-100)]
            self.offsets = [0,0,0]
        elif self.num_inputs==4:
            inputs_pos = [Point(-self.size_x_by_2,150), Point(-self.size_x_by_2,50), Point(-self.size_x_by_2,-50), Point(-self.size_x_by_2,-150)]
            self.offsets = [0,0,0,0]
        else:
            inputs_pos = []
            self.offsets = []
            top = (self.num_inputs-1)/2 * 100
            top = int(top/100) * 100
            for j in range(0, self.num_inputs):
                inputs_pos.append (Point (-self.size_x_by_2, top - j*100))
                self.offsets.append (0)
        return inputs_pos

    def get_output_positions(self):
        if self.num_inputs < 4:
            outputs_pos = [Point(self.size_x_by_2,0)]
        else:
            outputs_pos = [Point(self.size_x_by_2,0)]
        return outputs_pos
        
    def add_gate_graphic (self,comp,unit, variant):

        if self.num_inputs != 4:
            poly=PolyLine()
            poly.unit = unit
            poly.point_count=4
            poly.demorgan = variant
            poly.pensize = self.pensize
            poly.fill = self.fill
            poly.points.append (Point (0,150))
            poly.points.append (Point (-150,150))
            poly.points.append (Point (-150,-150))
            poly.points.append (Point (0,-150))
            comp.drawOrdered.append(poly.get_element())

            arc=Arc()
            arc.pos.x = 0
            arc.pos.y = 0
            arc.radius = 150
            arc.arcstart = -899
            arc.arcend = 899
            arc.unit = unit     
            arc.demorgan = variant
            arc.pensize = self.pensize
            arc.fill = self.fill
            arc.start.x= 0
            arc.start.y= -150
            arc.end.x  = 0
            arc.end.y  = 150
            comp.drawOrdered.append(arc.get_element())

        else:
            self.height = 350
            radius = self.height/2

            origin = Point (self.width/2, self.height/2)
            qx = self.width - radius

            pts = []
            pts.append (Point (qx,self.height))
            pts.append (Point (0,self.height))
            pts.append (Point (0,0))
            pts.append (Point (qx,0))
            poly=PolyLine()
            poly.SetParams (unit, variant, self.pensize, self.fill, self.adjust_origin (pts, origin))
            comp.drawOrdered.append(poly.get_element())

            arc=Arc()
            arc.pos = Point(qx,self.height/2).Sub(origin)
            arc.radius = radius
            arc.arcstart = -899
            arc.arcend = 899
            arc.unit = unit     
            arc.demorgan = variant
            arc.pensize= self.pensize
            arc.fill = self.fill
            arc.start   = Point(qx,0).Sub(origin)
            arc.end = Point(qx,self.height).Sub(origin)
            comp.drawOrdered.append(arc.get_element())

            
        if self.num_inputs > 4:
            height = (self.num_inputs-1) * 100
            top    = int(height/100/2) * 100

            poly=PolyLine()
            poly.unit = unit
            poly.demorgan = variant
            poly.point_count=2
            poly.points.append (Point (-self.size_x_by_2, top))
            poly.points.append (Point (-self.size_x_by_2, top-height))
            comp.drawOrdered.append(poly.get_element())
    

class OrGate (Gate):

    def __init__(self, num_inputs):
        Gate.__init__(self, num_inputs)


    def add_gate_graphic (self, comp, unit, variant):
        inputs_pos = self.get_input_positions()

        if self.num_inputs == 4:
            self.height = 350

        #
        origin = Point (self.width/2, self.height/2)

        pts = []
        qx2 = 0.1600 * self.width
        qx  = 0.4167 * self.width
          
        radius = 0.68 * self.height
        cp = self.circle_center_2 (Point(self.width, self.height/2), Point (qx, self.height), radius)

        b = self.r_pythagoras (self.height/2-cp.y, radius)
        ang1 = degrees(acos (b / radius))

        b = self.r_pythagoras (self.height-cp.y, radius)
        ang2 = degrees(acos (b / radius))

        pos = Point (cp.x, 0)
        if False:
            pos, pts = self.make_arc (pts, -ang2, -ang1, pos, Point(cp.x, self.height-cp.y), radius)
            pos, pts = self.make_arc (pts, ang1, ang2, pos, Point(cp.x, cp.y), radius)
        else:
            arc = Arc()
            arc.SetParams (unit, variant, self.pensize, self.fill, Point(self.width, self.height/2).Sub(origin), Point (qx, 0).Sub(origin), 
                Point(cp.x, self.height-cp.y).Sub(origin), radius, -ang1, -ang2)
            comp.drawOrdered.append(arc.get_element())
            arc = Arc()
            arc.SetParams (unit, variant, self.pensize, self.fill, Point(self.width, self.height/2).Sub(origin), Point (qx, self.height).Sub(origin), 
                cp.Sub(origin), radius, ang1, ang2)
            comp.drawOrdered.append(arc.get_element())

        pts=[]
        pts.append(Point (0, self.height))
        pts.append(Point (qx, self.height))
        poly=PolyLine()
        poly.SetParams (unit, variant, self.pensize, self.fill, self.adjust_origin(pts, origin))
        comp.drawOrdered.append(poly.get_element())

        pts=[]
        pts.append(Point (0, 0))
        pts.append(Point (qx, 0))
        poly=PolyLine()
        poly.SetParams (unit, variant, self.pensize, self.fill, self.adjust_origin(pts, origin))
        comp.drawOrdered.append(poly.get_element())

        # fill poly, no outline
        pts=[]
        pts.append(Point (qx, self.height))
        pts.append(Point (0, self.height))
        #
        cp, radius = self.circle_center (Point(0,self.height), Point(qx2,self.height/2), Point (0,0))
        ang = degrees(asin (self.height/2 / radius))
        pos, pts = self.make_arc (pts, -ang, ang, Point(0,0), Point(-radius+qx2,self.height/2), radius, reverso=1)
        #
        pts.append(Point (0, 0))
        pts.append(Point (qx, 0))

        poly=PolyLine()
        poly.SetParams (unit, variant, -1000, self.fill, self.adjust_origin(pts, origin))
        comp.drawOrdered.append(poly.get_element())

        # draw arc, no fill
        arc = Arc()
        arc.SetParams (unit, variant, self.pensize, 'N', Point(0, self.height).Sub(origin), Point (0, 0).Sub(origin), 
            cp.Sub(origin), radius, ang, -ang)
        comp.drawOrdered.append(arc.get_element())

        #for j in range (0, len(self.offsets)):
        #    poly=parse_polyline ("P 2 0 1 6 %d %d %d %d N" % (inputs_pos[j].x, inputs_pos[j].y, inputs_pos[j].x+self.offsets[j], inputs_pos[j].y ))
        #    poly.unit = unit
        #    poly.demorgan = variant
        #    comp.drawOrdered.append(['P', dict(zip(Component._POLY_KEYS, poly.getvalues() )) ])

        if self.num_inputs>4:
            height = (self.num_inputs-1) * 100
            top = int(height/100/2) * 100

            poly=PolyLine()
            poly.unit = unit
            poly.demorgan = variant
            poly.point_count=2
            poly.points.append (Point (-self.size_x_by_2, top))
            poly.points.append (Point (-self.size_x_by_2, 150))
            comp.drawOrdered.append(poly.get_element())

            poly=PolyLine()
            poly.unit = unit
            poly.demorgan = variant
            poly.point_count=2
            poly.points.append (Point (-self.size_x_by_2, -150))
            poly.points.append (Point (-self.size_x_by_2, top-height))
            comp.drawOrdered.append(poly.get_element())

    def get_input_positions (self):
        if self.num_inputs==2:
            inputs_pos = [Point(-self.size_x_by_2,100), Point(-self.size_x_by_2,-100)]
            self.offsets = [20, 20]
        elif self.num_inputs==3:
            inputs_pos = [Point(-self.size_x_by_2,100), Point(-self.size_x_by_2,0), Point(-self.size_x_by_2,-100)]
            self.offsets = [20,45,20]
        elif self.num_inputs==4:
            inputs_pos = [Point(-self.size_x_by_2,150), Point(-self.size_x_by_2,50), Point(-self.size_x_by_2,-50), Point(-self.size_x_by_2,-150)]
            self.offsets = [0,40,40,0]
        else:
            inputs_pos = []
            self.offsets = []
            top = (self.num_inputs-1)/2 * 100
            top = int(top/100) * 100
            for j in range(0, self.num_inputs):
                y = top - j*100

                if y < 150 and y > -150 :
                    # centre at -350,0
                    x = sqrt (250*250 - y*y)
                    self.offsets.append (int(x-200))
                else:
                    self.offsets.append (0)

                inputs_pos.append (Point (-self.size_x_by_2, top - j*100))
        return inputs_pos

    def get_output_positions (self):
        if self.num_inputs < 4:
            outputs_pos = [Point(self.size_x_by_2, 0)]
        else:
            outputs_pos = [Point(self.size_x_by_2, 0)]
        return outputs_pos


class XorGate (Gate):

    def __init__(self, num_inputs):
        Gate.__init__(self, num_inputs)

    def add_gate_graphic (self, comp, unit, variant):
        inputs_pos = self.get_input_positions()

        # get the basic OR shape
        or_gate = OrGate(self.num_inputs)
        or_gate.fill = self.fill
        or_gate.add_gate_graphic (comp, unit, variant)

        # add an extra arc on left
        qx1 = 0.083 * self.width
        qx2 = 0.1600 * self.width
        origin = Point (self.width/2, self.height/2)
        cp, radius = self.circle_center (Point(-qx1,self.height), Point(qx2-qx1,self.height/2), Point (-qx1,0))
        ang = degrees(asin (self.height/2 / radius))

        arc = Arc()
        arc.SetParams (unit, variant, self.pensize, 'N', Point(-qx1, self.height).Sub(origin), Point (-qx1, 0).Sub(origin), 
            cp.Sub(origin), radius, ang, -ang)
        comp.drawOrdered.append(arc.get_element())

        # ??
        for j in range (0, len(self.offsets)):
            poly=PolyLine ("P 2 0 1 6 %d %d %d %d N" % (inputs_pos[j].x, inputs_pos[j].y, inputs_pos[j].x+self.offsets[j], inputs_pos[j].y ))
            poly.unit = unit
            comp.drawOrdered.append(poly.get_element())


    def get_input_positions (self):
        if self.num_inputs==2:
            inputs_pos = [Point(-self.size_x_by_2,100), Point(-self.size_x_by_2,-100)]
            self.offsets = [25, 25]
        elif self.num_inputs==3:
            inputs_pos = [Point(-self.size_x_by_2, 100), Point(-self.size_x_by_2, 0), Point(-self.size_x_by_2, -100)]
            self.offsets = [0,25,0]
        else:
            inputs_pos = []
            self.offsets = []
        return inputs_pos

    def get_output_positions (self):
        if self.num_inputs < 4:
            outputs_pos = [Point(self.size_x_by_2,0)]
        else:
            outputs_pos = [Point(300,0)]
        return outputs_pos

class NotGate (Gate):

    def __init__(self, num_inputs):
        Gate.__init__(self, num_inputs)

    def add_gate_graphic (self, comp, unit, variant):

        poly = PolyLine("P 4 0 0 10 -150 150 -150 -150 150 0 -150 150 f")
        poly.unit = unit
        poly.demorgan = variant
        poly.fill = self.fill
        poly.pensize = self.pensize
        comp.drawOrdered.append(poly.get_element())
        
    def get_input_positions (self):
        inputs_pos = [Point(-150,0), Point(0, -75)]
        self.offsets = [0, 0]
        return inputs_pos

    def get_output_positions (self):
        outputs_pos = [Point(150,0)]
        return outputs_pos

    def get_center (self):
        return Point (self.width/3-self.width/2, 0)

#
# IEC style (box) logic symbols
#
class IecGate (Gate):

    type = "or"

    def __init__(self, num_inputs):
        Gate.__init__(self, num_inputs)

    def get_input_positions(self):
        inputs_pos = []
        self.offsets = []

        if self.num_inputs == 2:
            inputs_pos.append (Point (-self.size_x_by_2, 100))
            inputs_pos.append (Point (-self.size_x_by_2, -100))
            self.offsets.append (0)
            self.offsets.append (0)

        else:
            top = (self.num_inputs-1) * 100 / 2
            #top = int(top/100) * 100
            for j in range(0, self.num_inputs):
                inputs_pos.append (Point (-self.size_x_by_2, top - j*100))
                self.offsets.append (0)
        return inputs_pos

    def get_output_positions(self):
        #outputs_pos = [Point(self.size_x_by_2,0)]
        outputs_pos = []
        top = (self.num_outputs-1) * 100 / 2
        for j in range(0, self.num_outputs):
            outputs_pos.append (Point (self.size_x_by_2, top - j*100))

        return outputs_pos
        
    def add_gate_graphic (self,comp,unit,variant):

        if self.num_inputs*100 >= self.height:
            self.height = self.num_inputs*100 + 50

        origin = Point (self.width/2, self.height/2)

        rect = Rect ()
        rect.p1 = Point (0,0).Sub (origin)
        rect.p2 = Point (self.width, self.height).Sub (origin)
        rect.unit = unit
        rect.demorgan = variant
        comp.drawOrdered.append(rect.get_element())

        text = Text()
        text.unit = unit
        text.demorgan = variant
        if self.type in ["or","nor"]:
            text.value = "≥1" # ">=1" 
        elif self.type in ["and","nand"]:
            text.value = "&"
        elif self.type in ["xor","xnor"]:
            text.value = "=1"
        elif self.type in ["not","buffer"]:
            text.value = "1"

        #text.value = self.qualifiers + text.value
        #
        comp.drawOrdered.append(text.get_element())

        pos = Point(-len(get_chars(self.qualifiers)) * 50 - len(text.value.decode('utf-8'))*50/2, -25)
        draw_text (comp, unit, variant, pos, self.qualifiers, 50)

           
