#!/usr/bin/env python3

import pytoml as toml
import traceback
import mastodon
import time
import requests
import wand.image
import io
from bs4 import BeautifulSoup

from memes.this_your_admin import this_your_admin as _this_your_admin

with open('config.toml') as f:
	config = toml.load(f)

pleroma = mastodon.Mastodon(**config['creds'])

me = pleroma.me()

commands = {}
def command(func):
	commands[func.__name__.replace('_', '-')] = func
	return func

def reply(notif, status, **kwargs):
	if notif['status']['visibility'] in {'public', 'unlisted'}:
		kwargs['visibility'] = 'unlisted'
	mentions = [notif['account']['acct']]
	for mention in notif['status']['mentions']:
		if mention['acct'] != me['acct']:
			mentions.append(mention['acct'])
	return pleroma.status_post(
		''.join('@' + mention + ' ' for mention in mentions) + status,
		in_reply_to_id=notif['status'],
		**kwargs,
	)

def html_to_plain(content):
	soup = BeautifulSoup(content, 'html.parser')
	for br in soup.find_all('br'):
		br.replace_with('\n')
	return soup.text

def parse_mentions(content):
	"""'@a @b @bot @c ping pong' -> ['ping', 'pong']

	'@a @b @c foo bar
	@bot quux garply'
	-> ['quux', 'garply']
	"""
	command_content = []
	in_mentions_block = False
	has_me = False
	for word in html_to_plain(content).split():
		if command_content and not in_mentions_block and word.startswith('@'):
			break
		if word == '@' + me['acct']:
			has_me = True
			in_mentions_block = True
		if word.startswith('@') and not in_mentions_block and word != '@' + me['acct']:
			in_mentions_block = True
			has_me = False
		if not word.startswith('@'):
			in_mentions_block = False
		if has_me and not in_mentions_block:
			command_content.append(word)

	return command_content

def handle(notif):
	try:
		command_name, *command_args = parse_mentions(notif['status']['content'])
	except ValueError:
		return

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
