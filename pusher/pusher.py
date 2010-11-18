import json
from twisted.application.service import Service
from twisted.internet import reactor
from twisted.python import log
from twisted.web import resource, server
from twisted.web.error import Error

from apns import APNSConnection


class PusherService(Service):

    def __init__(self, interface, apns_host, apns_cert, apns_key, verbose):
        self.interface = interface
        self.verbose = bool(verbose)

        # APNS connection wrapper
        host, port = apns_host.split(':')
        self.apns = APNSConnection(host, int(port), apns_cert, apns_key)

    def startService(self):
        Service.startService(self)
        self.init_api()

    def init_api(self):
        log.msg('Starting HTTP on %s...' % self.interface)
        root = resource.Resource()
        root.putChild("send", APISendResource(self))
        site = server.Site(root, logPath='/dev/null')
        host, port = self.interface.split(':')
        reactor.listenTCP(int(port), site, interface=host)

    def log_verbose(self, message):
        if self.verbose:
            log.msg("VERBOSE: %s" % message)

    def send_push(self, device_token, payload):
        log.msg('Sending push to %s' % device_token)
        self.log_verbose('Payload = %r' % payload)
        self.apns.send_push(device_token, payload)

    def stopService(self):
        Service.stopService(self)
        self.apns.disconnect()


class APISendResource(resource.Resource):

    def __init__(self, service):
        self.service = service

    def render_POST(self, request):
        self.service.log_verbose('Received request: %r, %r'
                                 % (request, request.args))
        try:
            if 'deviceToken' not in request.args:
                raise Error(400, "Missing deviceToken argument")
            if 'payload' not in request.args:
                raise Error(400, "Missing payload argument")

            device_token = request.args['deviceToken'][0]
            payload = request.args['payload'][0]

            try:
                data = json.loads(payload)
            except Exception, e:
                raise Error(400, "Payload must be JSON: %s" % e)

            if 'aps' not in payload:
                raise Error(400, "Payload missing 'aps': %r" % payload)

            if len(device_token) != 64:
                raise Error(400, "Device token must be 64 bytes: %r"
                                 % device_token)

            self.service.send_push(device_token, data)
        except Error, e:
            log.msg('Bad request: %s' % e)
            request.setResponseCode(e.status)
            return str(e)
        except Exception, e:
            log.msg('Internal error: %s' % e)
            request.setResponseCode(500)
            return "Internal error: %s" % e

        return "QUEUED"
