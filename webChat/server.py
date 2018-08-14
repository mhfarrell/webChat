# -*- coding: utf-8 -*-
#!/usr/bin/env python

import os

import motor.motor_tornado
import bcrypt
#import time
#import json

import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.websocket
from tornado.options import options, define

import pika
from pika.adapters.tornado_connection import TornadoConnection


# Define available options
define("port", default=8888, type=int, help="run on the given port")
define("queue_host", default="127.0.0.1", help="Host for amqp daemon")
define("queue_user", default="guest", help="User for amqp daemon")
define("queue_password", default="guest", help="Password for amqp daemon")

PORT = 8888


class PikaClient(object):

    def __init__(self):

        # Construct a queue name we'll use for this instance only

        #Giving unique queue for each consumer under a channel.
        self.queue_name = "queue-%s" % (id(self),)
        # Default values
        self.connected = False
        self.connecting = False
        self.connection = None
        self.channel = None

        #Webscoket object.
        self.websocket = None

    def connect(self):

        if self.connecting:
                print('PikaClient: Already connecting to RabbitMQ')
                return

        print('PikaClient: Connecting to RabbitMQ on localhost:5672, Object: %s' % (self,))

        self.connecting = True

        credentials = pika.PlainCredentials('guest', 'guest')
        param = pika.ConnectionParameters(host='localhost',
                                          port=5672,
                                          virtual_host="/",
                                          credentials=credentials)
        self.connection = TornadoConnection(param,
                                            on_open_callback=self.on_connected)

    def on_connected(self, connection):
        print('PikaClient: Connected to RabbitMQ on localhost:5672')
        self.connected = True
        self.connection = connection
        self.connection.channel(self.on_channel_open)

    def on_channel_open(self, channel):

        print('PikaClient: Channel Open, Declaring Exchange, Channel ID: %s' %
              (channel,))
        self.channel = channel

        self.channel.exchange_declare(exchange='tornado',
                                      exchange_type="direct",
                                      auto_delete=True,
                                      durable=False,
                                      callback=self.on_exchange_declared)

    def on_exchange_declared(self, frame):
        print('PikaClient: Exchange Declared, Declaring Queue')
        self.channel.queue_declare(auto_delete=True,
                                   queue=self.queue_name,
                                   durable=False,
                                   exclusive=True,
                                   callback=self.on_queue_declared)

    def on_queue_declared(self, frame):

        print('PikaClient: Queue Declared, Binding Queue')
        self.channel.queue_bind(exchange='tornado',
                                queue=self.queue_name,
                                routing_key='tornado.*',
                                callback=self.on_queue_bound)

    def on_queue_bound(self, frame):
        print('PikaClient: Queue Bound, Issuing Basic Consume')
        self.channel.basic_consume(consumer_callback=self.on_pika_message,
                                   queue=self.queue_name,
                                   no_ack=True)

    def on_pika_message(self, channel, method, header, body):
        print('PikaCient: Message receive, delivery tag #%i' %
              method.delivery_tag)

        #Send the Cosumed message via Websocket to browser.
        self.websocket.write_message(body)

    def on_basic_cancel(self, frame):
        print('PikaClient: Basic Cancel Ok')
        # If we don't have any more consumer processes running close
        self.connection.close()

    def on_closed(self, connection):
        # We've closed our pika connection so stop the web chat
        tornado.ioloop.IOLoop.instance().stop()

    def chat_message(self, ws_msg):
        #Publish the message from Websocket to RabbitMQ
        properties = pika.BasicProperties(
            content_type="text/plain", delivery_mode=1)

        self.channel.basic_publish(exchange='tornado',
                                   routing_key='tornado.*',
                                   body=ws_msg,
                                   properties=properties)
        
class BaseHandler(tornado.web.RequestHandler):
    #get cookies value 
    def get_current_user(self):
        return self.get_secure_cookie("username")
    
class MainHandler(BaseHandler): 

    def get(self):
        #redirect to login if no active cookies found
        if not self.current_user:
            self.redirect("/login")
            return
        #sent to chat if active cookies found
        self.render("index.html", connected=self.application.pika.connected)

class LoginHandler(BaseHandler):

    def post(self):
        users = mongo.db.users
        loginUser = users.find_one({'username' : request.form['username']})
        hashPass = bcrypt.hashpw(request.form['password'].encode('utf-8'), loginUser['password'].encode('utf-8'))
        if loginUser:
            if hashPass == loginUser['password'].encode('utf-8'):
                self.set_secure_cookie("username", request.form['username'])
                self.redirect("/")
                return
            return #invalid username/password
        
        

class RegisterHandler(BaseHandler):

    def get(self):
        #duplicates


    def post(self):
        users = mongo.db.users
        existingUser = users.find_one({'username' : request.form['username']})

        if existingUser is None:
            hashPass = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.genselt())
            users.insert({'username' : request.form['username'], 'password' : hashPass})
            self.set_secure_cookie("username", request.form['username'])
            self.redirect("/")
            return 
        else:
            #user exists
            return #return error
        
            

class errorCatch(tornado.web.HTTPError):

    @tornado.web.asynchronous
    def get(self):

        # Send our 404 page
        self.render("404.html")


class WebSocketServer(tornado.websocket.WebSocketHandler):
    'WebSocket Handler, Which handle new websocket connection.'

    def open(self):
        'Websocket Connection opened.'

        #Initialize new pika client object for this websocket.
        self.pika_client = PikaClient()

        #Assign websocket object to a Pika client object attribute.
        self.pika_client.websocket = self

        ioloop.add_timeout(1000, self.pika_client.connect)

    def on_message(self, msg):
        'A message on the Webscoket.'
        #Publish the received message on the RabbitMQ
        self.pika_client.chat_message(msg)

    def on_close(self):
        'Closing the websocket..'
        print("WebSocket Closed")

        #close the RabbiMQ connection...
        self.pika_client.connection.close()

class TornadoWebServer(tornado.web.Application):
    ' Tornado Webserver Application...'
    def __init__(self):

        #Url to its handler mapping.
        handlers = [(r"/", MainHandler),
                    (r"/login", LoginHandler),
                    (r"/register", RegisterHandler),                    
                    (r"/404", errorCatch),
                    (r"/ws_channel", WebSocketServer),
                    (r"/images/(.*)", tornado.web.StaticFileHandler, {"path": "web/images"}),
                    (r"/js/(.*)", tornado.web.StaticFileHandler, {"path": "web/js"}),
                    (r"/style/(.*)", tornado.web.StaticFileHandler, {"path": "web/style"})]

        #Other Basic Settings..
        settings = dict(
            cookie_secret="set_this_later",
            login_url="/login",
            template_path=os.path.join(os.path.dirname(__file__), "web"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
            debug=True)

        #Initialize Base class also.
        tornado.web.Application.__init__(self, handlers, **settings)


if __name__ == '__main__':

    client = motor.motor_tornado.MotorClient('localhost', 27018)
    

    #Tornado Application
    print("Initializing Tornado Webapplications settings...")
    application = TornadoWebServer()

    # Helper class PikaClient makes coding async Pika apps in tornado easy
    pc = PikaClient()
    application.pika = pc  # We want a shortcut for below for easier typing

    # Start the HTTP Server
    print("Starting Tornado HTTPServer on port %i" % PORT)
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(PORT)

    # Get a handle to the instance of IOLoop
    ioloop = tornado.ioloop.IOLoop.instance()

    # Add our Pika connect to the IOLoop since we loop on ioloop.start
    #ioloop.add_timeout(1000, application.pika.connect)

    # Start the IOLoop
    ioloop.start()



