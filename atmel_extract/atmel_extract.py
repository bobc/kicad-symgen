#!/usr/bin/env python

# -*- coding: utf-8 -*-

"""
 Generate components from XML file

 Usage: ...

 Copyright Bob Cousins 2020

 Licensed under GPLv3

 Version 1

 todo:
"""

import os
import sys
import argparse
import datetime
import math

from lxml import etree

from str_utils import *

common = os.path.abspath(os.path.join(sys.path[0], '..', 'scan_libs'))
if not common in sys.path:
    sys.path.append(common)
import csv_files


PIN_NAME_MAP = {
    "RESET_N": "~RESET",
    "NRST": "~RST",
    }

PIN_TYPES_MAPPING_SYMGEN = {
     "Passive": "P",
     "Power"  : "PI",
     "IO"     : "B",
     "MonoIO" : "B",
     "Input"  : "I",
     "Reset"  : "I",
     "Boot"   : "I",
     "Clock"  : "I",
     "NC"     : "NN"
     }

PIN_TYPES_MAPPING = [
    ["VDDCORE"    , "Power"],
    ["VDD"    , "Power"],
    ["VSS"    , "Power"],
    ["VDD.*"  , "Power"],
    ["VSS.*"  , "Power"],

    ["VBG"      , "Input"],
    ["VREFP"    , "Input"],
    ["VREFN"    , "Input"],
    ["JTAGSEL"  , "Input"],
    ["TST"      , "Input"],
    #VBAT

    ["GND.*"  , "Power"],

    ["RESET.*" , "Reset"],
    ["NRST" , "Reset"],

    ["NC" , "NC"]

    ]


# Mapping to KiCad packages
PACKAGES = {
    ##
    "SOIC14"    : "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm.kicad_mod",  # 4
    "SOIC20"    : "Package_SO:SOIC-20W_7.5x12.8mm_P1.27mm.kicad_mod",  # 3   
    "SOIC32"    : "",  # 1   no such parts?

    "SSOP24"    : "Package_SO:SSOP-24_5.3x8.2mm_P0.65mm.kicad_mod",  # 6

    "QFN24"     : "Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm.kicad_mod",
    "QFN32"     : "Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.6x3.6mm.kicad_mod",
    "QFN48"     : "Package_DFN_QFN:QFN-48-1EP_7x7mm_P0.5mm_EP5.15x5.15mm",
    "QFN64"     : "Package_DFN_QFN:QFN-64-1EP_9x9mm_P0.5mm_EP4.7x4.7mm",
    "QFN100"    : "",   # no such parts?

    "LQFP64"    : "Package_QFP:LQFP-64_10x10mm_P0.5mm.kicad_mod",  # 20
    "LQFP100"   : "Package_QFP:LQFP-100_14x14mm_P0.5mm.kicad_mod",  # 22
    "LQFP144"   : "Package_QFP:LQFP-144_20x20mm_P0.5mm.kicad_mod",  # 19

    "TQFP32"    : "Package_QFP:TQFP-32_7x7mm_P0.8mm.kicad_mod",  # 43
    "TQFP48"    : "Package_QFP:TQFP-48_7x7mm_P0.5mm",
    "TQFP64"    : "Package_QFP:TQFP-64_10x10mm_P0.5mm",
    "TQFP100"   : "Package_QFP:TQFP-100_14x14mm_P0.5mm",
    "TQFP128"   : "Package_QFP:TQFP-128_14x14mm_P0.4mm.kicad_mod",  # 4

    "BGA64"     : "",  # 6
    "BGA100"    : "",  # 3

    "CTBGA64"   : "Package_BGA:UFBGA-64_5x5mm_Layout8x8_P0.5mm",  # 5

    "LFBGA144"  : "Package_BGA:LFBGA-144_10x10mm_Layout12x12_P0.8mm",  # 12

    "TFBGA100"  : "Package_BGA:TFBGA-100_9.0x9.0mm_Layout10x10_P0.8mm",  # 22
    "TFBGA120"  : "",  # 4
    "TFBGA144"  : "",  # 10

    "UFBGA144"  : "",  # 12
    "UFBGA64"   : "Package_BGA:UFBGA-64_5x5mm_Layout8x8_P0.5mm",  # 2

    "VFBGA100"  : "Package_BGA:VFBGA-100_7.0x7.0mm_Layout10x10_P0.65mm.kicad_mod",

    "WLCSP20" : "Package_CSP:WLCSP-20_1.934x2.434mm_Layout4x5_P0.4mm",  # 2
    "WLCSP27" : "",  # 2
    "WLCSP31" : "",  # 1
    "WLCSP32" : "",  # 6
    "WLCSP35" : "",  # 5
    "WLCSP45" : "",  # 4
    "WLCSP49" : "",  # 6
    "WLCSP56" : "Package_CSP:WLCSP-56_3.170x3.444mm_Layout7x8_P0.4mm",  # 4
    "WLCSP64" : "",  # 10

    ##
    }

all_packages = {}
missing_packages = {}

# datasheets = {}

verbose = False

def get_datasheets (path):
    global datasheets

    datasheets = {}

    try:
        with open(path, "r") as f:
            for line in f.readlines():
                tokens = line.strip("\n").split (",")

                key = tokens[0].strip()
                
                if len(tokens) > 1:
                    datasheets [key] = tokens[1].strip()
                else:
                    datasheets [key] = None
    except IOError:
        pass

    return datasheets

def get_key(x):
    if "_" in x:
        return int(before(x,"_"))*10 +1
    else:
        return int(x)*10

def get_filter_package (package, package_name):
    if package == package_name:
        # QFN48 becomes QFN?48*
        package = re.sub (r"\d", "", package_name) + "?" + re.sub (r"\D", "", package_name) + "*"
    else:
        package = after (package_name, ":")
        package = package.replace ("-", "?")
        package = package.replace ("_", "*") + "*"
    return package

def round_to (val, grid):
    return int(int((val+grid-1)/grid)*grid)

def alphanum (s):
    convert = lambda text: int(text) if text.isdigit() else text.rjust(3, '@')
    #parts = [ convert(c) for c in re.split('([-+]?[0-9]*\.?[0-9]*)', s) ]
    parts = [ convert(c) for c in re.split('([0-9]*)', s) ]
    return parts

def sort_human(l):
    convert = lambda text: float(text) if text.isdigit() else text
    alphanum = lambda key: [ convert(c) for c in re.split('([-+]?[0-9]*\.?[0-9]*)', key) ]
    l.sort( key=alphanum )
    return l

def sort_pin_name (p):
    return sort_human (p.name)

def textlen (s):
    return len(s) * 50

def ExitError( msg ):
    print(msg)
    os._exit(1)

class Logger :

    def __init__(self):
        self.num_errors = 0
        self.num_warnings = 0

    def info (self, f, s):
        if s is None:
            print (f)
        else:
            print (f % s)

    def debug (self, f, s=None):
        if verbose:
            if s is None:
                print (f)
            else:
                print (f % s)

    def warning (self, f, s=None):
        self.num_warnings += 1

        if s is None:
            print (f)
        else:
            print (f % s)

    def error (self, f, s=None):
        self.num_errors += 1

        if s is None:
            print (f)
        else:
            print (f % s)



LOGGER = Logger()

class Pin:
    def __init__(self, pinnumber, name, pintype):
        # print ("%s %s" % (pinnumber, name))

        self.pinnumber = pinnumber
        self.name = name
        self.pintype = pintype

        self.altNames = []

        self.pos = "L"

    def get_long_name (self):
        return '/'.join ([self.name]+self.altNames)

    def __repr__(self):
        return "%s %s %s" % (self.pinnumber, self.name, self.pintype)

class Device:

    def __init__(self, xmlfile):
        if verbose:
            print(xmlfile)
        self.xmlfile = xmlfile

        self.core = None
        self.tree = None

        self.memories = None
        self.modules = None
        self.gpios = None
        self.num_io=0
        self.data=None

        self.datasheet = ""

        self.pins = []
        #
        self.resetPins = []
        self.bootPins = []
        self.clockPins = []
        self.otherPins = []
        self.powerPins = []

        self.leftPins = []
        self.rightPins = []
        self.topPins = []
        self.bottomPins = []

        self.ports = {}

        #
        self.get_variants()

        if self.variants:
            key = next(iter(self.variants))
            d = self.variants[key]
            name = d[0]['ordercode']
            
            self.datasheet = datasheets.find (name)

    def queryTree(self, query):
        """
        This tries to apply the query to the device tree and returns either
        - an array of element nodes,
        - an array of strings or
        - None, if the query failed.
        """
        response = None
        try:
            response = self.tree.xpath(query)
        except:
            pass
            #LOGGER.error("Query failed for '%s'", str(query))

        return response

    def query(self, query, default=[]):
        result = self.queryTree(query)
        if result is not None:
            sorted_results = []
            for r in result:
                if r not in sorted_results:
                    sorted_results.append(r)
            return sorted_results

        return default

    def compactQuery(self, query):
        return self.query(query, None)

    def get_variants (self):

        self.tree = etree.parse(self.xmlfile)
        device_file = self


        self.family = device_file.query("//device")[0].get("family")
        self.series = device_file.query("//device")[0].get("series")

        self.device_name = device_file.query("//device")[0].get("name")
        self.has_pinout = device_file.query("//pinouts")

        self.variants = {}

        # package : [ordercode, pinout, ...]
        variants = device_file.query("//variants/variant")

        for variant in variants:
            ordercode = variant.get("ordercode")
            if not ordercode.startswith("AT"):
                ordercode = "AT" + ordercode

            package = variant.get("package")
            pinout = variant.get("pinout")
            freq = math.floor (int(variant.get ("speedmax")) / 1000000)
            voltage = [variant.get ("vccmin"), variant.get ("vccmax")]

            if pinout:
                key = package + "~" + pinout
            else:
                key = package

            if not key in self.variants:
                self.variants [key] = []

            d = {'ordercode': ordercode, 'package':package, 'pinout':pinout, 'freq':freq, 'voltage': voltage }
            self.variants [key].append (d)

        #return list(set(d for d in devices if d != "standard"))

    def read_device(self, variant):

        self.tree = etree.parse(self.xmlfile)
        device_file = self

        device = device_file.query("//device")[0]

        p={}
        p["id"] = device.get("name")

        #LOGGER.debug("Parsing '%s'", p["id"])

        p["pinout_pins"] = {
            p.get("position"): p.get("pad")
            for p in device_file.query(f'//pinouts/pinout[@name="{variant["pinout"]}"]/pin')
        }

        #self.pins = p['pinout_pins']

        # information about the core and architecture
        core = device_file.query("//device")[0].get("architecture").replace("PLUS", "+")
        for param in (device_file.query("//device/parameters")[0]):
            if param.get("name") == "__FPU_PRESENT" and param.get("value") == "1":
                core += "F"
        p["core"] = core
        self.core = core

        # find the values for flash, ram and (optional) eeprom
        self.flash = None
        self.ram = None
        memories = []
        for memory_segment in device_file.query("//memory-segment"):
            #memType = memory_segment.get("type")
            name = memory_segment.get("name")
            start = memory_segment.get("start")
            size = int(memory_segment.get("size"), 16)

            access = ""

            if name in ["FLASH"]:
                memories.append({"name":"flash", "access":"rx", "size":str(size), "start":start})
                self.flash = math.floor (int(size) / 1024)
            elif name in ["HMCRAMC0", "HMCRAM0", "HSRAM"]:
                memories.append({"name":"ram", "access":access, "size":str(size), "start":start})
                self.ram = math.floor (int(size) / 1024)
            elif name in ["LPRAM", "BKUPRAM"]:
                memories.append({"name":"lpram", "access":access, "size":str(size), "start":start})
            elif name in ["SEEPROM", "RWW"]:
                memories.append({"name":"eeprom", "access":"r", "size":str(size), "start":start})
            elif name in ["QSPI"]:
                memories.append({"name":"extram", "access":access, "size":str(size), "start":start})
            else:
                pass
                #LOGGER.debug("Memory segment '%s' not used", name)
        p["memories"] = memories
        self.memories = memories

        raw_modules = device_file.query("//peripherals/module/instance")
        modules = []
        ports = []
        for m in raw_modules:
            tmp = {"module": m.getparent().get("name"), "instance": m.get("name")}
            if tmp["module"] == "PORT":
                ports.append(tmp)
            else:
                modules.append(tmp)
        p["modules"] = sorted(list(set([(m["module"], m["instance"]) for m in modules])))
        self.modules = p['modules']

        signals = []
        gpios = []
        raw_signals = device_file.query("//peripherals/module/instance/signals/signal")
        for s in raw_signals:
            tmp = {"module": s.getparent().getparent().getparent().get("name"),
                    "instance": s.getparent().getparent().get("name")}
            tmp.update({k:v for k,v in s.items()})

            if tmp["group"] in ["P", "PIN"] or tmp["group"].startswith("PORT"):
                gpios.append(tmp)
            else:
                signals.append(tmp)
        gpios = sorted([(g["pad"]) for g in gpios])

        p["signals"] = signals
        # Filter gpios by pinout
        #p["gpios"] = [pin for pin in gpios if f"P{pin[0].upper()}{pin[1]}" in p["pinout_pins"].values()]

        self.gpios = gpios
        self.num_io = len (gpios)

        self.pins = []
        for pn in p['pinout_pins']:
            num = pn
            name = p['pinout_pins'][pn]
            pin_type = "Passive"

            if name in gpios:
                pin_type = "IO"

            for pattern in PIN_TYPES_MAPPING:
                if re.match (pattern[0], name):
                    pin_type = pattern[1]
                    break

            #
            functions = [x for x in signals if x["pad"] == name]

            altf=[]
            for f in functions:
                instances = [x[1] for x in self.modules if x[0] == f["module"]]

                num_instance = len (instances)

                if num_instance > 1 :
                    mod_prefix = f["instance"] + "."
                else:
                    mod_prefix = ""

                if 'index' in f:
                    alt_name = mod_prefix + f['group'] + f['index']
                else:
                    alt_name = mod_prefix + f['group']

                if alt_name != name:
                    if not alt_name in altf:
                        altf.append (alt_name)

            #
            if name in PIN_NAME_MAP:
                name = PIN_NAME_MAP[name]

            pin = Pin (num, name, pin_type)
            pin.altNames.extend(altf)

            self.pins.append (pin)


        #LOGGER.debug("Found GPIOs: [%s]", ", ".join(p))
        #LOGGER.debug("Available Modules are:\n" + Device._modulesToString(p["modules"]))

        self.data = p
        #
        self.processPins()

    def processPins(self):
        #
        self.resetPins = []
        self.bootPins = []
        self.clockPins = []
        self.otherPins = []

        self.powerPins = []

        self.ports = {}

        self.leftPins = []
        self.rightPins = []

        self.topPins = []
        self.bottomPins = []

        # Classify pins
        for pin in self.pins:
            if ((pin.pintype == "IO" or pin.pintype == "Clock") and pin.name.startswith("P")):
                port = pin.name[1]
                try:
                    # num = re.sub("\D", "", pin.name[2:])
                    num = pin.name[2:]
                    self.ports[port][num] = pin
                except KeyError:
                    self.ports[port] = {}
                    self.ports[port][num] = pin
                except ValueError as ex:
                    LOGGER.error ("error: not an int: %s" % repr(ex))

            elif pin.pintype == "Clock":
                self.clockPins.append(pin)  

            elif pin.pintype == "Power":

                if pin.name.startswith("VSS") or pin.name.startswith("GND") :
                    self.bottomPins.append(pin)

                elif pin.name.startswith("V"):
                    self.topPins.append(pin)

                else:
                    #self.powerPins.append(pin)
                    self.otherPins.append(pin)

            elif pin.pintype == "Reset":
                self.resetPins.append(pin)

            elif pin.pintype == "Boot":
                self.bootPins.append(pin)

            else:
                self.otherPins.append(pin)


        self.topPins = sorted(self.topPins, key=lambda p: p.name)
        self.bottomPins = sorted(self.bottomPins, key=lambda p: p.name)



    @staticmethod
    def _modulesToString(modules):
        string = ""
        mods = sorted(modules)
        char = mods[0][0][0:1]
        for module, instance in mods:
            if not instance.startswith(char):
                string += "\n"
            string += instance + " \t"
            char = instance[0][0:1]
        return string

    def writePins (self, f, pins):
        for pin in pins:
            if pin.pintype == ' ':
                f.write ("SPC \n")
            else:
                f.write ("%s %s %s %s\n" % (pin.pinnumber,
                                            pin.get_long_name(),
                                            PIN_TYPES_MAPPING_SYMGEN[pin.pintype], 
                                            pin.pos))

    def write_symgen (self, f, variants):

        #p = self.data

        if len(self.pins) < 100:
            pinlength = 100
        else:
            pinlength = 150

        variant = variants[0]

        #
        self.package_name = ""
        package = footprints.find (variant['ordercode'])

        if not package == "": 
            self.package_name = package
            all_packages[variant['ordercode']] = [ variant['package'], self.package_name ]

        else:
            if variant['package'] in PACKAGES:
                package = PACKAGES[variant['package']]

            if package:
                self.package_name = package
                all_packages[variant['ordercode']] = [ variant['package'], self.package_name ]
            else:        
                if not variant['package'] in missing_packages:
                    missing_packages [variant['package']] = []
                name = variant['ordercode'][:8]
                if not name in missing_packages [variant['package']]:
                    missing_packages [variant['package']].append (name)

                LOGGER.error ("error: Unknown package %s : %s" % (variant['ordercode'], variant['package']))
                
                # don't generate data if footprint not found
                return

            #all_packages[variant['ordercode']] = [ variant['package'], self.package_name ]


        #

        f.write ("#\n")
        f.write ("# %s\n" % variant['ordercode'])
        f.write ("#\n")

        f.write ("COMP %s U\n" % variant['ordercode'])

        f.write ("%%pinlen %d\n" % pinlength)

        f.write ("FIELD $FOOTPRINT \"%s\"\n" % self.package_name)

        f.write ("FPLIST %s\n" % get_filter_package(variant['package'], self.package_name))

        #
        for j,variant in enumerate (variants):

            f.write ("#\n")
            if j > 0:
                f.write ("ALIAS %s\n" % variant['ordercode'])

            items = []
            if self.core:
                items.append ("%s" % self.core)

            if self.flash:
                items.append ("%s KB Flash" % self.flash)

            if self.ram:
                items.append ("%s KB RAM" % self.ram)

            if self.num_io:
                items.append ("%s IO Pins" % self.num_io)

            if variant['freq']:
                items.append ("%s MHz" % variant['freq'])

            if variant['voltage']:
                v = variant['voltage']
                items.append ("%sV-%sV" % (v[0], v[1]))

            if variant['package']:
                items.append ("%s" % variant['package'])

            desc = ", ".join (items)

            keywords = " ".join([self.core, self.family, self.series])

            f.write ("DESC %s\n" % desc)
            f.write ("KEYW %s\n" % keywords)

            f.write ("DOC %s\n" % self.datasheet)

        #

        f.write ("#\n")



        space = Pin ("~", "~", " ")

        portNames = sorted(self.ports.keys())
        width = 800

        ports_per_unit = 1
        max_pins_per_unit = 100

        if len (self.pins) <= max_pins_per_unit :
            single_unit = True
            num_units = 1
        else:
            single_unit = False
            
            num_units = math.floor(len(portNames)/ports_per_unit)

            if num_units < ports_per_unit+1:
                single_unit = True
                num_units = 1
            else:
                # add power unit
                num_units += 1


        port_offset = 0

        for unit_num in range (1, num_units+1):
            left_pins = []
            right_pins = []
            top_pins = []
            bottom_pins = []

            if unit_num == 1:
                if self.resetPins:
                    left_pins.extend (self.resetPins + [space])
                if self.bootPins:
                    left_pins.extend (self.bootPins + [space])
                if self.clockPins:
                    left_pins.extend (self.clockPins + [space])
                if self.otherPins:
                    left_pins.extend (self.otherPins + [space])

            #while port_offset < min ( len (portNames), port_offset + ports_per_unit):

            if num_units == 1:
                ports_in_unit = len(portNames)
            else:
                ports_in_unit = min(ports_per_unit, len(portNames)-port_offset)

            for port_num in range (0, ports_in_unit):

                portname = portNames[port_offset + port_num]
                port = self.ports[portname]
                for pinname in sorted(port.keys(), key=lambda x : int(x)):
                    pin = port[pinname]

                    if port_num < ports_in_unit/2:
                        left_pins.append (pin)
                    else:
                        right_pins.append (pin)

                #
                if not port_num == ports_in_unit-1:
                    if port_num < ports_in_unit/2:
                        left_pins.append (space)
                    else:
                        right_pins.append (space)

            port_offset += ports_in_unit

            max_left = 0
            max_right = 0
            for pin in left_pins:
                max_left = max (max_left, textlen(pin.name))
                pin.pos = "L"
            for pin in right_pins:
                max_left = max (max_left, textlen(pin.name))
                pin.pos = "R"

            if unit_num == num_units:
                top_pins.extend (self.topPins)
                bottom_pins.extend (self.bottomPins)

            for pin in bottom_pins:
                pin.pos = "BC"
            for pin in top_pins:
                pin.pos = "TC"

            width = max_left + max_right + 50
            width = round_to (width, pinlength*2)

            #
            width = 0
            f.write ("UNIT WIDTH %s\n" % width)

            self.writePins (f, left_pins)
            self.writePins (f, right_pins)

            self.writePins (f, top_pins)
            self.writePins (f, bottom_pins)

            #width = max(len(self.topPins), len(self.bottomPins))*100
            #f.write ("UNIT WIDTH %d\n" % width)

        


        f.write ("END\n")





class SymFile:
    def __init__(self, filename):
        self.outfile = open (filename, "w")
        self.outfile.write ("#\n")
        self.outfile.write ("# Generated by atmel_extract\n")
        self.outfile.write ("# %s\n" % datetime.datetime.now().replace(microsecond=0).isoformat(' '))
        self.outfile.write ("#\n")

        self.outfile.write ("%pin_stack GND PAD EP\n")
        self.outfile.write ("%pin_stack VSS PAD EP\n")
        self.outfile.write ("%pin_stack AVSS\n")
        self.outfile.write ("#\n")

        self.writeLine (r"%pin_name_format AVDD AV_{DD}")
        self.writeLine (r"%pin_name_format AVSS AV_{SS}")
        #self.writeLine (r"%pin_name_format V(SS|DD)(RX|TX|PLL|CORE|) V_{\1\2}")
        self.writeLine (r"%pin_name_format V(SS|DD)(.*) V_{\1\2}")

        self.writeLine (r"%pin_name_format VREF\+ V_{REF+}")
        self.writeLine (r"%pin_name_format VREF\- V_{REF-}")
        self.writeLine (r"%pin_name_format CVREF CV_{REF}")
        self.writeLine (r"%pin_name_format VUSB3V3 V_{USB3V3}")
        self.writeLine (r"%pin_name_format VUSB V_{USB}")
        self.writeLine (r"%pin_name_format VPP V_{PP}")
        self.writeLine (r"%pin_name_format VCAP V_{CAP}")
        self.writeLine ("#")

    def writeLine (self, s):
        self.outfile.write (s + '\n')

    def close (self):
        self.outfile.close ()

#
# main
#
def main():
    #global all_packages
    #global missing_packages
    global verbose
    global datasheets
    global footprints

    parser = argparse.ArgumentParser(description="Generate component library")

    parser.add_argument("--inp", help="XML folder")
    parser.add_argument("--data", help="Data folder")
    parser.add_argument("-v", "--verbose", help="Enable verbose output", action="store_true")

    args = parser.parse_args()

    #
    if not args.inp:
        ExitError("error: XML folder not supplied (need --inp)")

    verbose = args.verbose


    # get xml files
    xml_files = []
    for (dirpath, dirnames, filenames) in os.walk(args.inp):
        for filename in filenames:
            # print os.path.join(after(root,sourcedir),filename)
            if filename.endswith ('.atdf'):
                xml_files.append ( os.path.join(dirpath, filename) )


    path = os.path.join (args.data, "datasheets.csv")
    datasheets = csv_files.DatasheetFile (path)

    path = os.path.join (args.data, "footprints.csv")
    footprints = csv_files.FootprintFile(path)

    if xml_files:

        counts = {}
        sym_file = {}
        num_devices = 0
        num_variants = 0

        all_devices = {}

        sym_gen = True

        print("info: Processing XML files")
        for xmlfile in xml_files:

            print ("Reading data from %s" % xmlfile)

            device = Device (xmlfile)

            if device.has_pinout:
                print ("{} ".format (device.device_name))
                num_devices += 1


                count_key = device.family
                if count_key in counts:
                    counts[count_key] += 1
                else:
                    counts[count_key] = 1

            for key in device.variants:
                
                if verbose:
                    print ("{} ".format (key))

                for d in device.variants[key]:
                    if verbose:
                        print ("   {} ".format (d))

                    name = before (d['ordercode'], '-')
                    if device.has_pinout and not name in all_devices:
                        all_devices [name] = device.datasheet

                num_variants += len(device.variants[key])

                d = device.variants[key][0]
                if d['pinout']:
                    device.read_device (d)

                    if sym_gen:
                        if not device.family in sym_file:
                            sym_file [device.family] = SymFile ("MCU_Microchip_"+device.family + ".txt")

                        device.write_symgen (sym_file[device.family].outfile, device.variants[key])

        # for

        if sym_gen:
            for key in sym_file:
                sym_file[key].outfile.close ()

        if missing_packages:
            print ("")
            print ("Missing packages:")
            for s in sorted(missing_packages):
                print ('    "%s" : "",  # %s' % (s, missing_packages[s]) )

        if True:
            print ("")
            print ("All packages:")
            for s in sorted(all_packages):
                print ('%s,%s,%s' % (s, all_packages[s][0], all_packages[s][1] ) )

        print ("")
        print ("Devices:")
        for s in sorted(all_devices):
            print ('%s,%s' % (s, all_devices[s]) )

        print ("")
        print ("Number of devices : %d" % num_devices)
        print ("Number of variants: %d" % num_variants)

        print ("")
        print ("Number of warnings: %d" % LOGGER.num_warnings)
        print ("Number of errors  : %d" % LOGGER.num_errors)

        print ("")
        for key in sorted(counts.keys()):
            print ("%s %d" % (key, counts[key]) ) 


    else:
        ExitError ("error: no ATDF files found")

main()
