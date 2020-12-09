

import os

from sym_drawing import *
from sym_comp import *
from lib_symgen import *

from sweet import *

#def convert_yes_no (y_or_n):
#    return 'yes' if y_or_n == 'Y' else 'no'

#def mils_to_mm (mils):
#    return float(mils) * 0.0254


class GenerateSweetLib(GenerateKicad):

    def __init__(self):
        self.libfile = None
        self.docfile = None
        self.num_errors = 0
        self.outfile = None

        return super(GenerateSweetLib, self).__init__()

    def get_pins (self, comp, unit, demorgan):
        pins = []

        numeric_pins = True

        if comp:
            for elem in comp.drawOrdered:
                if elem[0] == 'X':
                    item = dict(elem[1])
                    pin = SweetPin (item)

                    if (pin.unit == 0 or pin.unit == unit) and (demorgan == -1 or pin.demorgan==demorgan):
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

        #part_name = "%s:%s_U%d" % (self.symbols.out_basename, sgcomp.name, self.unit_num)

        # look for demorgan variants

        shapes = [-1]
        for elem in k_comp.drawOrdered:
            item = dict(elem[1])
            if int(item['convert']) > 1:
                shapes = [0,1,2]
                break

        for demorgan in shapes:

            if demorgan == -1:
                part_name = "%s_%d_%d" % (sgcomp.name, self.unit_num, 1)
            else:
                part_name = "%s_%d_%d" % (sgcomp.name, self.unit_num, demorgan)

            #
            has_items = False
            sexpr = '  (symbol "%s"\n' % (part_name) 

            pins = self.get_pins (k_comp, self.unit_num, demorgan)

            for elem in k_comp.drawOrdered:
                sweet_item = None
                if elem[0] == 'X':
                    pass
                elif elem[0] == 'S':
                    sweet_item = SweetRectangle(dict(elem[1]))

                elif elem[0] == 'P':
                    sweet_item = SweetPoly(dict(elem[1]))

                elif elem[0] == 'A':
                    sweet_item = SweetArc(dict(elem[1]))

                elif elem[0] == 'C':
                    sweet_item = SweetCircle(dict(elem[1]))

                elif elem[0] == 'T':
                    sweet_item = SweetText(dict(elem[1]))

                if sweet_item:
                    if (sweet_item.unit == 0 or sweet_item.unit == self.unit_num) and ( demorgan==-1 or sweet_item.demorgan == demorgan):
                        sexpr += sweet_item.get_sexpr()
                        has_items = True

            for sweet_pin in pins:
                sexpr += sweet_pin.get_sexpr(sgcomp)
                has_items = True

            sexpr += '  )\n'
            if has_items:
                self.outfile.write (sexpr)

        return part_name

    def write_field (self, field, id):

        self.outfile.write ('    (property "%s" "%s" (id %s) (at %g %g %s)' % 
                            (field.name, field.value.strip('"'), 
                             id,
                             mil_to_mm(field.pos.x), 
                             mil_to_mm(field.pos.y),
                             0
                            ) )

        if field.effects.get_sexpr(False) != "":
            self.outfile.write ('\n')
            self.outfile.write ('      %s\n' % (field.effects.get_sexpr(False)) )
            self.outfile.write ('    ')

        self.outfile.write (')\n')

    def draw_component (self, comp):
        assert isinstance(comp, SgComponent)

        self.last_unit = None #todo

        self.ref_pos= Point()
        self.ref_pos.x = -comp.settings.box_width/2
        self.ref_pos.y = 0
        self.ref_style.horiz_alignment = ha_center

        self.name_pos = Point()
        self.name_pos.x = -comp.settings.box_width/2
        self.name_pos.y = 0
        self.name_style.horiz_alignment = ha_center

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

        self.set_label_pos2 (comp)

        #
        ref_field = SweetField("Reference", comp.ref)
        ref_field.pos.x = int(self.ref_pos.x)
        ref_field.pos.y = int(self.ref_pos.y)
        ref_field.effects.h_justify = self.ref_style.horiz_alignment

        name_field = SweetField("Value", comp.name)
        name_field.pos.x = int(self.name_pos.x)
        name_field.pos.y = int(self.name_pos.y)
        name_field.effects.h_justify = self.name_style.horiz_alignment

        footprint_field = SweetField ("Footprint", comp.default_footprint)
        footprint_field.pos.x = int(self.footprint_pos.x)
        footprint_field.pos.y = int(self.footprint_pos.y)
        footprint_field.effects.h_justify = ha_left
        footprint_field.effects.visible = False

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
                if is_alias:
                    self.outfile.write ('  (symbol "%s:%s" (extends "%s") (in_bom yes) (on_board yes)\n' % (self.symbols.out_basename, name, comp.name) )
                else:
                    self.outfile.write ('  (symbol "%s:%s" (in_bom yes) (on_board yes)\n' % (self.symbols.out_basename, name) )
            else:
                if is_alias:
                    self.outfile.write ('  (symbol "%s:%s" (extends "%s")\n' % (self.symbols.out_basename, name, comp.name ) )
                else:
                    self.outfile.write ('  (symbol "%s:%s" (extends "%s") (in_bom yes) (on_board yes)\n' % (self.symbols.out_basename, name, comp.parent.name) )
                
                
            field_id = 0

            self.write_field (ref_field, field_id) 
            field_id += 1

            name_field.value = name
            self.write_field (name_field, field_id) 
            field_id += 1

            #if comp.default_footprint:
            self.write_field (footprint_field, field_id) 
            field_id += 1
            footprint_field.pos.y -= 100

            sgdoc = comp.doc_fields[name]

            #if sgdoc.datasheet:
            footprint_field.name = "Datasheet"
            footprint_field.value = sgdoc.datasheet if sgdoc.datasheet else ""
            self.write_field (footprint_field, field_id) 
            field_id += 1
            footprint_field.pos.y -= 100

            if not is_alias and flat_unit and len(comp.units) > 1:
                footprint_field.name = "ki_locked"
                footprint_field.value = ""
                self.write_field (footprint_field, field_id) 
                field_id += 1

            if sgdoc.keywords:
                footprint_field.name = "ki_keywords"
                footprint_field.value = sgdoc.keywords
                self.write_field (footprint_field, field_id) 
                field_id += 1

            if sgdoc.description:
                footprint_field.name = "ki_description"
                footprint_field.value = sgdoc.description
                self.write_field (footprint_field, field_id) 
                field_id += 1

            #if not is_alias:
            if comp.fplist:
                footprint_field.name = "ki_fp_filters"
                footprint_field.value = ' '.join(comp.fplist)
                self.write_field (footprint_field, field_id) 
                field_id += 1

            #todo: user fields

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

        # 20201005
        self.outfile.write ('(kicad_symbol_lib (version 20200126) (generator symgen "2.0.0")\n')

        if self.symbols.components:
            for comp in self.symbols.components:
                if not comp.is_template:
                    self.draw_component(comp)

        self.outfile.write (')\n' )
        self.outfile.close()
