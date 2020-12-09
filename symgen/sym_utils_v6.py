#!/usr/bin/env python

import os
import sys
import hashlib
import time
import copy

# from schlib import *
# v6 schlib

import sexpr
import kicad_sym

import sym_drawing

from sym_comp import *


def mil_to_mm(mil):
    return float(mil) * 0.0254

def mm_to_mil(mm):
    return round(mm / 0.0254)

def point_to_mm (p):

    np = Point (mil_to_mm(p.x), mil_to_mm(p.y))
    return np

def point_to_mil (p):

    np = Point (mm_to_mil(p.x), mm_to_mil(p.y))
    return np



                    

#todo: v5
def create_empty_lib (filename):

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


def read_ref_list(filename):

    data = []
    inf=open(filename)
    for line in inf:
        tokens = line.strip().split('\t')
        desc = LogicDesc (tokens)
        data.append (desc)

    return data

def process_ref_list(filename, out_filename):

    inf = open(filename)
    outf = open(out_filename, "w")

    for line in inf:
        tokens = line.strip().split('\t')
        tokens[2] = capitalise (tokens[2])
        s = '\t'.join (tokens)
        outf.write (s + '\n')

    outf.close()
    inf.close()

def iso_fmt_date_time (_time):
    return time.strftime("%Y-%m-%d %H:%M:%S", _time)

# check for short words? : of at to for in by 
def capitalise (s):
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

def align_to_grid (val, grid_size):
    return int (val/grid_size) * grid_size

#todo: v5
def convert_to_string (elem):
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


def get_drawing_bounds_v6 (elem):
    bb = BoundingBox()
    if isinstance (elem, kicad_sym.Polyline):
        for p in elem.points:
            bb.extend (point_to_mil(p))
    elif isinstance (elem, kicad_sym.Rectangle):
        bb.extend (point_to_mil(Point(elem.startx, elem.starty)))
        bb.extend (point_to_mil(Point(elem.endx, elem.endy)))
    elif isinstance (elem, kicad_sym.Circle):
        bb.extend (point_to_mil(Point(elem.centerx - elem.radius, elem.centery - elem.radius)))
        bb.extend (point_to_mil(Point(elem.centerx + elem.radius, elem.centery + elem.radius)))
    elif isinstance (elem, kicad_sym.Arc):
        bb.extend (point_to_mil(Point(elem.startx, elem.starty)))
        bb.extend (point_to_mil(Point(elem.endx, elem.endy)))
    else:
        raise Exception("unknown type")

    return bb

def get_bounds_v6 (comp, unit):
    bbs=[]
    for elem in comp.polylines + comp.rectangles + comp.arcs + comp.circles:
#        if key in ['P','S','C','A']:
        if elem.unit == unit and elem.demorgan <= 1:
            #drawing = create_drawing_object ([key, params])
            bbs.append (get_drawing_bounds_v6(elem))

    if len(bbs)==0:    
        return BoundingBox()
    else:
        return sum(bbs)

#todo: v5
def get_checksum (comp, unit, variant):

    data=''
    items=[]
    formatted_items = []

    items = comp.arcs + comp.circles + comp.polylines + comp.texts
    for elem in items:
        formatted_items.append (sexpr.build_sexp(elem.get_sexpr()))

    formatted_items.sort()

    data = ' '.join(formatted_items)

    try:
        md5 = hashlib.md5(data.encode('utf-8'))
    except UnicodeDecodeError:
        md5 = hashlib.md5(data)
            
    checksum = md5.hexdigest()
    return checksum

def get_fill_v6 (fill, style):
    if fill != "background":
        return fill 
    else:
        if style:
            return style.fill
        else:
            return fill

def match_unit (p, unit, variant):
    if (p.unit == 0 or p.unit == unit) and (p.demorgan == 0 or p.demorgan == variant):
        return True
    else:
        return False

# copy graphic items from src_comp[src_unit,src_variant] to dest_comp[dest_unit,variant]
def copy_icon_v6 (dest_comp, src_comp, offset, dest_unit, variant=0, src_unit=0, src_variant=1, style = None):
    
    # TODO: source unit
    # pensize, fill?

    for p in src_comp.arcs:
        if match_unit (p, src_unit, src_variant):
            item = kicad_sym.Arc.from_sexpr(p.get_sexpr(), dest_unit, variant)
            item.centery += offset.y
            item.starty += offset.y
            item.endy += offset.y
            item.fill_type = get_fill_v6 (p.fill_type, style)
            dest_comp.arcs.append (item)
    
    for p in src_comp.circles:
        if match_unit (p, src_unit, src_variant):
            item = kicad_sym.Circle.from_sexpr(p.get_sexpr(), dest_unit, variant)
            item.centery += offset.y
            item.fill_type = get_fill_v6 (p.fill_type, style)
            dest_comp.circles.append (item)

    for p in src_comp.polylines:
        if match_unit (p, src_unit, src_variant):
            item = kicad_sym.Polyline.from_sexpr (p.get_sexpr(), dest_unit, variant)
            for pt in item.points:
                pt.x += offset.x
                pt.y += offset.y
            item.fill_type = get_fill_v6 (p.fill_type, style)
            # poly.stroke_width = p.stroke_width
            dest_comp.polylines.append (item)

    for p in src_comp.rectangles:
        # TODO apply offset
        if match_unit (p, src_unit, src_variant):
            item = kicad_sym.Rectangle.from_sexpr (p.get_sexpr(), dest_unit, variant)
            item.fill_type = get_fill_v6 (p.fill_type, style)
            dest_comp.rectangles.append (item)

    for p in src_comp.texts:
        if match_unit (p, src_unit, src_variant):
            item = kicad_sym.Text.from_sexpr (p.get_sexpr(), dest_unit, variant)
            item.posy += offset.y
            dest_comp.texts.append (item)




def is_positive_power (pin):
    norm_name = pin.name.upper()
    name = norm_name
    if len(name) > 3 :
        name = name[-3:]
    if (norm_name in ["3.3V", "5V", "VCAP"] or name in ["VCC", "VDD", "V+"] 
            or norm_name.endswith ("VDD") 
            or norm_name.startswith ("VCC")
       ):
        return True
    elif (name in ["GND", "VSS", "VEE", "V-"] 
            or norm_name.startswith ("GND")
            or norm_name.startswith ("VSS") 
           ):
        return False
    else:
        return True

# other forms 5V 3.3V +5V
def is_power_pin (pin):
    norm_name = pin.name.upper()
    name = norm_name
    if len(name) > 3 :
        name = name[-3:]
    if (norm_name in ["3.3V", "5V", "VCAP"] or name in ["VCC", "VDD", "V+", "GND", "VSS", "VEE", "V-"] 
            or norm_name.endswith ("VDD") 
            or norm_name.startswith ("VCC")
            or norm_name.startswith ("GND")
       ):
        return True
    elif "power" in pin.etype:
        return True
    else:
        return False

def find_comp_pins (comp, unit):
    pins = []

    for pin in comp.pins:
        if pin.unit == 0 or pin.unit == unit:
            pins.append (pin)
    return pins

def numeric_pins (pins):
    for pin in pins:
        if not pin.number.isdigit():
            return False
    return True


def tokenise (s):
    in_quote = False
    tok = ""
    result = []
    j = 0
    while j < len(s):
        if in_quote:
            if s[j] == '"':
                in_quote = False
                tok = tok + s[j]
            else:
                tok = tok + s[j]
        else:
            if s[j] == '"':
                in_quote = True
                tok = tok + s[j]
            elif s[j] in [" ", '\t']:
                if tok:
                    result.append (tok)
                tok = ""
            else:
                tok = tok + s[j]
        j += 1

    if tok:
        result.append (tok)
    return result

