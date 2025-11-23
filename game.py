import pygame
import sys
import os
from snake import Snake
from food import Food
from utils import load_config, load_leaderboard, save_leaderboard

class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        
        self.config = load_config()
        self.width = self.config['window']['width']
        self.height = self.config['window']['height']
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption(self.config['window']['title'])
        
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 24)
        
        self.reset_game()
        
        # Load sounds
        self.eat_sound = None
        if self.config['audio']['enabled']:
            sound_path = os.path.join('assets', 'eat.wav')
            if os.path.exists(sound_path):
                self.eat_sound = pygame.mixer.Sound(sound_path)
                self.eat_sound.set_volume(self.config['audio']['volume'])
            else:
                print(f"Warning: Sound file {sound_path} not found.")

    def reset_game(self):
        start_pos = (self.width // 2, self.height // 2)
        self.snake = Snake(self.config, start_pos)
        self.food = Food(self.config)
        self.food.spawn(self.snake.body)
        self.score = 0
        self.game_over = False
        self.paused = False

    def run(self):
        while True:
            self.handle_events()
            if not self.game_over and not self.paused:
                self.update()
            self.draw()
            
            # Speed control
            speed = self.config['game']['speed'] * self.snake.speed_multiplier
            self.clock.tick(int(speed))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r and self.game_over:
                    self.reset_game()
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                else:
                    self.snake.handle_input(event)

    def update(self):
        self.snake.update()
        
        # Score for movement
        # self.score += self.config['game']['score_per_move'] # Requirement removed
        
        # Check collision
        if self.snake.check_collision():
            self.game_over = True
            self.save_score()
            return

        # Check food
        if self.snake.body[0] == self.food.position:
            self.snake.grow()
            self.score += self.config['game']['score_per_food']
            self.food.spawn(self.snake.body)
            if self.eat_sound:
                self.eat_sound.play()

    def save_score(self):
        leaderboard = load_leaderboard()
        leaderboard.append({'score': self.score})
        save_leaderboard(leaderboard)

    def draw(self):
        self.screen.fill(tuple(self.config['colors']['background']))
        
        self.snake.draw(self.screen)
        self.food.draw(self.screen)
        
        # Draw Score
        score_text = self.font.render(f"Score: {self.score}", True, tuple(self.config['colors']['text']))
        self.screen.blit(score_text, (10, 10))
        
        if self.game_over:
            game_over_text = self.font.render("GAME OVER - Press R to Restart", True, tuple(self.config['colors']['text']))
            text_rect = game_over_text.get_rect(center=(self.width/2, self.height/2))
            self.screen.blit(game_over_text, text_rect)
            
        pygame.display.flip()
