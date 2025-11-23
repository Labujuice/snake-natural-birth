import pygame
import random

class Food:
    def __init__(self, config):
        self.block_size = config['game']['block_size']
        self.color = tuple(config['colors']['food'])
        self.window_width = config['window']['width']
        self.window_height = config['window']['height']
        self.positions = []
        
    def spawn(self, snake_body, count=1):
        # Generate random position aligned with grid
        cols = self.window_width // self.block_size
        rows = self.window_height // self.block_size
        
        while len(self.positions) < count:
            x = random.randint(0, cols - 1) * self.block_size
            y = random.randint(0, rows - 1) * self.block_size
            
            # Check collision with snake body (rect based)
            food_rect = pygame.Rect(x, y, self.block_size, self.block_size)
            collides = False
            
            # Optimization: Check only if simple check fails or always?
            # Always check rects for safety in pixel mode
            for segment in snake_body:
                seg_rect = pygame.Rect(segment[0], segment[1], self.block_size, self.block_size)
                if food_rect.colliderect(seg_rect):
                    collides = True
                    break
            
            if not collides and (x, y) not in self.positions:
                self.positions.append((x, y))

    def remove(self, pos):
        if pos in self.positions:
            self.positions.remove(pos)

    def draw(self, surface):
        for pos in self.positions:
            pygame.draw.rect(surface, self.color, 
                             (pos[0], pos[1], self.block_size, self.block_size))
