#!/usr/bin/env python

# -*- coding: utf-8 -*-

"""
 Scan libraries for footprint and datasheet data
 
 Usage: symgen

 Copyright Bob Cousins 2020

 Licensed under GPLv3

 Version 1

"""

import os
import re
import sys
import fnmatch
import argparse
import csv_files

#import file_util
common = os.path.abspath(os.path.join(sys.path[0], '..', 'symgen'))
if not common in sys.path:
    sys.path.append(common)

from schlib import *

from str_utils import *

def ExitError( msg ):
    print(msg)
    sys._exit(1)


def find_files(base, pattern):
    '''Return list of files matching pattern in base folder.'''
    return [n for n in fnmatch.filter(os.listdir(base), pattern) if
        os.path.isfile(os.path.join(base, n))]
#
# main
#
parser = argparse.ArgumentParser(description="Generate library data")

parser.add_argument("--inp", help="path to libraries")
parser.add_argument("-v", "--verbose", help="Enable verbose output", action="store_true")

args = parser.parse_args()


if not args.inp:
    ExitError("error: input path required (need --inp)")

out_path = ""

items = args.inp.split (os.sep)

if len(items) == 1:
    path = ""
    file_spec = items [0]

elif len(items) > 1:
    path = os.sep.join (items[:-1])
    file_spec = items[-1]


files = find_files (path, file_spec)

if files:
    datasheets = csv_files.DatasheetFile (os.path.join (out_path, "datasheets.csv"))
    #datasheets.data = {}    

    footprints = csv_files.FootprintFile (os.path.join (out_path, "footprints.csv"))
    #footprints.data = []

    for f in files:
        if f.endswith (".lib"):
            lib_filename = os.path.join (path, f)
            print ("Extracting data %s" % lib_filename)

            lib = SchLib(lib_filename)

            for comp in lib.components:
                print(comp.name)

                name = before (comp.name, "-")

                footprint = comp.fields[2]['name']
                footprint = footprint.strip('"')
                fp_key = comp.documentation['description'].split(',')[-1]
                fp_key = fp_key.strip()
                if  '-' in fp_key:
                    # QFN-48 becomes QFN48
                    #fp_key = re.sub (r"\d", "", fp_key) + "-" + re.sub (r"\D", "", fp_key)
                    #fp_key = re.sub (r'(\D+)\-(\d+)', r'\1\2', fp_key, re.IGNORECASE)
                    fp_key = fp_key.replace ("-", "")


                if footprint:
                    #footprint_file.write ("{},{}\n".format (comp.name, footprint))
                    footprints.add (comp.name, fp_key, footprint)
            
                if comp.documentation['datasheet']:
                    #datasheet_file.write ("{},{}\n".format (comp.name, comp.documentation['datasheet']))
                    datasheets.add (name, comp.documentation['datasheet'])

                if len(comp.aliases) > 0:
                    for alias in list(comp.aliases.keys()):
                        print("  "+alias)
                        if footprint:
                            #footprint_file.write ("{},{}\n".format (alias, footprint))
                            footprints.add (alias, fp_key, footprint)

                        alias_doc = comp.aliases[alias]
                        if alias_doc:
                            f_doc = alias_doc['datasheet']
                            #datasheet_file.write ("{},{}\n".format (alias, f_doc))
                            datasheets.add (before(alias,"-"), f_doc)


    #
    datasheets.write_file()
    
    footprints.write_file()
