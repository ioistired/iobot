#!/usr/bin/env python3

import contextlib
import pytomlpp as toml
import requests
import wand.image
import io
from mastodon import Mastodon
from pleroma_bot import PleromaBot

from memes.this_your_admin import this_your_admin as _this_your_admin
from timecard import timecard as _timecard

with open('config.toml') as f:
	config = toml.load(f)

pleroma = Mastodon(**config['creds'])
bot = PleromaBot(pleroma, about='I am a basic bot created by https://csdisaster.club/io. I only run when summoned.')

@bot.command
def ping(notif, *_):
	bot.reply(notif, 'pong')

@bot.command
def this_your_admin(notif, *_):
	"""dankwraith dunks on your image

	Upload an image to use. If you don't, I'll pick the most recent image sent in this thread.
	Source: https://monads.online/@dankwraith/106178429002959039
	"""
	attach = bot.get_image(notif['status'])
	if not attach:
		return bot.reply(notif, 'Error: no image found attached to your message or in this thread.')

	with (
		requests.get(attach['url']) as resp,
		wand.image.Image(blob=resp.content) as img,
		_this_your_admin(img) as out,
	):
		outf = io.BytesIO()
		out.save(outf)
		media = bot.pleroma.media_post(
			outf.getbuffer(),
			mime_type='image/png',
			file_name='this_your_admin.png',
			description=(
				f'@dankwraith@monads.online says: "this your admin?" in response to an image:\n'
				+ attach["description"]
				+ '\n@dankwraith replies: how are you clowns not just ashamed of yourselves 24/7'
			)
		)
		bot.reply(notif, media_ids=[media])

@bot.command
def timecard(notif, *args):
	"""Generates a spongebob-style timecard using your text.

	Each argument is a line. Please quote multi-word arguments.
	"""
	outf = io.BytesIO()
	_timecard(args, file=outf)
	media = bot.pleroma.media_post(
		outf.getbuffer(),
		mime_type='image/png',
		file_name='timecard.png',
		description='\n'.join(args),
	)
	bot.reply(notif, media_ids=[media])

# this is defined as a help topic
@bot.command
def command_format(notif, *_):
	"""More help with summoning the bot.

	For commands that take more than one argument, you can pass one argument with spaces using quotes:
	@{username} timecard one "dance party" later

	To summon the bot, just mention it: @{username} ping
	If you're replying to someone, just add the bot's tag: @joe @karim @{username} ping
	If you want to say something and invoke a command in the same message, use two blocks of pings:

	@joe @karim Yeah I agree
	@{username} this-your-admin
	"""
	bot.help(notif, 'command-format')

if __name__ == '__main__':
	bot.run()
