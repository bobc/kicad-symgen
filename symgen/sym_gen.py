#!/usr/bin/env python

# -*- coding: utf-8 -*-

"""
 Generate components from text file
 
 Usage: symgen

 Copyright Bob Cousins 2017

 Licensed under GPLv3

 Version 1

 todo:

   ieee symbols
   field pos?
   (error reporting

   / de morgans 
   / doc fields, aliases - dcm 
   / smaller logic symbols?
   / pin length = 200?
   / parametize input/output file names etc 

 issues
   pin overlaps (top/bot)
   ? bad symbols
   / missing graphics
"""

import os, sys

# kicad lib utils
common = os.path.abspath(os.path.join(sys.path[0], 'common'))
if not common in sys.path:
    sys.path.append(common)

#from os import path, environ
import argparse
import re
#import copy
#import time
#import hashlib
import shlex
#from enum import Enum

from schlib import *
from print_color import *

from str_utils import *
from sym_drawing import *
from sym_comp import *
from sym_gates import *
from sym_iec import *

from sym_utils import *

from convert_library import *

class SymGen:

    verbose = False

    exit_code = 0
    num_errors = 0

    libfile = None
    docfile = None

    kw = ['COMP', 'DESC', 'KEYW', 'DOC', 'ALIAS', 'UNIT', 'ELEM', 'END']
    #  ELEM, GROUP

    lib = None
    icon_lib = None
    documentation = None
    out_path = None
    file = None
    line = None

    # some global settings
    opt_combine_power_for_single_units = True

    symbol_style = SymbolStyle.ANSI
    #symbol_style = SymbolStyle.IEC

    opt_pin_qualifiers = False

    def_logic_combine = "multi"

    def_pin_length = 200

    def_box_width = 600
    def_box_pen = 10
    def_box_fill = Background # background fill

    def_logic_fill = NoFill # default
    #def_logic_fill = Background

    def_name_offset = 20
    def_extra_offset = 40

    # name offset
    # logic fill
    # tristate symbol

    components = []

    # per component settings  
    pin_length = def_pin_length

    box_width = def_box_width
    box_pen = def_box_pen
    box_fill = def_box_fill

    logic_fill = def_logic_fill

    #
    box_height = 0

    comp_description = None
    comp_keywords = None
    comp_datasheet = None

    # units = []
    last_unit = None
    ##
    pin_pos_left = None
    pin_pos_right= None
    pin_pos_top = None
    pin_pos_bottom= None

    in_component = False
    cur_pos = Point()
    units_have_variant = 0 # 1 for de Morgan variants

    label_style = ""
    
    last_shape = ""
    unit_num = 0
    max_height = 600
    unit_label = ""

    # 
    ref_pos = Point()
    name_pos = Point()

    def __init__(self):
        self.kw = ['COMP', 'DESC', 'KEYW', 'DOC', 'ALIAS', 'UNIT', 'END']

        self.printer = PrintColor(True)




    def process_list(self):

        process_ref_list ("../74xx/7400_logic_ref.txt", "../74xx/7400_logic_ref_new.txt")

        process_ref_list ("../cmos4000/4000_list.csv", "../cmos4000/4000_list_new.csv")


            

    def strip_quotes (self, tok):
        if tok.startswith('"') and tok.endswith('"'):
            return tok[1:-1]
        else:
            return tok

    def gen_comp (self, path):

        reference = "U"

        for size in [100, 140, 150, 170, 225, 250]:
            name = "or-%d" % size
            filename = os.path.join (name+".sym")
            if os.path.exists(filename):
                os.remove (filename)

            sym_lib = SchLib (filename, create = True)

            comments = []
            comments.append ("#\n")
            comments.append ("# " + name + "\n")
            comments.append ("#\n")

            component_data = []
            component_data.append("DEF " + name + " " + reference+" 0 40 Y Y 1 L N")      # units are not interchangeable
            component_data.append("F0 \"U\" 0 0 50 H V C CNN")
            component_data.append("F1 \"74469\" 0 -200 50 H V C CNN")
            component_data.append("F2 \"\" 0 0 50 H I C CNN")
            component_data.append("F3 \"\" 0 0 50 H I C CNN")
            component_data.append("DRAW")
            component_data.append("ENDDRAW")
            component_data.append("ENDDEF")

            templ_comp = Component(component_data, comments, None)
            templ_comp.fields [0]['reference'] = reference
            templ_comp.fields [1]['name'] = name
            templ_comp.definition['reference'] = reference
            templ_comp.definition['name'] = name

            #
            gatedef = OrGate (2)
            gatedef.set_size (size, size)
            gatedef.pensize = size * 10.0/300.0
            gatedef.pensize = 6 if gatedef.pensize<6 else gatedef.pensize
            gatedef.add_gate_graphic (templ_comp, 0, 0)

            sym_lib.addComponent (templ_comp)
            sym_lib.save()




    def get_next_line(self):

        # ignore comments, blank lines

        self.line = self.file.readline()
        if self.verbose:
            print (self.line.rstrip())
        while self.line and (self.line.startswith ("#") or len(self.line.strip())==0):
            self.line = self.file.readline()
            if self.verbose:
                print (self.line.rstrip())
    
        self.line = self.line.strip()
            
    def find_pins (self, pin_list, direction, type=None):
        pins = []

        for pin in pin_list:
            # if pin.orientation == direction and pin.visible and (type is None or pin.type == type):
            if pin.orientation == direction and (type is None or pin.type == type):
                pins.append (pin)
        return pins

    def find_pins_with_label (self, pin_list, direction, type=None):
        pins = []

        for pin in pin_list:
            # if pin.orientation == direction and pin.visible and (type is None or pin.type == type):
            if pin.shape!=" " and pin.name!="~" and pin.orientation == direction and (type is None or pin.type == type) and len(pin.name)!=0:
                pins.append (pin)
        return pins


    def read_file (self, filename):

        inf = open (filename, "r")
        
        headings = inf.readline().rstrip('\n').split("\t")
        data_rows = []

        for line in inf:
            line = line.rstrip('\n').split("\t", )
            data_rows.append (line)

        return headings, data_rows

    def select_rows (self, headings, data_rows, fields):
        result = []
        for row in data_rows:           
            #print row, len(row)
            result_row = []
            for field in fields:
                j = headings.index (field)
                result_row.append (row[j])
            #print result_row
            result.append (result_row)
        return result

    def parse_element (self, shape):
        src_lines = []

        element = IecElement()

        tokens = self.line.split()

        #element.shape = "box"
        # todo: is this right?
        element.shape = shape 

        if tokens[0].upper() == "ELEM":
            j = 1
            while j < len(tokens):
                if tokens[j].upper() == "CONTROL":
                    element.shape = "control"
                elif tokens[j].upper() == "LABEL":
                    j += 1
                    if j < len(tokens):
                        element.label = self.strip_quotes(tokens[j])
                j += 1

            self.get_next_line()
            tokens = self.line.split()
        
        while not tokens[0] in ['COMP', 'UNIT', 'ELEM', 'END']:
            if tokens[0].startswith("%"):
                sel_fields = []
                filename = None
                state = "field"
                for tok in tokens[1:]:
                    if state == "field":
                        if tok == "FROM":
                            state = "table"
                        else:
                            sel_fields.append(tok)
                    elif state == "table":
                        filename = self.strip_quotes(tok)
                #
                headings, file_rows = self.read_file (filename)
                data_rows = self.select_rows (headings, file_rows, sel_fields)

                for row in data_rows:
                    if row[0]:
                        if "," in row[0]:
                            for pin in row[0].split(","):
                                src_lines.append ( "%s %s %s %s" % (pin, row[1], row[2], row[3]) )
                        else:
                            src_lines.append (' '.join (row))
            else:
                src_lines.append (self.line)

            self.get_next_line()
            tokens = self.line.split()
        # end while

        element.pins = self.parse_pins (src_lines, element)
        return element

    # return list of elements ?
    def parse_pins (self, lines, element):
        pins = []

        cur_pin_type = "I"
        cur_pin_dir = "L"
        cur_pin_align = "L"

        group_id = -1
        group = None

        for line in lines:
            tokens = line.split()
            if tokens[0].upper() == "SPC":
                if len(tokens) == 2:
                    _dir = tokens[1]
                else:
                    _dir = cur_pin_dir

                if "L" in _dir:
                    self.pin_pos_left.y -= 100
                elif "R" in _dir:
                    self.pin_pos_right.y-= 100
                #elif "T" in _dir:
                #    self.pin_pos_top.x += 100
                #elif "B" in _dir:
                #    self.pin_pos_bottom.x += 100

                if "C" in _dir:
                    cur_pin_align = "C"

                pin = Pin()
                pin.length = self.pin_length
                pin.number = "~"
                pin.name = "~"
                pin.type = " "
                pin.orientation = _dir
                pin.align = cur_pin_align
                pin.orientation = symgen_to_kicad_dir (pin.orientation)
                
                pin.group_id = group_id if group else -1

                pins.append (pin)

                if group:
                    group.pins.append (pin)

            elif tokens[0].upper() == "GROUP":
                group = Group()
                group_id += 1
                group.id = group_id
                element.groups.append(group)

                group.qualifiers = self.strip_quotes(tokens[1])
                group.type = tokens[2]
                group.label = self.strip_quotes(tokens[3])
            elif tokens[0].upper() == "END-GROUP":
                group = None
            else:    
                pin = Pin()
                pin.length = self.pin_length
                pin.number = tokens[0]
                pin.name = "~"
                #pin.unit = unit

                if len(tokens) >= 2:
                    pin.name = tokens[1]

                if len(tokens) >= 3:
                    cur_pin_type = tokens[2]

                # position, alignment
                if len(tokens) >= 4:
                    cur_pin_dir = tokens[3][0]
                    if "C" in tokens[3]:
                        cur_pin_align = "C"

                # qualifers (string) e.g. for schmitt inputs
                if len(tokens) >= 5:
                    pin.qualifiers = self.strip_quotes(tokens[4])

                #inverted =  len(pin.name) > 1 and pin.name.startswith("~")
            
                pin_type=cur_pin_type        

                inverted = False
                if pin_type.startswith("~"):
                    inverted = True
                    pin_type=pin_type[1:]

                flags = ""
                if len(pin_type)>1:
                    flags = pin_type[:-1]
                    pin_type = pin_type[-1]

                if inverted:
                    flags = flags + "I"

                if "P" in flags:
                    # power
                    flags = re.sub('^P', '', flags)
                    if pin_type == "I":
                        pin_type = "W"
                    else:
                        pin_type = "w"

                if pin_type in ["I", "O", "T", "C", "P", "B", "W","w", "N"]:
                    pin.type = pin_type
                else:
                    print "error: unknown pin type: " + pin_type
                    self.num_errors += 1
                pin.shape = flags

                pin.orientation = cur_pin_dir
                pin.align = cur_pin_align

                # not NC?
                if pin.type != "N" and "N" in pin.shape and len(pins) > 0 and pins[-1].type == pin.type:
                    can_stack = True
                else:
                    can_stack = False

                if "N" in pin.shape:
                    pin.length = 0
                    pin.visible = False
                else:
                    pin.length = self.pin_length

                if pin.orientation=="L":
                    pin.pos.x = self.pin_pos_left.x - pin.length
                    pin.pos.y = self.pin_pos_left.y
                    if not can_stack:
                        self.pin_pos_left.y -= 100
                
                elif pin.orientation=="R":
                    pin.pos.x = self.pin_pos_right.x + pin.length
                    pin.pos.y = self.pin_pos_right.y
                    if not can_stack:
                        self.pin_pos_right.y -= 100
                elif pin.orientation=="T":
                    pin.pos.x = self.pin_pos_top.x
                    pin.pos.y = self.pin_pos_top.y  + pin.length
                    #if not can_stack:
                    #    self.pin_pos_top.x += 100
                elif pin.orientation=="B":
                    pin.pos.x = self.pin_pos_bottom.x
                    pin.pos.y = self.pin_pos_bottom.y - pin.length
                    #if not can_stack:
                    #    self.pin_pos_bottom.x += 100
                # 
                pin.orientation = symgen_to_kicad_dir (pin.orientation)

                
                if group:
                    pin.group_id = group_id
                    group.pins.append (pin)
                else:
                    pin.group_id = -1

                pins.append (pin)

        #end while

        return pins




    ##
#
#
#
    def add_doc(self, comp, alias_name):

        if self.comp_description or self.comp_keywords or self.comp_datasheet:
            if alias_name is None:
                tname = comp.name
                self.lib.documentation.components[tname] = OrderedDict([('description',self.comp_description), ('keywords',self.comp_keywords), ('datasheet',self.comp_datasheet)])
            else:
                tname = alias_name
                self.lib.documentation.components[tname] = OrderedDict([('description',self.comp_description), ('keywords',self.comp_keywords), ('datasheet',self.comp_datasheet)])
                comp.aliases[tname] = self.lib.documentation.components[tname]
        #
        #self.comp_description = None
        #self.comp_keywords = None
        self.comp_datasheet = None

    def make_doc(self, sgcomp, alias_name):

        sgdoc = SgDoc()

        if self.comp_description or self.comp_keywords or self.comp_datasheet:
            if alias_name is None:
                tname = sgcomp.name
            else:
                tname = alias_name

            sgdoc.description = self.comp_description
            sgdoc.keywords = self.comp_keywords
            sgdoc.datasheet = self.comp_datasheet
        else:
            tname = sgcomp.name

        #
        #self.comp_description = None
        #self.comp_keywords = None
        self.comp_datasheet = None

        return tname, sgdoc



    def parse_fill (self, token):
        if token in ["F", "f", "N"]:
            return token
        elif token.startswith ("f"):    # foreground
            return "F"
        elif token.startswith ("b"):    # background
            return "f"
        elif token.startswith ("n"):    # none
            return "N"
        else:
            return None

    def parse_directive(self):

        tokens = self.line.split()
        
        if tokens[0] == "%lib":
            pass

        elif tokens[0] == "%pinlen":
            if self.in_component:
                self.pin_length = int (tokens[1])
            else:
                self.def_pin_length = int (tokens[1])

        elif tokens[0] == "%width":
            if self.in_component:
                self.box_width = int (tokens[1])
            else:
                self.def_box_width = int (tokens[1])

        elif tokens[0] == "%line":
            if self.in_component:
                self.box_pen = int (tokens[1])
            else:
                self.def_box_pen = int (tokens[1])

        elif tokens[0] == "%fill":
            fill = self.parse_fill (tokens[1])
            if fill:
                if self.in_component:
                    self.box_fill = fill
                    self.logic_fill = fill
                else:
                    self.def_box_fill = fill
            else:
                print "error : unknown fill %s" % self.line
                self.num_errors += 1


        elif tokens[0] == "%iconlib":
            if not self.in_component:
                # filename = os.path.join ("data", tokens[1])
                filename = os.path.abspath(os.path.join(self.out_path, tokens[1]))
                self.icon_lib = SchLib(filename)

        elif tokens[0] == "%style":
            tok = tokens[1].upper()

            # ANSI|IEC fill single|multi

            if tok == "ANSI":
                self.symbol_style = SymbolStyle.ANSI
            elif tok == "IEC":
                self.symbol_style = SymbolStyle.IEC
                self.opt_pin_qualifiers = True
            elif tok == "DIN":
                self.symbol_style = SymbolStyle.DIN
            else:
                print "error : unknown style %s : expecting ANSI, IEC or DIN" % tok
                self.num_errors += 1

            if len(tokens) > 2:
                fill = self.parse_fill (tokens[2])
                if fill:
                    self.def_logic_fill = tokens[2]
                else:
                    print "error : unknown fill %s" % self.line
                    self.num_errors += 1

        else:
            print "error : unknown directive %s" % self.line
            self.num_errors += 1

        self.get_next_line()



    def create_gate (self, unit_shape, num_inputs, num_outputs, demorgan):
        if self.symbol_style == SymbolStyle.ANSI:
            if demorgan == 0:
                if unit_shape in ["and", "nand"]:
                    gatedef = AndGate (num_inputs)
                elif unit_shape in ["or", "nor"]:
                    gatedef = OrGate (num_inputs)
                elif unit_shape in ["xor", "xnor"]:
                    gatedef = XorGate (num_inputs)
                elif unit_shape in ["not", "buffer"]:
                    gatedef = NotGate (num_inputs)
                else:
                    gatedef = None
            else:
                # de morgan variants only for and/or
                if unit_shape in ["and", "nand"]:
                    gatedef = OrGate (num_inputs)
                elif unit_shape in ["or", "nor"]:
                    gatedef = AndGate (num_inputs)
                else:
                    gatedef = None
        elif self.symbol_style == SymbolStyle.IEC:
            gatedef = IecGate (num_inputs)
            gatedef.num_outputs = num_outputs
            if demorgan == 0:
                gatedef.type = unit_shape
            else:
                if unit_shape in ["and", "nand"]:
                    gatedef.type = "or"
                elif unit_shape in ["or", "nor"]:
                    gatedef.type = "and"
        else:
            gatedef = None

        return gatedef

    def align_unit(self, unit):

        left_pins = []
        right_pins = []
        top_pins = []
        bottom_pins = []

        all_pins = {}
        all_pins ['R'] = left_pins
        all_pins ['L'] = right_pins
        all_pins ['U'] = bottom_pins
        all_pins ['D'] = top_pins

        bb_horiz = BoundingBox()

        for element in unit.elements:
            for pin in element.pins:
                if pin.visible and pin.type != " ":
                    l = all_pins[pin.orientation]
                    l.append (pin)
                    if pin.orientation in ['L','R']:
                        bb_horiz.extend (pin.pos)

        y_offset = align_to_grid (unit.unit_rect.size.y / 2, 50)

        if len(left_pins) + len(right_pins) > 0 :
            # align to horiz pins
            y = bb_horiz.pmax.y
            while (y+y_offset) % 100 != 0:
                y_offset -= 50
        return y_offset

    def parse_unit (self, comp):
        unit = IecSymbol()

        # new unit

        unit.set_width (self.box_width)

        unit.unit_rect.pos.x = -self.box_width / 2
        unit.unit_rect.pos.y = 0
        unit.unit_rect.size.x = self.box_width
        unit.unit_rect.size.y = 0

        self.unit_num = self.unit_num + 1

        tokens = self.line.split()

        # unit [ PWR|AND|... [ SEPerate | COMBined ] ] | Width int | ICON name

        unit.unit_shape = self.last_shape
        if not unit.unit_shape:
            unit.unit_shape = "box"
        
        self.unit_combine = "auto"

        unit.vert_margin = 200
        unit.qualifiers = self.unit_label
        #unit.pin_length = self.pin_length

        j = 1
        while j < len(tokens):
            token = tokens[j].upper()

            if token == "PWR":
                unit.unit_shape = "power"
            elif token == "NONE":
                unit.unit_shape = "none"
            elif token == "AND":
                unit.unit_shape = "and"
            elif token == "NAND":
                unit.unit_shape = "nand"
            elif token == "OR":
                unit.unit_shape = "or"
            elif token == "NOR":
                unit.unit_shape = "nor"
            elif token == "XOR":
                unit.unit_shape = "xor"
            elif token == "XNOR":
                unit.unit_shape = "xnor"
            elif token == "NOT":
                unit.unit_shape = "not"
            elif token == "BUF":
                unit.unit_shape = "buffer"

            elif token.startswith("SEP"):
                self.unit_combine = "seperate"
            elif token.startswith("COMB"):
                self.unit_combine = "combine"

            elif token.startswith("W"):
                j += 1
                self.box_width = int(tokens[j])
                unit.set_width (self.box_width)

            elif token.upper().startswith("LABEL"):
                j += 1
                self.unit_label = self.strip_quotes (tokens[j])
                unit.qualifiers = self.unit_label

            elif token.startswith("TEMP"):
                j += 1
                unit.template = tokens[j]
                unit.unit_shape = "none"
                self.last_shape = unit.unit_shape

            elif token.startswith("ICON"):
                self.last_shape = unit.unit_shape
                self.icons = []
                while j < len(tokens)-1:
                    j += 1
                    self.icons.append(tokens[j])
                unit.icons = self.icons
            else:
                print "error : unknown parameter %s in UNIT" % token
                self.num_errors += 1
            j += 1

        # 
        #self.get_next_line()

        if unit.unit_shape != self.last_shape:
            self.icons = []    
            unit.icons = []
            unit.template = None

        self.last_shape = unit.unit_shape

        unit.icons = self.icons
        unit.combine= self.unit_combine

        #if len(unit.icons) == 0 and unit.template:
        #    unit.icons.append(unit.template)

        #

        #debug
        #print "unit %d %s %s" % (self.unit_num, unit.unit_shape, "power" if unit.is_power_unit else "")

        # need pin pos generator ?

        self.pin_pos_left = Point()
        self.pin_pos_left.x = -self.box_width/2
        self.pin_pos_left.y = 0

        self.pin_pos_right = Point()
        self.pin_pos_right.x = self.box_width/2
        self.pin_pos_right.y = 0

        self.pin_pos_top.x = 0
        self.pin_pos_bottom.x = 0

        #if comp.name == "4017":
        #    print "oop"

        self.get_next_line()
        tokens = self.line.split()

        while tokens[0].upper() not in ['UNIT','END']:
            element = self.parse_element (unit.unit_shape)
            unit.elements.append (element)
            tokens = self.line.split()

        # ===============================================================================

        if unit.unit_shape in ["box", "none", "and", "nand", "or", "nor", "xor", "xnor", "not", "buffer", "power"]:

            if unit.unit_shape in ["and", "nand", "or", "nor", "xor", "xnor", "not", "buffer"]:
                self.label_style = "fixed"
                unit.fill = self.logic_fill
            else:
                unit.fill = self.box_fill

        else:
            print "error: unknown shape: " + unit.unit_shape
            self.num_errors += 1

        # ===============================================================================
        #
        #self.last_unit = unit
        return unit

    def parse_component (self):

        sgcomp = SgComponent()

        items = self.line.split()

        if len(items) >= 3:
            sgcomp.name = items[1]
            sgcomp.ref = items[2]
        else:
            print "error: expected COMP name ref: " + self.line
            self.num_errors += 1

        print "Component: "+ sgcomp.name

        #desc = self.get_descriptor(re.sub('[^0-9]', '', sgcomp.name))
        #if desc:
        #    print "found %s" % desc.description

        # reset all current vars

        sgcomp.units = []

        #pins = []
        self.unit_num = 0
        # template = None
        self.last_shape = None

        #self.unit_shape = None
        self.icons = []

        self.pin_length = self.def_pin_length
        self.box_width = self.def_box_width
        self.box_pen = self.def_box_pen
        self.box_fill = self.def_box_fill
        self.logic_fill = self.def_logic_fill

        self.pin_pos_left = Point()
        self.pin_pos_left.x = -self.box_width/2
        self.pin_pos_left.y = 0

        self.pin_pos_right = Point()
        self.pin_pos_right.x = self.box_width/2
        self.pin_pos_right.y = 0

        self.pin_pos_top = Point()
        self.pin_pos_top.x = 0
        self.pin_pos_top.y = 0

        self.pin_pos_bottom = Point()
        self.pin_pos_bottom.x = 0
        self.pin_pos_bottom.y = -600


        self.max_height = 0
        #self.y_offset = 0

        self.label_style = "floating"
        self.unit_label = ""

        self.ref_pos= Point()
        self.ref_pos.x = -self.box_width/2
        self.ref_pos.y = 0

        self.name_pos = Point()
        self.name_pos.x = -self.box_width/2
        self.name_pos.y = 0

        #cur_pin_type = "I"
        #cur_pin_dir = "L"

        self.comp_description = None
        self.comp_keywords = None
        self.comp_datasheet = None

        self.in_component = True
        self.units_have_variant = 0

        # 
        self.get_next_line()
        tokens = self.line.split()

        while self.line.startswith ("%"):
            self.parse_directive()

        sgcomp.pin_length = self.pin_length

        #
        tokens = self.line.split()
        while tokens[0].startswith ("FIELD"):

            if tokens[1].upper()== "$FOOTPRINT":
                field_text = after(self.line, tokens[1]).strip()
                sgcomp.default_footprint = field_text
            else:
                field_text = after(self.line, tokens[1]).strip()
                
                line = 'F%d %s 0 0 50 H I C CNN "%s"' % (len(sgcomp.user_fields), field_text, tokens[1])
                s = shlex.shlex(line)
                s.whitespace_split = True
                s.commenters = ''
                s.quotes = '"'
                line = list(s)
                values = line[1:] + ['' for n in range(len(Component._FN_KEYS) - len(line[1:]))] 

                sgcomp.user_fields.append (dict(zip(Component._FN_KEYS,values)))

            self.get_next_line()
            tokens = self.line.split()
    
        #
        if self.line.startswith ("FPLIST"):
            self.get_next_line()
            tokens = self.line.split()
        
            while not tokens[0] in self.kw:
                sgcomp.fplist.append (self.line)
                #comp.fplist.append (self.line)
                self.get_next_line()
                tokens = self.line.split()

        # get aliases, documentation fields
        alias_name = None
        tokens = self.line.split()
       
        while tokens[0] != "UNIT":
            if self.line.startswith ("DESC"):
                self.comp_description = after (self.line, " ")
                self.get_next_line()
                tokens = self.line.split()

            elif self.line.startswith ("KEYW"):
                self.comp_keywords = after (self.line, " ")
                self.get_next_line()
                tokens = self.line.split()

            elif self.line.startswith ("DOC"):
                self.comp_datasheet = after (self.line, " ")
                self.get_next_line()
                tokens = self.line.split()

            elif self.line.startswith ("ALIAS"):
                #if not self.comp_datasheet:
                #    if alias_name:
                #        self.comp_datasheet = "http://www.ti.com/lit/gpn/sn" + alias_name
                #    else:
                #        self.comp_datasheet = "http://www.ti.com/lit/gpn/sn" + name
                
                name, sgdoc = self.make_doc (sgcomp, alias_name)
                sgcomp.doc_fields [name] = sgdoc
                #self.add_doc(comp, alias_name)

                #
                alias_name = after (self.line, " ")
                self.get_next_line()
                tokens = self.line.split()

                #self.comp_description = None
                #self.comp_keywords = None
                self.comp_datasheet = None
            else:
                print "error: unexpected line: " + self.line
                self.num_errors += 1
                self.get_next_line()
                tokens = self.line.split()
        # while

        #if not self.comp_datasheet:
        #    if alias_name:
        #        self.comp_datasheet = "http://www.ti.com/lit/gpn/sn" + alias_name
        #    else:
        #        self.comp_datasheet = "http://www.ti.com/lit/gpn/sn" + name
        
        name, sgdoc = self.make_doc (sgcomp, alias_name)
        sgcomp.doc_fields [name] = sgdoc
        #! self.add_doc(comp, alias_name)

        # units

        while tokens[0].upper() == "UNIT":

            unit = self.parse_unit(sgcomp)

            #
            unit.is_overlay = False
                    
            if not self.regen and unit.unit_shape == "power":
                unit.is_power_unit = True

                if self.unit_combine == "seperate":
                    unit.set_width (400)
                    # self.box_height = self.max_height
                    if self.label_style=="fixed":
                        unit.unit_rect.size.y = 500    
                    else:
                        unit.unit_rect.size.y = 400    
                    unit.unit_shape = "box"
                    unit.elements[0].shape = "box"
                    unit.fill = NoFill
                # this relies on pwr unit being last unit...
                elif self.opt_combine_power_for_single_units and self.unit_num==2 or self.unit_combine=="combine":
                    #unit.unit_shape = "none"
                    unit.is_overlay = True
        
                    #self.unit_num = self.unit_num - 1

                    self.pin_pos_top.y    = self.last_unit.unit_rect.top()
                    self.pin_pos_bottom.y = self.last_unit.unit_rect.bottom()

                    if unit.elements:
                        for pin in unit.elements[0].pins:
                            if pin.orientation == 'D':
                                self.last_unit.elements[0].pins.append (pin)
                            elif pin.orientation == 'U':
                                self.last_unit.elements[-1].pins.append (pin)
                    else:
                        print "error: no elements ? %s" % sgcomp.name
                else:
                    unit.set_width (400)
                    #self.box_height = self.max_height
                    if self.label_style=="fixed":
                        unit.unit_rect.size.y = 500    
                    else:
                        unit.unit_rect.size.y = 400    
                    unit.unit_shape = "box"
                    unit.fill = NoFill
                    unit.elements[0].shape = "box"
            else:
                unit.is_power_unit = False

            #

            if not unit.is_overlay or self.regen:
                sgcomp.units.append (unit)

            self.last_unit = unit
            tokens = self.line.split()

        if self.line.startswith ("END"):
            self.get_next_line()
        else:
            print "error: expected END: " + self.line
            self.num_errors += 1


        return sgcomp



    def generate_component (self, sgcomp):
        comments = []
        comments.append ("#\n")
        comments.append ("# " + sgcomp.name + "\n")
        comments.append ("#\n")

        component_data = []
        component_data.append("DEF " + sgcomp.name + " " + sgcomp.ref + " 0 40 Y Y 1 L N")      # units are not interchangeable
        component_data.append("F0 \"U\" 0 0 50 H V C CNN")
        component_data.append("F1 \"74469\" 0 -200 50 H V C CNN")
        component_data.append("F2 \"\" 0 0 50 H I C CNN")
        component_data.append("F3 \"\" 0 0 50 H I C CNN")
        component_data.append("DRAW")
        component_data.append("ENDDRAW")
        component_data.append("ENDDEF")

        comp = Component(component_data, comments, self.documentation)
        comp.fields [0]['reference'] = sgcomp.ref
        comp.fields [1]['name'] = sgcomp.name
        comp.definition['reference'] = sgcomp.ref
        comp.definition['name'] = sgcomp.name

        comp.definition['text_offset'] = str(self.def_name_offset)

        for s in sgcomp.fplist:
            comp.fplist.append (s)

        for key in sgcomp.doc_fields:
            sgdoc = sgcomp.doc_fields[key]
            self.lib.documentation.components[key] = OrderedDict([('description',sgdoc.description), ('keywords',sgdoc.keywords), ('datasheet',sgdoc.datasheet)])
            if key != sgcomp.name:
                comp.aliases[key] = self.lib.documentation.components[key]

        if sgcomp.default_footprint:
            comp.fields [2]['posx'] = "0"
            comp.fields [2]['posy'] = "0"
            comp.fields [2]['visibility'] = "I"
            comp.fields [2]['name'] = sgcomp.default_footprint

        if sgcomp.user_fields:
            for f in sgcomp.user_fields:
                comp.fields.append (f)

        #
        # draw units

        self.unit_num = 1
        self.units_have_variant = 0

        for unit in sgcomp.units:
            self.draw_unit (sgcomp, comp, unit)

            self.unit_num += 1


        #
        comp.fields [0]['posx'] = str(self.ref_pos.x)
        comp.fields [0]['posy'] = str(self.ref_pos.y)

        comp.fields [1]['posx'] = str(self.name_pos.x)
        comp.fields [1]['posy'] = str(self.name_pos.y)

        values = []
        values.append (sgcomp.name)
        values.append (sgcomp.ref)
        values.append ("0")     # not used
        values.append ("40")    # text offset
        values.append ("Y")     # draw pin number    
        values.append ("Y")     # draw pin name
        values.append (str(self.unit_num))   # unit count
        values.append ("L")     # L=units are not interchangeable
        values.append ("N")     # option flag ( Normal or Power)
        # comp.definition = dict(zip(Component._DEF_KEYS, values))
        comp.definition['unit_count'] = str(len(sgcomp.units))

        cur_comp = self.lib.getComponentByName(comp.name)
    
        if cur_comp:
            print "replacing: " + comp.name
            self.lib.removeComponent (comp.name)
        else:
            print "adding: " + comp.name
        
        self.lib.addComponent (comp)



    def draw_unit (self, sgcomp, comp, unit):

        #debug
        #print "unit %d %s %s" % (self.unit_num, unit.unit_shape, "power" if unit.is_power_unit else "")


        self.pin_pos_left = Point()
        self.pin_pos_left.x = -unit.unit_rect.size.x / 2
        self.pin_pos_left.y = 0

        self.pin_pos_right = Point()
        self.pin_pos_right.x = unit.unit_rect.size.x / 2
        self.pin_pos_right.y = 0

        self.pin_pos_top.x = 0
        self.pin_pos_bottom.x = 0

        self.label_style = "floating"


        if unit.unit_shape == "box" or unit.unit_shape == "none":

            # draw unit

            #self.cur_pos = Point(0,50)
            self.cur_pos = Point(0,0)

            for element in unit.elements:
                for pin in element.pins:
                    if "C" in pin.shape:
                        comp.definition['text_offset'] = str(self.def_extra_offset)
                        break
                        
                #
                for variant in range (0, self.units_have_variant+1):
                    self.pin_pos_top.x = 0
                    self.pin_pos_bottom.x = 0
                    elem_height = self.draw_element (sgcomp, unit, element, comp, self.unit_num, variant + self.units_have_variant)

                self.cur_pos.y -= elem_height

            if unit.is_overlay:
                self.set_label_pos(self.last_unit) # ??
            else:
                offset = Point()
                # offset.y = self.align_to_grid (unit.unit_rect.size.y/2, 100)
                offset.y = self.align_unit (unit)
                self.move_items (comp, self.unit_num, offset)
                unit.unit_rect.pos.y = offset.y
                # move labels?
                if not unit.is_power_unit:
                    self.set_label_pos(unit)

        elif unit.unit_shape in ["and", "nand", "or", "nor", "xor", "xnor", "not", "buffer"]:

            #
            # pins
            #temp = self.pin_length

            comp.pin_length = 150

            element = unit.elements[0]
            
            unit_pins = []
            for pin in element.pins:
                if pin.type != " ":
                    unit_pins.append (pin)


            self.label_style = "fixed"

            self.ref_pos.x = 0
            self.ref_pos.y = 50

            self.name_pos.x = 0
            self.name_pos.y = -50
            #
            num_inputs=0
            num_outputs=0
            other_pins = []
            for pin in unit_pins:
                if pin.is_input():
                    num_inputs+=1
                elif pin.is_output():
                    num_outputs+=1
                else:
                    other_pins.append (pin)
            #num_outputs = len(unit_pins) - num_inputs

            #if num_inputs != len(unit_pins) - num_outputs:
            #    print "error: wrong number of input pins: expected %d got %d" % (len(unit_pins)-1, num_inputs)
            #    self.num_errors += 1
            #    #continue

            if not num_outputs in [1,2]:
                print "error: wrong number of output pins: expected 1-2 got %d" % (num_outputs)
                self.num_errors += 1
                #continue

            ##
            if unit.unit_shape in ["and", "nand", "or", "nor"]:
                demorgan = 1
                self.units_have_variant = 1
            else:
                demorgan = 0
                    
            for variant in range (0,demorgan+1):

                gatedef = self.create_gate (unit.unit_shape, num_inputs, num_outputs, variant)

                #
                gatedef.fill = unit.fill
                gatedef.qualifiers = unit.qualifiers
                gatedef.add_gate_graphic (comp, self.unit_num, variant + demorgan)
            
                inputs_pos = gatedef.get_input_positions()
                outputs_pos = gatedef.get_output_positions()
        
                if variant==0:
                    input_shape = " "
                    output_shape = " "
                    if unit.unit_shape in ['nand', 'nor', 'xnor', 'not']:
                        output_shape = "I"
                else:
                    # de morgan
                    input_shape = "I"
                    output_shape = "I"
                    if unit.unit_shape in ['nand', 'nor', 'not']:
                        output_shape = " "


                if self.unit_num == 1:
                    self.pin_pos_top.x = 0
                    self.pin_pos_top.y = gatedef.height/2

                    self.pin_pos_bottom.x = 0
                    self.pin_pos_bottom.y = -gatedef.height/2

                    self.max_height = gatedef.height

                    unit.unit_rect.pos.y = gatedef.height/2
                    unit.unit_rect.size.y = self.max_height
                    self.box_height = gatedef.height
                    #self.y_pin_extent = self.max_height
                else:
                    self.pin_pos_top.x = 0
                    self.pin_pos_top.y = 0

                    self.pin_pos_bottom.x = 0
                    self.pin_pos_bottom.y = -500    # todo: depends on pin_len

                    self.max_height = 600
                    
                    self.box_height = self.max_height

                    unit.unit_rect.size.y = self.max_height
                    #self.y_pin_extent = self.max_height


                if num_inputs > len(inputs_pos):
                    print "error: too many input pins, expected %d got %d" % ( len(inputs_pos), num_inputs)
                    self.num_errors += 1
            
    #            if comp.name=="74LS136":
    #                print "oops"

                if self.icon_lib and len(unit.icons)>0:
                    for icon_name in unit.icons:
                        comp_icon = self.icon_lib.getComponentByName(icon_name)
                        if comp_icon:
                            style = StyleAttributes()
                            style.fill = unit.fill
                            style.pensize = self.box_pen
                            copy_icon (comp, comp_icon, self.unit_num, gatedef.get_center(), style=style)
                        else:
                            print "error: unknown icon %s " % icon_name 
                            self.num_errors += 1

                j=0
                for pin in unit_pins:
                    if pin.is_input() and j<len(inputs_pos):
                        pin.length = comp.pin_length + gatedef.offsets[j]
                        pin.unit = self.unit_num
                        pin.demorgan = variant + demorgan
            
                        if unit.unit_shape == "buffer" and j==1:
                            dy = align_to_grid(abs(inputs_pos[j].y)+99, 100)
                            dy = dy - abs(inputs_pos[j].y)
                            pin.length += dy
                            pin.pos.x = inputs_pos[j].x 
                            pin.pos.y = inputs_pos[j].y - pin.length
                            pin.orientation="U"
                        else:
                            pin.pos.x = inputs_pos[j].x - pin.length + gatedef.offsets[j]
                            pin.pos.y = inputs_pos[j].y
                            pin.shape = input_shape
                            pin.orientation="R"

                        j += 1
                        #pins.append (pin)
                        comp.drawOrdered.append( pin.get_element () )
                        # pin text
                        if pin.qualifiers and self.opt_pin_qualifiers:
                            self.draw_pin_text (comp, self.unit_num, variant, pin, pin.qualifiers)

                j = 0
                for pin in unit_pins:
                    if pin.is_output():
                        pin.length = comp.pin_length
                        pin.unit = self.unit_num
                        pin.demorgan = variant + demorgan
                        pin.orientation = "L"
                        if j==0:
                            pin.shape = output_shape
                        else:
                            pin.shape = "I" if output_shape == " " else " "

                        pin.pos.x = outputs_pos[j].x + comp.pin_length
                        pin.pos.y = outputs_pos[j].y       
                        j += 1
                        #pins.append (pin)
                        comp.drawOrdered.append( pin.get_element () )

                        # pin text
                        if pin.qualifiers and self.opt_pin_qualifiers:
                            self.draw_pin_text (comp, self.unit_num, variant, pin, pin.qualifiers)

                # 
                self.draw_pins (unit, other_pins, comp, self.unit_num, variant + demorgan)


            ##
            #self.pin_length = temp


    def draw_pin_text (self, comp, unit, variant, pin, text):
        
        pos = Point(pin.pos.x, pin.pos.y)
        fontsize = pin.sizename

        offset = Point()
        offset.x = pin.length
        # todo handle overbars, variable width?
        if comp.definition['draw_pinname'] == "Y" and pin.name != "~":
            offset.x += len(pin.name) * fontsize 

        offset.x += int(comp.definition['text_offset'])

        # left edge ?
        if pin.orientation == "L":
            offset.x += fontsize

        # center v
        offset.y =  fontsize / 2

        if pin.orientation == "L":
            pos.x -= offset.x
            pos.y -= offset.y
        elif pin.orientation == "R":
            pos.x += offset.x
            pos.y -= offset.y

        draw_text (comp, unit, variant, pos, text, fontsize)



    def set_label_pos(self, unit):

        if self.label_style == "floating":
            self.max_height = max (self.max_height, unit.unit_rect.size.y)
    
            if unit.unit_shape == "box":
                margin = 50
            else:
                margin = 50 # ??

            y = unit.unit_rect.top() + margin
            #if y > self.ref_pos.y:
            self.ref_pos.x = unit.unit_rect.left()
            self.ref_pos.y = y

            y = unit.unit_rect.bottom() - margin
            #if y < self.name_pos.y:
            self.name_pos.x = unit.unit_rect.left()
            self.name_pos.y = y

    def draw_element (self, sgcomp, xunit, element, comp, unit, variant):

        left_pins = self.find_pins (element.pins, "R")
        right_pins = self.find_pins (element.pins, "L")

        top_pins = self.find_pins_with_label (element.pins, "D")
        bottom_pins = self.find_pins_with_label (element.pins, "U")

        xunit.unit_rect.pos.x = -xunit.unit_rect.size.x / 2
        xunit.unit_rect.size.x = xunit.unit_rect.size.x

        box_size = Point ()
        box_size.x = xunit.unit_rect.size.x
        box_size.y = max (len(left_pins), len(right_pins)) * 100

        if box_size.y == 0:
            box_size.y = 100

            if xunit.is_power_unit:
                # box_size.y = self.box_height
                box_size.y = xunit.unit_rect.size.y

                while box_size.y % 100 != 0:
                    box_size.y += 50

                if sgcomp.pin_length % 100 == 0:
                    # even
                    while box_size.y % 200 != 0:
                        box_size.y += 100
                else:
                    while box_size.y % 200 == 0:
                        box_size.y += 100

        if element.shape == "control":
            box_size.y += 100

        # apply a min height (power units only?)
        # should apply to unit?
        # shape, template
        min_size = 0

        top_margin = 0
        if len(top_pins) > 0:
            min_size += 200

            if len(left_pins)+len(right_pins) != 0:
                if sgcomp.pin_length == 150:
                    top_margin = 0
                else:
                    top_margin = 50                    

        bottom_margin = 0
        if len(bottom_pins) > 0:
            min_size += 200

            if len(left_pins)+len(right_pins) != 0:
                if sgcomp.pin_length == 150:
                    bottom_margin = 0
                else:
                    bottom_margin = 50                    

        box_size.y = max (box_size.y + top_margin + bottom_margin, min_size)

        #
        xunit.unit_rect.size.y = -self.cur_pos.y + box_size.y 

        #offset = Point (0,50)

        # draw element outline
        if element.shape == "box":
            rect = Rect()
            rect.p1.x = -box_size.x/2
            rect.p1.y = self.cur_pos.y

            rect.p2.x = box_size.x/2
            rect.p2.y = self.cur_pos.y - box_size.y

            rect.unit = unit
            rect.demorgan = variant
            rect.fill = xunit.fill
            rect.pensize = self.box_pen
            comp.drawOrdered.append( rect.get_element() )

        elif element.shape == "control":
            poly = PolyLine ()
            poly.unit = unit
            poly.demorgan = variant
            poly.fill = xunit.fill
            poly.pensize = self.box_pen
            poly.points.append (Point (-box_size.x/2 + 50, self.cur_pos.y - box_size.y))
            poly.points.append (Point (-box_size.x/2 + 50, self.cur_pos.y - box_size.y+50))
            poly.points.append (Point (-box_size.x/2, self.cur_pos.y - box_size.y+50))
            poly.points.append (Point (-box_size.x/2, self.cur_pos.y))
            poly.points.append (Point (box_size.x/2, self.cur_pos.y))
            poly.points.append (Point (box_size.x/2, self.cur_pos.y - box_size.y+50))
            poly.points.append (Point (box_size.x/2 - 50, self.cur_pos.y - box_size.y+50))
            poly.points.append (Point (box_size.x/2 - 50, self.cur_pos.y - box_size.y))
            poly.point_count = len(poly.points)
            comp.drawOrdered.append( poly.get_element() )

        if element.label:
            fontsize = 50
            pos = Point (0, self.cur_pos.y - box_size.y/2).Sub (Point(fontsize/2, fontsize/2))
            
            draw_text (comp, unit, variant, pos, element.label, fontsize)



        # add element pins

        self.pin_pos_left.x = -box_size.x/2
        self.pin_pos_left.y = self.cur_pos.y - 50 - top_margin

        self.pin_pos_right.x = box_size.x/2
        self.pin_pos_right.y = self.cur_pos.y - 50 - top_margin

        if not xunit.is_overlay:
            #self.pin_pos_top.x = 0

            self.pin_pos_bottom.x = 0
            
            if xunit.unit_shape == "none":
                # power unit (combine) ?
                # Note : might be template 
                self.pin_pos_bottom.y = self.cur_pos.y - self.max_height
            else:
                self.pin_pos_bottom.y = self.cur_pos.y - box_size.y

        self.draw_pins (xunit, element.pins, comp, unit, variant)

        #
        for group in element.groups:
            group_pos = Point()
            group_pos.x = -box_size.x/2
            group_pos.y = group.pins[0].pos.y + 50
            group_size = Point()
            group_size.x = 200
            group_size.y =  len(group.pins) * 100

            rect = Rect()
            rect.p1.x = group_pos.x
            rect.p1.y = group_pos.y
            rect.p2.x = group_pos.x + group_size.x
            rect.p2.y = group_pos.y - group_size.y
            rect.unit = unit
            rect.demorgan = variant
            rect.fill = NoFill
            rect.pensize = 6
            comp.drawOrdered.append( rect.get_element() )

            pos = Point()
            pos.x = group_pos.x + group_size.x
            pos.y = group_pos.y - group_size.y/2 - 25
            if group.type == "C":
                type_text = "&xrtri;"
            elif group.type == "~":
                type_text = "&circ;"
            else:
                type_text = ""

            if type_text:
                draw_text (comp, unit, variant, pos, type_text, 50)
                offset = 50
            else:
                offset = 10

            if group.qualifiers:
                pos.x = group_pos.x + group_size.x - len(get_chars(group.qualifiers)) * 50 - 25
                pos.y = group_pos.y - group_size.y/2 - 25
                draw_text (comp, unit, variant, pos, group.qualifiers, 50)
            
            if group.label:
                pos.x = group_pos.x + group_size.x + offset
                pos.y = group_pos.y - group_size.y/2 - 25
                draw_text (comp, unit, variant, pos, group.label, 50)

        # add icons
        if self.icon_lib and len(xunit.icons)>0:
            k = 0
            y_pos = self.cur_pos.y - xunit.unit_rect.size.y/2
            if len(xunit.icons) > 1:
                icons_y_extent = len(xunit.icons) * 125 + (len(xunit.icons)-1)*25
            else:
                icons_y_extent = 0

            for icon_name in xunit.icons:
                comp_icon = self.icon_lib.getComponentByName(icon_name)
                if comp_icon:
                    style = StyleAttributes()
                    # todo: not sure this is right way
                    if xunit.unit_shape == "box":
                        style.fill = xunit.fill
                    else:
                        style.fill = xunit.fill
                    style.pensize = self.box_pen
                    copy_icon (comp, comp_icon, unit, Point(0, y_pos -k * 150 + icons_y_extent/2), style=style)
                    k += 1
                else:
                    print "error: unknown icon %s " % icon_name
                    self.num_errors += 1

        if self.icon_lib and xunit.template:
            comp_icon = self.icon_lib.getComponentByName(xunit.template)
            style = StyleAttributes()
            #style.fill = xunit.fill
            if comp_icon:
                copy_icon (comp, comp_icon, unit, Point(0, 0), style=style)

        #
        #if self.label_style == "floating":
        #    self.max_height = max (self.max_height, xunit.unit_rect.size.y)
    
        #    if xunit.unit_shape == "box":
        #        margin = 50
        #    else:
        #        margin = 50 # ??

        #    y = 0 + margin
        #    if y > self.ref_pos.y:
        #        self.ref_pos.x = -box_size.x/2
        #        self.ref_pos.y = y

        #    y = -xunit.unit_rect.size.y - margin
        #    if y < self.name_pos.y:
        #        self.name_pos.x = -box_size.x/2
        #        self.name_pos.y = y
        #endif

        return box_size.y


    """
        if self.pin_pos_left.y == 0 and self.pin_pos_left.y == self.pin_pos_right.y:
            # there are no horiz pins, probably a power unit
            # ??
            if self.unit_shape == "none":
                # ??
                # self.y_pin_extent = self.pin_pos_top.y - self.pin_pos_bottom.y
                self.unit_height = self.y_pin_extent

                box_top_y    = self.pin_pos_top.y
                box_bottom_y = self.pin_pos_bottom.y
            else:
                self.y_pin_extent = self.pin_pos_top.y - self.pin_pos_bottom.y
                self.unit_height = self.y_pin_extent

                box_top_y = 0
                box_bottom_y = box_top_y - self.unit_height
        else:
            self.y_pin_extent = -min (self.pin_pos_left.y, self.pin_pos_right.y)-100
            if self.y_pin_extent % 200 == 100:
                self.vert_margin = 200
            else:
                self.vert_margin = 200
            self.unit_height = self.y_pin_extent + self.vert_margin
                        
            #self.vert_margin = align_to_grid(self.unit_height - self.y_pin_extent + 199, 200)
            box_top_y = self.vert_margin/2
            box_bottom_y = box_top_y - self.unit_height

        # move top/bottom pins
        top_pins = self.find_pins (element.pins, "D")
        if len(top_pins)>1:
            self.pin_pos_top.x = - 100 * int((len(top_pins)-1) / 2)
        else:
            self.pin_pos_top.x = 0

        bottom_pins = self.find_pins (element.pins, "U")
        if len(bottom_pins)>1:
            self.pin_pos_bottom.x = - 100 * int((len(bottom_pins)-1) / 2)
        else:
            self.pin_pos_bottom.x = 0

        for pin in element.pins:
            if pin.orientation == 'D':
                pin.pos.x += self.pin_pos_top.x
                pin.pos.y = box_top_y + pin.length
            elif pin.orientation == 'U':
                pin.pos.x += self.pin_pos_bottom.x
                pin.pos.y = box_bottom_y - pin.length

        # align pins (right)
        right_pins = self.find_pins (element.pins, "L")
        if len(right_pins)>0:
            if right_pins[0].align == "C":
                # need to force alignment to 100 mil grid?
                #top_y = 100 * (len(right_pins)-1) / 2
                top_y = (right_pins[0].pos.y - right_pins[-1].pos.y) / 2
                top_y = top_y - self.unit_height / 2 + 100

                dy = top_y - right_pins[0].pos.y

                j = 0
                for pin in element.pins:
                    if pin.orientation == 'L':
                        pin.pos.y += dy  # top_y - j * 100
                        j += 1

        self.y_offset = self.align_to_grid (self.y_pin_extent/2, 100)
        #self.y_offset = 0
        #print "unit %d ext %d offset %d" % (unit, self.y_pin_extent, self.y_offset)
    """

    def get_template_pins (self, name):
        pins = []

        comp = self.icon_lib.getComponentByName(name)

        for elem in comp.draw['pins']:
            item = dict(elem)
            pin = Pin()
            pin.pos = Point (int(item['posx']), int (item['posy']))
            pin.name = item['name']
            pin.number = item['num']
            pin.orientation = item['direction']

            pin.shape = item['pin_type']
            pin.type = item['electrical_type']

            pins.append (pin)

        # sort by num
        for passnum in range(len(pins)-1,0,-1):
            for i in range(passnum):
                if int(pins[i].number) > int(pins[i+1].number) :
                    temp = pins[i]
                    pins[i] = pins[i+1]
                    pins[i+1] = temp

        return pins

    def draw_pins (self, unit, pins, comp, unit_num, variant):
        for pin in pins:
            if pin.orientation == 'R':
                pin.pos.y = self.pin_pos_left.y
                self.pin_pos_left.y -= 100
            elif pin.orientation == 'L':
                pin.pos.y = self.pin_pos_right.y
                self.pin_pos_right.y -= 100

                if pin.type == "T"  and self.opt_pin_qualifiers:
                    self.draw_pin_text (comp, unit_num, variant, pin, "&xdtri;")
            elif pin.orientation == 'D':
                pin.pos.x = self.pin_pos_top.x
                pin.pos.y = self.pin_pos_top.y + pin.length
                #pin.pos.y = self.unit_rect.top() + pin.length
                self.pin_pos_top.x += 100
            elif pin.orientation == 'U':
                pin.pos.x = self.pin_pos_bottom.x
                
                pin.pos.y = self.pin_pos_bottom.y - pin.length
                #pin.pos.y = self.unit_rect.bottom() - pin.length
                self.pin_pos_bottom.x += 100

            if pin.qualifiers and self.opt_pin_qualifiers:
                self.draw_pin_text (comp, unit_num, variant, pin, pin.qualifiers)

            pin.unit = unit_num
            pin.demorgan = variant
        #

        if unit.template:
            template_pins = self.get_template_pins (unit.template)
            left_pins = self.find_pins (template_pins, "R")
            right_pins = self.find_pins (template_pins, "L")

            l_pin = 0
            r_pin = 0

            ##
            for pin in pins:
                if pin.type !=" " :
                    if pin.orientation == 'R':
                        if l_pin < len(left_pins):
                            pin.pos = left_pins[l_pin].pos
                            l_pin += 1
                        else:
                            print "error %s" % pin.number
                    elif pin.orientation == 'L':
                        if r_pin < len(right_pins):
                            pin.pos = right_pins[r_pin].pos
                            r_pin += 1
                        else:
                            print "error %s" % pin.number

        # align pins (right)
        right_pins = self.find_pins (pins, "L")
        if len(right_pins)>0:
            if right_pins[0].align == "C":
                # need to force alignment to 100 mil grid?

                height = unit.unit_rect.size.y/100 *100
                #top_y = 100 * (len(right_pins)-1) / 2
                top_y = (right_pins[0].pos.y - right_pins[-1].pos.y) / 2
                top_y = top_y - height / 2

                dy = top_y - right_pins[0].pos.y
                dy = align_to_grid (dy, 50)
                j = 0
                for pin in pins:
                    if pin.orientation == 'L':
                        pin.pos.y += dy  # top_y - j * 100
                        j += 1

        # align pins (bottom)
        _pins = self.find_pins (pins, "U")
        if len(_pins)>0:
            if _pins[0].align == "C":
                # need to force alignment to 100 mil grid?
                width = len(_pins) * 100 
                j = 0
                for pin in pins:
                    if pin.orientation == 'U':
                        pin.pos.x = -width/2 + j * 100 + 100
                        j += 1

        # align pins (top)
        _pins = self.find_pins (pins, "D")
        if len(_pins)>0:
            if _pins[0].align == "C":
                # need to force alignment to 100 mil grid?
                width = len(_pins) * 100
                j = 0
                for pin in pins:
                    if pin.orientation == 'D':
                        pin.pos.x = -width/2 + j * 100 + 100
                        j += 1

        for pin in pins:
            if pin.type != " ":
                comp.drawOrdered.append( pin.get_element() )


    def get_pos (self, params, name):
        x = int(params[name+'x'])
        y = int(params[name+'y'])
        return Point(x,y)

    def set_pos (self, params, name, p):
        params[name+'x'] = str(p.x)
        params[name+'y'] = str(p.y)

    def move_items (self, comp, unit, offset):
        for elem in comp.drawOrdered:
            params = elem[1]
            if params['unit'] == str(unit):
                if elem[0] == "P":
                    poly = PolyLine (convert_to_string(elem))
                    for p in poly.points:
                        p.x += offset.x
                        p.y += offset.y
                    params['points'] = poly.get_point_list()
                elif elem[0] == "A":
                    p = self.get_pos (params, "pos").Add (offset)
                    self.set_pos (params, "pos", p)            

                    p = self.get_pos (params, "start").Add (offset)
                    self.set_pos (params, "start", p)            

                    p = self.get_pos (params, "end").Add (offset)
                    self.set_pos (params, "end", p)            

                elif elem[0] == "S":
                    p = self.get_pos (params, "start").Add (offset)
                    self.set_pos (params, "start", p)            

                    p = self.get_pos (params, "end").Add (offset)
                    self.set_pos (params, "end", p)            
                else:
                    p = self.get_pos (params, "pos").Add (offset)
                    self.set_pos (params, "pos", p)            
    
    def write_symgen_file (self, out_filename):

        outf = open (out_filename, "w")

        outf.write ("#\n" )
        outf.write ("# %s\n" % os.path.basename (out_filename) )
        outf.write ("#\n" )
        outf.write ("%%lib %s\n" % os.path.basename (out_filename) )
        outf.write ("\n" )

        outf.write ("#\n" )
        outf.write ("# Global Defaults\n" )
        outf.write ("#\n" )
        outf.write ("%%line %d\n" % self.def_box_pen )
        outf.write ("\n" )
        outf.write ("%%pinlen %d\n" % self.def_pin_length )
        outf.write ("%%width %d\n" % self.def_box_width )

        if self.def_box_fill == NoFill:
            outf.write ("%%fill %s\n" % "None" )
        elif self.def_box_fill == Foreground:
            outf.write ("%%fill %s\n" % "fore" )
        elif self.def_box_fill == Background:
            outf.write ("%%fill %s\n" % "back" )

        outf.write ("\n" )

        outf.write ("%%style %s\n" % self.symbol_style.name )
        outf.write ("\n" )

        for comp in self.components:
            outf.write ("#\n" )
            outf.write ("# %s\n" % (comp.name))
            outf.write ("#\n" )
            outf.write ("COMP %s %s\n" % (comp.name, comp.ref))

            cur_width = self.def_box_width

            #if comp.pin_length == self.def_pin_length:
            #    outf.write ("%%pinlen %d\n" % comp.pin_length)

            if comp.default_footprint:
                outf.write ("FIELD $FOOTPRINT \"%s\"\n" % (comp.default_footprint))

            if comp.user_fields:
                for field in comp.user_fields:
                    outf.write ("FIELD %s \"%s\"\n" % (field['fieldname'], field['name']))

            if comp.fplist:
                outf.write ("FPLIST\n" )
                for s in comp.fplist:
                    outf.write ("%s\n" % (s))
                #outf.write ("#\n" )

            sgdoc = comp.doc_fields[comp.name]
            if sgdoc.description:
                outf.write ("DESC %s\n" % capitalise(sgdoc.description))
            if sgdoc.keywords:
                outf.write ("KEYW %s\n" % (sgdoc.keywords))
            if sgdoc.datasheet:
                outf.write ("DOC %s\n" % (sgdoc.datasheet))

            for key in comp.doc_fields:
                sgdoc = comp.doc_fields[key]

                if key != comp.name:
                    outf.write ("ALIAS %s\n" % (key))

                    if sgdoc.description:
                        outf.write ("DESC %s\n" % capitalise(sgdoc.description))
                    if sgdoc.keywords:
                        outf.write ("KEYW %s\n" % (sgdoc.keywords))
                    if sgdoc.datasheet:
                        outf.write ("DOC %s\n" % (sgdoc.datasheet))

            for unit in comp.units:
                line = "UNIT"

                if unit.unit_shape != "box":
                    if unit.unit_shape == "buffer":
                        line += " BUF"
                    elif unit.unit_shape == "power":
                        line += " PWR"
                        if unit.combine == "seperate":
                            line += " SEP"
                        elif unit.combine == "combine":
                            line += " COMB"
                    else:
                        line += " " + unit.unit_shape.upper()

                if unit.unit_rect.size.x != cur_width:
                    cur_width = unit.unit_rect.size.x
                    line += " WIDTH %d" % (cur_width)

                if unit.qualifiers:
                    line += " LABEL \"%s\"" % (unit.qualifiers)

                if unit.template:
                    line += " TEMPLATE %s" % (unit.template)

                if unit.icons:
                    line += " ICON"
                    for s in unit.icons:
                        line += " %s" % s

                outf.write ("%s\n" % (line))

                for elem in unit.elements:
                    if len(unit.elements) > 1 or elem.label:
                        line = "ELEM"
                        if elem.shape != "box":
                            line += " " + elem.shape.upper()
                        if elem.label:
                            line += ' LABEL "%s"' % elem.label

                        outf.write ("%s\n" % line)

                    group_id = -1
                    for pin in elem.pins:
                        #outf.write ("%s %s %s %s\n" % (pin.number, pin.name, pin.type, symgen_to_kicad_dir(pin.orientation) ))
                        if group_id != pin.group_id:
                            if group_id != -1:
                                outf.write ("END-GROUP\n")

                            if pin.group_id != -1:
                                group = elem.groups[pin.group_id]
                                outf.write ('GROUP "%s" %s "%s" \n' % (group.qualifiers, group.type, group.label))
                            group_id = pin.group_id

                        outf.write ("%s\n" % pin.get_string())

                    if group_id != -1:
                        outf.write ("END-GROUP\n")

            outf.write ("END\n")

        outf.close ()


    def parse_input_file (self, inp_filename):

        self.file = open (inp_filename, 'r')
        self.get_next_line()

        self.in_component = False
        self.num_errors = 0
        self.regen = False
        self.out_path, out_filename = os.path.split (inp_filename)

        while self.line:
            if self.line.startswith ("%"):
                self.parse_directive()

            elif self.line.startswith ("COMP"):
                comp = self.parse_component()

                self.components.append (comp)
            else:
                # 
                print "error: unexpected line: " + self.line
                self.num_errors += 1
                self.get_next_line()

        #
        #
        #
        out_basename = os.path.splitext (out_filename)[0]

        # test
        if self.regen:
            self.write_symgen_file (os.path.join (self.out_path, "test_file.txt"))

        #
        # combine power units

        #
        self.libfile = os.path.join (self.out_path, out_basename + ".lib")
        self.docfile = os.path.join (self.out_path, out_basename + ".dcm")

        # create an empty lib
        new_lib = True
        if new_lib:
            infile = open (self.libfile, 'w')
            infile.write ("EESchema-LIBRARY Version 2.3\n")
            infile.write ("#encoding utf-8\n")
            infile.write ("#\n")
            infile.write ("#End Library\n")
            infile.close()

            infile = open (self.docfile, 'w')
            infile.write ("EESchema-DOCLIB  Version 2.0\n")
            infile.write ("#\n")
            infile.write ("#\n")
            infile.write ("#End Doc Library\n")
            infile.close()

        #
        #
        print "Creating library"
        self.lib = SchLib(self.libfile)
        print 'Library: %s' % self.libfile
        self.documentation = Documentation (self.docfile)
        #

        if self.components:
            for comp in self.components:
                self.generate_component(comp)
        ###

        self.lib.save (filename = self.libfile)

        print "done - %d errors" % self.num_errors


def ExitError( msg ):
    print(msg)
    sys.exit(-1)

#
# main
#
parser = argparse.ArgumentParser(description="Generate component library")

parser.add_argument("--inp", help="symgen script file")
parser.add_argument("--lib", help="KiCad .lib file")
parser.add_argument("--ref", help="7400 logic reference list")
parser.add_argument("-d", "--dump", help="Dump an existing library", action='store_true')
parser.add_argument("-v", "--verbose", help="Enable verbose output", action="store_true")

args = parser.parse_args()

#

#
symgen = SymGen()
symgen.verbose = args.verbose

#temp
#symgen.gen_comp ("data")
#symgen.process_list()

if args.dump:
    # -d --lib C:\git_bobc\kicad-library\library\74xx.lib --ref ..\74xx\7400_logic_ref.txt
    if not args.lib:
        ExitError("error: library name not supplied (need --lib)")

    lib_filename = args.lib
    dump_path = ""

    convert = ConvertLibrary()
    ## convert.symbol_style = SymbolStyle.PHYSICAL
    convert.dump_lib (lib_filename, dump_path, args.ref)

else:
    # --inp 74xx.txt
    if not args.inp:
        ExitError("error: symgen script file not supplied (need --inp)")

    file = args.inp

    symgen.parse_input_file (file)


