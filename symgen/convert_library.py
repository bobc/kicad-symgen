#!/usr/bin/env python

# -*- coding: utf-8 -*-

"""
 Generate symgen script from library
 
 Copyright Bob Cousins 2020

 Licensed under GPLv3

"""

import os, sys
#import time
import re

# kicad lib utils
common = os.path.abspath(os.path.join(sys.path[0], 'common'))
if not common in sys.path:
    sys.path.append(common)

# v6 schlib
from kicad_sym import *

from str_utils import *
#from schlib import *

#todo: v5
from sym_utils_v6 import *


def alphanum (s):
    convert = lambda text: int(text) if text.isdigit() else text.rjust(3, '@')
    #parts = [ convert(c) for c in re.split('([-+]?[0-9]*\.?[0-9]*)', s) ]
    parts = [ convert(c) for c in re.split('([0-9]*)', s) ]
    return parts

def sort_num(pin):
    return int (pin.number)

def sort_name_num(pin):
    return pin.name, alphanum (pin.number)

def sort_human(l):
    convert = lambda text: float(text) if text.isdigit() else text
    alphanum = lambda key: [ convert(c) for c in re.split('([-+]?[0-9]*\.?[0-9]*)', key) ]
    l.sort( key=alphanum )
    return l


class ConvertLibrary:

    logic_list = []

    def __init__(self):
        self.num_errors = 0

        # conversion options
        self.auto_width = False
        self.squash_gaps = False

        self.use_templates = True
        self.separate_power_unit = True
        self.alternate_names = True

        self.label_style = ls_floating
        self.symbol_style = SymbolStyle.ANSI

    def get_descriptor (self, name):
        if self.logic_list:
            for desc in self.logic_list:
                if name == desc.id:
                    return desc
        return None

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

    def get_pin (self, pins, number):

        for pin in pins:
            if pin.number == str(number):
                return pin

        pin = Pin()
        pin.name = "NC"
        pin.number = str(number)
        pin.shape = "line"
        pin.etype = "unconnected"
        return pin

    def filter_pins (self, pins, direction):
        l = []
        for pin in pins:
            if pin.direction in direction:
                l.append (pin)
        return l

    def get_clean_name (self, name):
        return name.replace ( "/", "_")

    def get_property_value (self, comp, property_name):
        prop = [x for x in comp.properties if x.name == property_name]

        if prop:
            return prop[0].value
        else:
            return None

    def output_component_header (self, outf, name, reference, pin_len, comp, f_desc, f_keyw, f_doc, is_derived):

        # remove illegal chars
        clean_name = self.get_clean_name (name)

        if clean_name != name:
            print("warning: %s contains illegal chars, converted to %s" % (name, clean_name))

        outf.write ("#\n")
        outf.write ("# %s\n" % (clean_name))
        outf.write ("#\n")
        outf.write ("COMP %s %s" % (clean_name, reference))
        if comp.extends:
            outf.write (" FROM {}".format (self.get_clean_name (comp.extends)))
        elif is_derived:
            outf.write (" FROM {}".format (self.get_clean_name (comp.name)))
        outf.write ("\n")

        if not self.opt_force_pinlen and pin_len != self.def_pin_len:
            outf.write ("%%pinlen %d\n" % (pin_len))

        # TODO: need to repeat these ?
        for field in comp.properties:
            if field.name.startswith ("ki_") or field.name in ['Datasheet', 'Reference', 'Value']:
                pass
            elif field.name == "Footprint":
                if field.value:
                    outf.write ("FIELD $FOOTPRINT %s\n" % (field.value))
            else:
                outf.write ("FIELD %s %s\n" % (field.name, field.value))

        if comp.fplist:
            #outf.write ("FPLIST %s\n" % comp.fplist)

            outf.write ("FPLIST\n")
            if '\\n' in comp.fplist:
                fplist = comp.fplist.split('\\n')
            else:
                fplist = comp.fplist.split()
            for fp in fplist:
                outf.write ("%s\n" % fp)
            #outf.write ("\n")

        # doc fields

        if f_desc:
            outf.write ("DESC %s\n" % capitalise(f_desc))
                
        if f_keyw:
            outf.write ("KEYW %s\n" % f_keyw)
                
        if f_doc:
            outf.write ("DOC %s\n" % f_doc)
        #

    def dump_lib (self, lib_filename, dump_path, ref_list_filename):

        print("Reading %s" % (lib_filename))
        lib = KicadLibrary.from_file(lib_filename)

        self.opt_force_pinlen = False
        
        keywords = {}

        #out_path, out_filename = os.path.split (dump_path)
        out_path = dump_path
        out_filename = os.path.basename (lib_filename)
        out_filename = os.path.splitext (out_filename)[0]

        dump_filename = os.path.join (out_path, out_filename + ".txt")

        template_filename = os.path.join (out_path, out_filename + "_template.kicad_sym")

        if ref_list_filename:
            print("Reading ref list %s" % (ref_list_filename))
            self.logic_list = read_ref_list(ref_list_filename)

        print("Extracting library %s" % (dump_filename))

        #
        if self.use_templates:
            #create_empty_lib (template_filename)
            template_lib = KicadLibrary(template_filename)



        #
        if self.auto_width:
            def_width = 0
        else:
            def_width = 600

        #def_pin_len = 150
        self.def_pin_len = 100

        outf = open (dump_filename,'w')

        outf.write ("#\n")
        outf.write ("# Generated by sym_gen.py on %s\n" % (iso_fmt_date_time (time.localtime())))
        outf.write ("# Source lib: %s\n" % (lib_filename))
        outf.write ("#\n")

        outf.write ("#\n")
        outf.write ("# Global Defaults\n")
        outf.write ("#\n")
        outf.write ("%%lib %s.lib\n" % out_filename)
        outf.write ("%%pinlen %d\n" % self.def_pin_len)
        outf.write ("%%width %s\n" % ("auto" if self.auto_width else def_width ) )
        outf.write ("%fill back\n")
        outf.write ("%line 10\n")
        if self.use_templates:
            outf.write ("%%iconlib %s\n" % os.path.basename(template_filename))
        outf.write ("%%style %s\n" % self.symbol_style.name)
        if self.label_style == ls_center:
            outf.write ("%%label_style %s\n" % self.label_style)
        outf.write ("#\n")


        # temp
        #self.gen_comp (template_lib, docfile, "or", "U")
        ##

        for comp in lib.symbols:

            # look for hidden pins
            #hidden = False
            #for pin in comp.pins:
            #    if pin.shape == "N":
            #        hidden = True
            #        break
            #hidden = True


            # include all components
            
            if True:
                for pin in comp.pins:
                    pin.direction = kicad_to_symgen_dir (pin.get_direction()) ## todo:
                    pin.posx = mm_to_mil (pin.posx)
                    pin.posy = mm_to_mil (pin.posy)
                    pin.length = mm_to_mil (pin.length)


                unique_pins = {}

                max_pin_number = 0
                for pin in comp.pins:
                    unique_pins [pin.number] = "1"

                    if max_pin_number != -1:
                        if pin.number.isdigit():
                            if int(pin.number) > max_pin_number: 
                                max_pin_number = int(pin.number)
                        else:
                            max_pin_number = -1

                    pin_len = pin.length

                # todo: shorter pins?
                if len(comp.pins) < 100:
                    pin_len = 100
                elif len(comp.pins) < 1000:
                    pin_len = 150
                else:
                    pin_len = 200

                num_units = max (1, int(comp.unit_count))

                type=""
                # look up on ref list
                #family = re.match ('[AZaz]', comp.name)
                family,std_number = self.parse_74xx_name (comp.name)

                if not family:
                    family = "Standard"

                desc = self.get_descriptor(std_number)
                #if self.symbol_style == SymbolStyle.ANSI:
                description = ""
                if desc:
                    description = desc.description

                else:
                    description = self.get_property_value(comp, "ki_description")

                if description:
                    if "NAND" in description:
                        type = "NAND"
                    elif " AND" in description or "AND " in description:
                        type = "AND"
                    elif "NOR" in description:
                        type = "NOR"
                    elif "XNOR" in description:
                        type = "XNOR"
                    elif "XOR" in description:
                        type = "XOR"
                    elif " OR" in description or "OR " in description:
                        type = "OR"
                    elif "invert" in description.lower() and not "non-invert" in description.lower(): # inverter or inverting
                        type = "NOT"
                    elif "buffer" in description.lower():  # check num units, num inputs
                        type = "BUF"
                    else:
                        pass
                        #print("info: %s unknown type: %s" % (comp.name, description))
                        #self.num_errors += 1

                # todo: demorgan options?
                # power pins, unit = 0?
                # need to sort by y coord, detect gaps
                print(comp.name)

                #
                #
                #


                # auto select?
                pin_len = min (pin_len, 300)

                # 
                footprint = self.get_property_value(comp, "Footprint")
                if footprint is None:
                    footprint = ""

                comp.fplist = self.get_property_value(comp, "ki_fp_filters")
                if not comp.fplist and comp.pins:
                    if max_pin_number != -1: 
                        if max_pin_number != len(unique_pins):
                            print("warning: %s invalid num pins? unique=%d, max=%d" % (comp.name, len(unique_pins), max_pin_number))
                            self.num_errors += 1

                        elif not max_pin_number in [4,6,8,14,16,20,24,28,32,40,44,48,64,68,80,84,100,144]:
                            print("warning: %s invalid num pins? num=%d" % (comp.name, len(unique_pins)))
                            self.num_errors += 1

                    #outf.write ("DIP?%d*\n" % max_pin_number)

                # doc fields
                f_desc = None
                f_doc = None  
                f_keyw = None

                prop = self.get_property_value(comp, "ki_description")

                if prop:
                    f_desc = prop

                    f_keyw = self.get_property_value(comp, "ki_keywords")
                    if f_keyw:
                        for kw in f_keyw.split():
                            keywords [kw] = 1

                    ## todo remove invalid keywords, replace with ones from ref list

                    f_doc = self.get_property_value(comp, "Datasheet")
                    if not f_doc:
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
                if not f_desc:
                    print("info: missing DESC %s"  % (comp.name))
                if not f_keyw:
                    print("info: missing KEYW %s"  % (comp.name))
                if not f_doc:
                    print("info: missing DOC %s"  % (comp.name))

                #
                #
                #
                prop = self.get_property_value(comp, "Reference")
                if prop:
                    reference = prop
                else:
                    reference = ""

                self.output_component_header (outf, comp.name, reference, pin_len, comp, f_desc, f_keyw, f_doc, comp.extends)

                #
                #
                unit_template = None
                if self.use_templates and not type:

                    # get the graphics for this comp
                    # TODO: unit, variant

                    count = 0
                    count += len([x for x in comp.rectangles if x.unit<=1]) 
                    count += len([x for x in comp.circles if x.unit<=1]) 
                    count += len([x for x in comp.arcs if x.unit<=1]) 
                    count += len([x for x in comp.polylines if x.unit<=1]) 
                    count += len([x for x in comp.texts if x.unit<=1]) 

                    if count > 1:
                        templ_comp = KicadSymbol.new (comp.name, reference)
                        templ_comp.libname = out_filename + "_template"

                        bb = get_bounds_v6 (comp, 0)

                        if bb.pmax.y != bb.height /2 :
                            offset_y = bb.height /2 - bb.pmax.y
                            offset_y = align_to_grid (offset_y+100, 100)
                        else:   
                            offset_y = 0

                        copy_icon_v6 (templ_comp, comp, Point(0, offset_y), dest_unit=1, variant=1, src_unit=1, src_variant=1)
                        templ_comp.unit_count = 1
                        templ_comp.demorgan_count = 1

                        # compare to template comps
                        this_sum = get_checksum (templ_comp, 0, 0)

                        # print "this sum "+ this_sum
                        found = False
                        for xcomp in template_lib.symbols:
                            lib_sum = get_checksum (xcomp, 0, 0)
                            # print "  lib sum "+ lib_sum
                            if lib_sum == this_sum:
                                found = True
                                print(" same as " + xcomp.name)
                                unit_template = xcomp.name
                                break
                        if not found:
                            # add if different
                            print(" new template " + templ_comp.name)
                            template_lib.symbols.append(templ_comp)
                            unit_template = comp.name

                #
                # units
                bb = BoundingBox()

                bb = bb + get_bounds_v6 (comp, 0)

                # check pins
                for pin in comp.pins:
                    if pin.name != '~' and pin.name.startswith('~') and 'invert' in pin.shape:
                        pin.name = after (pin.name, "~")
                        print("info: double inversion %s %s %s"  % (comp.name, pin.number, pin.name))

                    if 'invert' in pin.shape and not pin.name == "~":
                        if pin.shape == "inverted":
                            pin.shape = "line"
                        elif pin.shape == "inverted_clock":
                            pin.shape = "clock"

                        if not pin.name.startswith('~'):
                            pin.name = "~" + pin.name

                if (footprint.find("DIP") != -1 or footprint.find("DIL") != -1 or
                        footprint.find("SOIC") != -1 or
                        footprint.find("SOP") != -1) :
                    package = "dip"
                elif (footprint.find("QFP") != -1 or footprint.find("QFN") != -1) :
                    package = "quad"
                else:
                    package = None

                if self.symbol_style == SymbolStyle.PHYSICAL and package:
                    max_len = 0
                    pins = []
                    for pin in comp.pins:
                        pins.append (pin)
                        pin.name = re.sub ("\(.*\)", "", pin.name)
                        if len(pin.name) * 50 > max_len:
                            max_len = len(pin.name) * 50

                    max_len += 50

                    bb = bb + get_bounds (comp, 1)

                    # sort by pin number
                    pins = sorted (pins, key=sort_num)

                    width = max_len * 2
                    #width = bb.width

                    if package == "quad":
                        width = (max_pin_number/4 + 2) * 100

                    line = "UNIT"
                    if width > 0 and width != def_width:
                        line += " WIDTH %d" % (width)
                    if unit_template:
                        line += " TEMPLATE %s" % (unit_template)
                    line += '\n'
                    outf.write (line)

                    if package == "dip":
                        for j in range(len(pins)/2):
                            pin = self.get_pin (pins, j+1)
                            # strip ()
                            outf.write ("%s %s %s %s\n" % (pin.number,pin.name, get_pin_type_v6(pin),"L"))

                        j = 0
                        while j < len(pins)/2:
                            pin = pins[len(pins)-j-1]
                            outf.write ("%s %s %s %s\n" % (pin.number,pin.name, get_pin_type_v6(pin),"R"))
                            j += 1
                    else:
                        pins_per_side = max_pin_number/4

                        # left side
                        outf.write ("SPC L\n")
                        j = 0
                        while j < pins_per_side:
                            pin = self.get_pin (pins, j+1)
                            outf.write ("%s %s %s %s\n" % (pin.number,pin.name, get_pin_type_v6(pin),"L"))
                            j += 1
                        outf.write ("SPC L\n")

                        # bottom side
                        j = 0
                        while j < pins_per_side:
                            pin = self.get_pin (pins, j + pins_per_side+1)
                            outf.write ("%s %s %s %s\n" % (pin.number,pin.name, get_pin_type_v6(pin),"BC"))
                            j += 1

                        # right side
                        j = 0
                        outf.write ("SPC R\n")
                        while j < pins_per_side:
                            pin = self.get_pin (pins, pins_per_side-j + pins_per_side*2)
                            outf.write ("%s %s %s %s\n" % (pin.number,pin.name, get_pin_type_v6(pin),"R"))
                            j += 1
                        outf.write ("SPC R\n")

                        # top side
                        j = 0
                        while j < pins_per_side:
                            pin = self.get_pin (pins, pins_per_side-j + pins_per_side*3)
                            outf.write ("%s %s %s %s\n" % (pin.number,pin.name, get_pin_type_v6(pin),"TC"))
                            j += 1


                    outf.write ("END\n")
                else:
                    # 1..1
                    # 1..2
                    for unit in range (1, num_units+1):
                    
                        bb = bb + get_bounds_v6 (comp, unit)
                        #print "unit %d width %d" % (unit, bb.width)

                        unit_pins = find_comp_pins (comp, unit)
                        if unit_pins:

                            pins = []
                            for pin in unit_pins:
                                # debug
                                if pin.unit==0 and num_units>1 and not is_power_pin (pin):
                                    print("info: common pin %s %s %s"  % (comp.name, pin.number, pin.name))

                                if pin.demorgan <= 1 and not (self.separate_power_unit and is_power_pin(pin)):
                                    pins.append (pin)

                            if pins:

                                # move horiz power pins to T/B ?

                                #horiz_pins = self.filter_pins (pins, "LR")
                                #vert_pins = self.filter_pins (pins, "TB")

                                horiz_pins=[]
                                vert_pins=[]
                                have_alternate_names = False
                                for pin in pins:
                                    if is_power_pin(pin):
                                        if is_positive_power(pin):
                                            pin.direction = 'T'
                                        else:
                                            pin.direction = 'B'
                                        pin.etype= 'power_in'
                                        pin.shape = 'line'
                                        vert_pins.append (pin)
                                    else:
                                        if pin.direction in "TB":
                                            vert_pins.append (pin)
                                        else:
                                            horiz_pins.append (pin)

                                    if '/' in pin.name:
                                        have_alternate_names = True
         

                                pins_def = ""

                                # look for horiz pins
                                # sort by y pos
                                pins = sorted (horiz_pins, key=lambda x: x.posy, reverse=True)

                                max_y = -99999
                                for pin in pins:
                                    if pin.direction in ['L','R']:
                                        if pin.posy > max_y:
                                            max_y = pin.posy

                                for _dir in ['L','R']:
                                    cur_y = max_y + 100
                                    for pin in pins:
                                        if is_power_pin(pin):
                                            if is_positive_power(pin):
                                                pin.direction = 'T'
                                            else:
                                                pin.direction = 'B'
                                            pin.etype= 'power_in'
                                            pin.shape = 'line'

                                        elif pin.direction == _dir:
                                            py = pin.posy
                                            first_space = True
                                            while cur_y > py + 100:
                                                if first_space or not self.squash_gaps:
                                                    pins_def += "SPC %s\n" % _dir
                                                    first_space = False
                                                cur_y -= 100

                                            if self.alternate_names and '/' in pin.name:
                                                alt_list = pin.name.split('/')

                                                # match common port names, eg. PA1, PTB2, RC3
                                                if _dir == 'R' and ( re.match('P[A-Z][0-9]+', alt_list[-1]) or re.match('PT[A-Z][0-9]+', alt_list[-1]) or re.match('R[A-Z][0-9]+', alt_list[-1]) ):
                                                    alt_list.reverse()
                                                    name = '/'.join (alt_list)
                                                else:
                                                    name = pin.name

                                                pins_def += "%s %s %s %s\n" % (pin.number, name, get_pin_type_v6(pin), pin.direction)
                                            else:
                                                pins_def += "%s %s %s %s\n" % (pin.number, pin.name, get_pin_type_v6(pin), pin.direction)
                                            
                                            cur_y = py

                                # look for vert pins
                                # sort by x pos
                                pins = sorted (vert_pins, key=lambda x: x.posx)

                                for _dir in ['T','B']:
                                    first = True
                                    for pin in pins:
                                        if pin.direction == _dir:
                                            if first:
                                                cur_x = pin.posx
                                                first = False
                                            px = pin.posx
                                            first_space = True
                                            while cur_x < px - 100:
                                                if first_space or not self.squash_gaps:
                                                    pins_def += "SPC %s\n" % _dir
                                                    first_space = False
                                                cur_x += 100

                                            # remove invisible attribute from power pins
                                            if is_power_pin (pin):
                                                #pin.shape = pin.shape.replace ("N", "")
                                                pin.is_hidden = False
                                                pin.name = pin.name.upper()

                                            pins_def += "%s %s %s %s\n" % (pin.number,pin.name, get_pin_type_v6(pin), pin.direction+'C')
                                            cur_x = px

                                # adjust width
                                width = bb.width
                                top_pins = self.filter_pins (pins, "T")
                                bottom_pins = self.filter_pins (pins, "B")
                                if len(top_pins) + len(bottom_pins) != 0:
                                    width = max (width, 50 * (max (len(top_pins), len(bottom_pins))+6) )

                                width += 2 * ((width/2 + pin_len) % 100)
                                line = "UNIT"
                                if type:
                                    line += " " + type
                                else:
                                    if width>0 and width != def_width and def_width != 0:
                                        if self.alternate_names and have_alternate_names:
                                            #TODO: need AUTO?
                                            #line += " AUTO"
                                            line += " WIDTH 0"
                                        else:
                                            line += " WIDTH %d" % (width)

                                    if unit_template:
                                        line += " TEMPLATE %s" % (unit_template)
                                line += '\n'

                                outf.write (line)
                                outf.write (pins_def)

                    #
                    if self.separate_power_unit:
                        # now look for power pins
                        pins = []
                        pin_map = {}
                        for pin in comp.pins:
                            if is_power_pin(pin) and not pin.number in pin_map:
                                if is_positive_power (pin):
                                    pin.direction = "T"
                                else:
                                    pin.direction = "B"
                                pins.append(pin)
                                pin_map [pin.number] = 1

                        if pins:
                            # sort by pin name/number
                            # if max_pin_number!=-1:
                            pins = sorted (pins, key=sort_name_num)
                                # pins = sort_human(pins)

                            top_pins = self.filter_pins (pins, "T")
                            bottom_pins = self.filter_pins (pins, "B")

                            width = def_width
                            if len(top_pins) + len(bottom_pins) != 0:
                                width = max (width, 50 * (max (len(top_pins), len(bottom_pins))+4) )

                            line = "UNIT PWR"
                            if width > 0 and width != def_width and def_width != 0:
                                line += " WIDTH %d" % (width)
                            line += '\n'
                            outf.write (line)

                            for pin in pins:
                                if is_positive_power (pin):
                                    pin.direction = "TC"
                                else:
                                    pin.direction = "BC"
                                # type may be power out?
                                # upper case name?
                                outf.write ("%s %s %s %s\n" % (pin.number,pin.name.upper(),"PI",pin.direction))

                    #
                    outf.write ("END\n")

                #
                # process aliases
                #


        outf.close()

        kw_filename = os.path.join (out_path, out_filename + "_key.txt")

        outf = open (kw_filename,'w')
        for kw in sorted(keywords):
            outf.write (kw + "\n")
        outf.close()

        #
        if self.use_templates:
            template_lib.write ()

