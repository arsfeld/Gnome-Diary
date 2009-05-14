#!/usr/bin/python

from __future__ import with_statement

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import os
import datetime
import re
import shutil

NO_CATEGORY = "No category"

class Error(Exception):
    pass

def cmp_filename(filename1, filename2):
    '''
    Auxiliar function to compare filenames grouping numbers.
    
    This function recognizes that, for instance, filename1 is less then 
    filename10 and so on, by grouping numbers together.
    '''
    def try_int(value):
        try:
            value = int(value)
        except:
            pass
        return value
    if not (filename1 and filename2):
        return cmp(filename1, filename2)
    regex = re.compile("(\d+|\D+)")
    groups1 = map(try_int, regex.findall(filename1))
    groups2 = map(try_int, regex.findall(filename2))
    return cmp(groups1, groups2)

class Model(object):
    def __init__(self, root):
        self.root = root
        self.categories = {NO_CATEGORY: []}
        self.entries = []
        self.scan_dir(self.root)

    def list_categories(self):
        return self.categories.keys()
    
    def list_entries(self, category):
        return self.categories[category]

    def scan_dir(self, path, category = NO_CATEGORY):
        regex = re.compile(r"(\d+)[\-\_]+(\d+)[\-\_]+(\d+)")
        for name in os.listdir(path):
            filename = os.path.join(path, name)
            if os.path.isdir(filename): 
                self.scan_dir(filename, name)
            elif os.path.isfile(filename) and not name[-1:] == '~':
                #print filename
                date = None
                try:
                    matches = regex.search(name)
                    new_match = True
                    #Search for the last match to the date pattern.
                    while matches and new_match:
                        #Skip the first group and try to match again
                        new_match = regex.search(name, matches.end(1) + 1)
                        if new_match:
                            matches = new_match
                    if matches:
                        year, month, day = [int(matches.group(i + 1)) for i in range(3)]
                        if year < 100:
                            if year > 50:
                                year += 1900
                            else:
                                year += 2000
                        date = datetime.date(year, month, day)
                    else:
                        raise Error("Filename format not expected")
                except Error:
                    pass
                finally:
                    self.add_entry(name, date, category, filename)
                    
    def add_category(self, category):
        '''
        Adds a new empty category.
        '''
        if category not in self.categories:
            self.categories[category] = []
    
    def add_entry(self, name, date, category = None, filename = None):
        '''
        Create a new entry and returns it.
        '''
        if category not in self.categories:
            self.categories[category] = []
        if not name:
            name = str(date)
        if not filename:
            if category == NO_CATEGORY:
                filename = os.path.join(self.root, name)
            else:
                filename = os.path.join(self.root, category, name)
        entry = Entry(name, date, category, filename)
        self.entries.append(entry)
        self.categories[category].append(entry)
        return entry

    def remove_entry(self, entry):
        '''
        Remove an entry from this model and from it's category.
        '''
        if entry.category:
            self.categories[entry.category].remove(entry)
        self.entries.remove(entry)

class Entry(object):
    '''
    An entry object contains all information about a diary entry.
    '''

    def __init__(self, name, date, category, filename):
        self.date = date
        self.name = name
        self.category = category
        self.filename = filename
        self.text = None
        self.error_loading = False
        self.error_message = ""
    
    def get_description(self):
        if self.date:
            text = str(self.date)
            if self.date == datetime.date.today():
                text += ' (Today)'
            if not self.exists():
                text += ' (Empty)'
            return text
        else:
            return self.name
    
    def __cmp__(self, other):
        if not other:
            return 1
        if not isinstance(other, Entry):
            raise Error("Comparing Entry to another object is unsupported")
        if self.date and other.date:
            return (-1) * cmp(self.date, other.date)
        else:
            return cmp_filename(self.name, other.name)
    
    def get_text(self):
        if self.text is not None:
            return self.text
        try:
            if not self.exists():
               return ''
            with open(self.filename, 'r') as f:
                text = f.read()
                try:
                    text = text.decode('UTF-8')
                except:
                    text = text.decode('iso8859_15')
                self.text = text
            return text
        except Exception, excp:
            self.error_loading = True
            self.error_message = "%s" % (excp)            
            return None
        
    def exists(self):
        return os.path.exists(self.filename)
    
    def set_text(self, text):
        self.text = text
        return self.save_text()
    
    def save_text(self):
        if self.error_loading or self.text is None:
            return False
        if self.exists():
            shutil.copyfile(self.filename, self.filename + '~')
        #Just remove empty entries
        if not self.text.strip():
            if self.exists():
                os.unlink(self.filename)
        else:
            if not os.path.exists(os.path.dirname(self.filename)):
                os.makedirs(os.path.dirname(self.filename))
            with open(self.filename, 'w') as f:
                f.write(self.text)
        
