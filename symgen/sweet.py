
from sym_utils_v6 import *

def convert_elect_type_to_v5 (elec_type):
    if elec_type == 'input':
        return 'I'
    elif elec_type == 'output':
        return 'O'
    elif elec_type == 'bidirectional':
        return 'B'
    elif elec_type == 'tri_state':
        return 'T'
    elif elec_type == 'passive':
        return 'P'
    elif elec_type == 'open_collector':
        return 'C'
    elif elec_type == 'open_emitter':
        return 'E'
    elif elec_type == 'unconnected':
        return 'N'
    elif elec_type == 'unspecified':
        return 'U'
    elif elec_type == 'power_in':
        return 'W'
    elif elec_type == 'power_out':
        return 'w'

def convert_pin_shape_to_v5 (pin_shape):
    if pin_shape == 'line':
        return ' '
    elif pin_shape == 'clock':
        return 'C'
    elif pin_shape == 'inverted':
        return 'I'
    elif pin_shape == 'falling_edge':
        return 'F'
    else:
        return ' '

    #also : 
    #   inverted_clock 
    #   input_low 
    #   clock_low 
    #   output_low 
    #   edge_clock_high 
    #   non_logic

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

    #also : 
    #   inverted_clock 
    #   input_low 
    #   clock_low 
    #   output_low 
    #   edge_clock_high 
    #   non_logic

def convert_direction (direction):
    if direction == 'R':
        return 0
    elif direction == 'U':
        return 90
    elif direction == 'L':
        return 180
    elif direction == 'D':
        return 270

def apply_format (comp, name):
    format = [x for x in comp.settings.pin_name_formats if re.match(x[0], name) ]

    if format:
        p = re.sub (format[0][0], format[0][1], name, flags=re.IGNORECASE)
        #print (f"{name} {p}")
        return p
    else:
        return name

def convert_fill (s):
    fill = "none"
    if   s == 'N':  fill = "none"
    elif s == 'F':  fill = "outline"
    elif s == 'f':  fill = "background"
    return fill

def convert_fill_to_v5 (s):
    
    fill = "N"

    if   s == 'none':       fill = "N"
    elif s == 'outline':    fill = "F"
    elif s == 'background': fill = "f"
        
    return fill

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
        self.text_size.x = mil_to_mm(field['text_size'])
        self.text_size.y = self.text_size.x

        self.visible = field['visibility'] == 'V'

        self.h_justify = field['htext_justify']

        self.v_justify = field['vtext_justify'][0]
        self.bold   = field['vtext_justify'][1] != 'N'
        self.italic = field['vtext_justify'][2] != 'N'

    def get_sexpr (self, default_empty = False):
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


class SweetBase(object):

    key = ' '
    unit=0
    demorgan=1
    pensize=10
    fill = NoFill

    def __init__(self, s=None):
        self.key = ' '
        self.unit=0
        self.demorgan=1
        self.pensize=10
        self.fill='none'

class SweetPin (SweetBase):

    opt_alternate_names = False

    def __init__(self, pin, alternate_names = False):

        self.opt_alternate_names = alternate_names
        self.alt_name_char = '/'

        self.elec_type = pin['electrical_type']
        self.pin_type = pin['pin_type']
        self.posx = mil_to_mm(pin['posx']) 
        self.posy = mil_to_mm(pin['posy'])
        self.direction = pin['direction']

        self.length = mil_to_mm(pin['length'])

        self.unit = int(pin['unit'])
        self.demorgan = int(pin['convert'])

        if self.opt_alternate_names and self.alt_name_char in pin['name']:
            names = pin['name'].split (self.alt_name_char)
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
        self.name_text_size.x = mil_to_mm(pin['name_text_size'])
        self.name_text_size.y = mil_to_mm(pin['name_text_size'])

        self.num = pin['num'] 
        self.num_text_size = Point()
        self.num_text_size.x = mil_to_mm(pin['num_text_size'])
        self.num_text_size.y = mil_to_mm(pin['num_text_size'])

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
        
    def get_sexpr(self, sgcomp):
        # TODO: add pin effects
        # '    (pin %s %s (at %s %s %s) (length %s) (name "%s" (effects (font (size %s %s)) %s)) (number "%s" (effects (font (size %s %s)) %s)) %s)\n' 

        s = '    (pin {} {} (at {:g} {:g} {}) (length {}) {}\n'.format (
                self.elec_type, self.pin_type, 
                self.posx, self.posy, self.direction,
                self.length,
                "hide" if not self.visible else ""
                ) 

        s += '      (name "{}" {})\n'.format (
                apply_format (sgcomp, self.name), 
                self.name_effects.get_sexpr(False)
                ) 

        s += '      (number "{}" {})\n'.format (
                self.num,
                self.num_effects.get_sexpr(False)
                ) 
            

        if self.alternate_names:
            for alt_name in self.alternate_names:
                s += '      (alternate "{}" {} {})\n'.format (
                       apply_format (sgcomp, alt_name.name), 
                       convert_elect_type_to_sweet(alt_name.type),
                       convert_pin_type_to_sweet(alt_name.shape)
                       ) 
                    

        s += '      )\n'
        return s


class SweetRectangle (SweetBase):

    def __init__(self, rect):
        # 'startx','starty','endx','endy','thickness','fill']

        self.unit = int(rect['unit'])
        self.demorgan = int(rect['convert'] )

        self.start = Point (mil_to_mm(rect['startx']), mil_to_mm(rect['starty']) )
        self.end = Point (mil_to_mm(rect['endx']), mil_to_mm(rect['endy']) )

        self.thickness = mil_to_mm (rect['thickness'])
        self.fill = convert_fill(rect['fill'])
        
    def get_sexpr(self):

        s = '    (rectangle (start {:g} {:g}) (end {:g} {:g})\n'.format (
                    self.start.x, self.start.y,
                    self.end.x, self.end.y,
                    )
                    
        s += '      (stroke (width {:g})) (fill (type {}))\n' .format ( self.thickness, self.fill )
        s += '    )\n'

        return s

class SweetPoly (SweetBase):

    def __init__(self, poly):
        # ['point_count','unit','convert','thickness','points','fill']

        self.unit = int(poly['unit'])
        self.demorgan = int(poly['convert'] )

        #
        self.points = []
        j = 0
        pts= poly['points']
        while j < len(pts)/2:
            self.points.append (Point (mil_to_mm(pts[j*2]), mil_to_mm(pts[j*2+1]) ))
            j += 1

        #
        self.thickness = mil_to_mm (poly['thickness'])
        self.fill = convert_fill(poly['fill'])
        

    def get_sexpr(self):

        s  = '    (polyline\n'
        s += '      (pts\n'

        for p in self.points :
            s += '      (xy {:g} {:g})\n'.format (p.x, p.y)

        s += '      )\n'
        s += '      (stroke (width {:g})) (fill (type {}))\n' .format ( self.thickness, self.fill )
        s += '    )\n'

        return s

class SweetArc (SweetBase):

    def __init__(self, arc):
        # ['posx','posy','radius','start_angle','end_angle', 'startx','starty','endx','endy']

        self.unit = int(arc['unit'])
        self.demorgan = int(arc['convert'] )

        self.center = Point (mil_to_mm(arc['posx']), mil_to_mm(arc['posy']) )
        self.radius = mil_to_mm(arc['radius'])

        self.start_angle = int(arc['start_angle']) / 10
        self.end_angle = int(arc['end_angle']) / 10

        self.start = Point (mil_to_mm(arc['startx']), mil_to_mm(arc['starty']) )
        self.end   = Point (mil_to_mm(arc['endx']), mil_to_mm(arc['endy']) )

        self.thickness = mil_to_mm (arc['thickness'])
        self.fill = convert_fill(arc['fill'])
        

    def get_sexpr(self):

        s = '    (arc (start {:g} {:g}) (end {:g} {:g}) (radius (at {:g} {:g}) (length {:g}) (angles {:g} {:g}))\n'.format (
                    self.start.x, self.start.y,
                    self.end.x, self.end.y,
                    self.center.x, self.center.y,
                    self.radius,
                    self.start_angle, self.end_angle
                    )
        s += '      (stroke (width {:g})) (fill (type {}))\n' .format ( self.thickness, self.fill )
        s += '    )\n'
        return s

class SweetText (SweetBase):

    def __init__(self, text):
        # ['direction','posx','posy','text_size','text_type','unit','convert','text', 'italic', 'bold', 'hjustify', 'vjustify']

        self.unit = int(text['unit'])
        self.demorgan = int(text['convert'] )

        self.pos = Point (mil_to_mm(text['posx']), mil_to_mm(text['posy']) )
        self.direction = int(int (text['direction'] )/10)

        self.effects = Effects()
        self.effects.init (mil_to_mm(text['text_size']), True, text['hjustify'], text['vjustify'])
        self.effects.bold   = text['bold'] != 'N'
        self.effects.italic = text['italic'] != 'N'

        self.text = text['text']
        self.text_type = text['text_type']

        

    def get_sexpr(self):

        s = '    (text "{}" (at {:g} {:g} {:g})\n'.format (
                    self.text,
                    self.pos.x, self.pos.y, self.direction
                    )
        s += '      ' + self.effects.get_sexpr() + '\n'
        s += '    )\n'
        return s

class SweetCircle (SweetBase):

    def __init__(self, circle):
        # ['posx','posy','radius','unit','convert','thickness','fill']

        self.unit = int(circle['unit'])
        self.demorgan = int(circle['convert'] )

        self.pos = Point (mil_to_mm(circle['posx']), mil_to_mm(circle['posy']) )
        self.radius = mil_to_mm(circle['radius'])

        self.thickness = mil_to_mm (circle['thickness'])
        self.fill = convert_fill(circle['fill'])
        

    def get_sexpr(self):

        s = '    (circle (center {:g} {:g}) (radius {:g}) (stroke (width {:g})) (fill (type {})))\n'.format (
                    self.pos.x, self.pos.y, 
                    self.radius,
                    self.thickness, self.fill 
                    )
        return s

class SweetField (SweetBase):

    def __init__(self, name=None, value=None):

        self.pos = Point()
        self.orientation = 0
        self.name = name
        self.value = value
        self.id = 0
        self.effects = Effects()



