

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
        

class GenerateSweetLib(GenerateKicad):

    def __init__(self):
        self.libfile = None
        self.docfile = None
        self.num_errors = 0
        self.outfile = None

        return super(GenerateSweetLib, self).__init__()

    def gen_unit (self, sgcomp, k_comp, unit):

        part_name = "%s_U%d" % (sgcomp.name, self.unit_num)

        self.unit_filename = os.path.join (self.lib_folder, "%s.kicad_part" % part_name )

        #
        self.unit_file = open (self.unit_filename, "w")

        self.unit_file.write ('(part "%s"\n' % part_name )
        # more stuff

        for elem in k_comp.drawOrdered:
            if elem[0] == 'X':
                pin = elem[1]

                sweet_pin = SweetPin (pin)

                self.unit_file.write (' (pin %s %s (at %s %s %s)\n' % ( sweet_pin.elec_type, sweet_pin.pin_type, sweet_pin.posx, sweet_pin.posy, sweet_pin.direction ) )
                self.unit_file.write ('   (length %s)\n' % sweet_pin.length )
                self.unit_file.write ('   (name "%s" (font (size %s %s)) (visible %s))\n' % ( sweet_pin.name, sweet_pin.name_text_size.x, sweet_pin.name_text_size.y, convert_yes_no(k_comp.definition['draw_pinname']) ) )
                self.unit_file.write ('   (number "%s" (font (size %s %s)) (visible %s))\n' % ( sweet_pin.num, sweet_pin.num_text_size.x, sweet_pin.num_text_size.y, convert_yes_no(k_comp.definition['draw_pinnumber']) ) )
                self.unit_file.write ('   (visible %s))\n' % (sweet_pin.visible) )

                #(name "" (font (size 1.2 1.2)) (visible yes))
                #(number "2" (font (size 1.2 1.2)) (visible yes))
                #(visible yes))


        self.unit_file.write (')\n' )
        self.unit_file.close()

        return part_name

    def draw_component (self, comp):
        assert isinstance(comp, SgComponent)

        # each part should be in separate file
        # each unit/variant should be in separate file?

        self.filename = os.path.join (self.lib_folder, comp.name + ".kicad_part")

        print "Generating: " + self.filename

        component_data = []
        # units are not interchangeable
        component_data.append("DEF %s %s 0 40 Y Y 1 L N" % (comp.name, comp.ref) )      
        component_data.append("F0 \"U\" 0 0 50 H V C CNN")
        component_data.append("F1 \"74469\" 0 -200 50 H V C CNN")
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
        self.outfile = open (self.filename, "w")

        self.outfile.write ('(part "%s"\n' % comp.name )
        self.outfile.write ('  (reference "%s")\n' % comp.ref )
        self.outfile.write ('  (value "%s")\n' % comp.name )
        # more stuff

        if comp.default_footprint:
            self.outfile.write ('  (footprint %s)\n' % comp.default_footprint )

        sgdoc = comp.doc_fields[comp.name]

        if sgdoc.datasheet:
            self.outfile.write ('  (datasheet "%s")\n' %  sgdoc.datasheet)
        if sgdoc.keywords:
            self.outfile.write ('  (keywords "%s")\n' %  sgdoc.keywords)
        if sgdoc.description:
            self.outfile.write ('  (property "Description" "%s")\n' % sgdoc.description)


        self.outfile.write ('  (alternates\n' )
        for unit_name in unit_list:
            self.outfile.write ('    %s\n' % unit_name)
        self.outfile.write ('  )\n' )

        self.outfile.write (')\n' )
        self.outfile.close()

    def GenerateLibrary (self, a_symbols):

        self.symbols = a_symbols
        self.num_errors = 0

        self.lib_folder = os.path.join (self.symbols.out_path, self.symbols.out_basename + ".sweet")

        if not os.path.exists (self.lib_folder):
            os.makedirs (self.lib_folder)

        if self.symbols.components:
            for comp in self.symbols.components:
                if not comp.is_template:
                    self.draw_component(comp)
