# Based on code from http://goo.gl/AgUHR

from OpenSSL import SSL
from twisted.internet import defer, protocol, reactor, task
from twisted.internet.ssl import ClientContextFactory
from twisted.python import log
import binascii
import json
import struct


class APNSClientContextFactory(ClientContextFactory):

    def __init__(self, cert_file, key_file):
        self.ctx = SSL.Context(SSL.SSLv3_METHOD)
        self.ctx.use_certificate_file(cert_file)
        self.ctx.use_privatekey_file(key_file)

    def getContext(self):
        return self.ctx


class APNSProtocol(protocol.Protocol):

    _disconnected = False

    def connectionLost(self, reason):
        protocol.Protocol.connectionLost(self, reason)
        log.msg('Lost connection to APNS: %s' % reason)
        self._disconnected = True

    def sendMessage(self, device_token, payload):
        """Sends a push notification

        device_token: 64 byte string containg hexlified device token
        payload: Dictionary containing ALL payload data (including 'aps')

        Notification messages are binary messages in network order using the
        following format. Official docs: http://goo.gl/bczsS

          <1 byte command><2 bytes length><token><2 bytes length><payload>

        """
        if len(device_token) != 64:
            raise Exception("Device token must be 64 bytes: %r" % device_token)

        if not isinstance(payload, dict):
            raise Exception("Payload must be a dictionary")

        payload = json.dumps(payload, separators=(',', ':'))
        payload_len = len(payload)
        fmt = "!cH32sH%ds" % payload_len
        command = '\x00'
        device_token = binascii.unhexlify(device_token)
        msg = struct.pack(fmt, command, 32, device_token, payload_len, payload)
        self.transport.write(msg)

    def timeoutConnection(self):
        self.transport.loseConnection()


class APNSConnection():
    """Managed APNS connection that supports reconnection."""

    # Max time to use an APNS connection
    CONNECTION_TIMEOUT = 59

    def __init__(self, host, port, cert_file, key_file):
        self.host = host
        self.port = port
        self.cert_file = cert_file
        self.key_file = key_file
        self.connection = None
        self.pending_deferreds = []
        self.pending_connection = False

        # Dissonnect every 59 minutes (Apple suggests every hour). The next
        # push will trigger a new connection to be made.
        lc = task.LoopingCall(self.disconnect)
        lc.start(self.CONNECTION_TIMEOUT * 60, now=False)

    def disconnect(self):
        if self.connection:
            log.msg('Closing APNS connection')
            self.connection.timeoutConnection()
            self.connection = None

    @defer.inlineCallbacks
    def send_push(self, device_token, payload):
        conn = yield self._connection()
        if not conn:
            defer.returnValue(False)

        conn.sendMessage(device_token, payload)
        defer.returnValue(True)

    def _connection(self):
        """Returns APNSProtocol connection in a deferred."""

        # return immediately if we're connected
        if self.connection:
            if self.connection._disconnected:
                self.connection = None
            else:
                d = defer.Deferred()
                d.callback(self.connection)
                return d

        # return a deferred if we're already waiting on a connection.
        # these deferreds are fired once the connection is established
        if self.pending_connection:
            d = defer.Deferred()
            self.pending_deferreds.append(d)
            return d

        def cb(conn):
            log.msg('Connected to APNS at %s:%s => %r'
                    % (self.host, self.port, conn))
            self.connection = conn
            # provide connection to waiting operations
            for d in self.pending_deferreds:
                d.callback(conn)
            self.pending_connection = False
            self.pending_deferreds = []
            return conn

        def eb(error):
            log.msg('ERROR: Unable to connect to APNS at %s:%s - %s'
                    % (self.host, self.port, error))
            for d in self.pending_deferreds:
                d.errback(error)
            self.pending_connection = False
            self.pending_deferreds = []
            return None

        self.pending_connection = True
        ctx = APNSClientContextFactory(self.cert_file, self.key_file)
        cc = protocol.ClientCreator(reactor, APNSProtocol)
        d = cc.connectSSL(self.host, self.port, ctx)
        d.addCallback(cb).addErrback(eb)
        return d
