Pusher
=======

A service for sending Apple push notifications using a persistent connection.


Install
-------

    $ sudo python setup.py install

Running
-------

Prod:

    $ twistd pusher --apns-cert=prod-cert.pem --apns-key=prod-key.pem

Dev:

    $ twistd pusher --sandbox --apns-cert=dev-cert.pem --apns-key=dev-key.pem


Note: You can also pass --apns-host to set it manually.


Sending pushes
--------------

HTTP POST to http://localhost:2196/send with the fields deviceToken and
payload. You can change the host and port for the REST API using the
--interface command line option.


To Do
-----

 * Reconnecting protocol for APNS
 * Restart APNS connection hourly
 * Idea: Poll feedback service & hit configurable webhook
 * Idea: Generic coiterator for getting jobs so we can plug in to other queues
