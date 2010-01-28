#!/usr/bin/python

import gtk

class SmartpenBrowser(object):
    def __init__(self):
        builder = gtk.Builder()
        builder.add_from_file("smartpen-browser.glade")
        self.window = builder.get_object("window1")
        self.window.show_all()

if __name__ == "__main__":
    x = SmartpenBrowser()
    gtk.main()
