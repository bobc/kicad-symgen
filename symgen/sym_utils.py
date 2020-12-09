#!/usr/bin/env python

import os
import hashlib
import time
import copy
import math

from schlib import *
from sym_drawing import *
from sym_comp import *

import sweet
import kicad_sym
import sym_utils_v6

                    

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

#todo: v5
def create_drawing_object (elem):
    key = elem[0]
    params = elem[1]
    s = convert_to_string (elem)
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

#todo: v5
def get_bounds (comp, unit):
    bbs=[]
    for elem in comp.drawOrdered:
        key = elem[0]
        params = elem[1]

        if key in ['P','S','C','A']:
            if int(params['unit']) == unit and int(params['convert']) <= 1:
                drawing = create_drawing_object ([key, params])
                bbs.append (drawing.get_bounds())

    if len(bbs)==0:    
        return BoundingBox()
    else:
        return sum(bbs)

#todo: v5
def get_checksum (comp, unit, variant):

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

def get_fill (fill, style):
    if fill != Background:
        return fill 
    else:
        if style:
            return style.fill
        else:
            return fill

# copy graphic items from src_comp[src_unit,src_variant] to dest_comp[dest_unit,variant]
#def copy_icon_v6 (dest_comp, src_comp, offset, dest_unit, variant=0, src_unit=0, src_variant=1, style = None):

def copy_icon_v5 (dest_comp, src_comp, dest_unit, offset, variant=1, src_unit=0, src_variant=1, style = None):
    
    # TODO: source unit
    # pensize, fill?

    if type(src_comp) == Component:
        for p in src_comp.draw['arcs']:
            # TODO apply offset pos
            item = dict(p)
            if item['convert'] == str(src_variant) or item['convert'] == '0':
                item ['unit'] = str(dest_unit)
                item ['convert'] = str(variant)
                item ['posy'] = str(int(item ['posy']) + offset.y)
                item ['starty'] = str(int(item ['starty']) + offset.y)
                item ['endy'] = str(int(item ['endy']) + offset.y)
                item ['fill'] = get_fill (item['fill'], style)
                dest_comp.drawOrdered.append (['A', item])
    
        for p in src_comp.draw['circles']:
            item = copy.deepcopy(p)
            if item['convert'] == str(src_variant) or item['convert'] == '0':
                item ['unit'] = str(dest_unit)
                item ['convert'] = str(variant)
                item ['posy'] = str(int(item ['posy']) + offset.y)
                item ['fill'] = get_fill (item['fill'], style)
                dest_comp.drawOrdered.append (['C', item])

        for p in src_comp.draw['polylines']:
            item = dict(p)
            if item['convert'] == str(src_variant) or item['convert'] == '0':
                poly = PolyLine (convert_to_string(['P',p]))
                poly.unit = dest_unit
                poly.demorgan = variant
                poly.fill = get_fill (item['fill'], style)
                poly.pensize = item['thickness']
                for pt in poly.points:
                    pt.x += offset.x    
                    pt.y += offset.y    
                dest_comp.drawOrdered.append (poly.get_element())

        for p in src_comp.draw['rectangles']:
            # TODO apply offset pos
            item = dict(p)
            if item['convert'] == str(src_variant) or item['convert'] == '0':
                rect = Rect()
                rect.unit = dest_unit
                rect.demorgan = variant
                rect.fill = get_fill (item['fill'], style)
                rect.p1 = Point(int(item['startx']), int(item['starty'])).Add(offset)
                rect.p2 = Point(int(item['endx']), int(item['endy'])).Add(offset)
                dest_comp.drawOrdered.append (rect.get_element())

        for p in src_comp.draw['texts']:
            item = copy.deepcopy(p)
            if item['convert'] == str(src_variant) or item['convert'] == '0':
                item ['unit'] = str(dest_unit)
                item ['convert'] = str(variant)
                item ['posy'] = str(int(item ['posy']) + offset.y)
                dest_comp.drawOrdered.append (['T',item])

    elif type(src_comp) == kicad_sym.KicadSymbol:
        for p in src_comp.arcs:
            if p.demorgan == src_variant or p.demorgan==0:
                item = {}
                item ['unit'] = str(dest_unit)
                item ['convert'] = str(variant)
                item ['posx'] = str(kicad_sym.mm_to_mil(p.centerx))
                item ['posy'] = str(kicad_sym.mm_to_mil(p.centery))
                item ['radius'] = str (kicad_sym.mm_to_mil(p.length))
                item ['start_angle'] = str(math.floor(p.angle_start * 10.0))
                item ['end_angle'] = str(math.floor(p.angle_stop * 10.0))
                item ['startx'] = str(kicad_sym.mm_to_mil(p.startx))
                item ['starty'] = str(kicad_sym.mm_to_mil(p.starty))
                item ['endx'] = str(kicad_sym.mm_to_mil(p.endx))
                item ['endy'] = str(kicad_sym.mm_to_mil(p.endy))
                item ['thickness'] = str(kicad_sym.mm_to_mil(p.stroke_width))
                item ['fill'] = sweet.convert_fill_to_v5(p.fill_type)

                item ['posy'] = str(int(item ['posy']) + offset.y)
                item ['starty'] = str(int(item ['starty']) + offset.y)
                item ['endy'] = str(int(item ['endy']) + offset.y)
                item ['fill'] = get_fill (item['fill'], style)
                dest_comp.drawOrdered.append (['A', item])
    
        for p in src_comp.circles:
            if p.demorgan == src_variant or p.demorgan == 0:
                item = {}
                item ['unit'] = str(dest_unit)
                item ['convert'] = str(variant)
                item ['posx'] = str(kicad_sym.mm_to_mil(p.centerx))
                item ['posy'] = str(kicad_sym.mm_to_mil(p.centery))
                item ['radius'] = str (kicad_sym.mm_to_mil(p.radius))
                item ['thickness'] = str(kicad_sym.mm_to_mil(p.stroke_width))
                item ['fill'] = sweet.convert_fill_to_v5(p.fill_type)

                item ['posy'] = str(int(item ['posy']) + offset.y)
                item ['fill'] = get_fill (item['fill'], style)
                dest_comp.drawOrdered.append (['C', item])

        for p in src_comp.polylines:
            if p.demorgan == src_variant or p.demorgan == 0:

                poly = PolyLine ()
                poly.unit = dest_unit
                poly.demorgan = variant
                poly.fill = sweet.convert_fill_to_v5(p.fill_type)
                poly.fill = get_fill (poly.fill, style)
                poly.pensize = kicad_sym.mm_to_mil(p.stroke_width)
                for pt in p.points:
                    mil_p = sym_utils_v6.point_to_mil (pt)
                    poly.points.append (mil_p.Add (offset))

                dest_comp.drawOrdered.append (poly.get_element())

        for p in src_comp.rectangles:
            # TODO apply offset
            if p.demorgan == src_variant or p.demorgan == 0:
                rect = Rect()
                rect.unit = dest_unit
                rect.demorgan = variant
                rect.fill = sweet.convert_fill_to_v5(p.fill_type)
                rect.fill = get_fill (rect.fill, style)
                rect.pensize = kicad_sym.mm_to_mil(p.stroke_width)
                rect.p1 = sym_utils_v6.point_to_mil(Point(p.startx, p.starty)).Add(offset)
                rect.p2 = sym_utils_v6.point_to_mil(Point(p.endx, p.endy)).Add(offset)
                dest_comp.drawOrdered.append (rect.get_element())

        for p in src_comp.texts:
            if p.demorgan == src_variant or p.demorgan == 0:
                item = {}
                item ['unit'] = str(dest_unit)
                item ['convert'] = str(variant)
                item ['posx'] = str(kicad_sym.mm_to_mil(p.posx))
                item ['posy'] = str(kicad_sym.mm_to_mil(p.posy))
                item ['direction'] = str(math.floor(p.rotation * 10.0))

                item ['text_size'] = str(kicad_sym.mm_to_mil(p.effects.sizex))
                item ['hjustify'] = "L" if p.effects.h_justify == "left" else "C"
                item ['vjustify'] = "B" if p.effects.v_justify == "bottom" else "C"
                item ['bold'] = "1" if p.effects.is_bold else "0"
                item ['italic'] = "Italic" if p.effects.is_italic else "Normal"
                item ['text_type'] = "1" if p.effects.is_hidden else "0"

                item ['text'] = p.text

                item ['posy'] = str(int(item ['posy']) + offset.y)
                dest_comp.drawOrdered.append (['T',item])





def is_positive_power (pin):
    norm_name = pin['name'].upper()
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
    norm_name = pin['name'].upper()
    name = norm_name
    if len(name) > 3 :
        name = name[-3:]
    if (norm_name in ["3.3V", "5V", "VCAP"] or name in ["VCC", "VDD", "V+", "GND", "VSS", "VEE", "V-"] 
            or norm_name.endswith ("VDD") 
            or norm_name.startswith ("VCC")
            or norm_name.startswith ("GND")
       ):
        return True
    elif pin['electrical_type'] in "Ww":
        return True
    else:
        return False

def find_comp_pins (comp, unit):
    pins = []

    for pin in comp.pins:
        if pin['unit'] =='0' or  pin['unit'] == str(unit):
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

