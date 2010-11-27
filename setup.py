#!/usr/bin/env python

# Based off http://chrismiles.livejournal.com/23399.html

import sys

try:
    import twisted
except ImportError:
    raise SystemExit("twisted not found. Make sure you "
                     "have installed the Twisted core package.")

from distutils.core import setup


def refresh_plugin_cache():
    from twisted.plugin import IPlugin, getPlugins
    list(getPlugins(IPlugin))


if __name__ == "__main__":
    setup(name='pusher',
        version='1.0',
        description='Service for sending push notifications.',
        author='Garret Heaton',
        author_email='garret@hipchat.com',
        url='http://github.com/hipchat/pusher',
        packages=[
            'pusher',
            'twisted.plugins'],
        package_data={
            'twisted': ['plugins/pusher_plugin.py']
        })

    refresh_plugin_cache()
