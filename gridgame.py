import pygame
from pygame import Surface
from os import path
from collections import defaultdict

UP = lambda coords: (coords[0], coords[1] - 1)
DOWN = lambda coords: (coords[0], coords[1] + 1)
LEFT = lambda coords: (coords[0] - 1, coords[1])
RIGHT = lambda coords: (coords[0] + 1, coords[1])
DIRECTION = {pygame.K_UP: UP,
		pygame.K_DOWN: DOWN,
		pygame.K_LEFT: LEFT,
		pygame.K_RIGHT: RIGHT}
OPPOSITE = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT, None: None}


def exists(cell, test=True):
	if not test:
		return True
	try:
		return cell.exists
	except AttributeError:
		pass
	return bool(cell)


def get_surf(cell, world):
	try:
		return cell.surface
	except AttributeError:
		pass
	try:
		surf = Surface((world.unit_x, world.unit_y))
		surf.fill(cell.rgb)
		return surf
	except AttributeError:
		pass
	surf = Surface((world.unit_x, world.unit_y))
	surf.fill((255, 255, 255))
	return surf


class RGB(object):
	def __init__(self, R, G, B):
		self.rgb = R, G, B


class Texture(object):
	def __init__(self, image_path):
		if image_path.startswith('/'):
			full_path = image_path
		else:
			main_file = __file__
			realpath = path.realpath(main_file)
			full_path = path.join(path.dirname(realpath), image_path)
		self.surface = pygame.image.load(full_path)


class GridEntity(object):
	coords = 0, 0
	world = None

	@property
	def x(self):
		return self.coords[0]

	@x.setter
	def x(self, val):
		self.coords = val, self.coords[1]

	@property
	def y(self):
		return self.coords[1]

	@y.setter
	def y(self, val):
		self.coords =  self.coords[0], val

	def __init__(self, grid=[[None]], coords=(0, 0), world=None):
		self.grid = grid
		self.coords = coords
		if world:
			world.add_obj(self)

	def normalize_coords(self, coords):
		return coords[0] + self.x, coords[1] + self.y

	def get_normal(self, coords):
		x = coords[0] - self.x
		y = coords[1] - self.y
		if x < 0 or y < 0:
			return None
		return self.grid[x][y]

	def set_normal(self, coords, val):
		x = coords[0] - self.x
		y = coords[1] - self.y
		if x < 0 or y < 0:
			return None
		self.grid[x][y] = val

	def check_normal_in(self, coords):
		x = self.x < coords[0] < self.x + len(self.grid[0])
		y = self.y < coords[1] < self.y + len(self.grid)
		return x and y

	def shares_coords(self, obj):
		return (self.x, self.y) == (obj.x, obj.y)

	def shares_coords_any(self, objs):
		for obj in objs:
			if obj != self and self.shares_coords(obj):
				return True
		return False

	def shares_coords_world(self):
		return self.shares_coords_any(self.world)

	def does_collide(self, obj, req_exist=(True, True)):
		for x, col in enumerate(self):
			for y, cell1 in enumerate(col):
				try:
					cell2 = obj.get_normal(self.normalize_coords((x, y)))
				except IndexError:
					pass
				else:
					if exists(cell1, req_exist[0]) and exists(cell2, req_exist[1]):
						return True
		return False

	def does_collide_any(self, objs, req_exist=(True, True)):
		for obj in objs:
			if obj != self and self.does_collide(obj, req_exist):
				return True
		return False

	def does_collide_world(self, req_exist=(True, True)):
		return self.does_collide_any(self.world)

	def merge(self, obj):
		new = self.copy()
		for x, col in enumerate(obj):
			for y, cell in enumerate(col):
				try:
					if exists(cell):
						coords = obj.normalize_coords((x, y))
						new.set_normal(coords, cell)
				except IndexError:
					pass
		return new

	def copy(self):
		grid = [list(row) for row in self]
		return type(self)(grid, (self.x, self.y))

	def set_grid(self, grid):
		self.grid = grid

	def __iter__(self):
		return iter(self.grid)

	def __len__(self):
		return len(self.grid)

	def __getitem__(self, sub):
		if sub[0] < 0:
			raise IndexError
		if len(sub) == 1:
			return self.grid[sub[0]]
		else:
			if sub[1] < 0:
				raise IndexError
			return self.grid[sub[0]][sub[1]]

	def __setitem__(self, sub, val):
		if sub[0] < 0:
			raise IndexError
		if len(sub) == 1:
			self.grid[sub[0]] = val
		else:
			self.grid[sub[0]][sub[1]] = val

	def __delitem__(self, sub):
		if sub[0] < 0:
			raise IndexError
		if len(sub) == 1:
			self.grid[sub[0]] = None
		else:
			self.grid[sub[0]][sub[1]] = None


class World(object):
	rgb = 0, 0, 0
	draw_x = 0
	draw_y = 0
	unit_x = 25
	unit_y = 25

	def __init__(self, surf=None):
		self._objs = []
		self.surf = surf

	def add_obj(self, obj):
		obj.world = self
		self._objs.append(obj)

	def remove_obj(self, obj):
		self._objs.remove(obj)
		obj.world = None

	def win_to_normal(self, coords):
		x = coords[0] / self.unit_x
		y = coords[1] / self.unit_y
		x, y = int(x), int(y)
		x, y = (x + self.draw_x), (y + self.draw_y)
		return x, y

	def normal_to_win(self, coords):
		x, y = (coords[0] - self.draw_x), (coords[1] - self.draw_y)
		x *= self.unit_x
		y *= self.unit_y
		return x, y

	def draw(self):
		self.surf.fill(self.rgb)
		width, height = self.surf.get_width(), self.surf.get_height()
		width = int(width / self.unit_x)
		height = int(height / self.unit_y)
		for x in range(self.draw_x, width + self.draw_x):
			for y in range(self.draw_y, height + self.draw_y):
				for cell, _ in self[x, y]:
					if exists(cell):
						draw_coords = self.normal_to_win((x, y))
						self.surf.blit(get_surf(cell, self), draw_coords)
		pygame.display.flip()

	def __getitem__(self, tup):
		for obj in self:
			try:
				val = obj.get_normal(tup)
				if val:
					yield (val, obj)
			except IndexError:
				pass

	def __iter__(self):
		return iter(self._objs)


class SimpleEventBus(object):
	def __init__(self, state=None):
		self.listeners = defaultdict(list)
		self.state = state

	def add_listener(self, listener, event):
		self.listeners[event].append(listener)

	def remove_listener(self, listener, event):
		self.listeners[event].remove(listener)

	def pump(self, elist):
		for event in elist:
			for listener in self.listeners[event.type]:
				if self.state is None:
					listener(event)
				else:
					listener(event, self.state)

