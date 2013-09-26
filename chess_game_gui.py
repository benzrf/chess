#!/usr/bin/python3.3
import chess_game
from PyQt4 import QtGui
from argparseui.argparseui import ArgparseUi

def main():
	"""Get options from a GUI, then run the game."""
	app = QtGui.QApplication([])
	a = ArgparseUi(chess_game.parser)
	a.show()
	app.exec_()
	if a.result():
		opts = a.parse_args()
		chess_game.run_game(opts)

if __name__ == '__main__':
	main()

