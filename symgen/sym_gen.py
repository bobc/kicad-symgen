#
# Generate components from text file
# 
# Usage: symgen
#
# Copyright Bob Cousins 2017
#
# Licensed under GPLv3
#
# Version 1

# todo:
#
#   de morgans 
#   symbol origin
#   xor, not
#   pin types, tristate etc
#   error reporting
#   field pos?
#   doc fields
#   ieee symbols
#   parametize input/output file names etc 


import os, re
from os import path, environ
import sys
#
# kicad lib utils
common = os.path.abspath(os.path.join(sys.path[0], 'common'))
if not common in sys.path:
    sys.path.append(common)
#
from schlib import *

from print_color import *

class Point:
    x = 0
    y = 0

    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

class Pin:
    unit = 0
    convert =0

    name=""
    number=""
    pos = Point()
    length = 100
    orientation="L"
    sizenum =50
    sizename =50
    type = "I"
    shape = " "
    visible = True

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

class Arc:
    unit=0
    demorgan=0
    pensize=0
    fill="N"

    pos=Point()
    radius=0
    arcstart=0
    arcend=0
    start=Point()
    end=Point()

    def getvalues (self):
        values = []
        values.append (str(self.pos.x))
        values.append (str(self.pos.y))

        values.append (str(self.radius))
        values.append (str(self.arcstart))
        values.append (str(self.arcend))
        values.append (str(self.unit))
        values.append (str(self.demorgan))
        values.append (str(self.pensize))
        values.append (self.fill)
        values.append (str(self.start.x))
        values.append (str(self.start.y))
        values.append (str(self.end.x))
        values.append (str(self.end.y))

        return values

class PolyLine:

    def __init__(self):
        self.unit=0
        self.demorgan=0
        self.pensize=0
        self.fill="N"

        self.point_count =0
        self.points = []

    def getvalues (self):
        values = []
        values.append (str(self.point_count))
        values.append (str(self.unit))
        values.append (str(self.demorgan))
        values.append (str(self.pensize))

        pts=[]
        for p in self.points:
            pts.append (str(p.x))
            pts.append (str(p.y))
        values.append (pts)
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
    
class Rect:
    unit = 0
    demorgan = 1
    pensize = 0
    fill = "N"

    p1 = Point()
    p2 = Point()

    def getvalues (self):
        values = []
        values.append (str(self.p1.x))
        values.append (str(self.p1.y))
        values.append (str(self.p2.x))
        values.append (str(self.p2.y));
        values.append (str(self.unit))
        values.append (str(self.demorgan))
        values.append (str(self.pensize))
        values.append (self.fill)
        return values

class ComponentDef:
    name = "name"
    ref = "ref"
    offset=0
    show_pin_number=True
    show_pin_name=True
    num_units=0
    locked = "F"
    power_sym = False

class ComponentField:
    number=0
    value="~"
    pos=Point()
    font_size=50
    angle="H"
    visible=False    
    horiz_alignment = "C"
    vert_alignment = "C"
    italic = False
    bold = False

class LogicDesc ():
    id=""
    gates=0
    description=""
    technologies =""

    def __init__(self,tokens):
        self.id=tokens[0].strip()
        if tokens[1]!="":
            self.gates=int(tokens[1])
        self.description=tokens[2].strip()
        if len(tokens)>3:
            self.technologies=tokens[3].strip()



#def get_comp (name):
#    for comp in lib.components:
#        if comp.name== name:
#            return comp
#    return None

def swap_dir (dir):
    if dir=="R":
        return "L"
    elif dir=="L":
        return "R"
    elif dir=="U":
        return "B"
    elif dir=="D":
        return "T"

logic_list = []

def read_ref_list():
    global logic_list
    inf=open("..\\7400_logic_ref.txt")
    for line in inf:
        tokens = line.strip().split('\t')
        desc = LogicDesc (tokens)
        logic_list.append (desc)

def get_descriptor (name):
    for desc in logic_list:
        if name == desc.id:
            return desc
    return None

def get_pin_type (type, shape):
    result = type
    if result == "W":
        result = "PI"
    elif result == "w":
        result = "PO"

    if shape == "I":
        result = "~" + result
        shape = ""
    elif shape == "CI":
        result = "~" + result
        shape = "C"
    elif shape == "F":
        shape = "CF"

    return shape + result

def dump_lib (libfile):
    lib = SchLib(libfile)

    outf = open ("c:\\temp3\\74xx_dump.txt",'w')
    for comp in lib.components:

        # look for hidden pins
        hidden = False
        for pin in comp.pins:
            if pin['pin_type'] == "N":
                hidden = True
                break

        if hidden:
            type=""
            # look up on ref list
            desc = get_descriptor(re.sub('[^0-9]', '', comp.name))
            if desc:
                if " AND " in desc.description:
                    type = "AND"
                elif " NAND " in desc.description:
                    type = "NAND"
                elif " OR " in desc.description:
                    type = "OR"
                elif " NOR " in desc.description:
                    type = "NOR"
                elif "XOR" in desc.description:
                    type = "XOR"
                elif "inverter" in desc.description:
                    type = "NOT"
                else:
                    print "%s unknown type: %s" % (comp.name, desc.description)

            # todo: demorgan options?
            # power pins, unit = 0?
            # need to sort by y coord, detect gaps
            print comp.name
            num_units = int(comp.definition['unit_count'])

            outf.write ("COMP %s %s\n" % (comp.name, comp.reference))

            if len(comp.fplist)>0:
                outf.write ("FPLIST\n")
                for fp in comp.fplist:
                    outf.write ("%s\n" % fp)

            if comp.documentation:
                descr = comp.documentation['description']
                if descr:
                    outf.write ("DESC %s\n" % descr)
                keyw = comp.documentation['keywords']
                if keyw:
                    outf.write ("KEYW %s\n" % keyw)
                doc = comp.documentation['datasheet']
                if doc:
                    outf.write ("DOC %s\n" % doc)

            if len(comp.aliases) > 0:
                line=""
                for alias in comp.aliases.keys():
                    outf.write ("ALIAS %s\n" % alias)
                    alias_doc = comp.aliases[alias]
                    if alias_doc:
                        descr = alias_doc['description']
                        if descr:
                            outf.write ("DESC %s\n" % descr)
                        keyw = alias_doc['keywords']
                        if keyw:
                            outf.write ("KEYW %s\n" % keyw)
                        doc = alias_doc['datasheet']
                        if doc:
                            outf.write ("DOC %s\n" % doc)

            # units
            for unit in range (1, num_units+1):
                outf.write ("UNIT %s\n" % type)

                pins = []
                for pin in comp.pins:
                    if pin['unit']==str(unit) and pin['convert'] == '1' and pin['pin_type'] != "N":
                        pin['direction'] = swap_dir (pin['direction'])
                        pins.append (pin)

                # sort by y pos
                for passnum in range(len(pins)-1,0,-1):
                    for i in range(passnum):
                        if int(pins[i]['posy']) < int(pins[i+1]['posy']):
                            temp = pins[i]
                            pins[i] = pins[i+1]
                            pins[i+1] = temp

                for dir in ['L','R','U','D']:
                    for pin in pins:
                        if pin['direction'] == dir:
                            outf.write ("%s %s %s %s\n" % (pin['num'],pin['name'],get_pin_type(pin['electrical_type'],pin['pin_type']),pin['direction']))

            outf.write ("UNIT PWR\n")
            for pin in comp.pins:
                if pin['pin_type']=="N":
                    outf.write ("%s %s %s %s\n" % (pin['num'],pin['name'],"P",pin['direction']))

            outf.write ("END\n")

    outf.close()



def get_pins ():
    global kw
    global line
    global file

    pins = []
    line = file.readline()
    tokens = line.split()
    cur_pin_type = "I"
    cur_pin_dir = "L"
    while not tokens[0] in kw:
        if tokens[0] == "SPC":
            if len(tokens) == 2:
                dir = tokens[1]
            else:
                dir = cur_pin_dir

            if dir == "L":
                pin_pos_left.y -= 100
            elif dir == "R":
                pin_pos_right.y-= 100
            elif dir == "T":
                pin_pos_top.x += 100
            elif dir == "B":
                pin_pos_bottom.x += 100
        else:    
            pin = Pin()
            pin.length = pin_length
            pin.number = tokens[0]
            pin.name = "~"
            pin.unit = unit

            if len(tokens) >= 2:
                pin.name = tokens[1]

            if len(tokens) >= 3:
                cur_pin_type = tokens[2]

            if len(tokens) >= 4:
                cur_pin_dir = tokens[3]

            inverted =  len(pin.name) > 1 and pin.name.startswith("~")
                    
            if cur_pin_type == "I":
                pin.type = cur_pin_type
                if inverted:
                    pin.shape = "I"
            elif cur_pin_type == "O":
                pin.type = cur_pin_type
                if inverted:
                    pin.shape = "I"
            elif cur_pin_type == "CI":
                pin.type = "I"
                if inverted:
                    pin.shape = "CI"
                else:
                    pin.shape ="C"
            elif cur_pin_type == "P":
                # power input
                pin.type = "W"

            pin.orientation = cur_pin_dir

            if pin.orientation=="L":
                pin.pos.x = pin_pos_left.x - pin_length
                pin.pos.y = pin_pos_left.y
                pin_pos_left.y -= 100
                pin.orientation="R"
            elif pin.orientation=="R":
                pin.pos.x = pin_pos_right.x + pin_length
                pin.pos.y = pin_pos_right.y
                pin_pos_right.y -= 100
                pin.orientation="L"
            elif pin.orientation=="T":
                pin.pos.x = pin_pos_top.x
                pin.pos.y = pin_pos_top.y  + pin_length
                pin_pos_top.x += 100
                pin.orientation="D"
            elif pin.orientation=="B":
                pin.pos.x = pin_pos_bottom.x
                pin.pos.y = pin_pos_bottom.y - pin_length
                pin_pos_bottom.x += 100
                pin.orientation="U"
            # 

            pins.append (pin)
            #comp.drawOrdered.append( ['X', dict(zip(comp._PIN_KEYS,pin.getvalues()))])
                
        line = file.readline()
        tokens = line.split()
    #end while

    return pins

def add_and_gate_graphic (comp,unit):
    poly=PolyLine()
    poly.unit = unit
    poly.point_count=4
    poly.points.append (Point (100,200))
    poly.points.append (Point (-300,200))
    poly.points.append (Point (-300,-200))
    poly.points.append (Point (100,-200))
    comp.drawOrdered.append(['P', dict(zip(Component._POLY_KEYS, poly.getvalues() )) ])
            
    arc=Arc()
    # A 100 0 200 896 -896 0 1 0 N 101 200 101 -199
    arc.pos.x = 100
    arc.pos.y = 0
    arc.radius = 200
    arc.arcstart = 896
    arc.arcend = -896
    arc.unit = unit     
    arc.demorgan=0
    arc.pensize=0
    arc.start.x=101
    arc.start.y=200
    arc.end.x =101
    arc.end.y=-199
    comp.drawOrdered.append(['A', dict(zip(Component._ARC_KEYS, arc.getvalues() )) ])

def get_and_gate_positions (num_inputs):
    inputs_pos = [Point(-300,100), Point(-300,-100)]
    outputs_pos = [Point(300,0)]
    return inputs_pos, outputs_pos

def add_or_gate_graphic (comp, unit):
    poly=parse_polyline ("P 2 0 1 8 -300 -200 0 -200 N")
    poly.unit = unit
    comp.drawOrdered.append(['P', dict(zip(Component._POLY_KEYS, poly.getvalues() )) ])

    poly=parse_polyline ("P 2 0 1 8 -300 200 0 200 N")
    poly.unit = unit
    comp.drawOrdered.append(['P', dict(zip(Component._POLY_KEYS, poly.getvalues() )) ])

    arc=parse_arc ("A -470 0 262 496 -496 0 1 8 N -300 200 -300 -200")
    arc.unit=unit
    comp.drawOrdered.append(['A', dict(zip(Component._ARC_KEYS, arc.getvalues() )) ])

    arc=parse_arc ("A -1 -127 327 898 228 0 1 8 N 0 200 300 0")
    arc.unit=unit
    comp.drawOrdered.append(['A', dict(zip(Component._ARC_KEYS, arc.getvalues() )) ])

    arc=parse_arc ("A -1 128 327 -230 -898 0 1 8 N 300 0 0 -200")
    arc.unit=unit
    comp.drawOrdered.append(['A', dict(zip(Component._ARC_KEYS, arc.getvalues() )) ])

def get_or_gate_positions (num_inputs):
    inputs_pos = [Point(-230,100), Point(-230,-100)]
    outputs_pos = [Point(300,0)]
    return inputs_pos, outputs_pos

def add_xor_gate_graphic (comp, unit):
    arc=parse_arc ("A -470 0 262 495 -495 0 1 0 N -300 199 -300 -198")
    arc.unit=unit
    comp.drawOrdered.append(['A', dict(zip(Component._ARC_KEYS, arc.getvalues() )) ])

    arc=parse_arc ("A -396 -2 281 457 -451 0 1 0 N -200 199 -198 -200")
    arc.unit=unit
    comp.drawOrdered.append(['A', dict(zip(Component._ARC_KEYS, arc.getvalues() )) ])

    arc=parse_arc ("A -2 126 326 -897 -225 0 1 0 N 0 -199 299 2")
    arc.unit=unit
    comp.drawOrdered.append(['A', dict(zip(Component._ARC_KEYS, arc.getvalues() )) ])

    arc=parse_arc ("A 4 -120 320 906 221 0 1 0 N 2 200 300 0")
    arc.unit=unit
    comp.drawOrdered.append(['A', dict(zip(Component._ARC_KEYS, arc.getvalues() )) ])

    poly=parse_polyline ("P 2 0 1 0 -200 -200 0 -200 N")
    poly.unit = unit
    comp.drawOrdered.append(['P', dict(zip(Component._POLY_KEYS, poly.getvalues() )) ])

    poly=parse_polyline ("P 2 0 1 0 -200 200 0 200 N")
    poly.unit = unit
    comp.drawOrdered.append(['P', dict(zip(Component._POLY_KEYS, poly.getvalues() )) ])

def get_xor_gate_positions (num_inputs):
    ## todo
    inputs_pos = [Point(-230,100), Point(-230,-100)]
    outputs_pos = [Point(300,0)]
    return inputs_pos, outputs_pos

#
#
#

verbose = False
printer = PrintColor(True)

read_ref_list()
exit_code = 0

if False:
    libfile = os.path.join ("C:\\git_kicad\\kicad-library\\library", "74xx.lib")
    print "Dump library " + libfile
    dump_lib (libfile)

#
libfile = os.path.join ("C:\\temp3", "74xx_new.lib")
docfile = os.path.join ("C:\\temp3", "74xx_new.dcm")

# create an empty lib
new_lib = True
if new_lib:
    file = open (libfile, 'w')
    file.write ("EESchema-LIBRARY Version 2.3\n")
    file.write ("#encoding utf-8\n")
    file.write ("#\n")
    file.write ("#End Library\n")
    file.close()
#
print "Creating library"
lib = SchLib(libfile)
print 'Library: %s' % libfile
documentation = Documentation (docfile)
#
kw = ['COMP','UNIT','END']
# some global settings
def_box_width = 600
def_box_pen = 10
def_box_fill = "f" # background fill

def_pin_length = 150

opt_combine_power_for_single_units = True

file = open (os.path.join ("C:\\temp3", "74xx_new.txt"), 'r')
line = file.readline()

while line:
    if line.startswith ("#") or len(line.strip())==0:
        # ignore comments
        line = file.readline()
        continue

    elif line.startswith ("COMP"):
        items = line.split()

        name = items[1]
        ref = items[2]

        comments = []
        comments.append ("#\n")
        comments.append ("# " + name + "\n")
        comments.append ("#\n")

        component_data = []
        component_data.append("DEF "+name + " "+ref+" 0 40 Y Y 1 L N")      # units are not interchangeable
        component_data.append("F0 \"U\" 0 0 50 H V C CNN")
        component_data.append("F1 \"74469\" 0 -200 50 H V C CNN")
        component_data.append("F2 \"\" 0 0 50 H I C CNN")
        component_data.append("F3 \"\" 0 0 50 H I C CNN")
        component_data.append("DRAW")
        component_data.append("ENDDRAW")
        component_data.append("ENDDEF")

        comp = Component(component_data, comments, documentation)
        comp.fields [0]['reference'] = ref
        comp.fields [1]['name'] = name
        comp.definition['reference'] = ref
        comp.definition['name'] = name

        print "Component: "+ name

        desc = get_descriptor(re.sub('[^0-9]', '', name))
        if desc:
            print "found %s" % desc.description

        # reset all current vars
        pins = []
        unit = 0
        unit_shape = "box"

        pin_pos_left = Point()
        pin_pos_left.x = -def_box_width/2
        pin_pos_left.y = 0

        pin_pos_right = Point()
        pin_pos_right.x = def_box_width/2
        pin_pos_right.y = 0
        pin_length = def_pin_length;

        pin_pos_top = Point()
        pin_pos_top.x = 0
        pin_pos_top.y = 0

        pin_pos_bottom = Point()
        pin_pos_bottom.x = 0
        pin_pos_bottom.y = -600

        max_height = 0

        label_style = "floating"
        ref_pos= Point()
        ref_pos.x = -def_box_width/2;

        name_pos = Point()
        name_pos.x = -def_box_width/2;

        cur_pin_type = "I"
        cur_pin_dir = "L"

        # 
        line = file.readline()

    elif line.startswith("UNIT"):
        # new unit
        unit = unit + 1

        tokens = line.strip().split()

        if len(tokens) >= 2:
            if tokens[1] == "PWR":
                unit_shape = "box"      # could be option?
                # this relies on pwr unit being last unit...
                if opt_combine_power_for_single_units and unit==2:
                    unit = unit - 1
                    pin_pos_top.y = 50
                    pin_pos_bottom.y = max_height + 50
            elif tokens[1] == "AND":
                unit_shape = "and"
            elif tokens[1] == "NAND":
                unit_shape = "nand"
            elif tokens[1] == "OR":
                unit_shape = "or"
            elif tokens[1] == "NOR":
                unit_shape = "nor"
            elif tokens[1] == "XOR":
                unit_shape = "xor"
            elif tokens[1] == "NOT":
                unit_shape = "not"
            else:
                unit_shape = "box"

        pin_pos_left = Point()
        pin_pos_left.x = -def_box_width/2
        pin_pos_left.y = 0

        pin_pos_right = Point()
        pin_pos_right.x = def_box_width/2
        pin_pos_right.y = 0

        if unit_shape == "box" or unit_shape == "none":
            line = file.readline()
            tokens = line.split()
            while not tokens[0] in kw:
                if tokens[0] == "SPC":
                    if len(tokens) == 2:
                        dir = tokens[1]
                    else:
                        dir = cur_pin_dir

                    if dir == "L":
                        pin_pos_left.y -= 100
                    elif dir == "R":
                        pin_pos_right.y-= 100
                    elif dir == "T":
                        pin_pos_top.x += 100
                    elif dir == "B":
                        pin_pos_bottom.x += 100
                else:    
                    pin = Pin()
                    pin.length = pin_length
                    pin.number = tokens[0]
                    pin.name = tokens[1]
                    pin.unit = unit

                    inverted =  pin.name.startswith("~")

                    if len(tokens) == 4:
                        cur_pin_dir = tokens[3]

                    if len(tokens) >= 3:
                        cur_pin_type = tokens[2]
                    
                    if cur_pin_type == "I":
                        pin.type = cur_pin_type
                        if inverted:
                            pin.shape = "I"
                    elif cur_pin_type == "O":
                        pin.type = cur_pin_type
                        if inverted:
                            pin.shape = "I"
                    elif cur_pin_type == "CI":
                        pin.type = "I"
                        if inverted:
                            pin.shape = "CI"
                        else:
                            pin.shape ="C"
                    elif cur_pin_type == "P":
                        # power input
                        pin.type = "W"

                    pin.orientation = cur_pin_dir

                    if pin.orientation=="L":
                        pin.pos.x = pin_pos_left.x - pin_length
                        pin.pos.y = pin_pos_left.y
                        pin_pos_left.y -= 100
                        pin.orientation="R"
                    elif pin.orientation=="R":
                        pin.pos.x = pin_pos_right.x + pin_length
                        pin.pos.y = pin_pos_right.y
                        pin_pos_right.y -= 100
                        pin.orientation="L"
                    elif pin.orientation=="T":
                        pin.pos.x = pin_pos_top.x
                        pin.pos.y = pin_pos_top.y  + pin_length
                        pin_pos_top.x += 100
                        pin.orientation="D"
                    elif pin.orientation=="B":
                        pin.pos.x = pin_pos_bottom.x
                        pin.pos.y = pin_pos_bottom.y - pin_length
                        pin_pos_bottom.x += 100
                        pin.orientation="U"
                    # 

                    pins.append (pin)

                    comp.drawOrdered.append( ['X', dict(zip(comp._PIN_KEYS,pin.getvalues()))])
                
                line = file.readline()
                tokens = line.split()
            #end while


            if unit_shape == "box":
                if pin_pos_left.y == 0 and pin_pos_left.y == pin_pos_right.y:
                    box_top_y = pin_pos_top.y
                    box_bottom_y = pin_pos_bottom.y
                else:
                    unit_height = min (pin_pos_left.y, pin_pos_right.y)
                    box_top_y = 50
                    box_bottom_y = unit_height +50

                rect = Rect()
                rect.p1.x = -def_box_width/2
                rect.p1.y = box_top_y

                rect.p2.x = def_box_width/2
                rect.p2.y = box_bottom_y

                rect.unit = unit
                rect.fill = def_box_fill
                rect.pensize = def_box_pen
                comp.drawOrdered.append(['S', dict(zip(Component._RECT_KEYS,rect.getvalues() )) ])

                ## todo
                if label_style == "floating":
                    max_height = min (max_height, unit_height)

                    ref_pos.y = 100
                    name_pos.y = max_height


        elif unit_shape in ["and", "nand", "or", "nor", "xor"]:

            pin_offset = 0

            # graphics for main symbol    
            if unit_shape in ["and", "nand"]:
                add_and_gate_graphic (comp, unit)
            elif unit_shape in ["or", "nor"]:
                add_or_gate_graphic (comp, unit)
                pin_offset = 20
            elif unit_shape == "xor":
                add_xor_gate_graphic (comp, unit)
            #
            # pins
            unit_pins = get_pins ()

            label_style = "fixed"
            ref_pos.x = 0
            ref_pos.y = 50

            name_pos.x = 0
            name_pos.y = -50
            #
            num_inputs = len(unit_pins)-1

            if unit_shape in ["and", "nand"]:
                inputs_pos, outputs_pos = get_and_gate_positions(num_inputs)
            elif unit_shape in ["or", "nor"]:
                inputs_pos, outputs_pos = get_or_gate_positions(num_inputs)
            elif unit_shape == "xor":
                inputs_pos, outputs_pos = get_xor_gate_positions(num_inputs)
        
            input_shape = " "
            output_shape = " "
            if unit_shape in ['nand','nor']:
                output_shape = "I"

            pin_pos_top.x = 0
            pin_pos_top.y = 300
            pin_pos_bottom.x = 0
            pin_pos_bottom.y = -300

            j=0
            for pin in unit_pins:
                if pin.type=="I":
                    pin.length = pin_length + pin_offset
                    pin.unit = unit
                    pin.orientation="R"
                    pin.shape = input_shape
                    pin.pos.x = inputs_pos[j].x - pin.length
                    pin.pos.y = inputs_pos[j].y
                    j += 1
                    pins.append (pin)
                    comp.drawOrdered.append( ['X', dict(zip(comp._PIN_KEYS,pin.getvalues()))])

            j = 0
            for pin in unit_pins:
                if pin.type=="O":
                    pin.length = pin_length
                    pin.unit = unit
                    pin.orientation="L"
                    pin.shape = output_shape
                    pin.pos.x = outputs_pos[j].x + pin_length
                    pin.pos.y = outputs_pos[j].y       
                    j += 1
                    pins.append (pin)
                    comp.drawOrdered.append( ['X', dict(zip(comp._PIN_KEYS,pin.getvalues()))])

        else:
            line = file.readline()
        #

        comp.fields [0]['posx'] = str(ref_pos.x)
        comp.fields [0]['posy'] = str(ref_pos.y)

        comp.fields [1]['posx'] = str(name_pos.x)
        comp.fields [1]['posy'] = str(name_pos.y)

    elif line.startswith ("END"):

        values = []
        values.append (name)
        values.append (ref)
        values.append ("0")
        values.append ("40")
        values.append ("Y")
        values.append ("Y")
        values.append (str(unit))
        values.append ("L")     # units are not interchangeable
        values.append ("N")
        comp.definition = dict(zip(Component._DEF_KEYS, values))

        cur_comp = lib.getComponentByName(comp.name)
    
        if cur_comp:
            print "replacing: " + comp.name
            lib.removeComponent (comp.name)
        else:
            print "adding: " + comp.name
        
        lib.addComponent (comp)

        line = file.readline()
    else:
        # 
        print "unexpected line: " + line
        line = file.readline()
    


###




lib.save (filename = libfile)

print "done"


