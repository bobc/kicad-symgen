

import os

from sym_drawing import *
from sym_comp import *
from lib_symgen import *

def convert_yes_no (y_or_n):
    return 'yes' if y_or_n == 'Y' else 'no'

def mils_to_mm (mils):
    return float(mils) * 0.0254

def convert_elect_type_to_sweet (elec_type):
    if elec_type == 'I':
        return 'input'
    elif elec_type == 'O':
        return 'output'
    elif elec_type == 'B':
        return 'bidirectional'
    elif elec_type == 'T':
        return 'tri_state'
    elif elec_type == 'P':
        return 'passive'
    elif elec_type == 'C':
        return 'open_collector'
    elif elec_type == 'E':
        return 'open_emitter'
    elif elec_type == 'N':
        return 'unconnected'
    elif elec_type == 'U':
        return 'unspecified'
    elif elec_type == 'W':
        return 'power_in'
    elif elec_type == 'w':
        return 'power_out'

def convert_pin_type_to_sweet (pin_type):
    if pin_type == ' ' or pin_type == '':
        return 'line'
    elif pin_type == 'C':
        return 'clock'
    elif pin_type == 'I':
        return  'inverted'
    elif pin_type == 'F':
        return  'falling_edge'
    else:
        return 'line'

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
        self.text_size.x = text_size
        self.text_size.y = text_size

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

    def sexpr (self, default_empty = False):
        if not default_empty or self.text_size.x != 1.27 or not self.visible or self.h_justify != 'C' or self.v_justify != 'C':
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
            return ""



class SweetPin (object):

    opt_alternate_names = True

    def __init__(self, pin):
        self.elec_type = pin['electrical_type']
        self.pin_type = pin['pin_type']
        self.posx = mils_to_mm(pin['posx']) 
        self.posy = mils_to_mm(pin['posy'])
        self.direction = pin['direction']

        self.length = mils_to_mm(pin['length'])

        if self.opt_alternate_names and '/' in pin['name']:
            names = pin['name'].split ('/')
            self.name = names[0]
            self.alternate_names = names[1:]

        else:
            if pin['alternate_names']:
                self.alternate_names = []
                self.alternate_names.extend (pin['alternate_names'])
            else:
                self.alternate_names = []
            self.name = pin['name']

        self.name_text_size = Point ()
        self.name_text_size.x = mils_to_mm(pin['name_text_size'])
        self.name_text_size.y = mils_to_mm(pin['name_text_size'])
        
        


        self.num = pin['num'] 
        self.num_text_size = Point()
        self.num_text_size.x = mils_to_mm(pin['num_text_size'])
        self.num_text_size.y = mils_to_mm(pin['num_text_size'])

        self.name_effects = Effects()
        self.name_effects.init(self.name_text_size.x, True, AlignCenter, AlignCenter)

        self.num_effects = Effects ()
        self.num_effects.init(self.num_text_size.x, True, AlignCenter, AlignCenter)

        self.elec_type = convert_elect_type_to_sweet (self.elec_type)

        if 'N' in pin['pin_type']:
            self.visible = False
            self.pin_type = self.pin_type.replace ('N', '')
        else:
            self.visible = True

        self.pin_type = convert_pin_type_to_sweet (self.pin_type)

        if self.direction == 'L':
            self.direction = 180
        elif self.direction == 'D':
            self.direction = 270
        elif self.direction == 'R':
            self.direction = 0
        elif self.direction == 'U':
            self.direction = 90
        

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

    def apply_format (self, comp, name):
        format = [x for x in comp.settings.pin_name_formats if re.match(x[0], name) ]

        if format:
            p = re.sub (format[0][0], format[0][1], name, flags=re.IGNORECASE)
            print (f"{name} {p}")
            return p
        else:
            return name

    def gen_unit (self, sgcomp, k_comp, unit):

        #part_name = "%s:%s_U%d" % (self.symbols.out_basename, sgcomp.name, self.unit_num)
        #todo: demorgan 
        part_name = "%s_%d_%d" % (sgcomp.name, self.unit_num, 0)

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

                self.outfile.write ('    (rectangle (start {:g} {:g}) (end {:g} {:g})\n'.format 
                    ( mils_to_mm (rect['startx']), mils_to_mm (rect ['starty']),
                      mils_to_mm (rect['endx']), mils_to_mm (rect ['endy'])
                    ))

                self.outfile.write ('      (stroke (width {:g})) (fill (type background))\n' .format ( 
                        mils_to_mm (rect['thickness'])
                    ))

                self.outfile.write ('    )\n')
            #

        for sweet_pin in pins:

            # TODO: add pin effects
            #self.outfile.write ('    (pin %s %s (at %s %s %s) (length %s) (name "%s" (effects (font (size %s %s)) %s)) (number "%s" (effects (font (size %s %s)) %s)) %s)\n' % 

            self.outfile.write ('    (pin {} {} (at {:g} {:g} {}) (length {}) {}\n'.format
                ( sweet_pin.elec_type, sweet_pin.pin_type, 
                    sweet_pin.posx, sweet_pin.posy, sweet_pin.direction,
                    sweet_pin.length,
                    "hide" if not sweet_pin.visible else ""
                    ) 
                )

            self.outfile.write ('      (name "{}" {})\n'.format
                (   self.apply_format (sgcomp, sweet_pin.name), 
                    sweet_pin.name_effects.sexpr(False)
                    ) 
                )

            self.outfile.write ('      (number "{}" {})\n'.format
                (   sweet_pin.num,
                    sweet_pin.num_effects.sexpr(False)
                    ) 
                )

            if sweet_pin.alternate_names:
                for alt_name in sweet_pin.alternate_names:
                    self.outfile.write ('      (alternate "{}" {} {})\n'.format
                        (   self.apply_format (sgcomp, alt_name.name), 
                            convert_elect_type_to_sweet(alt_name.type),
                            convert_pin_type_to_sweet(alt_name.shape)
                            ) 
                        )

            self.outfile.write ('      )\n')

            


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

        if effects.sexpr(False) != "":
            self.outfile.write ('\n')
            self.outfile.write ('      %s\n' % (effects.sexpr(False)) )
            self.outfile.write ('    ')

        self.outfile.write (')\n')

    def draw_component (self, comp):
        assert isinstance(comp, SgComponent)

        self.max_height = 0
        self.last_unit = None #todo

        self.ref_pos= Point()
        self.ref_pos.x = -comp.settings.box_width/2
        self.ref_pos.y = 0

        self.name_pos = Point()
        self.name_pos.x = -comp.settings.box_width/2
        self.name_pos.y = 0

        component_data = []
        # units are not interchangeable
        component_data.append("DEF %s %s 0 40 Y Y 1 L N" % (comp.name, comp.ref) )      
        component_data.append("F0 \"U\" 0 0 50 H V C CNN")
        component_data.append("F1 \"74469\" 0 -200 50 H V L CNN")
        component_data.append("F2 \"\" 0 0 50 H I L CNN")
        component_data.append("F3 \"\" 0 0 50 H I C CNN")
        component_data.append("DRAW")
        component_data.append("ENDDRAW")
        component_data.append("ENDDEF")
        
        k_comp = Component (component_data, [], None)

        if comp.settings.pin_names_inside:
            k_comp.definition['text_offset'] = "0"
        else:
            k_comp.definition['text_offset'] = str(self.symbols.def_name_offset)

        for s in comp.fplist:
            k_comp.fplist.append (s)


        # TODO: field posns

        # generate units

        self.unit_num = 1
        self.units_have_variant = 0

        unit_list = []

        for unit in comp.units:
            self.draw_unit (comp, k_comp, unit)
            #
            #name = self.gen_unit (comp, k_comp, unit)
            #unit_list.append (name)
            #
            self.last_unit = unit
            self.unit_num += 1

        #
        k_comp.fields [0]['posx'] = str(int(self.ref_pos.x))
        k_comp.fields [0]['posy'] = str(self.ref_pos.y)

        k_comp.fields [1]['posx'] = str(int(self.name_pos.x))
        k_comp.fields [1]['posy'] = str(self.name_pos.y)

        k_comp.fields [2]['posx'] = str(int(self.footprint_pos.x))
        k_comp.fields [2]['posy'] = str(self.footprint_pos.y)

        k_comp.fields [0]['htext_justify' ] = ha_right
        k_comp.fields [1]['htext_justify' ] = ha_right

        # if field is positioned on the right, justify text on left
        if comp.settings.label_horiz_align == ha_right:
            k_comp.fields [1]['htext_justify' ] = ha_left

        field_pos = Point()
        field_pos.x = self.footprint_pos.x
        field_pos.y = self.footprint_pos.y

        #
        # Loop through each alias. The first entry is assumed to be the "base" symbol
        #
        is_alias = False

        if comp.parent is None:
            flat_unit = True
        elif len([x for x in comp.units if x.modified]):
            flat_unit  = True
        else:
            flat_unit = False

        for name in comp.doc_fields.keys():
            #  (pin_names (offset %s))

            if flat_unit:
                self.outfile.write ('  (symbol "%s:%s" (in_bom yes) (on_board yes)\n' % (self.symbols.out_basename, name) )
            else:
                if is_alias:
                    self.outfile.write ('  (symbol "%s:%s" (extends "%s")\n' % (self.symbols.out_basename, name, comp.name ) )
                else:
                    self.outfile.write ('  (symbol "%s:%s" (extends "%s") (in_bom yes) (on_board yes)\n' % (self.symbols.out_basename, name, comp.parent.name) )
                
                
            self.write_field ("Reference", comp.ref, 0, k_comp.fields[0]) 

            self.write_field ("Value", name, 1, k_comp.fields[1]) 

            if comp.default_footprint:
                self.write_field ("Footprint", comp.default_footprint, 2, k_comp.fields[2]) 
                field_pos.y = field_pos.y - 100
                k_comp.fields [2]['posy'] = str(field_pos.y)

            sgdoc = comp.doc_fields[name]

            if sgdoc.datasheet:
                self.write_field ("Datasheet", sgdoc.datasheet, 3, k_comp.fields[2]) 
                field_pos.y = field_pos.y - 100
                k_comp.fields [2]['posy'] = str(field_pos.y)

            if sgdoc.keywords:
                self.write_field ("ki_keywords", sgdoc.keywords, 4, k_comp.fields[2]) 

            if sgdoc.description:
                self.write_field ("ki_description", sgdoc.description, 5, k_comp.fields[2]) 

            #if not is_alias:
            if k_comp.fplist:
                self.write_field ("ki_fp_filters", ' '.join(k_comp.fplist), 6, k_comp.fields[2]) 

                #self.outfile.write ('    (alternates\n' )
                #for unit_name in unit_list:
                #    self.outfile.write ('      %s\n' % unit_name)
                #self.outfile.write ('    )\n' )

            
            if not is_alias and flat_unit:
                # generate units
                self.unit_num = 1

                for unit in comp.units:
                    self.gen_unit (comp, k_comp, unit)
                    self.unit_num += 1

            #
            self.outfile.write ('  )\n' )

            is_alias = True

    def GenerateLibrary (self, a_symbols):

        self.symbols = a_symbols
        self.num_errors = 0

        self.libfile = os.path.join (self.symbols.out_path, self.symbols.out_basename + ".kicad_sym")
        self.outfile = open (self.libfile, "w")

        print("Creating library %s" % self.libfile)

        self.outfile.write ('(kicad_symbol_lib (version 20200126) (generator symgen "2.0.0")\n')

        if self.symbols.components:
            for comp in self.symbols.components:
                if not comp.is_template:
                    self.draw_component(comp)

        self.outfile.write (')\n' )
        self.outfile.close()
