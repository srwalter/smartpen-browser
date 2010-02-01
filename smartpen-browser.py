#!/usr/bin/python

import gtk
import pysmartpen
import xml.dom.minidom
import zipfile
import parsestf
import tempfile
import cairo
import os

class Parser(parsestf.STFParser):
    def __init__(self, stream):
        super(Parser, self).__init__(stream)
        self.last_force=0

    def handle_stroke_end(self, time):
        self.ctx.stroke()
        self.last_force = 0

    def handle_point(self, x, y, f, time):
        ctx = self.ctx
        if f:
            if self.last_force:
                ctx.line_to(x, y)
            else:
                ctx.move_to(x, y)
        self.last_force = 1

    def parse(self, ctx):
        self.ctx = ctx
        super(Parser, self).parse()


class Notebook(object):
    def __init__(self, pen, guid, title, pages):
        self.guid = guid
        self.title = title
        self.pen = pen
        self.pages = pages
        self.is_rendered = False

        ls = gtk.ListStore(str, gtk.gdk.Pixbuf)
        self.ls = ls

        iv = gtk.IconView(ls)
        iv.modify_base(gtk.STATE_NORMAL, gtk.gdk.Color("gray"))
        iv.set_text_column(0)
        iv.set_pixbuf_column(1)
        iv.show()

        sw = gtk.ScrolledWindow()
        sw.add(iv)
        sw.show()

        self.contents = sw

    def add(self, notebook):
        tab = gtk.Label(self.title)
        tab.show()
        notebook.append_page(self.contents, tab)

    def render(self):
        if is_rendered is True:
            return

        # XXX: cleanup temp file
        fd, tmpfile = tempfile.mkstemp()
        print self.guid
        self.pen.get_guid(tmpfile, self.guid, 0)
        z = zipfile.ZipFile(tmpfile, "r")

        # XXX: cleanup temp dir
        tmpdir = tempfile.mkdtemp()

        i = 0
        for name in z.namelist():
            if not name.startswith('data/'):
                continue
            i += 1
            f = z.open(name)
            p = Parser(f)

            # XXX: get dimension from pen data
            surface = cairo.ImageSurface(cairo.FORMAT_RGB24, 4963, 6278)
            ctx = cairo.Context(surface)
            ctx.set_source_rgb(255, 255, 255)
            ctx.paint()
            ctx.set_source_rgb(0,0,0)
            try:
                p.parse(ctx)
            except Exception, e:
                print "Parse error"
                print e
                continue
            fn = os.path.join(tmpdir, "page%d" % i)
            surface.write_to_png(fn)
            img = gtk.gdk.pixbuf_new_from_file(fn)
            img = img.scale_simple(img.props.width / 10,
                                   img.props.height / 10,
                                   "bilinear")
            self.ls.append(["Page %d" % i, img])
        self.is_rendered = True

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
