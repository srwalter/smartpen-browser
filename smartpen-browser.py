#!/usr/bin/python

import gtk
import pysmartpen
import xml.dom.minidom
import zipfile
import parsestf

class STFWidget(gtk.DrawingArea):
    class Parser(parsestf.STFParser):
        def __init__(self, stream):
            super(STFWidget.Parser, self).__init__(stream)
            self.last_force=0

        def handle_stroke_end(self, time):
            self.ctx.stroke()
            self.last_force = 0

        def handle_point(self, x, y, f, time):
            ctx = self.ctx
            if f:
                if self.last_force:
                    ctx.line_to(x/10, y/10)
                else:
                    ctx.move_to(x/10, y/10)
            self.last_force = 1

        def parse(self, ctx):
            self.ctx = ctx
            super(STFWidget.Parser, self).parse()

    def __init__(self, *args):
        super(STFWidget, self).__init__(*args)
        self.connect('expose-event', self.expose)
        self.parser = None
        self.ctx = None

    def expose(self, *args):
        print "expose"
        window = self.get_window()
        ctx = window.cairo_create()
        ctx.set_source_rgb(255, 255, 255)
        ctx.paint()
        ctx.set_source_rgb(0, 0, 0)
        if self.parser is not None:
            self.parser.parse(ctx)

    def parse(self, stream):
        p = STFWidget.Parser(stream)
        self.parser = p


class Notebook(object):
    def __init__(self, pen, guid, title, pages):
        self.guid = guid
        self.title = title
        self.pen = pen
        self.pages = pages

        child = STFWidget()
        child.set_size_request(500, 500)
        child.show()
        self.contents = child

    def add(self, notebook):
        tab = gtk.Label(self.title)
        tab.show()
        notebook.append_page(self.contents, tab)

    def render(self):
        #tmpfile = "tmpfile"
        #self.pen.get_guid(tmpfile, self.guid)
        tmpfile = file("/home/srwalter/programs/livescribe/data")
        z = zipfile.ZipFile(tmpfile, "r")

        name = None
        addr = self.pages[0]
        for fn in z.namelist():
            #if addr in fn:
            if fn.startswith('data/'):
                name = fn
                break
        f = z.open(name)
        self.contents.parse(f)

class SmartpenBrowser(object):
    def pen_connect(self, *args):
        self.pen.connect()
        self.connected = True

        changes = self.pen.get_changelist()
        dom = xml.dom.minidom.parseString(changes)
        cl = dom.getElementsByTagName('changelist')[0]

        notebooks = []
        tabs = self.builder.get_object('notebook1')
        tabs.connect('switch-page', self.switch_page, notebooks)

        for elm in cl.getElementsByTagName('lsp'):
            guid = elm.getAttribute('guid')
            if not guid:
                continue
            print guid

            title = elm.getAttribute('title')

            pages = []
            for p in elm.getElementsByTagName('page'):
                addr = p.getAttribute('pageaddress')
                pages.insert(0, addr)

            nb = Notebook(self.pen, guid, title, pages)
            notebooks.append(nb)
            nb.add(tabs)
        pass

    def switch_page(self, notebook, page, page_num, notebooks):
        print "switch page %d" % page_num
        notebooks[page_num].render()

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
