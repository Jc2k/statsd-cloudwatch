=================
statsd-cloudwatch
=================

This is a simple service that runs in the foreground and publishes metrics
received via the statsd protocol on  udp port 8125 to CloudWatch. It's
expecting to run on EC2 with an IAM Instance Profile defined.


Installation
============

You can install this with pip::

    pip install statsd-cloudwatch

It will install a binary called ``statsd_cloudwatch``. This will run in the
foreground and listen on port 8125. To run it as a service you can use systemd
or upstart.

The following snippets assuming you have created a user called statsd.

For upstart, add ``/etc/init/statsd.conf``::

    start on runlevel [2345]
    stop on runlevel [!2345]
    setuid statsd
    setgid statsd
    kill timeout 900
    respawn
    exec /app/bin/statsd_cloudwatch


Credentials
===========

It is assumed that you will run this service on EC2 instances and that they
will receive their credentials via the Amazon metadata service. You will need
the following IAM policy::

    {
        "Statement": [{
            "Action": ["cloudwatch:PutMetricData"],
            "Effect": "Allow",
            "Resource": "*"
        }]
    }
