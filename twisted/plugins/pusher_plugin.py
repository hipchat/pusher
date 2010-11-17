import sys
from pusher.pusher import PusherService
from twisted.application.service import IServiceMaker
from twisted.plugin import IPlugin
from twisted.python import usage
from zope.interface import implements


class Options(usage.Options):
    optFlags = [
        ["verbose", "v", "Verbose logging"]]

    optParameters = [
        ["apns-host", None, "gateway.push.apple.com:2195", "APNS host."],
        ["gearman-host", None, "localhost:4730", "Gearman server host."],
        ["ssl-cert", None, None, "Path to SSL cert in .pem format."],
        ["ssl-key", None, None, "Path to SSL key in .pem format."]]

    longdesc = 'Pusher is a Gearman worker service for sending push \
        notifications. Please see http://github.com/hipchat/pusher to \
        report issues or get help.'


class PusherServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = "pusher"
    description = "A Gearman worker for sending push notifications."
    options = Options

    def makeService(self, options):
        for opt, val in dict(options).items():
            if val is None:
                print "ERROR: Please provide --%s.\n" % opt
                print options
                sys.exit(1)

        return PusherService(options['apns-host'],
                             options['gearman-host'],
                             options['ssl-cert'],
                             options['ssl-key'],
                             bool(options['verbose']))


serviceMaker = PusherServiceMaker()
