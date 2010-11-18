Pusher
=======

A service for sending Apple push notifications using a persistent connection.
Why? Because [Apple says](http://goo.gl/3UgbY):

 > You should also retain connections with APNs across multiple notifications. APNs may consider connections that are rapidly and repeatedly established and torn down as a denial-of-service attack.

Pusher manages the connection to APNS for you and provides a simple RESTful API for sending push notifications.


Install
-------

    $ sudo python setup.py install


Running
-------

Production:

    $ twistd pusher --apns-cert=prod-cert.pem --apns-key=prod-key.pem

Development (sandbox):

    $ twistd pusher --sandbox --apns-cert=dev-cert.pem --apns-key=dev-key.pem

Note: You can also pass `--apns-host` to set the APNS host explicitly.


Sending pushes
--------------

HTTP POST to `http://localhost:2196/send` with the fields `deviceToken` (64 byte string) and `payload` (JSON) containing the same data you would normally send to the APNS server directly. You can change the host and port for the REST API using the`--interface` command line option.

    $ curl http://localhost:2196/send \
        -d "deviceToken=<your token>&payload={\"aps\":{\"alert\":\"Testing Pusher\"}}" 

The HTTP request will return immediately since Pusher does not wait for the push to be delivered to the APNS server. It will return an error if your deviceToken or payload appear to be malformed, however.


To Do
-----

 * Idea: Poll feedback service & hit configurable webhook
