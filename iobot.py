#!/usr/bin/env python3

import contextlib
import pytoml as toml
import traceback
import mastodon
import time
import requests
import wand.image
import io
import shlex
from bs4 import BeautifulSoup

from memes.this_your_admin import this_your_admin as _this_your_admin
from timecard import timecard as _timecard

with open('config.toml') as f:
	config = toml.load(f)

pleroma = mastodon.Mastodon(**config['creds'])

me = pleroma.me()

commands = {}
def command(func):
	command_name = func.__name__.replace('_', '-')
	commands[command_name] = func
	func.command_name = command_name
	if func.__doc__:
		func.short_help = func.__doc__.partition('\n')[0]
	else:
		func.short_help = None
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

def get_image(status):
	def get_attach(status):
		attachments = status['media_attachments']
		for attach in attachments:
			if attach['pleroma']['mime_type'].startswith('image/'):
				return attach

	return (
		get_attach(status)
		or next(filter(None, map(get_attach, pleroma.status_context(status['id'])['ancestors'])), None)
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
	for word in shlex.split(html_to_plain(content)):
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
	"""dankwraith dunks on your image

	Upload an image to use. If you don't, I'll pick the most recent image sent in this thread.
	Source: https://monads.online/@dankwraith/106178429002959039
	"""
	attach = get_image(notif['status'])
	if not attach:
		return reply(notif, 'Error: no image found attached to your message or in this thread.')

	with (
		requests.get(attach['url']) as resp,
		wand.image.Image(blob=resp.content) as img,
		_this_your_admin(img) as out,
	):
		outf = io.BytesIO()
		out.save(outf)
		media = pleroma.media_post(
			outf.getbuffer(),
			mime_type='image/png',
			file_name='this_your_admin.png',
			description=(
				f'@dankwraith@monads.online says: "this your admin?" in response to an image:\n'
				+ attach["description"]
				+ '\n@dankwraith replies: how are you clowns not just ashamed of yourselves 24/7'
			)
		)
		reply(notif, '', media_ids=[media])

@command
def timecard(notif, *args):
	"""Generates a spongebob-style timecard using your text.

	Each argument is a line. Please quote multi-word arguments.
	"""
	outf = io.BytesIO()
	_timecard(args, file=outf)
	media = pleroma.media_post(
		outf.getbuffer(),
		mime_type='image/png',
		file_name='timecard.png',
		description='\n'.join(args),
	)
	reply(notif, '', media_ids=[media])

@command
def command_format(*_):
	"""More help with summoning the bot.

	For commands that take more than one argument, you can pass one argument with spaces using quotes:
	@{username} timecard one "dance party" later

	To summon the bot, just mention it: @{username} ping
	If you're replying to someone, just add the bot's tag: @joe @karim @{username} ping
	If you want to say something and invoke a command in the same message, use two blocks of pings:

	@joe @karim Yeah I agree
	@{username} this-your-admin
	"""

@command
def help(notif, command=None, /, *_):
	"""Shows this message. Pass the name of a command for more info."""
	if command:
		try:
			docs = commands[command].__doc__
		except KeyError:
			return reply(notif, f'Command {command} not found.')

		if not docs:
			return reply(notif, f'{command}: no help given.')

		reply(notif, docs.format(username=me['acct']).replace('@', '@\N{zero width space}'))
	else:
		topics = []
		for func in commands.values():
			if func.short_help:
				topics.append(f'• {func.command_name} — {func.short_help}')
			else:
				topics.append(f'• {func.command_name}')

		reply(
			notif,
			'I am a basic bot created by https://csdisaster.club/io. I only run when summoned. '
			'Available commands/help topics:\n\n'
			+ '\n'.join(topics)
		)

def main():
	print('Logged in as:', '@' + me['acct'])
	while True:
		notifs = pleroma.notifications(mentions_only=True)
		for notif in notifs:
			handle(notif)
		pleroma.notifications_clear()

		time.sleep(1)

if __name__ == '__main__':
	with contextlib.suppress(KeyboardInterrupt):
		main()
