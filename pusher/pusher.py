import json
from os import getpid
from socket import gethostname
from twisted.application.service import Service
from twisted.internet import defer, protocol, reactor, task
from twisted.python import log

import apns
from vendor.twistedgears import client  # github.com/dustin/twisted-gears


class PusherService(Service):

    def __init__(self, apns_host, gearman_host, gearman_queue, ssl_cert,
                 ssl_key, verbose):
        self.apns_host = apns_host
        self.gearman_host = gearman_host
        self.gearman_queue = gearman_queue
        self.ssl_cert = ssl_cert
        self.ssl_key = ssl_key
        self.verbose = bool(verbose)

        self.apns_proto = None
        self.gearman_proto = None

    @defer.inlineCallbacks
    def startService(self):
        Service.startService(self)
        log.msg('Service starting')

        yield self.apns_connect()
        yield self.gearman_connect()

    @defer.inlineCallbacks
    def apns_connect(self):
        self.log_verbose('Connecting to APNS...')

        try:
            cc = protocol.ClientCreator(reactor, apns.APNSProtocol)
            ctx = apns.APNSClientContextFactory(self.ssl_cert, self.ssl_key)
            host, port = self.apns_host.split(':')
            self.apns_proto = yield cc.connectSSL(host, int(port), ctx)
            log.msg('Connected to APNS at %s' % self.apns_host)
        except Exception, e:
            log.msg('ERROR: Unable to connect to APNS at %s: %s'
                    % (self.apns_host, e))
            defer.returnValue(False)

        defer.returnValue(True)

    @defer.inlineCallbacks
    def gearman_connect(self):
        self.log_verbose('Connecting to Gearman...')
        worker_id = self.get_worker_id()

        try:
            cc = protocol.ClientCreator(reactor, client.GearmanProtocol)
            host, port = self.gearman_host.split(':')
            self.gearman_proto = yield cc.connectTCP(host, int(port))
            log.msg('Connected to Gearman at %s. queue=%s, workerid=%s'
                    % (self.gearman_host, self.gearman_queue, worker_id))
        except Exception, e:
            log.msg('ERROR: Unable to connect to Gearman at %s: %s'
                    % (self.gearman_host, e))
            defer.returnValue(False)

        # setup worker object
        w = client.GearmanWorker(self.gearman_proto)
        w.setId(worker_id)
        w.registerFunction(self.gearman_queue, self.process_job)

        # start 5 coiterators
        # TODO: Should we store these and call stop() in stopService?
        coop = task.Cooperator()
        for i in range(5):
            reactor.callLater(0.1 * i, lambda: coop.coiterate(w.doJobs()))

        defer.returnValue(True)

    def get_worker_id(self):
        return 'pusher-%s-%s' % (gethostname(), getpid());

    def stopService(self):
        Service.stopService(self)
        log.msg('Service stopping')

    def log_verbose(self, message):
        if self.verbose:
            log.msg("VERBOSE: %s" % message)

    def process_job(self, job_data, job_handle):
        try:
            log.msg('Processing job: %s' % job_handle)
            try:
                data = json.loads(job_data)
            except Exception, e:
                log.err(e)
                return defer.succeed("ERROR: Job data is not valid JSON: %s, %r"
                                     % (e, job_data))

            if 'device_token' not in data:
                raise Exception("'device_token' not found: %r" % data)
            if 'payload' not in data:
                raise Exception("'payload' not found: %r" % data)

            device_token = str(data['device_token'])
            payload = data['payload']

            self.log_verbose('device_token = %r' % device_token)
            self.log_verbose('payload = %r' % payload)
            self.apns_proto.sendMessage(device_token, payload)

            return defer.succeed("OK")
        except Exception, e:
            log.err(e)
            return defer.succeed("ERROR: %s" % e)
