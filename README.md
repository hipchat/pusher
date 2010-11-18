Pusher
=======

A service for sending Apple push notifications using a persistent connection.
Why? Because Apple says:

 > You should also retain connections with APNs across multiple notifications.
 > APNs may consider connections that are rapidly and repeatedly established
 > and torn down as a denial-of-service attack. (http://goo.gl/3UgbY)

Pusher manages the connection to APNS for you and provides a simple RESTful API
for sending push notifications.


Install
-------

    $ sudo python setup.py install

Running
-------

Prod:

    $ twistd pusher --apns-cert=prod-cert.pem --apns-key=prod-key.pem

Dev:

    $ twistd pusher --sandbox --apns-cert=dev-cert.pem --apns-key=dev-key.pem


Note: You can also pass --apns-host to set the APNS host explicitly.


Sending pushes
--------------

HTTP POST to http://localhost:2196/send with the fields deviceToken and
payload. You can change the host and port for the REST API using the
`--interface` command line option.


To Do
-----

 * Idea: Poll feedback service & hit configurable webhook
 * Idea: Generic coiterator for getting jobs so we can plug in to other queues
