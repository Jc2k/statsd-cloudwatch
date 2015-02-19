from setuptools import setup, find_packages
import os

version = '0.0.1'

setup(
    name='statsd-cloudwatch',
    version=version,
    url="http://github.com/Jc2k/statsd-cloudwatch",
    description="A statsd server that publishes to cloudwatch",
    long_description = open("README.rst").read(),
    author="Isotoma Limited",
    author_email="support@isotoma.com",
    license="Apache Software License",
    classifiers = [
        "Intended Audience :: System Administrators",
        "Operating System :: POSIX",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
    ],
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'boto',
    ],
    entry_points='''
        [console_scripts]
        statsd_cloudwatch = statsd_cloudwatch.main:main
    ''',
)
