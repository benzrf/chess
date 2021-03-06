#!/usr/bin/python3.3
from __future__ import print_function
import pygame
import chess
import gridgame
import socket
import argparse
import sys

b = gridgame.RGB(0, 0, 0)
w = gridgame.RGB(255, 255, 255)
g = gridgame.RGB(100, 255, 100)

bg_grid = [
	[w, b, w, b, w, b, w, b],
	[b, w, b, w, b, w, b, w],
	[w, b, w, b, w, b, w, b],
	[b, w, b, w, b, w, b, w],
	[w, b, w, b, w, b, w, b],
	[b, w, b, w, b, w, b, w],
	[w, b, w, b, w, b, w, b],
	[b, w, b, w, b, w, b, w]]

parser = argparse.ArgumentParser(description="A chess game.")
parser.add_argument('-p', '--port', type=int, default=2009,
		help="The port to host on or connect to.")
parser.add_argument('-c', '--connect', metavar="hostname",
		help="Connect to a host.")
parser.add_argument('-o', '--hotseat', action='store_true')
parser.add_argument('-l', '--log', action='store_true')


def beep():
	print('\a', file=sys.stderr)


class ChessGame:
	"""Represents a game state."""
	def __init__(self, color='white', sock=None, hotseat=False, log=False):
		self.color = color
		self.my_turn = color == 'white'
		self.sock = sock
		self.hotseat = hotseat
		self.log = log

		world = gridgame.World()
		world.unit_x, world.unit_y = 64, 64
		world.add_obj(gridgame.GridEntity(bg_grid))
		self.world = world

		board = chess.new_board()
		world.add_obj(gridgame.GridEntity(board))
		self.board = board

		piece_selector_texture = gridgame.Texture("chess_textures/select_piece.png")
		move_selector_texture = gridgame.Texture("chess_textures/select_move.png")
		piece_selector = gridgame.GridEntity([[piece_selector_texture]],
						coords=(4, 4), world=world)
		move_selector = gridgame.GridEntity([[move_selector_texture]],
						coords=(-1, -1), world=world)
		active_selector = piece_selector
		self.piece_selector = piece_selector
		self.move_selector = move_selector
		self.active_selector = active_selector

		bus = gridgame.SimpleEventBus()
		bus.add_listener(self.on_key, pygame.KEYDOWN)
		bus.add_listener(lambda e: exit(), pygame.QUIT)
		self.bus = bus

	def play(self):
		"""Run the game."""
		pygame.init()
		pygame.key.set_repeat(400, 100)
		scr = pygame.display.set_mode((512, 512))

		self.world.surf = scr

		changed = True
		while True:
			if self.color == 'black':
				self.rotate_board()
				self.world.draw()
				self.rotate_board()
			else:
				self.world.draw()
			if self.my_turn:
				self.bus.pump_one(pygame.event.wait())
			else:
				self.serve()

	@property
	def checkmated(self):
		#TODO: Implement a method to check if this player is in checkmate
		pass

	def rotate_board(self):
		"""Rotate the board 180 degrees."""
		for col in self.board:
			col.reverse()
		self.board.reverse()
		#self.board._grid = list(zip(self.board._grid[::-1]))
		#self.board._grid = list(zip(self.board._grid[::-1]))

	def on_key(self, event):
		"""Handle a keypress event."""
		active_selector = self.active_selector
		piece_selector = self.piece_selector
		move_selector = self.move_selector
		if event.key in gridgame.DIRECTION:
			self.update_selector(event.key)
		elif event.key == pygame.K_RETURN:
			if active_selector is piece_selector:
				if self.color == 'white':
					selection = self.board[piece_selector.x][piece_selector.y]
				else:
					selection = self.board[7 - piece_selector.x][7 - piece_selector.y]
				if selection and selection.color == self.color:
					move_selector.coords = piece_selector.coords
					self.active_selector = move_selector
				else:
					beep()
			elif active_selector is move_selector:
				if self.try_move(piece_selector.coords,
						move_selector.coords):
					piece_selector.coords = move_selector.coords
					move_selector.coords = -1, -1
					self.active_selector = piece_selector
					self.my_turn = False
				else:
					beep()
		elif event.key == pygame.K_ESCAPE:
			if active_selector is move_selector:
				move_selector.coords = -1, -1
				self.active_selector = piece_selector

	def update_selector(self, direction):
		"""Move a selector in the given direction, respecting board bounds."""
		mod = gridgame.DIRECTION[direction]
		selector = self.active_selector
		new_coords = mod(selector.coords)
		if 0 <= new_coords[0] < 8 and 0 <= new_coords[1] < 8:
			selector.coords = new_coords
		else:
			beep()

	def try_move(self, source, dest):
		"""Attempt to execute a move and validate it with the other player."""
		if self.color == 'black':
			source = 7 - source[0], 7 - source[1]
			dest = 7 - dest[0], 7 - dest[1]
		move = chess.Move(self.board, source, dest)
		if move.is_valid() and self.confirm(move):
			move.apply()
			return True
		return False

	def confirm(self, move):
		"""Confirm the validity of this move with the other game instance."""
		if self.hotseat:
			if self.log:
				print(move.shorthand)
			return True
		self.sock.send(move.shorthand.encode('UTF-8') + b'\r\n')
		valid = self.sock.recv(100).strip().decode() == 'OK'
		if valid and self.log:
			print(move.shorthand)
		return valid

	def serve(self):
		"""Wait for the other game instance to make a move, then validate it."""
		if self.hotseat:
			self.my_turn = True
			self.color = 'black' if self.color == 'white' else 'white'
			return
		got_move = False
		while not got_move:
			shorthand = self.sock.recv(100).strip().decode()
			try:
				move = chess.Move.from_shorthand(self.board, shorthand)
				got_move = move.is_valid()
			except ValueError as e:
				pass
			if got_move:
				self.sock.send(b'OK\r\n')
				if self.log:
					print(shorthand)
			else:
				self.sock.send(b'NO\r\n')
		move.apply()
		pygame.event.get()
		self.my_turn = True


def run_game(opts):
	"""Run the program."""
	if opts.hotseat:
		ChessGame(hotseat=True, log=opts.log).play()
		return
	if not opts.connect:
		color = 'white'
		ssock = socket.socket()
		ssock.bind(('0.0.0.0', opts.port))
		ssock.listen(1)
		print("Awaiting connection...")
		sock, _ = ssock.accept()
	else:
		color = 'black'
		sock = socket.socket()
		sock.connect((opts.connect, opts.port))
	print("Connection established! Starting game...")
	ChessGame(color, sock, log=opts.log).play()

def main_cli():
	"""Get options from the command-line flags, then run the game."""
	opts = parser.parse_args()
	run_game(opts)


if __name__ == '__main__':
	main_cli()

