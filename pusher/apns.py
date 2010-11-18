# Based on code from http://goo.gl/AgUHR

from OpenSSL import SSL
from twisted.internet.protocol import Protocol
from twisted.internet.ssl import ClientContextFactory
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


class APNSProtocol(Protocol):

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
