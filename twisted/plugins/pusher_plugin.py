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
        ["apns-cert", None, None, "Path to APNS SSL cert in .pem format."],
        ["apns-key", None, None, "Path to APNS SSL key in .pem format."],
        ["interface", None, "localhost:2196",
            "Interface to accept requests on."],
        ["feedback-url", None, None,
            "URL to hit with feedback service data. See README for format."],
        ["feedback-frequency", None, 60,
            "Minutes between feedback service checks."]]

    longdesc = 'Pusher is a service for sending push notifications using \
        a persistent connection. Please see http://github.com/hipchat/pusher \
        to report issues or get help.'


class PusherServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = "pusher"
    description = "A service for sending push notifications."
    options = Options

    def makeService(self, options):
        required = ['apns-cert', 'apns-key', 'interface']
        for opt in required:
            if options[opt] is None:
                print "ERROR: Please provide --%s.\n" % opt
                print options
                sys.exit(1)

        return PusherService(options['interface'],
                             bool(options['sandbox']),
                             options['apns-cert'],
                             options['apns-key'],
                             options['feedback-url'],
                             options['feedback-frequency'],
                             bool(options['verbose']))


serviceMaker = PusherServiceMaker()
