import os    
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.websocket
from tornado.options import options, define


# Define available options
define("port", default=8888, type=int, help="run on the given port")

PORT = 8888

class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("user")

class MainHandler(BaseHandler): 

    def get(self):

        # Send our main document
        if not self.current_user:
            self.redirect("/login")
            return

        self.render("index.html")

class LoginHandler(BaseHandler):

    def get(self):
        self.write('<html><body><form action="/login" method="post">'
                   'Name: <input type="text" name="name">'
                   '<input type="submit" value="Sign in">'
                   '</form></body></html>')

    def post(self):
        self.set_secure_cookie("user", self.get_argument("name"))
        self.redirect("/")        

class TornadoWebServer(tornado.web.Application):
    ' Tornado Webserver Application...'
    def __init__(self):

        #Url to its handler mapping.
        handlers = [(r"/", MainHandler),
                    (r"/login", LoginHandler),
                    (r"/images/(.*)", tornado.web.StaticFileHandler, {"path": "web/images"}),
                    (r"/js/(.*)", tornado.web.StaticFileHandler, {"path": "web/js"}),
                    (r"/style/(.*)", tornado.web.StaticFileHandler, {"path": "web/style"})]

        #Other Basic Settings..
        settings = dict(
            cookie_secret="set_this_later",
            login_url="/login",
            template_path=os.path.join(os.path.dirname(__file__), "web"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=False,
            debug=True)

        #Initialize Base class also.
        tornado.web.Application.__init__(self, handlers, **settings)


if __name__ == '__main__':

    #Tornado Application
    print("Initializing Tornado Webapplications settings...")
    application = TornadoWebServer()

    # Start the HTTP Server
    print("Starting Tornado HTTPServer on port %i" % PORT)
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(PORT)
	
    # Get a handle to the instance of IOLoop
    ioloop = tornado.ioloop.IOLoop.instance()

    # Start the IOLoop
    ioloop.start()
