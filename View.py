from __future__ import with_statement

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import os
import datetime
import re
import time

import MsgArea

#TODO Make this value configurable and stored in GConf
SAVE_TIMEOUT = 5

class Error(Exception):
    pass

class View(object):
    IMAGE_COLUMN, NAME_COLUMN, ENTRY_COLUMN = range(3)
    
    def __init__(self):
        '''
        Creates the View
        
        Doesnt do much.
        '''
        self.window = None
        self.updating = False
        self.selected_entry = None
        self.selected_iter = None
        self.last_changed = None
        self.save_timeout = False
    
    def make_window(self):
        '''
        Create the top-level window and it's widgets.
        '''
        
        if self.window:
            return
        
        self.builder = gtk.Builder()
        self.builder.add_from_file('DiaryUI.glade')
        self.builder.connect_signals(self)
        
        self.window = self.builder.get_object('main_window')
        
        self.category_box = self.builder.get_object('category_box')
        self.categories_model = self.builder.get_object('categories_model')
        cat_renderer = gtk.CellRendererText()
        self.category_box.pack_start(cat_renderer)
        self.category_box.set_attributes(cat_renderer, text=0)
        self.calendar = self.builder.get_object('calendar')
        
        #model1 = gtk.ListStore(str)
        #print model1.get_column_type(0)
        #model1.set_column_types(str)
        #print model1.get_column_type(0)
        
        # Construct the model ourselfs, because we cant have Python objects otherwise
        self.entries_model = gtk.ListStore(str, str, object)
        #self.entries_model = self.builder.get_object('entries_model')
        self.entries_model.set_default_sort_func(self.sort_entries_cb)
        self.entries_model.set_sort_column_id(-1, gtk.SORT_ASCENDING)
        
        self.entries_treeview = self.builder.get_object("entries_treeview")
        self.entries_treeview.set_model(self.entries_model)
        self.entries_treeview.insert_column_with_attributes(-1, "", gtk.CellRendererPixbuf(),  stock_id=self.IMAGE_COLUMN)
        self.entries_treeview.insert_column_with_attributes(-1, "Name", gtk.CellRendererText(),  text=self.NAME_COLUMN)        
        
        self.text_buffer = self.builder.get_object('text_buffer')
        self.text_view = self.builder.get_object('text_view')
        
        self.entry_header = self.builder.get_object('entry_header')
        self.entry_header_box = self.builder.get_object('entry_header_box')
                
        self.msg_area = MsgArea.MsgAreaController()
        self.builder.get_object('right_side_vbox').pack_start(self.msg_area, False, False)
        
        self.first_time = True
        self.first_msg = self.msg_area.new_from_text_and_icon(gtk.STOCK_DIALOG_INFO,
            "Welcome to your diary", 
            "Just start writing today's entry (you don't have to save it, that's automatic)"
        ).show()        
        
        '''
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        #self.window.set_border_width(8)
        self.window.set_default_size(800, 600)
        
        ui = ''
            <ui>              
              <toolbar action="maintoolbar">
                <separator/>
                <toolitem name="Settings" action="SettingsAction"/>
                <separator/>
              </toolbar>
            </ui>
            ''
            
        actions = (
            ('SettingsAction', gtk.STOCK_PREFERENCES, None, None, None, self.on_settings_action),
            ('AddCategoryAction', gtk.STOCK_ADD, 'Add Category', None, None, self.on_category_add),
            ('RenameEntryAction', gtk.STOCK_EDIT, 'Rename Entry', None, None, self.on_rename_entry),
        )
        
        self.action_group = gtk.ActionGroup('actions')
        self.action_group.add_actions(actions)
        self.ui_manager = gtk.UIManager()
        self.ui_manager.insert_action_group(self.action_group)
        self.ui_manager.add_ui_from_string(ui)
        
        root_vbox = gtk.VBox()
        root_vbox.pack_start(self.ui_manager.get_widget('/maintoolbar'), False, False)        
        
        self.window.connect("destroy", self.destroy)
    
        self.hpaned = gtk.HPaned()
        self.hpaned.set_border_width(8)
        
        root_vbox.pack_start(self.hpaned)
    
        self.entries_model = gtk.ListStore(str, str, object)
        self.entries_model.set_default_sort_func(self.sort_entries_cb)
        self.entries_model.set_sort_column_id(-1, gtk.SORT_ASCENDING)
        
        self.file_icon = gtk.STOCK_FILE
        self.folder_icon = gtk.STOCK_DIRECTORY
        
        self.vpaned = gtk.VPaned()
        
        self.tree = gtk.TreeView()
        self.tree.set_headers_visible(False)
        self.tree.connect("cursor-changed", self.on_tree_selection_changed)
        self.tree.set_model(self.entries_model)
        self.tree.set_rules_hint(True)
        self.tree.insert_column_with_attributes(-1, "", gtk.CellRendererPixbuf(), stock_id=self.IMAGE_COLUMN)
        self.tree.insert_column_with_attributes(-1, "Name", gtk.CellRendererText(), text=self.NAME_COLUMN)
        
        self.tree_scrolled_window = gtk.ScrolledWindow()
        self.tree_scrolled_window.add(self.tree)
        self.tree_scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.vpaned.pack2(self.tree_scrolled_window)

        vbox = gtk.VBox()
        vbox.set_spacing(8)
        
        self.calendar = gtk.Calendar()
        self.calendar.connect('month-changed', self.on_calendar_month_changed)
        self.calendar.connect('day-selected', self.on_calendar_day_selected)
        
        cat_hbox = gtk.HBox()
        
        self.combobox = gtk.combo_box_new_text()
        self.combobox.connect('changed', self.on_category_changed)
        add_cat_button = self.action_group.get_action('AddCategoryAction').create_tool_item()
        
        cat_hbox.pack_start(self.combobox)
        cat_hbox.pack_start(add_cat_button, False, False)
        
        vbox.pack_start(cat_hbox)
        vbox.pack_start(self.calendar)
        
        self.vpaned.pack1(vbox)
        
        self.text_buffer = gtk.TextBuffer()
        self.text_buffer.connect('changed', self.on_text_buffer_changed)
        self.text_view = gtk.TextView(self.text_buffer)
        self.text_view.set_wrap_mode(gtk.WRAP_WORD)
        self.text_scrolled_window = gtk.ScrolledWindow()
        self.text_scrolled_window.add(self.text_view)
        self.text_scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        
        self.msg_area = MsgArea.MsgAreaController()
        
        self.first_time = True
        self.first_msg = self.msg_area.new_from_text_and_icon(gtk.STOCK_DIALOG_INFO,
            "Welcome to your diary", 
            "Just start writing today's entry (you don't have to save it, that's automatic)"
        ).show()
        
        self.entry_header = gtk.Label("My entry")
        self.entry_header.set_alignment(0.0, 0.5)
        
        rename_entry_button = self.action_group.get_action('RenameEntryAction').create_tool_item()
        
        title_hbox = gtk.HBox()
        #title_hbox.set_border(0)
        title_hbox.pack_start(self.entry_header)
        #title_hbox.pack_start(rename_entry_button, False, False)
        
        from FadingWidget import FadingWidget
        self.saving_indicator = FadingWidget()
        title_hbox.pack_start(self.saving_indicator, False, False)
        
        vbox2 = gtk.VBox()
        #vbox2.set_spacing(8)
        vbox2.pack_start(self.msg_area, False, False)
        vbox2.pack_start(title_hbox, False)
        vbox2.pack_start(self.text_scrolled_window)

        self.hpaned.pack1(self.vpaned, False, False)
        self.hpaned.pack2(vbox2, True, True)
        
        self.window.add(root_vbox)

        '''
        self.init_entries()

        self.window.show_all()
        
    def on_settings_action(self, widget):
        pass

    def _run_entry_dialog(self, title, text):
        dialog = gtk.Dialog(title,
                     self.window,
                     gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                     (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                      gtk.STOCK_OK, gtk.RESPONSE_OK)
                 )
        dialog.vbox.set_border_width(8)
        box = gtk.HBox()
        entry = gtk.Entry()
        box.set_spacing(8)
        box.set_border_width(8)
        box.pack_start(gtk.Label(text))
        box.pack_start(entry)
        box.show_all()
        dialog.vbox.set_spacing(8)
        dialog.vbox.pack_start(box, False, False)
        if dialog.run() == gtk.RESPONSE_OK:
            response = entry.get_text()
        else:
            response = None
        dialog.destroy()
        return response
    
    def on_add_category_action_activate(self, widget):
        new_category = self._run_entry_dialog("New category", "Category name:")
        if new_category and new_category.strip():
            self.model.add_category(new_category)
            self.update_categories(new_category)
    
    def on_rename_entry(self, widget):
        if self._run_entry_dialog("Rename entry", "New name:"):
            pass
        
    def set_model(self, model):
        self.model = model

    def init_entries(self):
        self.update_categories()
        
    def update_categories(self, category_name = None):
        self.categories_model.clear()
        active = 0
        for idx, name in enumerate(self.model.list_categories()):
            if name == category_name:
                active = idx
            self.categories_model.append((str(name),))
        self.category_box.set_active(active)
        self.update_calendar()        
        
    def on_category_changed(self, combobox): 
        self.category = combobox.get_active_text()
        self.update_category()
        self.open_date(datetime.date.today())
        
    def update_category(self):
        self.entries_model.clear()
        self.selected_iter = None
        for entry in self.model.list_entries(self.category):
            iter_ = self.entries_model.append((gtk.STOCK_FILE, entry.get_description(), entry))
            if entry == self.selected_entry:
                self.open_document(iter_)
        #self.open_date(datetime.date.today())
        self.update_calendar()
        
    def on_calendar_month_changed(self, calendar):
        self.update_calendar()
        
    def on_calendar_day_selected(self, calendar):
        year, month, day = calendar.get_date()
        date = datetime.date(year, month + 1, day)
        self.open_date(date)
        
    def update_calendar(self):
        self.calendar.clear_marks()
        self.entries_model.foreach(self.update_calendar_tree_cb, (self.calendar.get_property('month') + 1, self.calendar.get_property("year")))
        
    def update_calendar_tree_cb(self, model, path, iter_, data):
        entry = model.get_value(iter_, self.ENTRY_COLUMN)
        date = entry.date
        month, year = data
        if date and date.month == month and date.year == year: 
            #self.calendar.select_month(date.month - 1, date.year)
            self.calendar.mark_day(date.day)
            
    def sort_entries_cb(self, model, iter1, iter2):
        entry1 = model.get_value(iter1, self.ENTRY_COLUMN)
        entry2 = model.get_value(iter2, self.ENTRY_COLUMN)
        return cmp(entry1, entry2)
        
    def on_tree_selection_changed(self, tree):
        model, iter_ = tree.get_selection().get_selected()
        if not iter_:
            return 
        #if not model.get_value(iter_, self.FOLDER_COLUMN):
        self.open_document(iter_)

    def format_date_column(self, column, cell, model, iter_):
        is_folder = model.get_value(iter_, self.FOLDER_COLUMN)
        date = model.get_value(iter_, self.DATE_COLUMN)
        if is_folder:
            text = "Folder"
        elif date:
            text = str(date)
        else:
            text = "Unknown"
        cell.set_property("text", text)
        
    def on_text_buffer_changed(self, text_buffer):
        if self.updating:
            return
        #empty = self.text_buffer.get_text(self.text_buffer.get_start_iter(), self.text_buffer.get_end_iter()).strip()
        if not self.last_changed:
            self.save_document()
        else:
            now = time.time()
            if int(now - self.last_changed) < SAVE_TIMEOUT:
                if self.save_timeout:
                    return
                timeout = int(SAVE_TIMEOUT - now + self.last_changed) * 1000
                self.save_timeout = gobject.timeout_add(timeout, self.save_document_timeout, self.selected_entry)
            else:
                self.save_document()
    
    def save_document_timeout(self, entry):
        self.save_document(entry)
        self.save_timeout = None
        return False
    
    def save_document(self, entry = None):
        '''
        Save the current entry (if entry is defined, must be the selected entry).
        '''
        self.saving_indicator.update()
        self.last_changed = time.time()
        try:
            if entry:
                if entry != self.selected_entry:
                    raise Error("Entry is not the one selected")
            entry = entry or self.selected_entry
            text = self.text_buffer.get_text(self.text_buffer.get_start_iter(), self.text_buffer.get_end_iter())
            #Make sure we're not saving an empty entry, when the entry doesn't 
            #exist in the first place
            if entry.exists() or text.strip():
                entry.set_text(text)
            if self.selected_iter:
                self.entries_model.set_value(self.selected_iter, self.NAME_COLUMN, entry.get_description())
        except Exception, excp:
            if entry:
                text = "Error saving %s" % entry.name
            else:
                text = "Error saving entry"
            self.msg_area.new_from_text_and_icon(gtk.STOCK_DIALOG_ERROR, text, "%s" % excp).show()
            raise

    def open_document(self, iter_):
        '''
        Open the entry defined in the iter_
        '''
        if self.updating:
            return
        self.updating = True
        if self.save_timeout:
            gobject.source_remove(self.save_timeout)
            self.save_timeout = None
            self.save_document()
        self.selected_iter = None
        try:
            entry = self.entries_model.get_value(iter_, self.ENTRY_COLUMN)
            #Remove the old entry if it doesnt exist
            if entry != self.selected_entry and self.selected_entry and not self.selected_entry.exists():
                self.model.remove_entry(self.selected_entry)
                self.update_category()
            self.selected_entry = entry
            self.selected_iter = iter_
            self.last_changed = None
            date = entry.date
            if date:
                self.calendar.select_month(date.month - 1, date.year)
                self.calendar.select_day(date.day)
                header_text = date.strftime("%A, %d %B %Y")
            else:
                header_text = entry.name
            self.entry_header.set_label(header_text)
            text = entry.get_text()
            if not self.first_time:
                self.msg_area.clear()
            self.first_time = False
            if text is not None:
                self.text_buffer.set_text(text)
                self.text_view.set_sensitive(True)
                if date:
                    diff_days = (datetime.date.today() - date).days
                else:
                    diff_days = 0
                if diff_days < 0 or diff_days > 5:
                    def msg_response(msg, resp):
                        self.text_view.set_sensitive(True)
                        self.msg_area.clear()
                    if diff_days < 0:
                        msg_text = "This date is in the future"
                    else:
                        msg_text = "This is an older entry"
                    msg = self.msg_area.new_from_text_and_icon(gtk.STOCK_DIALOG_QUESTION, 
                        msg_text,
                        "Do you want to edit this entry?")
                    msg.add_stock_button_with_text("Edit anyway", gtk.STOCK_EDIT, gtk.RESPONSE_YES)
                    msg.connect('response', msg_response)
                    msg.show_all()
                    self.text_view.set_sensitive(False)
            else:
                self.text_buffer.set_text('')
                self.text_view.set_sensitive(False)
                self.msg_area.new_from_text_and_icon(gtk.STOCK_DIALOG_ERROR, 
                    "Error loading %s" % entry.name, entry.error_message
                ).show_all()
        finally:
            self.updating = False
    
    def open_date(self, date):
        found = []
        self.entries_model.foreach(self.open_date_tree_cb, (date, found))
        if not found:
            self.model.add_entry(None, date, self.category)            
            self.update_category()
            self.open_date(date)
        
    def open_date_tree_cb(self, model, path, iter_, (date, found)):
        iter_date = model.get_value(iter_, self.ENTRY_COLUMN).date
        if date == iter_date:
            self.entries_treeview.set_cursor(self.entries_model.get_string_from_iter(iter_))
            found.append(True)
            return True
    
    def on_destroy(self, widget, data=None):
        gtk.main_quit()

    def main(self):
        self.make_window()
        gtk.main()


