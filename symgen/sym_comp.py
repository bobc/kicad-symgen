
from collections import OrderedDict

from sym_drawing import *

class ComponentDef:
    name = "name"
    ref = "ref"
    offset = 0
    show_pin_number = True
    show_pin_name = True
    num_units = 0
    locked = "F"
    power_sym = False

    def __init__(self):
        pass


class ComponentField:
    number=0
    value="~"
    pos=Point()
    font_size=50
    angle="H"
    visible=False    
    horiz_alignment = "C"
    vert_alignment = "C"
    italic = False
    bold = False

    def __init__(self):
        pass


class LogicDesc:
    id=""
    gates=0
    description = ""
    input_type = ""
    output_type = ""
    technologies = OrderedDict ()

    def __init__(self, tokens):
        self.id=tokens[0].strip()
        if tokens[1]!="":
            self.gates=int(tokens[1])
        self.description=tokens[2].strip()

        self.input_type=""
        self.output_type=""
        self.technologies = OrderedDict ()

        if len(tokens) > 3:
            self.input_type=tokens[3]
            self.output_type=tokens[4]

            if len(tokens) > 5:
                j = 5
                while j < len(tokens):
                    if tokens[j] != "None":
                        self.technologies [tokens[j].strip()] = tokens[j+1].strip()
                    j += 2
