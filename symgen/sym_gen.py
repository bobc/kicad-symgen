#!/usr/bin/env python

# -*- coding: utf-8 -*-

"""
 Generate components from text file
 
 Usage: symgen

 Copyright Bob Cousins 2017

 Licensed under GPLv3

 Version 1

 todo:

   ieee symbols
   field pos?
   (error reporting

   / de morgans 
   / doc fields, aliases - dcm 
   / smaller logic symbols?
   / pin length = 200?
   / parametize input/output file names etc 

 issues
   pin overlaps (top/bot)
   ? bad symbols
   / missing graphics
"""

import sys
import argparse

import file_util
from lib_symgen import *
from convert_library import *


def ExitError( msg ):
    print(msg)
    sys.exit(-1)

#
# main
#
parser = argparse.ArgumentParser(description="Generate component library")

parser.add_argument("--inp", help="symgen script file")
parser.add_argument("--lib", help="KiCad .lib file")
parser.add_argument("--fp_dir", help="folder containing valid footprints")
parser.add_argument("--ref", help="7400 logic reference list")
parser.add_argument("-d", "--dump", help="Dump an existing library", action='store_true')
parser.add_argument("-v", "--verbose", help="Enable verbose output", action="store_true")
parser.add_argument("--regen", help="Dump an existing library and regenerate from script", action='store_true')
parser.add_argument("--output", help="Output format : legacy, v6-sweet")

args = parser.parse_args()

#
#
symgen = SymGen()
symgen.verbose = args.verbose

#temp
#symgen.gen_comp ("data")
#symgen.process_list()

if args.regen:
    actions = "dump,gen"
elif args.dump:
    actions = "dump"
else:
    actions = "gen"

# --regen -lib C:\git_bobc\kicad-library\library\74xx.lib 

if "dump" in actions:
    # -d --lib C:\git_bobc\kicad-library\library\74xx.lib --ref ..\74xx\7400_logic_ref.txt
    # -d --lib C:\git_bobc\kicad-library\library\Logic_74xx.lib --ref ..\74xx\7400_logic_ref.txt
    # 
    if not args.lib:
        ExitError("error: library name not supplied (need --lib)")

    lib_filename = args.lib
    dump_path = ""

    print ("Extracting library %s" % lib_filename)
    convert = ConvertLibrary()
    ## convert.symbol_style = SymbolStyle.PHYSICAL
    convert.dump_lib (lib_filename, dump_path, args.ref)

if "gen" in actions:
    # --inp 74xx.txt
    # --inp mcu_stm32_stm32f0.txt --fp_dir c:\github\kicad-footprints

    if args.regen:
        file = os.path.basename (args.lib)
        file = file_util.change_extension (file, ".txt")
    else:
        if not args.inp:
            ExitError("error: symgen script file not supplied (need --inp)")
        file = args.inp

    symgen.footprints_folder = args.fp_dir
    if args.output:
        symgen.output_format = args.output
    else:
        symgen.output_format = "legacy"


    print ("Generating library from %s" % file)
    symgen.parse_input_file (file)


