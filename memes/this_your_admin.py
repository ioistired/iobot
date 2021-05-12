#!/usr/bin/env python3

import wand.image
import wand.color
import wand.drawing

def this_your_admin(to_insert: wand.image.Image) -> wand.image.Image:
	with (
		wand.image.Image(filename='res/thisyouradmin1.png') as this_your_admin,
		wand.image.Image(filename='res/thisyouradmin2.png') as you_clowns,
	):
		to_insert.transform(resize=f'621x{to_insert.width}')
		out = wand.image.Image(
			width=this_your_admin.width,
			height=this_your_admin.height + to_insert.height + you_clowns.height,
		)
		out.composite(this_your_admin, 0, 0)
		with wand.drawing.Drawing() as post_background:
			post_background.fill_color = wand.color.Color('#191b22')
			post_background.rectangle(left=0, top=130, right=out.width, bottom=130+to_insert.height)
			post_background.fill_color = wand.color.Color('#313543')
			post_background.rectangle(left=5, top=130, right=out.width-7, bottom=130+to_insert.height)
			post_background(out)
		out.composite(to_insert, 28, 130)
		out.composite(you_clowns, 0, 130 + to_insert.height)
		return out.convert('png')
