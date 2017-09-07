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
    section :    [1+]
        control  [0..1]
            group 
                pin    
            pin

        element  [1+]
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

# aka Unit
class IecSymbol (IecBase):
    #control = None
    sections = []

    def __init__(self):
        pass

    def draw (self, comp, unit, variant):
        pos = Point(0,0)
        width = 600
        for section in sections:
            height = section.draw (comp, unit, variant, pos, width)
            pos.y += height
        # return height
        return pos.y


class IecSection (IecBase):
    groups = []

    # todo: for now
    pins = []
    
    def __init__(self):
        pass

class IecControl (IecSection):

    def __init__(self):
        pass

class IecElement (IecSection):

    def __init__(self):
        pass

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




