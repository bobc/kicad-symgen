import os

from sym_comp import *
from lib_symgen import *

class LibraryGenerator(object):
    """description of class"""

    def __init__(self):
        pass

    def GenerateLibrary(self, a_symbols):
        pass


class GenerateKicad(LibraryGenerator):

    def __init__(self):
        self.libfile = None
        self.docfile = None

        self.max_height = 0
        self.last_unit = None
        self.ref_pos= Point()
        self.name_pos = Point()
        
        return super(GenerateKicad, self).__init__()

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

        y_offset = align_to_grid (unit.unit_rect.size.y / 2, 50)

        if len(left_pins) + len(right_pins) > 0 :
            # align to horiz pins
            y = bb_horiz.pmax.y
            while (y+y_offset) % 100 != 0:
                y_offset -= 50
        return y_offset

    def check_pin_grid (self, comp, unit):
        for elem in comp.drawOrdered:
            params = elem[1]
            if params['unit'] == str(unit):
                if elem[0] == "X":
                    pos = self.get_pos (params, "pos")
                    length = int(params["length"])
                    orientation = params ["direction"]
        
                    if orientation == 'D':
                        if pos.y  % 100 != 0:
                            print "error: pin not on grid: %s %s" % (params["name"], pos)
                            self.num_errors += 1
                    elif orientation == 'U':
                        if pos.y % 100 != 0:
                            print "error: pin not on grid: %s %s" % (params["name"], pos)
                            self.num_errors += 1
                    elif orientation in ['L', "R"]:
                        if pos.x % 100 != 0:
                            print "error: pin not on grid: %s %s" % (params["name"], pos)
                            self.num_errors += 1
        
    def create_gate (self, unit_shape, num_inputs, num_outputs, demorgan):
        if self.symbols.symbol_style == SymbolStyle.ANSI:
            if demorgan == 1:
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
        elif self.symbols.symbol_style == SymbolStyle.IEC:
            gatedef = IecGate (num_inputs)
            gatedef.num_outputs = num_outputs
            if demorgan == 1:
                gatedef.type = unit_shape
            else:
                if unit_shape in ["and", "nand"]:
                    gatedef.type = "or"
                elif unit_shape in ["or", "nor"]:
                    gatedef.type = "and"
        else:
            gatedef = None

        return gatedef

    def find_pins (self, pin_list, direction, type=None):
        pins = []
        for pin in pin_list:
            # if pin.orientation == direction and pin.visible and (type is None or pin.type == type):
            if pin.orientation == direction and (type is None or pin.type == type):
                pins.append (pin)
        return pins

    def find_pins_with_label (self, pin_list, direction, type=None):
        pins = []
        for pin in pin_list:
            # if pin.orientation == direction and pin.visible and (type is None or pin.type == type):
            if pin.shape!=" " and pin.name!="~" and pin.orientation == direction and (type is None or pin.type == type) and len(pin.name)!=0:
                pins.append (pin)
        return pins

    def find_pins_non_stacked (self, pin_list, direction, type=None):
        pins = []
        for pin in pin_list:
            if pin.orientation == direction and (type is None or pin.type == type) and not pin.can_stack:
                pins.append (pin)
        return pins

    def test_size (self):
        for j in range (1,41):
            print "%s %s" % (j, self.get_scaled_fontsize(50, j))

    def get_scaled_fontsize (self, minsize, num_pins):
        size = max(minsize, num_pins / 5 * 25 )
        return min(size, 200)

    def get_template_pins (self, name):
        pins = []

        numeric_pins = True

        comp = self.symbols.icon_lib.getComponentByName(name)

        if comp:
            for elem in comp.draw['pins']:
                item = dict(elem)
                pin = Pin()
                pin.pos = Point (int(item['posx']), int (item['posy']))
                pin.name = item['name']
                pin.number = item['num']
                pin.orientation = item['direction']

                pin.shape = item['pin_type']
                pin.type = item['electrical_type']

                pins.append (pin)

                if not pin.number.isdigit():
                    numeric_pins = False

            if numeric_pins:
                # sort by num
                for passnum in range(len(pins)-1,0,-1):
                    for i in range(passnum):
                        if int(pins[i].number) > int(pins[i+1].number) :
                            temp = pins[i]
                            pins[i] = pins[i+1]
                            pins[i+1] = temp

        return pins

    def get_text_extent (self, pins, filter=None):
        bb = BoundingBox()
        for pin in pins:
            bb += pin.get_text_bounds()

        return bb

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
                    poly = PolyLine (convert_to_string(elem))
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

    def set_label_pos(self, sgcomp, unit):

        if sgcomp.settings.label_style == ls_floating:
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
            if sgcomp.settings.label_horiz_align == ha_left:
                self.name_pos.x = unit.unit_rect.left()
            else:
                self.name_pos.x = unit.unit_rect.right() - 200

            self.name_pos.y = y
        else: # ls_center
            self.ref_pos.x = 0
            self.ref_pos.y = 50

            self.name_pos.x = 0
            self.name_pos.y = -50

            sgcomp.settings.label_horiz_align = ha_center

    def set_power_unit_size (self, sgcomp, unit):
        #unit.set_width (400)

        if self.symbols.opt_power_unit_style == PowerStyle.BOX:
            if sgcomp.settings.label_style == ls_center:
                unit.unit_rect.size.y = 200    
            else:
                unit.unit_rect.size.y = 400    

            unit.unit_shape = "box"
            unit.elements[0].shape = "box"
            #unit.fill = NoFill
            #unit.fill = Background
        else:
            if sgcomp.settings.label_style == ls_center:
                # sgcomp.pin_names_inside
                # unit.unit_rect.size.y = 200    
                unit.unit_rect.size.y = sgcomp.units[0].unit_rect.size.y
            else:
                unit.unit_rect.size.y = 400    

            unit.unit_shape = "none"
            unit.elements[0].shape = "none"


    #
    #
    #
    def draw_pins (self, unit, pins, comp, unit_num, variant):
        for j,pin in enumerate(pins):
            if pin.orientation == 'R':
                pin.pos.y = self.pin_pos_left.y
                self.pin_pos_left.y -= 100
            elif pin.orientation == 'L':
                pin.pos.y = self.pin_pos_right.y
                self.pin_pos_right.y -= 100
                # todo: should be option?
                if pin.type == "T"  and self.symbols.opt_pin_qualifiers:
                    self.draw_pin_text (comp, unit_num, variant, pin, "&xdtri;")
            elif pin.orientation == 'D':
                pin.pos.x = self.pin_pos_top.x
                pin.pos.y = self.pin_pos_top.y + pin.length
                self.pin_pos_top.x += 100
            elif pin.orientation == 'U':
                pin.pos.x = self.pin_pos_bottom.x
                pin.pos.y = self.pin_pos_bottom.y - pin.length
                self.pin_pos_bottom.x += 100

            if pin.qualifiers and self.symbols.opt_pin_qualifiers:
                self.draw_pin_text (comp, unit_num, variant, pin, pin.qualifiers)

            pin.unit = unit_num
            pin.demorgan = variant
            #

            #if pin.orientation == 'D':
            #    if pin.pos.y - pin.length % 100 != 0:
            #        print "error: pin not on grid: %s %s" % (pin.name, pin.pos)
            #        self.num_errors += 1
            #elif pin.orientation == 'U':
            #    if pin.pos.y + pin.length % 100 != 0:
            #        print "error: pin not on grid: %s %s" % (pin.name, pin.pos)
            #        self.num_errors += 1

        #

        if unit.template:
            template_pins = self.get_template_pins (unit.template)
            left_pins = self.find_pins (template_pins, "R")
            right_pins = self.find_pins (template_pins, "L")

            l_pin = 0
            r_pin = 0

            ##
            for pin in pins:
                if pin.type !=" " :
                    if pin.orientation == 'R':
                        if l_pin < len(left_pins):
                            pin.pos = left_pins[l_pin].pos
                            l_pin += 1
                        else:
                            print "warning: pin %s not found in template %s" % (pin.number, unit.template)
                    elif pin.orientation == 'L':
                        if r_pin < len(right_pins):
                            pin.pos = right_pins[r_pin].pos
                            r_pin += 1
                        else:
                            print "warning: pin %s not found in template %s" % (pin.number, unit.template)

        # align pins (right)
        right_pins = self.find_pins (pins, "L")
        if len(right_pins)>0:
            if right_pins[0].align == "C":
                # need to force alignment to 100 mil grid?

                height = unit.unit_rect.size.y/100 *100
                #top_y = 100 * (len(right_pins)-1) / 2
                top_y = (right_pins[0].pos.y - right_pins[-1].pos.y) / 2
                top_y = top_y - height / 2

                dy = top_y - right_pins[0].pos.y
                dy = align_to_grid (dy, 50)
                j = 0
                for pin in pins:
                    if pin.orientation == 'L':
                        pin.pos.y += dy  # top_y - j * 100
                        j += 1

        # align pins (bottom)
        _pins = self.find_pins_non_stacked (pins, "U")
        if len(_pins) > 0:
            if _pins[0].align == "C":
                # need to force alignment to 100 mil grid?
                width = len(_pins) * 100 
                if len(_pins) % 2 == 0:
                    x_offset = -width/2 + 100
                else:
                    x_offset = -width/2 + 50
                j = 0
                for k,pin in enumerate(pins):
                    if pin.orientation == 'U':
                        pin.pos.x = j * 100 + x_offset
                        if pins[k].can_stack:
                            # passive, invisible
                            pin.shape = "N"
                            pin.type = "P"

                        if k < len(pins)-1 and pins[k+1].can_stack:
                            pass
                        else:
                            j += 1

        # align pins (top)
        _pins = self.find_pins_non_stacked (pins, "D")
        if len(_pins) > 0:
            if _pins[0].align == "C":
                # need to force alignment to 100 mil grid?
                width = len(_pins) * 100
                if len(_pins) % 2 == 0:
                    x_offset = -width/2 + 100
                else:
                    x_offset = -width/2 + 50
                j = 0
                for k,pin in enumerate(pins):
                    if pin.orientation == 'D':
                        pin.pos.x = j * 100 + x_offset
                        if pins[k].can_stack:
                            # passive, invisible
                            pin.shape = "N"
                            pin.type = "P"

                        if k < len(pins)-1 and pins[k+1].can_stack:
                            pass
                        else:
                            j += 1

        for pin in pins:
            if pin.type != " ":
                comp.drawOrdered.append( pin.get_element() )

    def draw_element (self, sgcomp, xunit, element, comp, unit, variant):

        fontsize = 50

        #self.test_size()

        left_pins = self.find_pins (element.pins, "R")
        right_pins = self.find_pins (element.pins, "L")

        top_pins = self.find_pins_with_label (element.pins, "D")
        bottom_pins = self.find_pins_with_label (element.pins, "U")

        xunit.unit_rect.pos.x = -xunit.unit_rect.size.x / 2
        xunit.unit_rect.size.x = xunit.unit_rect.size.x

        box_size = Point ()
        box_size.x = xunit.unit_rect.size.x
        box_size.y = max (len(left_pins), len(right_pins)) * 100

        # apply a min height (power units only?)
        # should apply to unit?
        # shape, template
        min_height = 0
        
        if sgcomp.settings.label_style == ls_center:
            min_height = 200

        #if min_height == 0:
        #    offset = 200
        #else:
        #    offset = 150

        top_margin = 0
        if len(top_pins) > 0 or (element.shape == "control" and element.label):
            extent = self.get_text_extent (top_pins)
            if len(top_pins) > 0:
                min_height += align_to_grid(extent.height+99,100)  # 200

            if len(left_pins)+len(right_pins) != 0:
                if sgcomp.settings.pin_length == 150:
                    top_margin = 0
                else:
                    top_margin = 50                    

            if element.shape == "control" and element.label:
                top_margin = 100

        bottom_margin = 0
        if len(bottom_pins) > 0:
            extent = self.get_text_extent (bottom_pins)

            min_height += align_to_grid(extent.height+99,100) # 200

            if len(left_pins)+len(right_pins) != 0:
                if sgcomp.settings.pin_length == 150:
                    bottom_margin = 0
                else:
                    bottom_margin = 50                    

        #if box_size.y == 0:
        #    box_size.y = min_height # min box height

        #if xunit.is_power_unit:
        #    #box_size.y = xunit.unit_rect.size.y

        #    while (box_size.y % 100) != 0:
        #        box_size.y += 50

        #    if (sgcomp.pin_length % 100) == 0:
        #        # even
        #        while (box_size.y % 200) != 0:
        #            box_size.y += 100
        #    else:
        #        while (box_size.y % 200) == 0:
        #            box_size.y += 100

        if element.shape == "control":
            box_size.y += 100

        box_size.y = max (box_size.y + top_margin + bottom_margin, min_height)

        #if xunit.is_power_unit:
        if len(left_pins)+len(right_pins) == 0:
            if len(top_pins) + len(bottom_pins) != 0:
                while (box_size.y / 2 + top_pins[0].length) % 100 != 0:
                    box_size.y += 50
                    top_margin += 25

        # update the actual unit size (for label pos)
        xunit.unit_rect.size.y = -self.cur_pos.y + box_size.y 

        #print "element %s %s unit_size %d  box_size %d" % (element.shape, "P" if xunit.is_power_unit else " ", 
        #                                                   xunit.unit_rect.size.y, box_size.y)

        #offset = Point (0,50)

        # draw element outline
        if element.shape == "box":
            rect = Rect()
            rect.p1.x = -box_size.x/2
            rect.p1.y = self.cur_pos.y

            rect.p2.x = box_size.x/2
            rect.p2.y = self.cur_pos.y - box_size.y

            rect.unit = unit
            rect.demorgan = variant
            rect.fill = xunit.fill
            rect.pensize = sgcomp.settings.box_pen
            comp.drawOrdered.append( rect.get_element() )

        elif element.shape == "control":
            poly = PolyLine ()
            poly.unit = unit
            poly.demorgan = variant
            poly.fill = xunit.fill
            poly.pensize = sgcomp.settings.box_pen
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
           
            if element.shape == "control":
                pos = Point (0, self.cur_pos.y - fontsize - 25)
                align_horiz = AlignCenter
                align_vert  = AlignBottom
            else:
                pos = Point (0, self.cur_pos.y - box_size.y/2).Sub (Point(fontsize/2, fontsize/2))
                align_horiz = AlignLeft
                align_vert  = AlignBottom

            draw_text (comp, unit, variant, pos, element.label, fontsize, align_horiz, align_vert)



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
                # self.pin_pos_bottom.y = self.cur_pos.y - self.max_height
                self.pin_pos_top.y = 0
                self.pin_pos_bottom.y = self.cur_pos.y - box_size.y

                #if sgcomp.label_style == "fixed": 
                #    #self.pin_pos_bottom.y = -600
                #    self.pin_pos_top.y = -150
                #    self.pin_pos_bottom.y = -450
                #else:
                #    self.pin_pos_top.y = 0
                #    self.pin_pos_bottom.y = -400

            elif xunit.unit_shape == "box":
                self.pin_pos_top.y = 0
                self.pin_pos_bottom.y = self.cur_pos.y - box_size.y
            else:
                pass

        self.draw_pins (xunit, element.pins, comp, unit, variant)

        #
        for group in element.groups:
            extent = self.get_text_extent (group.pins)

            group_size = Point()
            group_size.x = max (200, int(extent.width) + self.symbols.def_name_offset)      ##todo: name_offset should be sgcomp field
            group_size.y = len(group.pins) * 100

            group_pos = Point()
            if group.pins[0].orientation == "R":
                group_pos.x = -box_size.x/2
            else:
                group_pos.x = box_size.x/2 - group_size.x

            group_pos.y = group.pins[0].pos.y + 50

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
                draw_text (comp, unit, variant, pos, type_text, fontsize )
                offset = 50
            else:
                offset = 10

            if group.qualifiers:
                if group.pins[0].orientation == "R":
                    pos.x = group_pos.x + group_size.x - TextLength(group.qualifiers, fontsize) - 25
                else:
                    pos.x = box_size.x/2 - group_size.x + 25

                pos.y = group_pos.y - group_size.y/2 - 25
                draw_text (comp, unit, variant, pos, group.qualifiers, fontsize)
            
            if group.label:
                size = self.get_scaled_fontsize (fontsize, len(group.pins) ) 
                if group.pins[0].orientation == "R":
                    pos.x = group_pos.x + group_size.x + offset
                else:
                    pos.x = box_size.x/2 - group_size.x - offset - TextLength(group.label, size)
                pos.y = group_pos.y - group_size.y/2 - 25
                draw_text (comp, unit, variant, pos, group.label, size)

        # add icons
        if self.symbols.icon_lib and len(xunit.icons)>0:
            k = 0
            y_pos = self.cur_pos.y - (-self.cur_pos.y + box_size.y) / 2
            if len(xunit.icons) > 1:
                icons_y_extent = len(xunit.icons) * 125 + (len(xunit.icons)-1)*25
            else:
                icons_y_extent = 0

            for icon_name in xunit.icons:
                comp_icon = self.symbols.icon_lib.getComponentByName(icon_name)
                if comp_icon:
                    style = StyleAttributes()
                    # todo: not sure this is right way
                    if xunit.unit_shape == "box":
                        style.fill = xunit.fill
                    else:
                        style.fill = xunit.fill
                    style.pensize = sgcomp.settings.box_pen
                    copy_icon (comp, comp_icon, unit, Point(0, y_pos -k * 150 + icons_y_extent/2), style=style)
                    k += 1
                else:
                    print "error: unknown icon %s " % icon_name
                    self.num_errors += 1

        if self.symbols.icon_lib and xunit.template:
            comp_icon = self.symbols.icon_lib.getComponentByName(xunit.template)
            style = StyleAttributes()
            #style.fill = xunit.fill
            if comp_icon:
                copy_icon (comp, comp_icon, unit, Point(0, 0), style=style)

        #
        #if self.label_style == "floating":
        #    self.max_height = max (self.max_height, xunit.unit_rect.size.y)
    
        #    if xunit.unit_shape == "box":
        #        margin = 50
        #    else:
        #        margin = 50 # ??

        #    y = 0 + margin
        #    if y > self.ref_pos.y:
        #        self.ref_pos.x = -box_size.x/2
        #        self.ref_pos.y = y

        #    y = -xunit.unit_rect.size.y - margin
        #    if y < self.name_pos.y:
        #        self.name_pos.x = -box_size.x/2
        #        self.name_pos.y = y
        #endif

        return box_size.y

    def draw_unit (self, sgcomp, comp, unit):
        # type: (SgComponent, Component, IecSymbol) -> None
        assert isinstance(sgcomp, SgComponent)
        assert isinstance(unit, IecSymbol)

        #debug
        #print "unit %d %s %s w=%s" % (self.unit_num, unit.unit_shape, "power" if unit.is_power_unit else "", unit.unit_rect.size.x)

        self.pin_pos_left = Point()
        self.pin_pos_left.x = -unit.unit_rect.size.x / 2
        self.pin_pos_left.y = 0

        self.pin_pos_right = Point()
        self.pin_pos_right.x = unit.unit_rect.size.x / 2
        self.pin_pos_right.y = 0

        self.pin_pos_top = Point()

        self.pin_pos_bottom = Point()

        #? self.label_style = "floating"

        if unit.unit_shape in [ "box", "none", "power"]:

            #
            if unit.is_power_unit:
                self.set_power_unit_size (sgcomp, unit)

            if unit.unit_rect.size.x == 0:
                # set width
                # width = unit.unit_rect.size.x
                bbs = {}
                bbs ['L'] = BoundingBox()
                bbs ['R'] = BoundingBox()
                bbs ['U'] = BoundingBox()
                bbs ['D'] = BoundingBox()

                count={}
                count ['L'] = 0
                count ['R'] = 0
                count ['U'] = 0
                count ['D'] = 0

                for element in unit.elements:
                    for pin in element.pins:
                        bb = pin.get_text_bounds()
                        bbs[pin.orientation] += bb
                        count[pin.orientation] += 1

                count ['U'] = len(self.find_pins_non_stacked (element.pins, 'U'))
                count ['D'] = len(self.find_pins_non_stacked (element.pins, 'D'))

                width = max (bbs['L'].width, bbs['R'].width) * 2 + max (count['U'], count['D']) * 100

                # round to multiple of 100
                width = int(round(width))
                width += width % 100

                # allow for pin_len
                width += 2 * ((width/2 + sgcomp.settings.pin_length) % 100)

                unit.set_width (width)
            
            self.pin_pos_left.x = -unit.unit_rect.size.x / 2
            self.pin_pos_right.x = unit.unit_rect.size.x / 2

            # update L/R pin pos
            for element in unit.elements:
                for pin in element.pins:
                    assert isinstance(pin, Pin)
                    if pin.orientation == "R":
                        if pin.type == "N":
                            pin.pos.x = self.pin_pos_left.x
                        else:
                            pin.pos.x = self.pin_pos_left.x - pin.length
                    elif pin.orientation == "L":
                        if pin.type == "N":
                            pin.pos.x = align_to_grid(self.pin_pos_right.x, 100)
                        else:
                            pin.pos.x = self.pin_pos_right.x + pin.length

            #self.cur_pos = Point(0,50)
            self.cur_pos = Point(0,0)

            # draw each element
            for element in unit.elements:
                for pin in element.pins:
                    if "C" in pin.shape:
                        comp.definition['text_offset'] = str(self.symbols.def_extra_offset)
                        break
                        
                # 
                variant_from = 1
                variant_to = 1+self.units_have_variant
                if unit.is_power_unit:
                    variant_from = 0
                    variant_to = 0

                for variant in range (variant_from, variant_to+1):
                    self.pin_pos_top.x = 0
                    self.pin_pos_bottom.x = 0
                    elem_height = self.draw_element (sgcomp, unit, element, comp, self.unit_num, variant) # self.units_have_variant

                self.cur_pos.y -= elem_height

            if unit.is_overlay:
                self.set_label_pos(sgcomp, self.last_unit) # ??
            else:
                offset = Point()
                # offset.y = self.align_to_grid (unit.unit_rect.size.y/2, 100)
                offset.y = self.align_unit (unit)
                self.move_items (comp, self.unit_num, offset)
                unit.unit_rect.pos.y = offset.y
                # move labels?
                if not unit.is_power_unit:
                    self.set_label_pos(sgcomp, unit)

                #
                self.check_pin_grid (comp, self.unit_num)

        elif unit.unit_shape in ["and", "nand", "or", "nor", "xor", "xnor", "not", "buffer"]:

            #
            # pins
            #temp = self.pin_length

            sgcomp.settings.pin_length = 150

            element = unit.elements[0]
            
            unit_pins = []
            for pin in element.pins:
                if pin.type != " ":
                    unit_pins.append (pin)


            #? self.label_style = "fixed"

            self.ref_pos.x = 0
            self.ref_pos.y = 50

            self.name_pos.x = 0
            self.name_pos.y = -50

            sgcomp.settings.label_horiz_align = ha_center

            #
            num_inputs=0
            num_outputs=0
            other_pins = []
            for pin in unit_pins:
                if pin.is_input():
                    num_inputs+=1
                elif pin.is_output():
                    num_outputs+=1
                else:
                    other_pins.append (pin)
            #num_outputs = len(unit_pins) - num_inputs

            #if num_inputs != len(unit_pins) - num_outputs:
            #    print "error: wrong number of input pins: expected %d got %d" % (len(unit_pins)-1, num_inputs)
            #    self.num_errors += 1
            #    #continue

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
            
            # demorgan    variant 
            #        0    1
            
            #        1    [ 0 (common) ]
            #               1 (first)
            #               2 (second)

            for variant in range (1, 1+demorgan+1):

                gatedef = self.create_gate (unit.unit_shape, num_inputs, num_outputs, variant)

                #
                gatedef.fill = unit.fill
                gatedef.qualifiers = unit.qualifiers
                gatedef.add_gate_graphic (comp, self.unit_num, variant)
            
                inputs_pos = gatedef.get_input_positions()
                outputs_pos = gatedef.get_output_positions()
        
                if variant==1:
                    # normal variant
                    input_shape = " "
                    output_shape = " "
                    if unit.unit_shape in ['nand', 'nor', 'xnor', 'not']:
                        output_shape = "I"
                else:
                    # de morgan equivalent
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
                    unit.unit_rect.size.y = gatedef.height
                    
                    #self.y_pin_extent = self.max_height
                else:
                    # setup size for power unit ?
                    self.pin_pos_top.x = 0
                    #self.pin_pos_top.y = 0

                    self.pin_pos_bottom.x = 0
                    #self.pin_pos_bottom.y = -500    # todo: depends on pin_len

                    if self.symbols.opt_power_unit_style == PowerStyle.BOX:
                        #? self.max_height = 600
                        pass
                        # unit.unit_rect.size.y = self.max_height
                        #self.y_pin_extent = self.max_height
                    else:
                        #? self.max_height = 200
                        pass
                        # unit.unit_rect.size.y = self.max_height

                if num_inputs > len(inputs_pos):
                    print "error: too many input pins, expected %d got %d" % ( len(inputs_pos), num_inputs)
                    self.num_errors += 1
            
    #            if comp.name=="74LS136":
    #                print "oops"

                if self.symbols.icon_lib and len(unit.icons)>0:
                    for icon_name in unit.icons:
                        comp_icon = self.symbols.icon_lib.getComponentByName(icon_name)
                        if comp_icon:
                            style = StyleAttributes()
                            style.fill = unit.fill
                            style.pensize = sgcomp.settings.box_pen
                            copy_icon (comp, comp_icon, self.unit_num, gatedef.get_center(), style=style)
                        else:
                            print "error: unknown icon %s " % icon_name 
                            self.num_errors += 1

                j=0
                for pin in unit_pins:
                    if pin.is_input() and j<len(inputs_pos):
                        pin.length = sgcomp.settings.pin_length + gatedef.offsets[j]
                        pin.unit = self.unit_num
                        pin.demorgan = variant
            
                        if unit.unit_shape == "buffer" and j==1:
                            dy = align_to_grid(abs(inputs_pos[j].y)+99, 100)
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
                        # pin text
                        if pin.qualifiers and self.symbols.opt_pin_qualifiers:
                            self.draw_pin_text (comp, self.unit_num, variant, pin, pin.qualifiers) # -1 ?

                j = 0
                for pin in unit_pins:
                    if pin.is_output():
                        pin.length = sgcomp.settings.pin_length
                        pin.unit = self.unit_num
                        pin.demorgan = variant
                        pin.orientation = "L"
                        if j==0:
                            pin.shape = output_shape
                        else:
                            pin.shape = "I" if output_shape == " " else " "

                        pin.pos.x = outputs_pos[j].x + sgcomp.settings.pin_length
                        pin.pos.y = outputs_pos[j].y       
                        j += 1
                        #pins.append (pin)
                        comp.drawOrdered.append( pin.get_element () )

                        # pin text
                        if pin.qualifiers and self.symbols.opt_pin_qualifiers:
                            self.draw_pin_text (comp, self.unit_num, variant, pin, pin.qualifiers) # -1 ?

                # 
                self.draw_pins (unit, other_pins, comp, self.unit_num, variant)


            ##
            #self.pin_length = temp

    draw_unit.__annotations__ = {'sgcomp': SgComponent, 'comp': Component, 'unit': IecSymbol, 'return': None}

    def draw_pin_text (self, comp, unit, variant, pin, text):
        
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

        draw_text (comp, unit, variant, pos, text, fontsize)

    def draw_component (self, sgcomp):
        assert isinstance (sgcomp, SgComponent)

        self.max_height = 0
        self.last_unit = None #todo

        self.ref_pos= Point()
        self.ref_pos.x = -sgcomp.settings.box_width/2
        self.ref_pos.y = 0

        self.name_pos = Point()
        self.name_pos.x = -sgcomp.settings.box_width/2
        self.name_pos.y = 0


        comments = []
        comments.append ("#\n")
        comments.append ("# " + sgcomp.name + "\n")
        comments.append ("#\n")

        component_data = []
        # units are not interchangeable
        component_data.append("DEF %s %s 0 40 Y Y 1 L N" % (sgcomp.name, sgcomp.ref) )      
        component_data.append("F0 \"U\" 0 0 50 H V C CNN")
        component_data.append("F1 \"74469\" 0 -200 50 H V C CNN")
        component_data.append("F2 \"\" 0 0 50 H I C CNN")
        component_data.append("F3 \"\" 0 0 50 H I C CNN")
        component_data.append("DRAW")
        component_data.append("ENDDRAW")
        component_data.append("ENDDEF")

        comp = Component(component_data, comments, self.documentation)
        comp.fields [0]['reference'] = sgcomp.ref

        comp.fields [1]['name'] = sgcomp.name

        comp.definition['reference'] = sgcomp.ref
        comp.definition['name'] = sgcomp.name

        if sgcomp.settings.pin_names_inside:
            comp.definition['text_offset'] = "0"
        else:
            comp.definition['text_offset'] = str(self.symbols.def_name_offset)
        
        for s in sgcomp.fplist:
            comp.fplist.append (s)

        for key in sgcomp.doc_fields:
            sgdoc = sgcomp.doc_fields[key]
              
            doc_fields = OrderedDict()
            if sgdoc.description:
                doc_fields ['description'] = sgdoc.description
            if sgdoc.keywords:
                doc_fields ['keywords'] = sgdoc.keywords
            if sgdoc.datasheet:
                doc_fields ['datasheet'] = sgdoc.datasheet
            self.lib.documentation.components[key] = doc_fields
            if key != sgcomp.name:
                comp.aliases[key] = self.lib.documentation.components[key]

        if sgcomp.default_footprint:
            comp.fields [2]['posx'] = "0"
            comp.fields [2]['posy'] = "0"
            comp.fields [2]['visibility'] = "I"
            comp.fields [2]['name'] = sgcomp.default_footprint

        # check footprints
        match = None
        if self.symbols.footprints:
            found = False
            if sgcomp.default_footprint:
                if not sgcomp.default_footprint.strip ('"') in self.symbols.footprints:
                    print "error: (%s) footprint not found: %s" % (sgcomp.name, sgcomp.default_footprint)
                    self.num_errors += 1
                elif self.symbols.verbose:
                    print ("found: %s" % sgcomp.default_footprint.strip ('"'))

            if sgcomp.fplist:
                for filter in sgcomp.fplist:
                    fp = filter.replace ("?", ".")
                    fp = fp.replace ("*", ".*")
                    regex = re.compile(fp)
                    match = [m.group(0) for l in self.symbols.footprints for m in [regex.search(l)] if m]

                    if not match:
                        print "error: (%s) no matches for filter: %s" % (sgcomp.name, filter)
                        self.num_errors += 1
                    elif self.symbols.verbose:
                        print ("found: %s" % match)

        if len(sgcomp.fplist) == 1 and not sgcomp.default_footprint:
            print "error: (%s) footprint field should contain default footprint (%s)" % (comp.name, match if match and len(match)<=2 else sgcomp.fplist[0])
            self.num_errors += 1

        #
        if sgcomp.user_fields:
            for f in sgcomp.user_fields:
                comp.fields.append (f)

        #
        # draw units

        self.unit_num = 1
        self.units_have_variant = 0

        for unit in sgcomp.units:
            self.draw_unit (sgcomp, comp, unit)

            self.last_unit = unit
            self.unit_num += 1


        #
        comp.fields [0]['posx'] = str(self.ref_pos.x)
        comp.fields [0]['posy'] = str(self.ref_pos.y)

        comp.fields [1]['posx'] = str(self.name_pos.x)
        comp.fields [1]['posy'] = str(self.name_pos.y)

        # if field is positioned on the right, justify text on left
        if sgcomp.settings.label_horiz_align == ha_right:
            comp.fields [1]['htext_justify' ] = ha_left

        values = []
        values.append (sgcomp.name)
        values.append (sgcomp.ref)
        values.append ("0")     # not used
        values.append ("40")    # text offset
        values.append ("Y")     # draw pin number    
        values.append ("Y")     # draw pin name
        values.append (str(self.unit_num))   # unit count
        values.append ("L")     # L=units are not interchangeable
        values.append ("N")     # option flag ( Normal or Power)

        comp.definition['unit_count'] = str(len(sgcomp.units))
        if len(sgcomp.units) == 1 :
            comp.definition['units_locked'] = "F"

        cur_comp = self.lib.getComponentByName(comp.name)
    
        if cur_comp:
            print "replacing: " + comp.name
            self.lib.removeComponent (comp.name)
        else:
            print "adding: " + comp.name
        
        self.lib.addComponent (comp)


    def GenerateLibrary (self, a_symbols):

        self.symbols = a_symbols
        self.num_errors = 0

        self.libfile = os.path.join (self.symbols.out_path, self.symbols.out_basename + ".lib")
        self.docfile = os.path.join (self.symbols.out_path, self.symbols.out_basename + ".dcm")

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

        obsolete = []

        if self.symbols.components:
            for comp in self.symbols.components:
                if not comp.is_template:
                    self.draw_component(comp)

                    for name in comp.doc_fields:
                        if (comp.doc_fields[name].description and 
                                "obsolete" in comp.doc_fields[name].description.lower() ):
                            obsolete.append (name+ ": " + comp.doc_fields[name].description)

            if obsolete:
                print ("")
                print ("Obsolescence report")
                print ("-------------------")
                print ("The following components are marked for 'Obsolete' status:")
                print ("")
                for name in obsolete:
                    print ("%s" % name)
                print ("")
        ###

        self.lib.save (filename = self.libfile)

