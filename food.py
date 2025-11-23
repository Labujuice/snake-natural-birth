import pygame
import random

class Food:
    def __init__(self, config):
        self.block_size = config['game']['block_size']
        self.color = tuple(config['colors']['food'])
        self.window_width = config['window']['width']
        self.window_height = config['window']['height']
        self.position = (0, 0)
        # Initial spawn will be called by Game class
        
    def spawn(self, snake_body):
        # Generate random position aligned with grid
        cols = self.window_width // self.block_size
        rows = self.window_height // self.block_size
        
        while True:
            x = random.randint(0, cols - 1) * self.block_size
            y = random.randint(0, rows - 1) * self.block_size
            if (x, y) not in snake_body:
                self.position = (x, y)
                break

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, 
                         (self.position[0], self.position[1], self.block_size, self.block_size))
