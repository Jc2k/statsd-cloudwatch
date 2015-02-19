import argparse
import copy
import datetime
import logging
import re
import select
import socket
import sys

from boto.ec2.cloudwatch import connect_to_region


log = logging.getLogger(__name__)


class Metric(object):

    unit = "None"
    value = None
    statistics = None
    default = None

    def __init__(self, server, name):
        self.server = server
        self._namespace, self.name = name.rsplit(".", 1)
        self._namespace = self._namespace.replace(".", "/")
        self._value = copy.copy(self.default)

    @property
    def namespace(self):
        return "{}/{}".format(self.server.namespace, self._namespace)

    def update(self, value, args, timestamp):
        self.timestamp = timestamp

    def push(self):
        if not self.statistics and not self.value:
            return
        self.server.cloudwatch.put_metric_data(
            namespace=self.namespace,
            name=self.name,
            timestamp=self.timestamp,
            unit=self.unit,
            value=self.value,
            statistics=self.statistics,
        )


class Counter(Metric):
    """ Counter: A gauge, but calculated at the server. Metrics sent incr
    or decr the value. Metrics may have a sample rate, which incoming
    metrics are scaled against."""

    unit = "Count"
    default = 0

    @property
    def value(self):
        return self._value

    def update(self, value, args, timestamp):
        super(Counter, self).update(value, args, timestamp)
        sample_rate = 1.0
        if len(args) == 1:
            sample_rate = float(re.match('^@([\d\.]+)', args[0]).group(1))
            if sample_rate == 0:
                return

        self._value += float(value or 1) * (1 / sample_rate)


class Gauge(Metric):
    """ Gauge: An instantaneous measurement of a value """

    default = 0

    @property
    def value(self):
        return self._value

    def update(self, value, args, timestamp):
        super(Gauge, self).update(value, args, timestamp)
        if value.startswith("+"):
            self._value += float(value[1:])
        elif value.startswith("-"):
            self._value -= float(value[1:])
        else:
            self._value = float(value)


class Meter(Metric):
    """ Meters: Measure the rate of events over time, calculated at the
    server. They may also be thought of as increment-only counters. """

    default = 0

    @property
    def value(self):
        return self._value

    def update(self, value, args, timestamp):
        super(Meter, self).update(value, args, timestamp)
        self._value += int(value or 1)


class Timer(Metric):
    """ Timer: Measure of the number of milliseconds elapsed between a
    start and end time """

    unit = "Milliseconds"
    default = []

    def update(self, value, args, timestamp):
        super(Timer, self).update(value, args, timestamp)
        self._value.append(float(value))

    @property
    def statistics(self):
        value = sorted(self._value)
        return {
            'minimum': value[0],
            'maximum': value[-1],
            'sum': sum(value),
            'samplecount': len(value),
        }


class Histogram(Timer):
    """ Histogram: A measure of the distribution of timer values over time,
    calculated at the server. As the data exported for timers and
    histograms is the same, this is currently an alias for a timer."""

    pass


class Set(Metric):
    """ Sets: count the number of unique values passed to a key """

    default = set()

    def update(self, value, args, timestamp):
        super(Set, self).update(value, args, timestamp)
        self._value.add(value)

    @property
    def value(self):
        return len(self._value)


class Server(object):

    metric_types = {
        "c": Counter,
        "g": Gauge,
        "h": Timer,
        "m": Histogram,
        "ms": Timer,
        "s": Set,
    }

    def __init__(self, namespace="Statsd"):
        self.namespace = namespace
        self.metrics = {}
        self.flush_due = datetime.datetime.now()
        self.cloudwatch = connect_to_region('eu-west-1')

    def clean_key(self, key):
        return re.sub(r'[^a-zA-Z_\-0-9\.]', '', re.sub(
            r'\s+', '_', key.replace('/', '-').replace(' ', '_'))
        )

    def process(self, data):
        timestamp = datetime.datetime.now()

        for metric in data.split('\n'):
            match = re.match('\A([^:]+):([^|]+)\|(.+)', metric)
            if not match:
                log.warn("Skipping malformed metric: {}".format(metric))
                continue

            metric = self.clean_key(match.group(1))
            value = match.group(2)
            args = match.group(3).split('|')
            metric_type = args.pop(0)

            try:
                klass = self.metric_types[metric_type]
            except KeyError:
                log.error("Unknown metric type {}".format(metric_type))
                continue

            if metric not in self.metrics:
                self.metrics[metric] = klass(self, metric)

            if not isinstance(self.metrics[metric], klass):
                log.error("Metric previously type {}, now type {}".format(type(self.metrics[metric]), klass))
                continue

            self.metrics[metric].update(value, args, timestamp)

    def push(self):
        log.debug("Pushing stats to CloudWatch")

        for name, metric in self.metrics.items():
            metric.push()
            del self.metrics[name]

    def serve(self, hostname='127.0.0.1', port=8125):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind((hostname, port))

        self.running = True
        while self.running:
            r, w, x = select.select([self._sock], [], [], 1)

            if r:
                data, addr = self._sock.recvfrom(8192)
                try:
                    self.process(data)
                except Exception:
                    log.exception("Unable to process datagram")

            if datetime.datetime.now() > self.flush_due:
                try:
                    self.push()
                except Exception:
                    log.exception('Error whilst storing statistics')

                self.flush_due = datetime.datetime.now() + datetime.timedelta(seconds=60)
                log.debug("Next flush at {}".format(self.flush_due))

        self._sock.close()

    def stop(self):
        self.running = False


def main(argv=sys.argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', dest='debug', action='store_true', default=False)
    parser.add_argument('-p', '--port', dest='port', type=int, default=8125)
    options = parser.parse_args(argv[1:])

    logging.basicConfig(loglevel=logging.DEBUG if options.debug else logging.INFO)

    server = Server()

    try:
        server.serve(port=options.port)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
