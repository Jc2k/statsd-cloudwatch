=================
statsd-cloudwatch
=================

This is a simple service that runs in the foreground and publishes metrics
received via udp on port 8125 to CloudWatch. It's expecting to run on EC2 with
an IAM Instance Profile defined.

