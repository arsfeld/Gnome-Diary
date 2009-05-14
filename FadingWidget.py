import cairo
import gobject
import gtk

gtk.gdk.threads_init()

def load_surface_from_icon(icon_name, size = 32):
    '''
    Load an arbitrary image file into a Cairo image surface.
    '''
    #pixbuf = gtk.gdk.pixbuf_new_from_file(filename)
    pixbuf = gtk.icon_theme_get_default().load_icon("gtk-save", size, gtk.ICON_LOOKUP_USE_BUILTIN)

    format = cairo.FORMAT_RGB24
    if pixbuf.get_has_alpha():
        format = cairo.FORMAT_ARGB32
    width = pixbuf.get_width()
    height = pixbuf.get_height()
    image = cairo.ImageSurface(format, width, height)

    context = cairo.Context(image)
    gdkcontext = gtk.gdk.CairoContext(context)
    gdkcontext.set_source_pixbuf(pixbuf, 0, 0)
    gdkcontext.paint()
    return image

TIMER = 50

# Create a GTK+ widget on which we will draw using Cairo
class FadingWidget(gtk.DrawingArea):

    # Draw in response to an expose-event
    __gsignals__ = { "expose-event": "override" }

    def __init__(self):
        gtk.DrawingArea.__init__(self)
        self.image = None
        self.alpha = 0
        self.signal = True
        self.set_size_request(32, 32)
        self.drawing = False
        #self.image = load_surface_from_file()
        #self.image = gtk.gdk.CairoContext(self.window.cairo_create())
        #image = gtk.icon_theme_get_default().load_icon("gtk-save")
        #self.image.set_source_pixbuf(image, 0, 0)
        
    def update(self):
        self.alpha = 0
        self.signal = True
        gobject.timeout_add(TIMER, self.update_image)
        
    def update_image(self):
        self.drawing = True
        if self.signal:
            self.alpha += (TIMER / 10.0)
        else:
            self.alpha -= (TIMER / 10.0)
        if self.alpha > 100:
            self.signal = False
        self.queue_draw()
        if self.alpha < 0:
            return False
        return True

    def do_configure_event(self, event):
        self.image = load_surface_from_icon("gtk-save", min(*self.window.get_size()))

    # Handle the expose-event by drawing
    def do_expose_event(self, event):

        # Create the cairo context
        cr = self.window.cairo_create()

        # Restrict Cairo to the exposed area; avoid extra work
        cr.rectangle(event.area.x, event.area.y,
                event.area.width, event.area.height)
        cr.clip()

        self.draw(cr, *self.window.get_size())

    def draw(self, cr, width, height):
        # Fill the background with gray   
        cr.translate(width / 2.0 - self.image.get_width() / 2.0, height / 2.0 - self.image.get_height() / 2.0)
        #print "%sx%s" % (width / 2.0 - self.image.get_width() / 2.0, height / 2.0 - self.image.get_height() / 2.0)
        cr.set_source_surface(self.image)
        cr.paint_with_alpha(self.alpha / 100.0)
        #self.image.paint(cr)

