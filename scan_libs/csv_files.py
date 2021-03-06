import os
import sys
import csv



class DatasheetFile (object):
    """description of class"""

    field_names = ['name', 'datasheet_url']

    def __init__ (self, filename):

        self.filename = filename
        self.data = {}

        if os.path.isfile (filename):
            with open(filename, newline='') as f:
                reader = csv.reader(f)
                for j,row in enumerate(reader):
                    if j==0:
                        pass
                    else:
                        self.data [row[0]] = row[1]

    def add (self, name, url):
        if not name in self.data:
            self.data[name] = url
        else:
            if not self.data[name] == url:
                print ("different : {}, {}, {}".format (name, self.data[name], url))

    def find (self, name):
        if name in self.data:
            return self.data[name]
        else:
            found = None
            max_len = 0
            for key in self.data:
                #if key == name[0:len(key)] and len(key) > max_len:
                if key == name and len(key) > max_len: # exact match
                    max_len = len(key)
                    found = self.data[key]

            if found:
                return found
            else:
                return ""

    def write_file (self):
        with open(self.filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow (self.field_names)
            writer.writerows(self.data.items())


class FootprintFile (object):
    """description of class"""

    field_names = ['name', 'footprint_short', 'footprint_long']
    
    def __init__ (self, filename):

        self.filename = filename
        self.data = []

        if os.path.isfile (filename):
            with open(filename, newline='') as f:
                reader = csv.reader(f)
                for j,row in enumerate(reader):
                    if not j==0:
                        self.data.append(row)

    def add (self, name, fp_key, fp_long):

        # replace existing
        #new_data = [x for x in self.data if not (x[0]==name and x[1]==fp_key)]
        #new_data.append ([name, fp_key, fp_long])
        #self.data = new_data

        existing = self.find (name)
        if existing == "":
            self.data.append ([name, fp_key, fp_long])
        else:
            if not existing == fp_long:
                print ("different : {}, {}, {}".format (name, existing, fp_long))


    def find (self, name):
        found = None
        max_len = 0
        for row in self.data:
            if row[0] == name and len(row[0]) > max_len:
                found = row[2]
                max_len = len(row[0])
        if found:
            return found
        else:
            return ""

    def write_file (self):
        with open(self.filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow (self.field_names)
            for item in self.data:
                writer.writerow(item)




