# Based on code from http://goo.gl/AgUHR

from OpenSSL import SSL
from twisted.internet import defer, protocol, reactor, ssl, task
from twisted.python import log
import binascii
import json
import struct

from StringIO import StringIO as _StringIO

class StringIO(_StringIO):
  """Add context management protocol to StringIO
      ie: http://bugs.python.org/issue1286
  """
  
  def __enter__(self):
    if self.closed:
      raise ValueError('I/O operation on closed file')
    return self
  
  def __exit__(self, exc, value, tb):
    self.close()


class ClientContextFactory(ssl.ClientContextFactory):

    def __init__(self, cert_file, key_file):
        self.ctx = SSL.Context(SSL.SSLv3_METHOD)
        self.ctx.use_certificate_file(cert_file)
        self.ctx.use_privatekey_file(key_file)

    def getContext(self):
        return self.ctx


class PushProtocol(protocol.Protocol):

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


class PushConnection():
    """Managed APNS connection that supports reconnection."""

    HOST = "gateway.push.apple.com"
    HOST_SANDBOX = "gateway.sandbox.push.apple.com"
    PORT = 2195

    # Max time to use an APNS connection
    CONNECTION_TIMEOUT = 59

    def __init__(self, sandbox, cert_file, key_file):
        self.cert_file = cert_file
        self.key_file = key_file
        self.connection = None
        self.pending_deferreds = []
        self.pending_connection = False

        self.host = self.HOST_SANDBOX if sandbox else self.HOST
        self.port = self.PORT

        # Disonnect every so often (Apple suggests every hour). The next
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
        ctx = ClientContextFactory(self.cert_file, self.key_file)
        cc = protocol.ClientCreator(reactor, PushProtocol)
        d = cc.connectSSL(self.host, self.port, ctx)
        d.addCallback(cb).addErrback(eb)
        return d


class FeedbackProtocol(protocol.Protocol):

    def __init__(self):
        self.buffer = ''
        self.d = defer.Deferred()

    def dataReceived(self, data):
        log.msg('dataReceived raw: %r' % data)
        log.msg('dataReceived hex: %r' % binascii.hexlify(data))
        self.buffer = self.buffer + data

    def connectionLost(self, reason):
        log.msg('FeedbackConnection.connectionLost: %s' % reason)
        self.d.callback(self.buffer)

    def get(self):
        return self.d


class FeedbackConnection():

    HOST = 'feedback.push.apple.com'
    HOST_SANDBOX = 'feedback.sandbox.push.apple.com'
    PORT = 2196

    def __init__(self, sandbox, cert_file, key_file):
        self.cert_file = cert_file
        self.key_file = key_file
        self.sandbox = sandbox

        self.host = self.HOST_SANDBOX if sandbox else self.HOST
        self.port = self.PORT

    @defer.inlineCallbacks
    def get(self):
        """Get all available feedback"""
        ctx = ClientContextFactory(self.cert_file, self.key_file)
        log.msg('host=%r, port=%r' % (self.host, self.port))
        cc = protocol.ClientCreator(reactor, FeedbackProtocol)
        conn = yield cc.connectSSL(self.host, self.port, ctx)
        data = yield conn.get()
        log.msg('Feedback data: %r' % data)
        log.msg('Feedback data hex: %r' % binascii.hexlify(data))
        decoded = self.decode_feedback(data)
        log.msg("Decoded: %r" % decoded)
        defer.returnValue(decoded)

    def decode_feedback(self, binary_tuples):
      """Returns a list of tuples in (datetime, token_str) format

      Taken from https://github.com/samuraisam/pyapns

      """
      fmt = '!lh32s'
      size = struct.calcsize(fmt)
      with StringIO(binary_tuples) as f:
        return [(datetime.datetime.fromtimestamp(ts), binascii.hexlify(tok))
                for ts, toklen, tok in (struct.unpack(fmt, tup) 
                                  for tup in iter(lambda: f.read(size), ''))]
