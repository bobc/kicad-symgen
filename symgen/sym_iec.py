# -*- coding: utf-8 -*-

from  math import *
from schlib import *
from sym_drawing import *



class IecBase(object):
    """description of class"""

    def __init__(self):
        pass
"""
symbol-unit
    element  [control] [1+]
        group 
            pin    
        pin
      

--
comp 40245
unit 
control
19 G ~I L
1 Dir ~I 
element "1"
2 ~ B L
18 ~ B R
element [3,17]
...
end


comp 400
unit 
control
19 CP ~C L
element
1 DA I L
13 Q3A O R
11 Q3B O R
element

18 Q3B O R
...
end


==
unit box | or
    element [1]
        pins*

unit pwr
"""

class Group (IecBase):

    def __init__(self):
        self.label = ""
        self.id = 0
        self.pins = []
        self.type = " "
        self.label = ""
        self.qualifiers = ""

# aka Unit
class IecSymbol (IecBase):
    #control = None

    elements = []

    def __init__(self):
        self.icons = []
        self.elements = []

        self.unit_shape = ""
        self.template = None

        self.is_power_unit = False
        self.is_overlay = False

        self.unit_rect = Rectangle()

        self.vert_margin = 0
        # self.box_width = 0
        # self.y_offset = 0
        # self.y_pin_extent = 0

    def draw (self, comp, unit, variant):
        pos = Point(0,0)
        width = 600
        for element in elements:
            height = element.draw (comp, unit, variant, pos, width)
            pos.y += height
        # return height
        return pos.y


class IecElement (IecBase):

#    groups = []
#    shape = "box"
    # todo: for now
#    pins = []

    def __init__(self):
        self.pins = []
        self.shape = "box"
        self.label = ""
        self.groups = []

    def draw (self, comp, unit, variant, pos, width):
        height = 100

        origin = Point (width/2, 0)

        rect = Rect ()
        rect.p1 = Point (0,0).Sub (origin)
        rect.p2 = Point (width, height).Sub (origin)
        rect.unit = unit
        rect.demorgan = variant
        comp.drawOrdered.append(rect.get_element())

        # return height?
        return height




