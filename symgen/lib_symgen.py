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
import fnmatch

# kicad lib utils
common = os.path.abspath(os.path.join(sys.path[0], 'common'))
if not common in sys.path:
    sys.path.append(common)

#from os import path, environ
import re
#import copy
#import time
#import hashlib
import shlex
#from enum import Enum

import kicad_sym

from schlib import *
from print_color import *

from str_utils import *
from sym_drawing import *
from sym_comp import *
from sym_gates import *
from sym_iec import *

from sym_utils import *
#import file_util

from gen_legacy import *
from gen_sweet import *


class SymGen:

    exit_code = 0
    num_errors = 0

    kw = ['COMP', 'DESC', 'KEYW', 'DOC', 'ALIAS', 'UNIT', 'ELEM', 'END']
    #  ELEM, GROUP

    #lib = None
    icon_lib = None
    #documentation = None
    file = None
    line = None

    footprints = None


    #
    #def_pin_length = 200
    #def_box_width = 600
    #def_box_pen = 10
    #def_box_fill = Background # background fill
    #def_logic_fill = NoFill # default
    ##def_logic_fill = Background
    #def_label_style = ls_floating
    #def_pin_stacking = False

    def_name_offset = 20
    def_extra_offset = 40

    # name offset
    # logic fill
    # tristate symbol

    components = []

    # per component settings  
    #pin_length = def_pin_length
    #box_width = def_box_width
    #box_pen = def_box_pen
    #box_fill = def_box_fill
    #logic_fill = def_logic_fill

    #
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

    last_shape = ""
    unit_num = 0
    #max_height = 600
    unit_label = ""

    # 
    #ref_pos = Point()
    #name_pos = Point()

    def __init__(self):
        self.kw = ['COMP', 'DESC', 'KEYW', 'DOC', 'ALIAS', 'UNIT', 'END']

        self.printer = PrintColor(True)
        self.footprints_folder = None

        self.verbose = False

        self.def_settings = SgSettings()

        self.out_path = None
        self.out_basename = None

        # some global settings
        self.opt_combine_power_for_single_units = True
        self.opt_power_unit_style = PowerStyle.BOX
        #self.opt_power_unit_style = PowerStyle.LINES

        self.symbol_style = SymbolStyle.ANSI
        #self.symbol_style = SymbolStyle.IEC

        self.opt_pin_qualifiers = False

        #self.opt_alternate_names = True

        self.def_logic_combine = "multi"

        self.output_format = "v6"



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
        #if self.verbose:
        #    print(self.line.rstrip())
        while self.line and (self.line.startswith ("#") or len(self.line.strip())==0):
            self.line = self.file.readline()
            #if self.verbose:
            #    print(self.line.rstrip())
    
        self.line = self.line.strip()

        self.tokens = tokenise (self.line)
            
    def find_component (self, name):
        for comp in self.components:
            if comp.name == name:
                return comp
        return None

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

    def parse_element (self, sgcomp, unit):
        src_lines = []

        element = IecElement()

        #element.shape = "box"
        # todo: is this right?
        element.shape = unit.unit_shape 

        element_num = 0

        if self.tokens[0].upper() == "ELEM":
            j = 1
            while j < len(self.tokens):
                if self.tokens[j].upper() == "CONTROL":
                    element.shape = "control"
                elif self.tokens[j].upper() == "LABEL":
                    j += 1
                    if j < len(self.tokens):
                        element.label = self.strip_quotes(self.tokens[j])
                elif self.tokens[j].isnumeric():
                    element_num = int (self.tokens[j])

                j += 1

            self.get_next_line()
        else:
            pass

        if unit.is_derived:
            element = unit.elements[element_num]
            element.is_derived = True

        while not self.tokens[0] in ['COMP', 'UNIT', 'ELEM', 'END']:
            if self.tokens[0].startswith("%"):
                sel_fields = []
                filename = None
                state = "field"
                for tok in self.tokens[1:]:
                    if state == "field":
                        if tok == "FROM":
                            state = "table"
                        else:
                            sel_fields.append(tok)
                    elif state == "table":
                        filename = self.strip_quotes(tok)
                #
                headings, file_rows = self.read_file (filename)
                print(headings)
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
        # end while

        element.pins = self.parse_pins (src_lines, sgcomp, element)
        return element

    def get_pin_by_number (self, pins, number):
        for pin in pins:
            if pin.number == number:
                return pin
        return None

    def find_pattern (self, sgcomp, name):
        
        for k,pattern in enumerate(sgcomp.settings.stack_patterns):
        
            if name in pattern:
                return k

        return -1

    def match_stacking_pattern (self, sgcomp, prev_pin, this_pin):

        if len(sgcomp.settings.stack_patterns)==0:
            return False

        pattern = self.find_pattern (sgcomp, this_pin.name)

        if pattern == -1:
            return False

        # check for same type and orientation
        if this_pin.type == prev_pin.type and this_pin.orientation == prev_pin.orientation and pattern == self.find_pattern(sgcomp, prev_pin.name):
            return True
        else:
            return False

    # return list of elements ?
    def parse_pins (self, lines, sgcomp, element):
        pins = element.pins

        cur_pin_type = "I"
        cur_pin_dir = "L"
        cur_pin_align = "L"

        group_id = -1
        group = None

        for line in lines:
            tokens = tokenise(line)
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
                pin.length = sgcomp.settings.pin_length
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
                # GROUP qualifiers type label
                group = Group()
                group_id += 1
                group.id = group_id
                element.groups.append(group)

                group.qualifiers = ""
                group.type = ""
                group.label = ""

                if len(tokens) > 1:
                    group.qualifiers = self.strip_quotes(tokens[1])
                if len(tokens) > 2:
                    group.type = tokens[2]
                if len(tokens) > 3:
                    group.label = self.strip_quotes(tokens[3])
            elif tokens[0].upper() == "END-GROUP":
                group = None
            elif tokens[0].upper() == "DEL":
                j = 1
                while j < len(tokens):
                    num = tokens[j]
                    filtered_pins = [x for x in pins if x.number != num]
                    pins = filtered_pins
                    j +=1

            else:    
                pin = Pin()
                pin.length = sgcomp.settings.pin_length
                pin.number = tokens[0]
                pin.name = "~"
                #pin.unit = unit

                if len(tokens) >= 2:
                    pin.name = tokens[1]

                if len(tokens) >= 3:
                    cur_pin_type = tokens[2]

                #

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
                    print(line)
                    print("error: unknown pin type: " + pin_type)
                    self.num_errors += 1
                pin.shape = flags

                #
                if sgcomp.settings.opt_alternate_names and sgcomp.settings.alt_name_char in pin.name:
                    names = pin.name.split (sgcomp.settings.alt_name_char)
                    pin.name = names[0]
                    for name in names[1:]:
                        pin.alternate_names.append (AlternatePin(name, pin.type, pin.shape))

                #
                pin.orientation = cur_pin_dir
                pin.align = cur_pin_align

                # no connect
                if "N" in pin.shape:
                    #pin.length = 0
                    pin.length = sgcomp.settings.pin_length
                    pin.visible = False
                else:
                    pin.length = sgcomp.settings.pin_length

                # pin position will be set later
                pin.orientation = symgen_to_kicad_dir (pin.orientation)

                # can stack power in pins; if same name/pos/type
                if sgcomp.settings.pin_stacking and "W" in pin.type and len(pins) > 0 and self.match_stacking_pattern (sgcomp, pins[-1], pin):
                    pin.can_stack = True
                else:
                    pin.can_stack = False
                
                cur_pin = self.get_pin_by_number (pins, pin.number)

                if cur_pin:
                    # add to existing
                    cur_pin.alternate_names.append (AlternatePin (pin.name, pin.type, pin.shape))
                else:
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
    #def add_doc(self, comp, alias_name):

    #    if self.comp_description or self.comp_keywords or self.comp_datasheet:
    #        if alias_name is None:
    #            tname = comp.name
    #            self.lib.documentation.components[tname] = OrderedDict([('description',self.comp_description), ('keywords',self.comp_keywords), ('datasheet',self.comp_datasheet)])
    #        else:
    #            tname = alias_name
    #            self.lib.documentation.components[tname] = OrderedDict([('description',self.comp_description), ('keywords',self.comp_keywords), ('datasheet',self.comp_datasheet)])
    #            comp.aliases[tname] = self.lib.documentation.components[tname]
    #    #
    #    #self.comp_description = None
    #    #self.comp_keywords = None
    #    self.comp_datasheet = None

    def make_doc(self, sgcomp, alias_name):

        sgdoc = SgDoc()

        if alias_name is None:
            tname = sgcomp.name
        else:
            tname = alias_name

        if self.comp_description or self.comp_keywords or self.comp_datasheet:
            sgdoc.description = self.comp_description
            sgdoc.keywords = self.comp_keywords
            sgdoc.datasheet = self.comp_datasheet

        #
        #self.comp_description = None
        #self.comp_keywords = None
        # todo: Hmmm
        #self.comp_datasheet = None

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

    def parse_directive(self, sgcomp):

        if self.tokens[0] == "%alt_names":

            if self.tokens[1].lower() == "off":
                alternate_names = False
            else:
                alternate_names = True
                alt_char = "/"

            if self.in_component:
                sgcomp.settings.opt_alternate_names = alternate_names
                sgcomp.settings.alt_name_char = alt_char
            else:
                self.def_settings.opt_alternate_names = alternate_names

        elif self.tokens[0] == "%lib":
            self.out_basename = self.tokens[1]
            if self.out_basename.endswith (".lib"):
                self.out_basename = before (self.out_basename, ".lib")

        elif self.tokens[0] == "%pinlen":
            if self.in_component:
                sgcomp.settings.pin_length = int (self.tokens[1])
            else:
                self.def_settings.pin_length = int (self.tokens[1])

        elif self.tokens[0] == "%pin_stack":
            stack = None
            stack_pattern =None

            if self.tokens[1].lower() == "off":
                stack = False
            else:
                stack = True
                stack_pattern = self.tokens[1:]

            if stack:
                if self.in_component:
                    sgcomp.settings.pin_stacking = stack
                    if stack_pattern:
                        sgcomp.settings.stack_patterns.append(stack_pattern)
                else:
                    self.def_settings.pin_stacking = stack
                    if stack_pattern:
                        self.def_settings.stack_patterns.append (stack_pattern)

        elif self.tokens[0] == "%pin_name_format":
            
            name_format =None

            if len(self.tokens) >= 3:
                name_format = self.tokens[1:]

                if self.in_component:
                    sgcomp.settings.pin_name_formats.append(name_format)
                else:
                    self.def_settings.pin_name_formats.append (name_format)
            else:
                print("error : insufficient argements %s : expecting '%%pin_name_format name format'" % self.line)

        elif self.tokens[0] == "%width":
            if self.tokens[1].lower() == "auto":
                width = 0
            else:
                width = int (self.tokens[1])

            if self.in_component:
                sgcomp.settings.box_width = width
            else:
                self.def_settings.box_width = width

        elif self.tokens[0] == "%line":
            if self.in_component:
                sgcomp.settings.box_pen = int (self.tokens[1])
            else:
                self.def_settings.box_pen = int (self.tokens[1])

        elif self.tokens[0] == "%label_style":
            if self.in_component:
                sgcomp.settings.label_style = self.tokens[1]
            else:
                self.def_settings.label_style = self.tokens[1]

        elif self.tokens[0] == "%fill":
            fill = self.parse_fill (self.tokens[1])
            if fill:
                if self.in_component:
                    sgcomp.settings.box_fill = fill
                    sgcomp.settings.logic_fill = fill
                else:
                    self.def_settings.box_fill = fill
            else:
                print("error : unknown fill %s" % self.line)
                self.num_errors += 1

        elif self.tokens[0] == "%iconlib":
            if not self.in_component:
                # filename = os.path.join ("data", self.tokens[1])
                filename = os.path.abspath(os.path.join(self.out_path, self.tokens[1]))

                if after(filename, ".").lower() == "lib":
                    self.icon_lib = SchLib(filename)
                elif after(filename, ".").lower() == "kicad_sym":
                    self.icon_lib = kicad_sym.KicadLibrary.from_file(filename)

        elif self.tokens[0] == "%style":
            tok = self.tokens[1].upper()

            # ANSI|IEC|DIN <fill> single|multi

            if tok == "ANSI":
                self.symbol_style = SymbolStyle.ANSI
            elif tok == "IEC":
                self.symbol_style = SymbolStyle.IEC
                self.opt_pin_qualifiers = True
            elif tok == "DIN":
                self.symbol_style = SymbolStyle.DIN
            else:
                print("error : unknown style %s : expecting ANSI, IEC or DIN" % tok)
                self.num_errors += 1

            if len(self.tokens) > 2:
                fill = self.parse_fill (self.tokens[2])
                if fill:
                    self.def_settings.logic_fill = fill
                else:
                    print("error : unknown fill %s" % self.line)
                    self.num_errors += 1

        else:
            print("error : unknown directive %s" % self.line)
            self.num_errors += 1

        self.get_next_line()





    def parse_unit (self, comp):

        # new unit
        unit = IecSymbol()

        unit.unit_rect.pos.x = 0
        unit.unit_rect.pos.y = 0
        unit.unit_rect.size.x = 0
        unit.unit_rect.size.y = 0

        unit.set_width (comp.settings.box_width)

        unit.unit_shape = self.last_shape
        if not unit.unit_shape:
            unit.unit_shape = "box"
        
        self.unit_num = self.unit_num + 1
        self.unit_combine = "auto"

        unit.vert_margin = 200
        unit.qualifiers = self.unit_label
        #unit.pin_length = self.pin_length

        # unit [ PWR|AND|... [ SEPerate | COMBined ] ] | Width int | ICON name
        # unit EXTENDS int
        j = 1
        while j < len(self.tokens):
            token = self.tokens[j].upper()

            if token == "PWR":
                unit.unit_shape = "power"
                # TODO: maybe not right place ?
                unit.set_width(200)
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

            elif token == "EXTENDS":
                # this works with FROM inheritance at COMP level
                # EXTENDS <unit num>
                j += 1
                src_unit = int(self.tokens[j])

                self.unit_num = self.unit_num - 1
                unit = comp.units[src_unit]
                unit.is_derived = True
                unit.modified = True

            elif token.startswith("W"):
                j += 1
                comp.settings.box_width = int(self.tokens[j])
                
                unit.set_width (comp.settings.box_width)

            elif token.upper().startswith("LABEL"):
                j += 1
                self.unit_label = self.strip_quotes (self.tokens[j])
                
                unit.qualifiers = self.unit_label

            elif token.startswith("TEMP"):
                j += 1
                unit.template = self.tokens[j]
                unit.unit_shape = "none"
                self.last_shape = unit.unit_shape

            elif token.startswith("ICON"):
                self.last_shape = unit.unit_shape
                self.icons = []
                while j < len(self.tokens)-1:
                    j += 1
                    self.icons.append(self.tokens[j])
                unit.icons = self.icons
            else:
                print("error : unknown parameter %s in UNIT" % token)
                self.num_errors += 1
            j += 1

        # 
        if not unit.is_derived:
            if unit.unit_shape != self.last_shape:
                self.icons = []    
                unit.icons = []
                unit.template = None

            self.last_shape = unit.unit_shape

            unit.icons = self.icons
            unit.combine = self.unit_combine

        #if len(unit.icons) == 0 and unit.template:
        #    unit.icons.append(unit.template)

        #
        #debug
        #print("unit %d %s %s" % (self.unit_num, unit.unit_shape, "power" if unit.is_power_unit else ""))

        # need pin pos generator ?

        self.pin_pos_left = Point()
        self.pin_pos_left.x = -comp.settings.box_width/2
        self.pin_pos_left.y = 0

        self.pin_pos_right = Point()
        self.pin_pos_right.x = comp.settings.box_width/2
        self.pin_pos_right.y = 0

        self.pin_pos_top.x = 0
        self.pin_pos_bottom.x = 0

        #if comp.name == "4017":
        #    print("oop")

        self.get_next_line()

        while self.tokens[0].upper() not in ['UNIT','END']:
            element = self.parse_element (comp, unit)

            if not element.is_derived:
                unit.elements.append (element)

        # ===============================================================================

        if unit.unit_shape in ["box", "none", "and", "nand", "or", "nor", "xor", "xnor", "not", "buffer", "power"]:

            if unit.unit_shape in ["and", "nand", "or", "nor", "xor", "xnor", "not", "buffer"]:

                ###
                #comp.settings.label_style = ls_center

                if self.opt_power_unit_style == PowerStyle.LINES:
                    comp.settings.pin_names_inside = True

                unit.fill = comp.settings.logic_fill
            else:
                unit.fill = comp.settings.box_fill

        else:
            print("error: unknown shape: " + unit.unit_shape)
            self.num_errors += 1

        # ===============================================================================
        #
        #self.last_unit = unit
        return unit


    def parse_component (self):

        sgcomp = SgComponent()
        sgcomp.settings = copy.copy (self.def_settings)

        # reset all current vars used during parsing

        self.last_shape = None
        self.unit_label = ""
        self.unit_num = 0
        self.last_unit = None
        self.icons = []

        self.pin_pos_left = Point()
        self.pin_pos_left.x = -sgcomp.settings.box_width/2
        self.pin_pos_left.y = 0

        self.pin_pos_right = Point()
        self.pin_pos_right.x = sgcomp.settings.box_width/2
        self.pin_pos_right.y = 0

        self.pin_pos_top = Point()
        self.pin_pos_top.x = 0
        self.pin_pos_top.y = 0

        self.pin_pos_bottom = Point()
        self.pin_pos_bottom.x = 0
        self.pin_pos_bottom.y = -600


        self.comp_description = None
        self.comp_keywords = None
        self.comp_datasheet = None

        self.in_component = True
        self.units_have_variant = 0

        # parse COMP ...
        items = self.line.split()

        if len(items) >= 3:

            if len(items) >= 4:
                if items[3].upper () == "FROM":
                    # todo: check num items
                    src_name = items[4]
                    src_comp = self.find_component (src_name)
                    if src_comp:
                        sgcomp = copy.deepcopy (src_comp)
                        sgcomp.is_template = False
                        sgcomp.parent = src_comp
                        # remove all aliases
                        # rename doc entry for comp
                        doc = sgcomp.doc_fields[src_name]
                        assert isinstance(doc, SgDoc)
                        sgcomp.doc_fields = {}
                        self.comp_description = doc.description
                        self.comp_keywords = doc.keywords
                        self.comp_datasheet = doc.datasheet

                        for unit in sgcomp.units:
                            unit.modified = False
                    else:
                        print("error: %s not defined in FROM: %s" % (src_name, self.line))
                        self.num_errors += 1
                elif items[3].upper () == "TEMPLATE":
                    sgcomp.is_template = True
                else:
                    print("error: expected FROM: " + self.line)
                    self.num_errors += 1
            #
            sgcomp.name = items[1]
            sgcomp.ref = items[2]

        else:
            print("error: expected COMP name ref: " + self.line)
            self.num_errors += 1

        print("Component: "+ sgcomp.name)

        # 
        self.get_next_line()

        while self.line.startswith ("%"):
            self.parse_directive(sgcomp)

        #
        while self.tokens[0].startswith ("FIELD"):

            # FIELD $FOOTPRINT value
            # FIELD NAME value
            if self.tokens[1].upper()== "$FOOTPRINT":
                field_text = after(self.line, self.tokens[1]).strip()
                sgcomp.default_footprint = field_text
            else:
                field_text = after(self.line, self.tokens[1]).strip()
                
                line = 'F%d %s 0 0 50 H I C CNN "%s"' % (len(sgcomp.user_fields), field_text, self.tokens[1])
                s = shlex.shlex(line)
                s.whitespace_split = True
                s.commenters = ''
                s.quotes = '"'
                line = list(s)
                values = line[1:] + ['' for n in range(len(Component._FN_KEYS) - len(line[1:]))] 

                sgcomp.user_fields.append (dict(zip(Component._FN_KEYS,values)))

            self.get_next_line()
    
        #
        if self.line.startswith ("FPLIST"):
            sgcomp.fplist = []
            sgcomp.fplist.extend (self.tokens[1:])

            self.get_next_line()
            
            while not self.tokens[0] in self.kw:
                sgcomp.fplist.append (self.line)
                self.get_next_line()

        # get aliases, documentation fields
        alias_name = None
       
        while self.tokens[0].upper() not in ["UNIT", "END"]:
            if self.line.startswith ("DESC"):
                self.comp_description = after (self.line, " ")
                self.get_next_line()

            elif self.line.startswith ("KEYW"):
                self.comp_keywords = after (self.line, " ")
                self.get_next_line()

            elif self.line.startswith ("DOC"):
                self.comp_datasheet = after (self.line, " ")
                self.get_next_line()

            elif self.line.startswith ("ALIAS"):
               
                name, sgdoc = self.make_doc (sgcomp, alias_name)
                sgcomp.doc_fields [name] = sgdoc
                #
                alias_name = after (self.line, " ")
                self.get_next_line()

                #self.comp_description = None
                #self.comp_keywords = None
                #self.comp_datasheet = None
            else:
                print("error: unexpected line: " + self.line)
                self.num_errors += 1
                self.get_next_line()
        # while

        name, sgdoc = self.make_doc (sgcomp, alias_name)
        sgcomp.doc_fields [name] = sgdoc

        # units

        while self.tokens[0].upper() == "UNIT":

            unit = self.parse_unit(sgcomp)

            if unit.is_derived:
                # derived_unit
                pass
            
            else:
                # new unit
                unit.is_overlay = False
                    
                if not self.regen and unit.unit_shape == "power":
                    unit.is_power_unit = True

                    if self.unit_combine == "seperate" or not self.opt_combine_power_for_single_units:
                        pass
                        # todo: is this needed?
                        #self.set_power_unit_size (sgcomp, unit)
                    
                        #sgcomp.pin_names_inside = True

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
                            print("error: no elements ? %s" % sgcomp.name)

                    # todo: is this needed?
                    #else:
                    #    # auto
                    #    self.set_power_unit_size (sgcomp, unit)                        
                else:
                    unit.is_power_unit = False

                #
                if not unit.is_overlay or self.regen:
                    sgcomp.units.append (unit)

                self.last_unit = unit
            #

        if self.line.startswith ("END"):
            self.get_next_line()
        else:
            print("error: expected END: " + self.line)
            self.num_errors += 1

        self.in_component = False

        return sgcomp

    def write_symgen_file (self, out_filename):

        outf = open (out_filename, "w")

        outf.write ("#\n" )
        outf.write ("# %s\n" % os.path.basename (out_filename) )
        outf.write ("#\n" )
        outf.write ("%%lib %s\n" % os.path.basename (out_filename) )
        outf.write ("\n" )

        global_defaults = SgSettings()

        outf.write ("#\n" )
        outf.write ("# Global Defaults\n" )
        outf.write ("#\n" )
        outf.write ("%%line %d\n" % global_defaults.box_pen )
        outf.write ("\n" )
        outf.write ("%%pinlen %d\n" % global_defaults.pin_length )
        outf.write ("%%width %d\n" % global_defaults.box_width )

        if global_defaults.box_fill == NoFill:
            outf.write ("%%fill %s\n" % "None" )
        elif global_defaults.box_fill == Foreground:
            outf.write ("%%fill %s\n" % "fore" )
        elif global_defaults.box_fill == Background:
            outf.write ("%%fill %s\n" % "back" )

        outf.write ("\n" )

        outf.write ("%%style %s\n" % self.symbol_style.name )   # is this real default?
        outf.write ("\n" )

        for comp in self.components:
            outf.write ("#\n" )
            outf.write ("# %s\n" % (comp.name))
            outf.write ("#\n" )
            outf.write ("COMP %s %s\n" % (comp.name, comp.ref))

            cur_width = global_defaults.box_width

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

    def load_footprints (self, sourcedir):

        self.footprints = []

        print("Loading footprints")
        for root, dirnames, filenames in os.walk(sourcedir):
            for filename in fnmatch.filter(filenames, '*.kicad_mod'):
                dir = os.path.split (root) [-1]
                dir = before (dir, ".")
                self.footprints.append(dir + ":" +before(filename, '.kicad_mod'))

        print("%d footprints loaded" % len(self.footprints))

    def parse_input_file (self, inp_filename):


        #TODO: option
        # "c:\github\kicad-footprints")
        if self.footprints_folder:
            self.load_footprints (self.footprints_folder) 

        self.file = open (inp_filename, 'r')
        self.get_next_line()

        self.in_component = False
        self.num_errors = 0
        self.regen = False
        self.out_path, out_filename = os.path.split (inp_filename)

        self.out_basename = os.path.splitext (out_filename)[0]

        while self.line:
            if self.line.startswith ("%"):
                self.parse_directive(None)

            elif self.line.startswith ("COMP"):
                comp = self.parse_component()

                self.components.append (comp)
            else:
                # 
                print("error: unexpected line: " + self.line)
                self.num_errors += 1
                self.get_next_line()

        #
        #
        #

        # test
        if self.regen:
            self.write_symgen_file (os.path.join (self.out_path, "test_file.txt"))

        #
        # combine power units

        #
        if self.output_format == "v5":
            generator = GenerateKicad()
        elif self.output_format == "v6":
            generator = GenerateSweetLib()
        else:
            print ("error: invalid output format : %s" % self.output_format)

        if generator:
            generator.GenerateLibrary (self)

            print("%d parse errors" % self.num_errors)
            print("%d generate errors" % generator.num_errors)

