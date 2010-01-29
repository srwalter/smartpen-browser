#!/usr/bin/python

import gtk
import pysmartpen
import xml.dom.minidom

class Notebook(object):
    def __init__(self, notebook, guid, title):
        self.guid = guid
        self.title = title

        child = gtk.Label(guid)
        child.show()
        tab = gtk.Label(title)
        tab.show()
        notebook.append_page(child, tab)

class SmartpenBrowser(object):
    def pen_connect(self, *args):
        self.pen.connect()
        self.connected = True

        changes = self.pen.get_changelist()
        dom = xml.dom.minidom.parseString(changes)
        cl = dom.getElementsByTagName('changelist')[0]

        notebooks = []
        tabs = self.builder.get_object('notebook1')

        for elm in cl.getElementsByTagName('lsp'):
            guid = elm.getAttribute('guid')
            if not guid:
                continue
            print guid

            title = elm.getAttribute('title')
            nb = Notebook(tabs, guid, title)
            notebooks.append(nb)
        print notebooks

    def pen_disconnect(self, *args):
        self.pen.disconnect()
        self.connected = False

    def pen_info(self, *args):
        info = self.pen.get_info()
        dom = xml.dom.minidom.parseString(info)
        info = dom.getElementsByTagName('peninfo')[0]
        penid = info.getAttribute('penid')

        elem = info.getElementsByTagName('battery')[0]
        voltage = elem.getAttribute('voltage')
        battlevel = elem.getAttribute('level')

        elem = info.getElementsByTagName('memory')[0]
        totalmem = elem.getAttribute('totalbytes')
        freemem = elem.getAttribute('freebytes')

        elem = info.getElementsByTagName('version')[0]
        swrev = elem.getAttribute('swrev')

        print penid
        print voltage
        print battlevel
        print freemem
        print totalmem
        print swrev

        freemem = int(freemem)
        totalmem = int(totalmem)

        label = self.builder.get_object('penid')
        label.props.label = penid
        label = self.builder.get_object('battery')
        label.props.label = battlevel
        label = self.builder.get_object('memory')
        label.props.label = "%dk / %dk" % ((totalmem - freemem)/1024,
                totalmem / 1024)
        label = self.builder.get_object('version')
        label.props.label = swrev

        dlg = self.builder.get_object('infowin')
        dlg.run()
        dlg.hide()

    def about(self, *args):
        dlg = self.builder.get_object('aboutwin')
        dlg.run()
        dlg.hide()

    def quit(self, *args):
        if self.connected is True:
            self.pen.disconnect()
        gtk.main_quit()

    def __init__(self):
        builder = gtk.Builder()
        builder.add_from_file("smartpen-browser.glade")
        self.builder = builder
        self.connected = False

        pen = pysmartpen.Smartpen()
        self.pen = pen

        window = builder.get_object("window1")
        window.connect('delete-event', self.quit)
        window.set_size_request(640, 480)
        window.show_all()

        mi = builder.get_object("quit")
        mi.connect('activate', self.quit)

        mi = builder.get_object("connect")
        mi.connect('activate', self.pen_connect)

        mi = builder.get_object("disconnect")
        mi.connect('activate', self.pen_disconnect)

        mi = builder.get_object("peninfo")
        mi.connect('activate', self.pen_info)

        mi = builder.get_object("about-mi")
        mi.connect('activate', self.about)

if __name__ == "__main__":
    x = SmartpenBrowser()
    gtk.main()
