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
import copy
import time
import hashlib
import shlex
from enum import Enum

from schlib import *
from print_color import *

from str_utils import *
from sym_drawing import *
from sym_comp import *
from sym_gates import *
from sym_iec import *

class SymbolStyle (Enum):
    # ANSI/MIL MIL-STD-806, now also IEEE Standard 91-1984 "distinctive shapes" 
    ANSI = 1
    # IEC 60617-12, now also IEEE Standard 91-1984
    IEC = 2
    # DIN 40700
    DIN = 3

class SymGen:

    verbose = False

    exit_code = 0
    num_errors = 0

    libfile = None
    docfile = None

    logic_list = []
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

    def_pin_length = 200

    def_box_width = 600
    def_box_pen = 10
    def_box_fill = "f" # background fill

    #def_logic_fill = NoFill
    def_logic_fill = Background

    def_name_offset = 20
    def_extra_offset = 40

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

    units = []
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

    # 
    ref_pos = Point()
    name_pos = Point()

    def __init__(self):
        self.kw = ['COMP', 'DESC', 'KEYW', 'DOC', 'ALIAS', 'UNIT', 'END']

        self.printer = PrintColor(True)



    def convert_to_string (self, elem):
        item=elem[1]
        keys_list = Component._DRAW_KEYS[elem[0]] # e.g 'A' -> keys of all properties of arc
        line = elem[0] + ' ' # 'arcs' -> 'A'
        for k in keys_list:
            if k == 'points':
                for i in item['points']:
                    line += '{0} '.format(i)
            else:
                line += item[k] + ' '

        line = line.rstrip()
        return line

    def create_drawing_object (self, elem):
        key = elem[0]
        params = elem[1]
        s = self.convert_to_string (elem)
        if key == 'S':
            drawing = Rect (s)
        elif key == 'C':
            drawing = Circle(s)
        elif key == 'P':
            drawing = PolyLine(s)
        elif key == 'A':
            drawing = Arc(s)
        else:
            drawing = None

        return drawing

    # convert pin orientation from KiCad directions to symgen directions
    def kicad_to_symgen_dir (self, direction):
        if direction=="R":
            return "L"
        elif direction=="L":
            return "R"
        elif direction=="U":
            return "B"
        elif direction=="D":
            return "T"

    # convert pin orientation from symgen directions to KiCad directions
    def symgen_to_kicad_dir (self, direction):
        if direction=="R":
            return "L"
        elif direction=="L":
            return "R"
        elif direction=="B":
            return "U"
        elif direction=="T":
            return "D"


    def read_ref_list(self, filename):

        data = []
        inf=open(filename)
        for line in inf:
            tokens = line.strip().split('\t')
            desc = LogicDesc (tokens)
            data.append (desc)

        return data

    def process_ref_list(self, filename, out_filename):

        inf = open(filename)
        outf = open(out_filename, "w")

        for line in inf:
            tokens = line.strip().split('\t')
            tokens[2] = self.capitalise (tokens[2])
            s = '\t'.join (tokens)
            outf.write (s + '\n')

        outf.close()
        inf.close()

    def process_list(self):

        self.process_ref_list ("../74xx/7400_logic_ref.txt", "../74xx/7400_logic_ref_new.txt")

        self.process_ref_list ("../cmos4000/4000_list.csv", "../cmos4000/4000_list_new.csv")

    def get_descriptor (self, name):
        if self.logic_list:
            for desc in self.logic_list:
                if name == desc.id:
                    return desc
        return None

    # convert kicad to symgen
    def get_pin_type (self, _type, shape):

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

    def is_positive_power (self, pin):
        name = pin['name'].upper()
        if len(name)>3 :
            name = name[0:3]
        if pin['name'].upper() in ["3.3V", "5V"] or name in ["VCC", "VDD", "V+"]:
            return True

    # other forms 5V 3.3V +5V
    def is_power_pin (self, pin):
        name = pin['name'].upper()
        if len(name)>3 :
            name = name[0:3]
        if pin['name'].upper() in ["3.3V", "5V"] or name in ["VCC", "VDD", "V+", "GND", "VSS", "VEE", "V-"]:
            return True
        elif pin['electrical_type'] in "Ww":
            return True
        else:
            return False

    def find_comp_pins (self, comp, unit):
        pins = []

        for pin in comp.pins:
            if pin['unit'] =='0' or  pin['unit'] == str(unit):
                pins.append (pin)
        return pins

    # abc 74 abc nG 123
    # abc 4nnn abc
    # abc 14nnn abc
    def parse_74xx_name (self, s):
        s = s.upper()

        prefix = ""
        match = re.match ('([A-Za-z]+)', s)
        if match:
            prefix = match.group(1)
            s = after (s, prefix)
        else:
            prefix = ""

        if s.startswith("74"):
            s = after (s, "74")
            if "G" in s:
                number = after (s, "G")
                match = re.match ('([A-Za-z]+)', before(s, "G"))
                if match:
                    family = match.group(1)
                else:
                    family = ""
                std_number = "74x" + after (s, family)
            else:
                # 74 
                # HCT 240 _PWR
                match = re.match ('([A-Za-z]+)', s)
                if match:
                    family = match.group(1)
                else:
                    family = ""
                std_number = "74" + re.sub ("[^0-9]", "", after (s, family))
        else:
            family = "4000"
            std_number = re.sub ("[^0-9]", "", s)

        return family, std_number
            
    def iso_fmt_date_time (self, _time):
        return time.strftime("%Y-%m-%d %H:%M:%S", _time)

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

    def get_checksum (self, comp, unit, variant):

        data=''
        items=[]
        for elem in comp.drawOrdered:
            if elem[0] in ['A','C','P','T']:
                items.append (elem)

        items.sort()
        for elem in items:
            item=elem[1]
            keys_list = Component._DRAW_KEYS[elem[0]]   # 'A' -> keys of all properties of arc
            line = elem[0] + ' '                        # 'arcs' -> 'A'
            for k in keys_list:
                if k == 'points':
                    for i in item['points']:
                        line += '{0} '.format(i)
                else:
                    line += item[k] + ' '
            data += line
        try:
            md5 = hashlib.md5(data.encode('utf-8'))
        except UnicodeDecodeError:
            md5 = hashlib.md5(data)
            
        checksum = md5.hexdigest()
        return checksum

    def get_bounds (self, comp, unit):
        bbs=[]
        for elem in comp.drawOrdered:
            key = elem[0]
            params = elem[1]

            if key in ['P','S','C','A']:
                if int(params['unit']) == unit and int(params['convert']) <= 1:
                    drawing = self.create_drawing_object ([key, params])
                    bbs.append (drawing.get_bounds())

        if len(bbs)==0:    
            return BoundingBox()
        else:
            return sum(bbs)

    # check for short words? : of at to for in by 
    def capitalise (self, s):
        words = s.split()
        result = ""
        is_first = True
        for word in words:
            if word.isupper():
                result += word + " "
            elif is_first or word in ["hex"] or ( word[0].isalpha and len(word)>3 and not word in ["with"] ):
                result += word[0].upper() + word[1:] + " "
            else:
                result += word + " "
            is_first = False
        return result.strip()

    def dump_lib (self, lib_filename, dump_path, ref_list_filename):

        print "Reading %s" % (lib_filename)
        lib = SchLib(lib_filename)

        keywords = {}

        #out_path, out_filename = os.path.split (dump_path)
        out_path = dump_path
        out_filename = os.path.basename (lib_filename)
        out_filename = os.path.splitext (out_filename)[0]

        dump_filename = os.path.join (out_path, out_filename + "_dump.txt")

        template_filename = os.path.join (out_path, out_filename + "_template.lib")
        template_doc_filename = os.path.join (out_path, out_filename + "_template.dcm")

        if ref_list_filename:
            print "Reading ref list %s" % (ref_list_filename)
            self.logic_list = self.read_ref_list(ref_list_filename)

        print "Extracting library %s" % (dump_filename)

        #
        self.create_empty_lib (template_filename)
        template_lib = SchLib(template_filename)
        docfile = Documentation (template_doc_filename)

        #
        def_width = 600

        outf = open (dump_filename,'w')

        outf.write ("#\n")
        outf.write ("# Generated by sym_gen.py on %s\n" % (self.iso_fmt_date_time (time.localtime())))
        outf.write ("# Source lib: %s\n" % (lib_filename))
        outf.write ("#\n")

        outf.write ("#\n")
        outf.write ("# Global Defaults\n")
        outf.write ("#\n")
        outf.write ("%%lib %s.lib\n" % out_filename)
        outf.write ("%pinlen 200\n")
        outf.write ("%width 600\n")
        outf.write ("%fill back\n")
        outf.write ("%line 10\n")
        outf.write ("%%iconlib %s\n" % os.path.basename(template_filename))
        outf.write ("%%style %s\n" % self.symbol_style.name)
        outf.write ("#\n")


        # temp
        #self.gen_comp (template_lib, docfile, "or", "U")
        ##

        for comp in lib.components:

            # look for hidden pins
            #hidden = False
            #for pin in comp.pins:
            #    if pin['pin_type'] == "N":
            #        hidden = True
            #        break
            #hidden = True


            # include all components
            
            if True:
                unique_pins = {}
                max_pin_number = 0
                for pin in comp.pins:
                    unique_pins [pin['num']] = "1"
                    if int(pin['num']) > max_pin_number: 
                        max_pin_number = int(pin['num'])

                num_units = int(comp.definition['unit_count'])

                type=""
                # look up on ref list
                #family = re.match ('[AZaz]', comp.name)
                family,std_number = self.parse_74xx_name (comp.name)

                if not family:
                    family = "Standard"

                desc = self.get_descriptor(std_number)
                #if self.symbol_style == SymbolStyle.ANSI:
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
                    elif "XNOR" in desc.description:
                        type = "XNOR"
                    elif "invert" in desc.description and not "non-invert" in desc.description: # inverter or inverting
                        type = "NOT"
                    elif "buffer" in desc.description:  # check num units, num inputs
                        type = "BUF"
                    else:
                        print "info: %s unknown type: %s" % (comp.name, desc.description)
                        self.num_errors += 1

                # todo: demorgan options?
                # power pins, unit = 0?
                # need to sort by y coord, detect gaps
                print comp.name

                outf.write ("#\n")
                outf.write ("# %s\n" % (comp.name))
                outf.write ("#\n")
                outf.write ("COMP %s %s\n" % (comp.name, comp.reference))

                # 
                j = 2
                for field in comp.fields[2:]:
                    if field['fieldname']:
                        if field['name'] and field['name'] != '""':
                            outf.write ("FIELD %s %s\n" % (field['fieldname'], field['name']))
                    else:
                        if field['name'] != '""':
                            if j==2:
                                outf.write ("FIELD $FOOTPRINT %s\n" % (field['name']))
                            else:
                                outf.write ("FIELD $DATASHEET%d %s\n" % (j, field['name']))
                            j += 1


                outf.write ("FPLIST\n")
                if len(comp.fplist) == 0:
                    if not max_pin_number in [4,14,16,20,24]:
                        print "warning: %s invalid num pins? unique=%d, max=%d" % (comp.name, len(unique_pins), max_pin_number)
                        self.num_errors += 1
                    outf.write ("DIP?%d*\n" % max_pin_number)
                else:
                    for fp in comp.fplist:
                        outf.write ("%s\n" % fp)

                # doc fields
                f_desc = None
                f_doc = None  
                f_keyw = None

                if comp.documentation:
                    descr = comp.documentation['description']
                    if descr:
                        f_desc = descr
                    elif desc:
                        f_desc = desc.description

                    f_keyw = comp.documentation['keywords']
                    if f_keyw:
                        for kw in f_keyw.split():
                            keywords [kw] = 1

                    ## todo remove invalid keywords, replace with ones from ref list

                    f_doc = comp.documentation['datasheet']
                    if f_doc is None:
                        if desc and desc.get_datasheet (family):
                            f_doc = desc.get_datasheet (family)
                elif desc:
                    f_desc = desc.description
                    
                    if len(type) > 0:
                        f_keyw = type
                        keywords [type] = 1

                    if desc.get_datasheet (family):
                        f_doc = desc.get_datasheet (family)

                #
                if f_desc:
                    outf.write ("DESC %s\n" % self.capitalise(f_desc))
                else:
                    print "info: missing DESC %s"  % (comp.name)
                if f_keyw:
                    outf.write ("KEYW %s\n" % f_keyw)
                else:
                    print "info: missing KEYW %s"  % (comp.name)
                if f_doc:
                    outf.write ("DOC %s\n" % f_doc)
                else:
                    print "info: missing DOC %s"  % (comp.name)

                # process aliases
                if len(comp.aliases) > 0:
                    # todo use desc?
                    for alias in comp.aliases.keys():
                        f_desc = None
                        f_doc = None  
                        f_keyw = None

                        outf.write ("ALIAS %s\n" % alias)
                        alias_doc = comp.aliases[alias]
                        
                        if alias_doc:
                            f_desc = alias_doc['description']

                            f_keyw = alias_doc['keywords']
                            if f_keyw:
                                for kw in f_keyw.split():
                                    keywords [kw] = 1

                            f_doc = alias_doc['datasheet']
                        #
                        if f_desc:
                            outf.write ("DESC %s\n" % self.capitalise(f_desc))
                        else:
                            print "info: missing DESC %s"  % (alias)
                        if f_keyw:
                            outf.write ("KEYW %s\n" % f_keyw)
                        else:
                            print "info: missing KEYW %s"  % (alias)
                        if f_doc:
                            outf.write ("DOC %s\n" % f_doc)
                        else:
                            print "info: missing DOC %s"  % (alias)

                #
                for pin in comp.pins:
                    pin['direction'] = self.kicad_to_symgen_dir (pin['direction'])

                #
                comments = []
                comments.append ("#\n")
                comments.append ("# " + comp.name + "\n")
                comments.append ("#\n")

                component_data = []
                component_data.append("DEF "+comp.name + " "+comp.reference+" 0 40 Y Y 1 L N")      # units are not interchangeable
                component_data.append("F0 \"U\" 0 0 50 H V C CNN")
                component_data.append("F1 \"74469\" 0 -200 50 H V C CNN")
                component_data.append("F2 \"\" 0 0 50 H I C CNN")
                component_data.append("F3 \"\" 0 0 50 H I C CNN")
                component_data.append("DRAW")
                component_data.append("ENDDRAW")
                component_data.append("ENDDEF")

                templ_comp = Component(component_data, comments, docfile)
                templ_comp.fields [0]['reference'] = comp.reference
                templ_comp.fields [1]['name'] = comp.name
                templ_comp.definition['reference'] = comp.reference
                templ_comp.definition['name'] = comp.name

                # get the graphics for this comp
                # TODO: unit, variant

                count = 0
                for d in comp.drawOrdered:
                    if d[0] in ['A','C','P','T','S']:
                        count += 1

                if comp.name=="4009":
                    print "ehhlo"

                unit_template = None
                if count > 1:
                    bb = self.get_bounds (comp, 0)

                    if bb.pmax.y != bb.height /2 :
                        offset_y = bb.height /2 - bb.pmax.y
                        offset_y = self.align_to_grid (offset_y+100, 100)
                    else:   
                        offset_y = 0

                    self.copy_icon (templ_comp, comp, 0, Point(0, offset_y))

                    # compare to template comps
                    this_sum = self.get_checksum (templ_comp, 0, 0)

                    # print "this sum "+ this_sum
                    found = False
                    for xcomp in template_lib.components:
                        lib_sum = self.get_checksum (xcomp, 0, 0)
                        # print "  lib sum "+ lib_sum
                        if lib_sum == this_sum:
                            found = True
                            print "same as " + xcomp.name
                            unit_template = xcomp.name
                            break
                    if not found:
                        # add if different
                        template_lib.addComponent (templ_comp)
                        unit_template = comp.name

                #
                # units
                bb = BoundingBox()

                bb = bb + self.get_bounds (comp, 0)

                # check pins
                for pin in comp.pins:
                    if pin['name'] != '~' and pin['name'].startswith('~') and 'I' in pin['pin_type']:
                        pin['name'] = after (pin['name'], "~")
                        print "info: double inversion %s %s %s"  % (comp.name, pin['num'], pin['name'])

                # 1..1
                # 1..2
                for unit in range (1, num_units+1):
                    
                    bb = bb + self.get_bounds (comp, unit)
                    #print "unit %d width %d" % (unit, bb.width)

                    unit_pins = self.find_comp_pins (comp, unit)
                    if unit_pins:

                        pins = []
                        for pin in unit_pins:
                            # debug
                            if pin['unit']==str(0) and num_units>1 and not self.is_power_pin (pin):
                                print "info: common pin %s %s %s"  % (comp.name, pin['num'], pin['name'])

                            if pin['convert'] in ['0','1'] and not self.is_power_pin(pin):
                                pins.append (pin)

                        if pins:
                            line = "UNIT"
                            if type:
                                line += " " + type
                            else:
                                if bb.width>0 and bb.width != def_width:
                                    line += " WIDTH %d" % (bb.width)
                                if unit_template:
                                    line += " TEMPLATE %s" % (unit_template)
                            line += '\n'

                            outf.write (line)

                            if type == "BUF":
                                print "ehhlo"

                            # sort by y pos
                            for passnum in range(len(pins)-1,0,-1):
                                for i in range(passnum):
                                    if int(pins[i]['posy']) < int(pins[i+1]['posy']):
                                        temp = pins[i]
                                        pins[i] = pins[i+1]
                                        pins[i+1] = temp

                            max_y = -99999
                            for pin in pins:
                                if pin['direction'] in ['L','R']:
                                    if int(pin['posy']) > max_y:
                                        max_y = int(pin['posy'])

                            # look for horiz pins
                            for _dir in ['L','R']:
                                cur_y = max_y
                                for pin in pins:
                                    if pin['direction'] == _dir:
                                        py = int(pin['posy'])    
                                        while cur_y > py + 100:
                                            outf.write ("SPC %s\n" % _dir)
                                            cur_y -= 100
                                        outf.write ("%s %s %s %s\n" % (pin['num'],pin['name'],self.get_pin_type(pin['electrical_type'],pin['pin_type']),pin['direction']))
                                        cur_y = py

                            # sort by x pos
                            for passnum in range(len(pins)-1,0,-1):
                                for i in range(passnum):
                                    if int(pins[i]['posx']) < int(pins[i+1]['posx']):
                                        temp = pins[i]
                                        pins[i] = pins[i+1]
                                        pins[i+1] = temp

                            # look for vert pins
                            for _dir in ['T','B']:
                                first = True
                                for pin in pins:
                                    if pin['direction'] == _dir:
                                        if first:
                                            cur_x = int(pin['posx'])
                                            first = False
                                        px = int(pin['posx'])    
                                        while cur_x < px:
                                            outf.write ("SPC %s\n" % _dir)
                                            cur_x += 100
                                        outf.write ("%s %s %s %s\n" % (pin['num'],pin['name'],self.get_pin_type(pin['electrical_type'],pin['pin_type']),pin['direction']))
                                        cur_x = px

                # now look for power pins
                pins = []
                pin_map = {}
                for pin in comp.pins:
                    if self.is_power_pin(pin) and not pin['num'] in pin_map:
                        pins.append(pin)
                        pin_map [pin['num']] = 1

                # sort by pin number
                for passnum in range(len(pins)-1,0,-1):
                    for i in range(passnum):
                        if int(pins[i]['num']) > int(pins[i+1]['num']):
                            temp = pins[i]
                            pins[i] = pins[i+1]
                            pins[i+1] = temp

                outf.write ("UNIT PWR\n")
                for pin in pins:
                    if self.is_positive_power (pin):
                        pin['direction'] = "T"
                    else:
                        pin['direction'] = "B"
                    # type may be power out?
                    # upper case name?
                    outf.write ("%s %s %s %s\n" % (pin['num'],pin['name'].upper(),"PI",pin['direction']))

                outf.write ("END\n")

        outf.close()

        kw_filename = os.path.join (out_path, out_filename + "_key.txt")

        outf = open (kw_filename,'w')
        for kw in sorted(keywords):
            outf.write (kw + "\n")
        outf.close()

        #
        template_lib.save ()

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
            if pin.orientation == direction and pin.visible and (type is None or pin.type == type):
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
                pin.orientation = self.symgen_to_kicad_dir (pin.orientation)
                pin.group_id = group_id

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
                pin.orientation = self.symgen_to_kicad_dir (pin.orientation)

                pin.group_id = group_id
                pins.append (pin)
                
                if group:
                    group.pins.append (pin)
        #end while

        return pins




    ##
    def align_to_grid (self, val, grid_size):
        return int (val/grid_size) * grid_size
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

    def get_fill (self, fill, style):
        if fill != Background:
            return fill 
        else:
            if style:
                return style.fill
            else:
                return fill

    def copy_icon (self, comp, comp_icon, unit, pos, variant=0, src_unit=0, src_variant=1, style = None):
    
        # TODO: source unit
        # pensize, fill?

        for p in comp_icon.draw['arcs']:
            # TODO apply offset pos
            item = dict(p)
            if item['convert'] == str(src_variant) or item['convert'] == '0':
                item ['unit'] = str(unit)
                item ['convert'] = str(variant)
                item ['posy'] = str(int(item ['posy']) + pos.y)
                item ['starty'] = str(int(item ['starty']) + pos.y)
                item ['endy'] = str(int(item ['endy']) + pos.y)
                item['fill'] = self.get_fill (item['fill'], style)
                comp.drawOrdered.append (['A', item])
    
        for p in comp_icon.draw['circles']:
            item = copy.deepcopy(p)
            if item['convert'] == str(src_variant) or item['convert'] == '0':
                item ['unit'] = str(unit)
                item ['convert'] = str(variant)
                item ['posy'] = str(int(item ['posy']) + pos.y)
                item['fill'] = self.get_fill (item['fill'], style)
                comp.drawOrdered.append (['C', item])

        for p in comp_icon.draw['polylines']:
            item = dict(p)
            if item['convert'] == str(src_variant) or item['convert'] == '0':
                poly = PolyLine (self.convert_to_string(['P',p]))
                poly.unit = unit
                poly.demorgan = variant
                poly.fill = self.get_fill (item['fill'], style)
                for pt in poly.points:
                    pt.x += pos.x    
                    pt.y += pos.y    
                comp.drawOrdered.append (poly.get_element())

        for p in comp_icon.draw['rectangles']:
            # TODO apply offset pos
            item = dict(p)
            if item['convert'] == str(src_variant) or item['convert'] == '0':
                rect = Rect()
                rect.unit = unit
                rect.demorgan = variant
                rect.fill = self.get_fill (item['fill'], style)
                rect.p1 = Point(int(item['startx']), int(item['starty'])).Add(pos)
                rect.p2 = Point(int(item['endx']), int(item['endy'])).Add(pos)
                comp.drawOrdered.append (rect.get_element())

        for p in comp_icon.draw['texts']:
            item = copy.deepcopy(p)
            if item['convert'] == str(src_variant) or item['convert'] == '0':
                item ['unit'] = str(unit)
                item ['convert'] = str(variant)
                item ['posy'] = str(int(item ['posy']) + pos.y)
                comp.drawOrdered.append (['T',item])

    def parse_fill (self, token):
        if token in ["F", "f", "N"]:
            return token
        elif token.startswith ("f"):
            return "F"
        elif token.startswith ("b"):
            return "f"
        elif token.startswith ("n"):
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

            if tok == "ANSI":
                self.symbol_style = SymbolStyle.ANSI
            elif tok == "IEC":
                self.symbol_style = SymbolStyle.IEC
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

    def create_empty_lib (self, filename):

        basename = os.path.splitext (filename)[0]

        infile = open (basename+".lib", 'w')
        infile.write ("EESchema-LIBRARY Version 2.3\n")
        infile.write ("#encoding utf-8\n")
        infile.write ("#\n")
        infile.write ("#End Library\n")
        infile.close()

        infile = open (basename+".dcm", 'w')
        infile.write ("EESchema-DOCLIB  Version 2.0\n")
        infile.write ("#\n")
        infile.write ("#\n")
        infile.write ("#End Doc Library\n")
        infile.close()


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

        y_offset = self.align_to_grid (unit.unit_rect.size.y / 2, 50)

        if len(left_pins) + len(right_pins) > 0 :
            # align to horiz pins
            y = bb_horiz.pmax.y
            while (y+y_offset) % 100 != 0:
                y_offset += 50
        return y_offset

    def parse_unit (self, comp):
        unit = IecSymbol()

        # new unit

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
        unit_combine = "auto"

        unit.vert_margin = 200
                
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
                unit_combine = "seperate"
            elif token.startswith("COMB"):
                unit_combine = "combine"

            elif token.startswith("W"):
                j += 1
                self.box_width = int(tokens[j])

            elif token.startswith("TEMP"):
                j += 1
                unit.template = tokens[j]
                unit.unit_shape = "none"
                self.last_shape = unit.unit_shape

            elif token.startswith("ICON"):
                self.last_shape = unit.unit_shape
                unit.icons = []
                while j < len(tokens)-1:
                    j += 1
                    unit.icons.append(tokens[j])
            else:
                print "error : unknown parameter %s in UNIT" % token
                self.num_errors += 1
            j += 1

        # 
        #self.get_next_line()

        if unit.unit_shape != self.last_shape:
            unit.icons = []
            unit.template = None

        self.last_shape = unit.unit_shape

        if len(unit.icons) == 0 and unit.template:
            unit.icons.append(unit.template)


        unit.is_overlay = False
        if unit.unit_shape == "power":
            unit.is_power_unit = True

            if unit_combine == "seperate":
                self.box_width = 400
                self.box_height = self.max_height
                unit.unit_shape = "box"
            # this relies on pwr unit being last unit...
            elif self.opt_combine_power_for_single_units and self.unit_num==2 or unit_combine=="combine":
                unit.unit_shape = "none"
                unit.is_overlay = True
                self.unit_num = self.unit_num - 1

                self.pin_pos_top.y    = self.last_unit.unit_rect.top()
                self.pin_pos_bottom.y = self.last_unit.unit_rect.bottom()

            else:
                self.box_width = 400
                self.box_height = self.max_height
                unit.unit_shape = "box"
        else:
            unit.is_power_unit = False

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

        self.get_next_line()
        tokens = self.line.split()

        if comp.name == "4017":
            print "oop"

        while tokens[0].upper() not in ['UNIT','END']:
            element = self.parse_element (unit.unit_shape)
            unit.elements.append (element)
            tokens = self.line.split()

        # ===============================================================================
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
                    elem_height = self.draw_element (unit, element, comp, self.unit_num, variant + self.units_have_variant)

                self.cur_pos.y -= elem_height

            if not unit.is_overlay:
                offset = Point()
                # offset.y = self.align_to_grid (unit.unit_rect.size.y/2, 100)
                offset.y = self.align_unit (unit)
                self.move_items (comp, self.unit_num, offset)
                unit.unit_rect.pos.y = offset.y
                # move labels?
                self.set_label_pos(unit)
            else:
                self.set_label_pos(self.last_unit) # ??

        elif unit.unit_shape in ["and", "nand", "or", "nor", "xor", "xnor", "not", "buffer"]:

            #
            # pins
            temp = self.pin_length
            self.pin_length = 150

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
            for pin in unit_pins:
                if pin.is_input():
                    num_inputs+=1
                if pin.is_output():
                    num_outputs+=1
            #num_outputs = len(unit_pins) - num_inputs

            if num_inputs != len(unit_pins) - num_outputs:
                print "error: wrong number of input pins: expected %d got %d" % (len(unit_pins)-1, num_inputs)
                self.num_errors += 1
                #continue

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
                gatedef.fill = self.logic_fill
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

                    self.max_height = 500
                    
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
                            style.fill = self.logic_fill
                            style.pensize = self.box_pen
                            self.copy_icon (comp, comp_icon, self.unit_num, gatedef.get_center(), style=style)
                        else:
                            print "error: unknown icon %s " % icon_name 
                            self.num_errors += 1

                j=0
                for pin in unit_pins:
                    if pin.is_input() and j<len(inputs_pos):
                        pin.length = self.pin_length + gatedef.offsets[j]
                        pin.unit = self.unit_num
                        pin.demorgan = variant + demorgan
            
                        if unit.unit_shape == "buffer" and j==1:
                            dy = self.align_to_grid(abs(inputs_pos[j].y)+99, 100)
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

                j = 0
                for pin in unit_pins:
                    if pin.is_output():
                        pin.length = self.pin_length
                        pin.unit = self.unit_num
                        pin.demorgan = variant + demorgan
                        pin.orientation = "L"
                        if j==0:
                            pin.shape = output_shape
                        else:
                            pin.shape = "I" if output_shape == " " else " "

                        pin.pos.x = outputs_pos[j].x + self.pin_length
                        pin.pos.y = outputs_pos[j].y       
                        j += 1
                        #pins.append (pin)
                        comp.drawOrdered.append( pin.get_element () )

                        # pin text
                        if pin.qualifiers:
                            self.draw_pin_text (comp, self.unit_num, pin, pin.qualifiers)

            ##
            self.pin_length = temp

        else:
            print "error: unknown shape: " + tokens[1]
            self.num_errors += 1

            #todo : parse unit
            #self.get_pins()
        #

        comp.fields [0]['posx'] = str(self.ref_pos.x)
        comp.fields [0]['posy'] = str(self.ref_pos.y)

        comp.fields [1]['posx'] = str(self.name_pos.x)
        comp.fields [1]['posy'] = str(self.name_pos.y)

        self.last_unit = unit
        return unit

    def draw_pin_text (self, comp, unit, pin, text):
        
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

        self.draw_text (comp, unit, pos, text, fontsize)

    def get_chars (self, text):
        list = []

        while len(text)>0:
            if text.startswith ("&"):
                tok = before (text, ";")
                text = after (text, ";")
                list.append (tok+";")
            else:
                list.append (text[0])
                text = text[1:]
                
        return list

    def draw_text (self, comp, unit, pos, s, fontsize):

        chars = self.get_chars (s)
        for char in chars :
            if char == "&xdtri;":
                # white down-pointing triangle
                # unicode U+025BD
                poly = PolyLine ()
                poly.unit = unit
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
                circle.pensize = 0
                comp.drawOrdered.append( circle.get_element() )
                pos.x += fontsize + 10
            elif char == "&st;":
                # schmitt trigger
                poly = PolyLine ()
                poly.unit = unit
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
                text = Text()        
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
                text.value = char
                text.unit = unit
                text.pos = pos
                text.horiz_alignment="L"
                text.vert_alignment="B"
                comp.drawOrdered.append (text.get_element())
                pos.x += fontsize + 10


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

    def draw_element (self, xunit, element, comp, unit, variant):

        left_pins = self.find_pins (element.pins, "R")
        right_pins = self.find_pins (element.pins, "L")

        top_pins = self.find_pins (element.pins, "D")
        bottom_pins = self.find_pins (element.pins, "U")

        xunit.unit_rect.pos.x = -self.box_width/2
        xunit.unit_rect.size.x = self.box_width

        box_size = Point ()
        box_size.x = self.box_width
        box_size.y = max (len(left_pins), len(right_pins)) * 100

        if box_size.y == 0:
            box_size.y = 100

            if xunit.is_power_unit:
                box_size.y = self.box_height
                if self.pin_length % 100 == 0:
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
                if self.pin_length == 150:
                    top_margin = 0
                else:
                    top_margin = 50                    

        if len(bottom_pins) > 0:
            min_size += 200

        box_size.y = max (box_size.y + top_margin, min_size)

        #
        xunit.unit_rect.size.y = -self.cur_pos.y + box_size.y 

        #offset = Point (0,50)

        # draw element outline
        if element.shape == "box":
            rect = Rect()
            rect.p1.x = -box_size.x/2
            rect.p1.y = self.cur_pos.y + top_margin

            rect.p2.x = box_size.x/2
            rect.p2.y = self.cur_pos.y - box_size.y

            rect.unit = unit
            rect.demorgan = variant
            rect.fill = self.box_fill
            rect.pensize = self.box_pen
            comp.drawOrdered.append( rect.get_element() )

        elif element.shape == "control":
            poly = PolyLine ()
            poly.unit = unit
            poly.demorgan = variant
            poly.fill = self.box_fill
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
            
            self.draw_text (comp, unit, pos, element.label, fontsize)



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

        for pin in element.pins:
            if pin.orientation == 'R':
                pin.pos.y = self.pin_pos_left.y
                self.pin_pos_left.y -= 100
            elif pin.orientation == 'L':
                pin.pos.y = self.pin_pos_right.y
                self.pin_pos_right.y -= 100

                if pin.type == "T":
                    self.draw_pin_text (comp, unit, pin, "&xdtri;")
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

            if pin.qualifiers:
                self.draw_pin_text (comp, unit, pin, pin.qualifiers)

            pin.unit = unit
            pin.demorgan = variant
            if pin.type != " ":
                comp.drawOrdered.append( pin.get_element() )

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
                self.draw_text (comp, unit, pos, type_text, 50)
                offset = 50
            else:
                offset = 10

            if group.qualifiers:
                pos.x = group_pos.x + group_size.x - len(self.get_chars(group.qualifiers)) * 50 - 25
                pos.y = group_pos.y - group_size.y/2 - 25
                self.draw_text (comp, unit, pos, group.qualifiers, 50)
            
            if group.label:
                pos.x = group_pos.x + group_size.x + offset
                pos.y = group_pos.y - group_size.y/2 - 25
                self.draw_text (comp, unit, pos, group.label, 50)

        # add icons
        if self.icon_lib and len(xunit.icons)>0:
            k=0
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
                        style.fill = self.box_fill
                    else:
                        style.fill = self.logic_fill
                    style.pensize = self.box_pen
                    self.copy_icon (comp, comp_icon, unit, Point(0, y_pos -k * 150 + icons_y_extent/2), style=style)
                    k += 1
                else:
                    print "error: unknown icon %s " % icon_name
                    self.num_errors += 1

        #
        if self.label_style == "floating":
            self.max_height = max (self.max_height, xunit.unit_rect.size.y)
    
            if xunit.unit_shape == "box":
                margin = 50
            else:
                margin = 50 # ??

            y = 0 + margin
            if y > self.ref_pos.y:
                self.ref_pos.x = -box_size.x/2
                self.ref_pos.y = y

            y = -xunit.unit_rect.size.y - margin
            if y < self.name_pos.y:
                self.name_pos.x = -box_size.x/2
                self.name_pos.y = y
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
                    poly = PolyLine (self.convert_to_string(elem))
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
    
    def parse_input_file (self, inp_filename):

        self.out_path, out_filename = os.path.split (inp_filename)
        out_basename = os.path.splitext (out_filename)[0]

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

        self.file = open (inp_filename, 'r')
        self.get_next_line()

        self.in_component = False
        self.num_errors = 0

        while self.line:
            if self.line.startswith ("%"):
                self.parse_directive()

            elif self.line.startswith ("COMP"):
                items = self.line.split()

                if len(items) >= 3:
                    name = items[1]
                    ref = items[2]
                else:
                    print "error: expected COMP name ref: " + self.line
                    self.num_errors += 1

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

                comp = Component(component_data, comments, self.documentation)
                comp.fields [0]['reference'] = ref
                comp.fields [1]['name'] = name
                comp.definition['reference'] = ref
                comp.definition['name'] = name

                comp.definition['text_offset'] = str(self.def_name_offset)
                

                print "Component: "+ name

                desc = self.get_descriptor(re.sub('[^0-9]', '', name))
                if desc:
                    print "found %s" % desc.description

                # reset all current vars

                #pins = []
                self.unit_num = 0
                # template = None
                self.last_shape = None

                #self.unit_shape = None
                #self.icons = []

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

                #
                tokens = self.line.split()
                while tokens[0].startswith ("FIELD"):

                    if tokens[1].upper()== "$FOOTPRINT":
                        field_text = after(self.line, tokens[1]).strip()
                        comp.fields [2]['name'] = field_text
                    else:
                        field_text = after(self.line, tokens[1]).strip()
                        line = 'F%d %s 0 0 50 H I C CNN "%s"' % (len(comp.fields), field_text, tokens[1])
                        s = shlex.shlex(line)
                        s.whitespace_split = True
                        s.commenters = ''
                        s.quotes = '"'
                        line = list(s)
                        values = line[1:] + ['' for n in range(len(Component._FN_KEYS) - len(line[1:]))] 
                        comp.fields.append(dict(zip(Component._FN_KEYS,values)))

                    self.get_next_line()
                    tokens = self.line.split()
    
                #
                if self.line.startswith ("FPLIST"):
                    self.get_next_line()
                    tokens = self.line.split()
        
                    while not tokens[0] in self.kw:
                        comp.fplist.append (self.line)
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
                        self.add_doc(comp, alias_name)
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
                self.add_doc(comp, alias_name)

                # units

                while tokens[0].upper() == "UNIT":

                    unit = self.parse_unit(comp)
                    tokens = self.line.split()

                if self.line.startswith ("END"):
                    self.get_next_line()
                else:
                    print "error: expected END: " + self.line
                    self.num_errors += 1

                # draw units

                values = []
                values.append (name)
                values.append (ref)
                values.append ("0")     # not used
                values.append ("40")    # text offset
                values.append ("Y")     # draw pin number    
                values.append ("Y")     # draw pin name
                values.append (str(self.unit_num))   # unit count
                values.append ("L")     # L=units are not interchangeable
                values.append ("N")     # option flag ( Normal or Power)
                # comp.definition = dict(zip(Component._DEF_KEYS, values))
                comp.definition['unit_count'] = str(self.unit_num)

                cur_comp = self.lib.getComponentByName(comp.name)
    
                if cur_comp:
                    print "replacing: " + comp.name
                    self.lib.removeComponent (comp.name)
                else:
                    print "adding: " + comp.name
        
                self.lib.addComponent (comp)
            else:
                # 
                print "error: unexpected line: " + self.line
                self.num_errors += 1
                self.get_next_line()
    


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
symgen.process_list()

if args.dump:
    # -d --lib C:\git_bobc\kicad-library\library\74xx.lib --ref ..\74xx\7400_logic_ref.txt
    if not args.lib:
        ExitError("error: library name not supplied (need --lib)")

    lib_filename = args.lib
    dump_path = ""
    symgen.dump_lib (lib_filename, dump_path, args.ref)
else:
    # --inp 74xx.txt
    if not args.inp:
        ExitError("error: symgen script file not supplied (need --inp)")

    file = args.inp

    symgen.parse_input_file (file)


