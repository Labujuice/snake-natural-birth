import pygame
from enum import Enum

class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

class Snake:
    def __init__(self, config, start_pos):
        self.block_size = config['game']['block_size']
        self.color = tuple(config['colors']['snake'])
        self.body = [start_pos] # List of (x, y) tuples
        self.direction = Direction.RIGHT
        self.next_direction = Direction.RIGHT
        self.grow_pending = 0
        self.speed_multiplier = 1.0
        self.base_speed = config['game']['speed']
        
        self.window_width = config['window']['width']
        self.window_height = config['window']['height']
        self.solid_walls = config['game']['solid_walls']

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            new_dir = None
            if event.key == pygame.K_UP:
                new_dir = Direction.UP
            elif event.key == pygame.K_DOWN:
                new_dir = Direction.DOWN
            elif event.key == pygame.K_LEFT:
                new_dir = Direction.LEFT
            elif event.key == pygame.K_RIGHT:
                new_dir = Direction.RIGHT
            
            if new_dir:
                # Prevent reversing direction immediately
                # Check if new direction is opposite to current
                if (new_dir.value[0] * -1 != self.direction.value[0] or 
                    new_dir.value[1] * -1 != self.direction.value[1]):
                    
                    if new_dir == self.direction:
                        self.speed_multiplier = 1.5 # Accelerate
                    else:
                        self.next_direction = new_dir
                        self.speed_multiplier = 1.0 # Reset speed on turn

    def update(self):
        self.direction = self.next_direction
        
        head_x, head_y = self.body[0]
        dx, dy = self.direction.value
        
        new_x = head_x + dx * self.block_size
        new_y = head_y + dy * self.block_size
        
        if not self.solid_walls:
            new_x = new_x % self.window_width
            new_y = new_y % self.window_height
            
        new_head = (new_x, new_y)
        
        self.body.insert(0, new_head)
        
        if self.grow_pending > 0:
            self.grow_pending -= 1
        else:
            self.body.pop()
            
    def grow(self):
        self.grow_pending += 1

    def draw(self, surface):
        for segment in self.body:
            pygame.draw.rect(surface, self.color, 
                             (segment[0], segment[1], self.block_size, self.block_size))

    def check_collision(self):
        head = self.body[0]
        
        # Wall collision
        if self.solid_walls:
            if (head[0] < 0 or head[0] >= self.window_width or 
                head[1] < 0 or head[1] >= self.window_height):
                return True

        # Self collision
        if head in self.body[1:]:
            return True
            
        return False
