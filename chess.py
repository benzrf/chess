#!/usr/bin/python3
import pygame
from os import path
from warnings import warn

pieces = ['rook', 'knight', 'bishop', 'king',
	'queen', 'bishop', 'knight', 'rook']
pawns = ['pawn'] * 8


def new_board():
	"""Create a new list-of-lists to populate the piece layer with."""
	new_board = []
	new_board.append([Piece('white', piece)
			for piece in reversed(pieces)])
	new_board.append([Piece('white', piece)
			for piece in pawns])
	new_board.extend([[None] * 8] * 4)
	new_board.append([Piece('black', piece)
			for piece in pawns])
	new_board.append([Piece('black', piece)
			for piece in pieces])
	new_board = list(map(list, zip(*new_board[::-1])))
	return new_board


def irange(start, end):
	if start > end:
		return range(start - 1, end, -1)
	else:
		return range(start + 1, end)


def coord_range(source, dest):
	source_file, source_rank = source
	dest_file, dest_rank = dest
	file_range = irange(source_file, dest_file)
	rank_range = irange(source_rank, dest_rank)
	gen = zip(file_range, rank_range)
	#next(gen)
	return gen

main_file = __file__
realpath = path.realpath(main_file)
realpath_dir = path.dirname(realpath)


class Piece(object):
	"""A chess piece."""

	textures = {}

	def __init__(self, color, piece_type):
		self.color, self.piece_type = color, piece_type
		if (color, piece_type) not in self.textures:
			texture_path = "chess_textures/{}{}.png".format(color[0], piece_type)
			full_path = path.join(realpath_dir, texture_path)
			self.textures[color, piece_type] = pygame.image.load(full_path)
		self.surface = self.textures[color, piece_type]
		if piece_type in ('pawn', 'rook', 'king'):
			self.moved = False
		if piece_type == 'pawn':
			self.two_space = False

	def __repr__(self):
		return "{} {}".format(self.color, self.piece_type)


def under_attack(board, loc, spiece):
	for file, col in enumerate(board):
		for rank, piece in enumerate(col):
			capture = Move(board, (file, rank), loc)
			if (piece and piece.piece_type != 'king' and
					capture.is_valid(ignore_check=True)):
				return True
	my_color = spiece.color
	file, rank = loc
	for file_add in -1, 0, 1:
		for rank_add in -1, 0, 1:
			o_file = file + file_add
			o_rank = rank + rank_add
			if not -1 < o_file < 8 or not -1 < o_rank < 8:
				continue
			o_piece = board[o_file][o_rank]
			if (o_piece and o_piece.color != my_color and
					o_piece.piece_type == 'king'):
				return True
	return False


class Move(object):
	"""A move in a chess game."""

	def __init__(self, board, source, dest):
		self.board, self.source, self.dest = board, source, dest
		self.source_piece = board[source[0]][source[1]]
		self.dest_piece = board[dest[0]][dest[1]]
		self.file_dist = abs(self.source[0] - self.dest[0])
		self.rank_dist = abs(self.source[1] - self.dest[1])

	@classmethod
	def from_shorthand(cls, board, shorthand):
		"""Create a new move from shorthand."""
		alpha = "ABCDEFGH"
		nums = "87654321"
		fields = shorthand.split()
		if len(fields) != 3 or fields[1] != 'to':
			raise ValueError("Malformed shorthand: " + shorthand)
		fields = fields[0], fields[2]
		for field in fields:
			if (len(field) != 2 or
					field[0] not in alpha or
					field[1] not in nums):
				raise ValueError("Invalid coordinates: " + field)
		source = alpha.index(fields[0][0]), nums.index(fields[0][1])
		dest = alpha.index(fields[1][0]), nums.index(fields[1][1])
		return cls(board, source, dest)

	def apply(self, silenced=False):
		"""Modify the board to the state it would be if this move were made."""
		if not silenced and not self.is_valid():
			warn('Applying invalid move')
		if self.source_piece.piece_type in ('pawn', 'rook', 'king'):
			self.source_piece.moved = True
		if self.source_piece.piece_type == 'pawn':
			direction = 1 if self.is_black_move else -1
			if self.dest[1] == self.source[1] + (direction * 2):
				self.source_piece.two_space = True
		self.board[self.source[0]][self.source[1]] = None
		self.board[self.dest[0]][self.dest[1]] = self.source_piece
		if self.is_en_passant:
			dest_file, dest_rank = self.dest
			self.board[dest_file][dest_rank - direction] = None
		for col in self.board:
			for piece in col:
				if (piece and piece.color != self.source_piece.color and
						piece.piece_type == 'pawn'):
					piece.two_space = False

	@property
	def is_capture(self):
		return ((bool(self.dest_piece) and
			self.source_piece.color != self.dest_piece.color) or
			self.is_en_passant)

	@property
	def is_black_move(self):
		return self.source_piece.color == 'black'

	@property
	def is_white_move(self):
		return self.source_piece.color == 'white'

	@property
	def is_en_passant(self):
		"""Check whether this move is an en passant capture."""
		try:
			if self.source_piece.piece_type == 'pawn':
				dest_file, dest_rank = self.dest
				direction = 1 if self.is_black_move else -1
				passing_piece = self.board[dest_file][dest_rank - direction]
				return (bool(passing_piece) and
					passing_piece.piece_type == 'pawn' and
					passing_piece.two_space and
					passing_piece.color != self.source_piece.color)
		except IndexError:
			pass
		return False

	@property
	def in_check(self):
		"""Check whether the king of this side is under attack."""
		for file, col in enumerate(self.board):
			for rank, piece in enumerate(col):
				if (piece and piece.piece_type == 'king'
						and piece.color == self.source_piece.color):
					return under_attack(self.board,
								(file, rank), piece)
		return False

	@property
	def into_check(self):
		"""Check whether this move describes a move into check."""
		hypo_board = [col[:] for col in self.board]
		hypo_move = Move(hypo_board, self.source, self.dest)
		hypo_move.apply(silenced=True)
		return under_attack(hypo_board, self.dest, self.source_piece)

	@property
	def resolves_check(self):
		"""Check whether this move will cause the king of this side to no longer be in check."""
		hypo_board = [col[:] for col in self.board]
		hypo_move = Move(hypo_board, self.source, self.dest)
		hypo_move.apply(silenced=True)
		return not hypo_move.in_check

	def is_valid(self, ignore_check=False):
		"""Check whether this move is valid according to the rules of chess.

		This property does NOT account for check lockdown!"""
		if not ignore_check and self.in_check and not self.resolves_check:
			return False
		delegate_response = getattr(self,
					'is_valid_' + self.source_piece.piece_type)
		into_self = bool(self.dest_piece) and not self.is_capture
		return delegate_response and not into_self

	@property
	def is_valid_pawn(self):
		"""Check whether this move is valid, assuming the source piece is a pawn."""
		source_file, source_rank = self.source
		dest_file, dest_rank = self.dest
		direction = 1 if self.is_black_move else -1
		one_forward = dest_rank == source_rank + direction
		if self.is_capture:
			diagonal_move = dest_file in (source_file + 1, source_file - 1)
			return one_forward and diagonal_move
		else:
			straight_move = dest_file == source_file
			first_move = not self.source_piece.moved
			double_move = dest_rank == source_rank + (direction * 2)
			nothing_blocking = not self.board[source_file][source_rank + direction]
			correct_forward = one_forward or (first_move and
							double_move and nothing_blocking)
			return correct_forward and straight_move

	@property
	def is_valid_knight(self):
		"""Check whether this move is valid, assuming the source piece is a knight."""
		return set((self.file_dist, self.rank_dist)) == {1, 2}

	@property
	def is_valid_king(self):
		"""Check whether this move is valid, assuming the source piece is a king."""
		return (self.file_dist in (0, 1) and
			self.rank_dist in (0, 1) and not
			self.into_check)

	@property
	def is_valid_rook(self):
		"""Check whether this move is valid, assuming the source piece is a rook."""
		file_dist, rank_dist = self.file_dist, self.rank_dist
		if file_dist and rank_dist:
			return False
		elif file_dist:
			for file in irange(self.dest[0], self.source[0]):
				if self.board[file][self.source[1]]:
					return False
		elif rank_dist:
			for rank in irange(self.dest[1], self.source[1]):
				if self.board[self.source[0]][rank]:
					return False
		return True

	@property
	def is_valid_bishop(self):
		"""Check whether this move is valid, assuming the source piece is a bishop."""
		file_dist, rank_dist = self.file_dist, self.rank_dist
		if file_dist != rank_dist:
			return False
		for file, rank in coord_range(self.source, self.dest):
			if self.board[file][rank]:
				return False
		return True

	@property
	def is_valid_queen(self):
		"""Check whether this move is valid, assuming the source piece is a queen."""
		return self.is_valid_rook or self.is_valid_bishop

	@property
	def shorthand(self):
		"""Convert this move to a string suitable for text-based communication."""
		alpha = "ABCDEFGH"
		nums = "87654321"
		source_file, source_rank = self.source
		source_coords = alpha[source_file] + nums[source_rank]
		dest_file, dest_rank = self.dest
		dest_coords = alpha[dest_file] + nums[dest_rank]
		return "{} to {}".format(source_coords, dest_coords)

	def __repr__(self):
		alpha = "ABCDEFGH"
		source_piece = repr(self.source_piece)
		source_file, source_rank = self.source
		source_coords = alpha[source_file] + nums[source_rank]
		dest_file, dest_rank = self.dest
		dest_coords = alpha[dest_file] + nums[dest_rank]
		dest_piece = repr(self.dest_piece)
		return "{} at {} to {} at {}".format(source_piece, source_coords,
							dest_piece, dest_coords)

