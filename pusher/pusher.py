import json
from twisted.application.service import Service
from twisted.internet import defer, reactor
from twisted.internet.task import LoopingCall
from twisted.python import log
from twisted.web import resource, server
from twisted.web.error import Error

import apns


class PusherService(Service):

    def __init__(self, interface, sandbox, apns_cert, apns_key,
                 feedback_url, feedback_frequency, verbose):
        self.apns_cert = apns_cert
        self.apns_key = apns_key
        self.feedback_frequency = int(feedback_frequency)
        self.feedback_url = feedback_url
        self.interface = interface
        self.sandbox = bool(sandbox)
        self.verbose = bool(verbose)

        # APNS connection wrapper
        self.apns = apns.PushConnection(sandbox, apns_cert, apns_key)

    @defer.inlineCallbacks
    def feedback_check(self):
        log.msg('Checking feedback service...')

        data = yield apns.FeedbackConnection(self.sandbox, self.apns_cert,
                                             self.apns_key).get()
        log.msg('Feedback: %r' % data)

    def init_api(self):
        log.msg('Starting HTTP on %s...' % self.interface)
        root = resource.Resource()
        root.putChild("send", APISendResource(self))
        site = server.Site(root, logPath='/dev/null')
        host, port = self.interface.split(':')
        reactor.listenTCP(int(port), site, interface=host)

    def init_feedback_check(self):
        if not self.feedback_url:
            self.log_verbose('Not enabling feedback check')
            return
        log.msg('Enabling feedback check: url=%s, frequency=%d'
                % (self.feedback_url, self.feedback_frequency))
        lc = LoopingCall(self.feedback_check)
        lc.start(self.feedback_frequency, now=True)

    def log_verbose(self, message):
        if self.verbose:
            log.msg("VERBOSE: %s" % message)

    def send_push(self, device_token, payload):
        log.msg('Sending push to %s' % device_token)
        self.log_verbose('Payload = %r' % payload)
        self.apns.send_push(device_token, payload)

    def startService(self):
        Service.startService(self)
        self.init_api()
        self.init_feedback_check()

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
