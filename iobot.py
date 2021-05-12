#!/usr/bin/env python3

import pytoml as toml
import traceback
import mastodon
import time
import requests

from memes.this_your_admin import this_your_admin as _this_your_admin

with open('config.toml') as f:
	config = toml.load(f)

pleroma = mastodon.Mastodon(**config['creds'])

me = pleroma.me()

commands = {}
def command(func):
	commands[func.__name__.replace('_', '-')] = func
	return func

def handle(notif):
	content = notif['status']['pleroma']['content']['text/plain']
	before, mention, command = content.partition('@iobot')
	command = command.strip()
	command_name, *command_args = command.split()
	try:
		command_handler = commands[command_name]
	except KeyError:
		return

	command_handler(notif, *command_args)

@command
def ping(notif, *_):
	pleroma.status_post('pong', in_reply_to_id=notif['status'])

def main():
	while True:
		notifs = pleroma.notifications(mentions_only=True)
		for notif in notifs:
			handle(notif)
		pleroma.notifications_clear()

		time.sleep(1)

if __name__ == '__main__':
	main()
