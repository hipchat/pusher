import sys
from pusher.pusher import PusherService
from twisted.application.service import IServiceMaker
from twisted.plugin import IPlugin
from twisted.python import usage
from zope.interface import implements


class Options(usage.Options):
    optFlags = [
        ["sandbox", None, "Use default sandbox APNS server."],
        ["verbose", "v", "Verbose logging"]]

    optParameters = [
        ["apns-host", None, "gateway.push.apple.com:2195", "APNS host."],
        ["apns-cert", None, None, "Path to APNS SSL cert in .pem format."],
        ["apns-key", None, None, "Path to APNS SSL key in .pem format."],
        ["interface", None, "localhost:2196",
            "Interface to accept requests on."]]

    longdesc = 'Pusher is a service for sending push notifications using \
        a persistent connection. Please see http://github.com/hipchat/pusher \
        to report issues or get help.'


class PusherServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = "pusher"
    description = "A service for sending push notifications."
    options = Options

    def makeService(self, options):
        for opt, val in dict(options).items():
            if val is None:
                print "ERROR: Please provide --%s.\n" % opt
                print options
                sys.exit(1)

        if options['sandbox']:
            apns_host = "gateway.sandbox.push.apple.com:2195"
        else:
            apns_host = options['apns-host']

        return PusherService(options['interface'],
                             apns_host,
                             options['apns-cert'],
                             options['apns-key'],
                             bool(options['verbose']))


serviceMaker = PusherServiceMaker()
