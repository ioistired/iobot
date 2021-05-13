#!/usr/bin/env python3

import pytoml as toml
import traceback
import mastodon
import time
import requests
import wand.image
import io

from memes.this_your_admin import this_your_admin as _this_your_admin

with open('config.toml') as f:
	config = toml.load(f)

pleroma = mastodon.Mastodon(**config['creds'])

me = pleroma.me()

commands = {}
def command(func):
	commands[func.__name__.replace('_', '-')] = func
	return func

def reply(notif, *args, **kwargs):
	if notif['status']['visibility'] in {'public', 'unlisted'}:
		kwargs['visibility'] = 'unlisted'
	return pleroma.status_post(*args, in_reply_to_id=notif['status'], **kwargs)

def handle(notif):
	content = notif['status']['pleroma']['content']['text/plain']
	before, mention, command = content.partition('@' + me['acct'])
	command = command.strip()
	command_name, *command_args = command.split()
	try:
		command_handler = commands[command_name]
	except KeyError:
		return

	command_handler(notif, *command_args)

@command
def ping(notif, *_):
	reply(notif, 'pong')

@command
def this_your_admin(notif, *_):
	attachments = notif['status']['media_attachments']
	if len(attachments) != 1:
		return reply(notif, 'Error: please attach exactly one image file.')

	attach = attachments[0]
	if not attach['pleroma']['mime_type'].startswith('image/'):
		return reply(notif, 'Error: an image file is required, got ' + attach['pleroma']['mime_type'])
	with (
		requests.get(attach['url']) as resp,
		wand.image.Image(blob=resp.content) as img,
		_this_your_admin(img) as out,
	):
		outf = io.BytesIO()
		out.save(outf)
		media = pleroma.media_post(outf.getbuffer(), mime_type='image/png', file_name='this_your_admin.png')
		reply(notif, '', media_ids=[media])

def main():
	while True:
		notifs = pleroma.notifications(mentions_only=True)
		for notif in notifs:
			handle(notif)
		pleroma.notifications_clear()

		time.sleep(1)

if __name__ == '__main__':
	main()
