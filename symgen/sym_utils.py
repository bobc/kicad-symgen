#!/usr/bin/env python

import os
import hashlib
import time
import copy

from schlib import *
from sym_drawing import *
from sym_comp import *


class SymbolStyle (Enum):
    # ANSI/MIL MIL-STD-806, now also IEEE Standard 91-1984 "distinctive shapes" 
    ANSI = 1
    # IEC 60617-12, now also IEEE Standard 91-1984
    IEC = 2
    # DIN 40700
    DIN = 3
    #
    PHYSICAL = 4

class PowerStyle (Enum):
    # A box
    BOX = 1
    # No box
    LINES = 2
                    


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

def copy_icon (comp, comp_icon, unit, pos, variant=0, src_unit=0, src_variant=1, style = None):
    
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
            item['fill'] = get_fill (item['fill'], style)
            comp.drawOrdered.append (['A', item])
    
    for p in comp_icon.draw['circles']:
        item = copy.deepcopy(p)
        if item['convert'] == str(src_variant) or item['convert'] == '0':
            item ['unit'] = str(unit)
            item ['convert'] = str(variant)
            item ['posy'] = str(int(item ['posy']) + pos.y)
            item['fill'] = get_fill (item['fill'], style)
            comp.drawOrdered.append (['C', item])

    for p in comp_icon.draw['polylines']:
        item = dict(p)
        if item['convert'] == str(src_variant) or item['convert'] == '0':
            poly = PolyLine (convert_to_string(['P',p]))
            poly.unit = unit
            poly.demorgan = variant
            poly.fill = get_fill (item['fill'], style)
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
            rect.fill = get_fill (item['fill'], style)
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




def is_positive_power (pin):
    norm_name = pin['name'].upper()
    name = norm_name
    if len(name) > 3 :
        name = name[-3:]
    if (norm_name in ["3.3V", "5V", "VCAP"] or name in ["VCC", "VDD", "V+"] 
        or norm_name.endswith ("VDD") 
        ):
        return True

# other forms 5V 3.3V +5V
def is_power_pin (pin):
    norm_name = pin['name'].upper()
    name = norm_name
    if len(name) > 3 :
        name = name[-3:]
    if ( norm_name in ["3.3V", "5V", "VCAP"] or name in ["VCC", "VDD", "V+", "GND", "VSS", "VEE", "V-"] 
        or norm_name.endswith ("VDD") 
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
