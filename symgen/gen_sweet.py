

import os

from sym_drawing import *
from sym_comp import *
from lib_symgen import *

def convert_yes_no (y_or_n):
    return 'yes' if y_or_n == 'Y' else 'no'

def mils_to_mm (mils):
    return float(mils) * 0.0254

class SweetPin (object):
    def __init__(self, pin):
        self.elec_type = pin['electrical_type']
        self.pin_type = pin['pin_type']
        self.posx = mils_to_mm(pin['posx']) 
        self.posy = mils_to_mm(pin['posy'])
        self.direction = pin['direction']

        self.length = mils_to_mm(pin['length'])

        self.name = pin['name']
        self.name_text_size = Point ()
        self.name_text_size.x = mils_to_mm(pin['name_text_size'])
        self.name_text_size.y = mils_to_mm(pin['name_text_size'])
        
        self.num = pin['num'] 
        self.num_text_size = Point()
        self.num_text_size.x = mils_to_mm(pin['num_text_size'])
        self.num_text_size.y = mils_to_mm(pin['num_text_size'])


        if self.elec_type == 'I':
            self.elec_type = 'input'
        elif self.elec_type == 'O':
            self.elec_type = 'output'
        elif self.elec_type == 'B':
            self.elec_type = 'bidirectional'
        elif self.elec_type == 'T':
            self.elec_type = 'tristate'
        elif self.elec_type == 'P':
            self.elec_type = 'passive'
        elif self.elec_type == 'C':
            self.elec_type = 'open_collector'
        elif self.elec_type == 'E':
            self.elec_type = 'open_emitter'
        elif self.elec_type == 'N':
            self.elec_type = 'unconnected'
        elif self.elec_type == 'U':
            self.elec_type = 'unspecified'
        elif self.elec_type == 'W':
            self.elec_type = 'power_in'
        elif self.elec_type == 'w':
            self.elec_type = 'power_out'

        if 'N' in pin['pin_type']:
            self.visible = 'no'
            self.pin_type = self.pin_type.replace ('N', '')
        else:
            self.visible = 'yes'

        if self.pin_type == ' ' or self.pin_type == '':
            self.pin_type = 'line'
        elif self.pin_type == 'C':
            self.pin_type = 'clock'
        elif self.pin_type == 'I':
            self.pin_type = 'inverted'
        elif self.pin_type == 'F':
            self.pin_type = 'falling_edge'
        else:
            self.pin_type = 'line'

        if self.direction == 'L':
            self.direction = 0
        elif self.direction == 'D':
            self.direction = 90
        elif self.direction == 'R':
            self.direction = 180
        elif self.direction == 'U':
            self.direction = 270
        
class Effects(object):

    def __init__(self):
        self.text_size = Point ()
        self.text_size.x = 1.27
        self.text_size.y = 1.27

        self.visible = True

        self.h_justify = 'C'
        self.v_justify = 'C'

        self.bold = False
        self.italic = False

    def init(self, text_size, visible, h_justify, v_justify):
        self.text_size = Point ()
        self.text_size.x = mils_to_mm(text_size_mil)
        self.text_size.y = mils_to_mm(text_size_mil)

        self.visible = visible

        self.h_justify = h_justify
        self.v_justify = v_justify

    def init_field(self, field):
        self.text_size = Point ()
        self.text_size.x = mils_to_mm(field['text_size'])
        self.text_size.y = self.text_size.x

        self.visible = field['visibility'] == 'V'

        self.h_justify = field['htext_justify']

        self.v_justify = field['vtext_justify'][0]
        self.bold   = field['vtext_justify'][1] != 'N'
        self.italic = field['vtext_justify'][2] != 'N'

    def sexpr (self):
        if self.text_size.x != 1.27 or not self.visible or self.h_justify != 'C' or self.v_justify != 'C':
            t = "(effects (font (size %s %s))" % (self.text_size.x, self.text_size.y)

            if self.h_justify != 'C' or self.v_justify != 'C':
                t += " (justify "
                if self.h_justify == 'L':
                    t += " left"
                elif self.h_justify == 'R':
                    t += " right"
                t += ")"

            if not self.visible:
                t += " hide"

            t += ")"

            return t
        else:
            return None



class GenerateSweetLib(GenerateKicad):

    def __init__(self):
        self.libfile = None
        self.docfile = None
        self.num_errors = 0
        self.outfile = None

        return super(GenerateSweetLib, self).__init__()

    def get_pins (self, comp):
        pins = []

        numeric_pins = True

        if comp:
            for elem in comp.drawOrdered:
                if elem[0] == 'X':
                    item = dict(elem[1])

                    pin = SweetPin (item)

                    pins.append (pin)

                    if not pin.num.isdigit():
                        numeric_pins = False

            if numeric_pins:
                # sort by num
                for passnum in range(len(pins)-1,0,-1):
                    for i in range(passnum):
                        if pins[i].num > pins[i+1].num :
                            temp = pins[i]
                            pins[i] = pins[i+1]
                            pins[i+1] = temp

        return pins

    def gen_unit (self, sgcomp, k_comp, unit):

        part_name = "%s:%s_U%d" % (self.symbols.out_basename, sgcomp.name, self.unit_num)

        #
        self.outfile.write ('  (symbol "%s"\n' % (part_name) )
        # more stuff

        # TODO: unit, convert
        pins = self.get_pins (k_comp)

        for elem in k_comp.drawOrdered:
            if elem[0] == 'X':
                pass
            elif elem[0] == 'S':
                rect = elem[1]

                self.outfile.write ('    (rectangle (start %s %s) (end %s %s) (stroke (width %s)) (fill (type background)))\n' % 
                    ( mils_to_mm (rect['startx']), mils_to_mm (rect ['starty']),
                      mils_to_mm (rect['endx']), mils_to_mm (rect ['endy']),
                      mils_to_mm (rect['thickness'])
                    ))
            #

        for sweet_pin in pins:

            # TODO: add pin effects
            #self.outfile.write ('    (pin %s %s (at %s %s %s) (length %s) (name "%s" (effects (font (size %s %s)) %s)) (number "%s" (effects (font (size %s %s)) %s)) %s)\n' % 

            self.outfile.write ('    (pin {} {} (at {:g} {:g} {}) (length {}) (name "{}") (number "{}") {})\n'.format
                ( sweet_pin.elec_type, sweet_pin.pin_type, 
                    sweet_pin.posx, sweet_pin.posy, sweet_pin.direction,
                    sweet_pin.length,
                    sweet_pin.name, 
                    sweet_pin.num,
                    "hide" if not sweet_pin.visible else ""
                    ) 
                )

        self.outfile.write ('  )\n' )

        return part_name

    def write_field (self, name, value, id, field):

        effects = Effects ()
        effects.init_field (field)

        self.outfile.write ('    (property "%s" "%s" (id %s) (at %g %g %s)' % 
                            (name, value.strip('"'), 
                             id,
                             mils_to_mm(field['posx']), 
                             mils_to_mm(field['posy']),
                             0 if field['text_orient'] == 'H' else 90
                            ) )

        if effects.sexpr():
            self.outfile.write ('\n')
            self.outfile.write ('      %s\n' % (effects.sexpr()) )
            self.outfile.write ('    ')

        self.outfile.write (')\n')

    def draw_component (self, comp):
        assert isinstance(comp, SgComponent)


        component_data = []
        # units are not interchangeable
        component_data.append("DEF %s %s 0 40 Y Y 1 L N" % (comp.name, comp.ref) )      
        component_data.append("F0 \"U\" 0 0 50 H V C CNN")
        component_data.append("F1 \"74469\" 0 -200 50 H V L CNN")
        component_data.append("F2 \"\" 0 0 50 H I C CNN")
        component_data.append("F3 \"\" 0 0 50 H I C CNN")
        component_data.append("DRAW")
        component_data.append("ENDDRAW")
        component_data.append("ENDDEF")
        k_comp = Component (component_data, [], None)

        # generate units

        self.unit_num = 1
        self.units_have_variant = 0

        unit_list = []

        for unit in comp.units:
            self.draw_unit (comp, k_comp, unit)

            #
            name = self.gen_unit (comp, k_comp, unit)
            unit_list.append (name)

            #
            self.last_unit = unit
            self.unit_num += 1
        #
        # Loop through each alias. The first entry is assumed to be the "base" symbol
        #
        is_alias = False

        for name in comp.doc_fields.keys():
            if is_alias:
                self.outfile.write ('  (symbol "%s:%s" (extends "%s")\n' % (self.symbols.out_basename, name, comp.name ) )
            else:
                self.outfile.write ('  (symbol "%s:%s" (pin_names (offset %s))\n' % (self.symbols.out_basename, name, 0.508 ) )
                #
                self.write_field ("Reference", comp.ref, 0, k_comp.fields[0]) 

            self.write_field ("Value", name, 1, k_comp.fields[1]) 

            if not is_alias:
                if comp.default_footprint:
                    self.write_field ("Footprint", comp.default_footprint, 2, k_comp.fields[2]) 

            sgdoc = comp.doc_fields[name]

            if sgdoc.datasheet:
                self.write_field ("Datasheet", sgdoc.datasheet, 3, k_comp.fields[2]) 
            if sgdoc.keywords:
                self.write_field ("ki_keywords", sgdoc.keywords, 4, k_comp.fields[2]) 
            if sgdoc.description:
                self.write_field ("ki_description", sgdoc.description, 5, k_comp.fields[2]) 

            if not is_alias:
                if k_comp.fplist:
                    self.write_field ("ki_fp_filters", k_comp.fplist, 6, k_comp.fields[2]) 

                self.outfile.write ('    (alternates\n' )
                for unit_name in unit_list:
                    self.outfile.write ('      %s\n' % unit_name)
                self.outfile.write ('    )\n' )

            self.outfile.write ('  )\n' )

            is_alias = True

    def GenerateLibrary (self, a_symbols):

        self.symbols = a_symbols
        self.num_errors = 0

        self.libfile = os.path.join (self.symbols.out_path, self.symbols.out_basename + ".kicad_sym")
        self.outfile = open (self.libfile, "w")

        print("Creating library %s" % self.libfile)

        self.outfile.write ('(kicad_symbol_lib (version 20200126) (host symgen "2.0.0")\n')

        if self.symbols.components:
            for comp in self.symbols.components:
                if not comp.is_template:
                    self.draw_component(comp)

        self.outfile.write (')\n' )
        self.outfile.close()
