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
        self.input_active = False
        self.input_text = ""
        self.showing_leaderboard = False

    def run(self):
        while True:
            self.handle_events()
            if not self.game_over and not self.paused:
                self.update()
            self.draw()
            
            # Speed control
            if self.config['game'].get('pixel_movement', False):
                # Fixed FPS for smooth movement
                self.clock.tick(60)
            else:
                # Legacy grid-based speed
                speed = self.config['game']['speed'] * self.snake.speed_multiplier
                self.clock.tick(int(speed))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if self.game_over:
                    if self.input_active:
                        if event.key == pygame.K_RETURN:
                            self.save_score(self.input_text)
                            self.input_active = False
                            self.input_text = ""
                        elif event.key == pygame.K_BACKSPACE:
                            self.input_text = self.input_text[:-1]
                        else:
                            # Limit name length
                            if len(self.input_text) < 10:
                                self.input_text += event.unicode
                    elif event.key == pygame.K_r:
                        self.reset_game()
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                else:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    elif event.key == pygame.K_p:
                        self.paused = not self.paused
                        self.showing_leaderboard = False # Hide leaderboard if just pausing
                    elif event.key == pygame.K_l:
                        if not self.showing_leaderboard:
                            self.paused = True
                            self.showing_leaderboard = True
                        else:
                            self.paused = False
                            self.showing_leaderboard = False
                    elif not self.paused:
                        self.snake.handle_input(event)

    def update(self):
        self.snake.update()
        
        # Score for movement
        # self.score += self.config['game']['score_per_move'] # Requirement removed
        
        # Check collision
        if self.snake.check_collision():
            self.game_over = True
            self.check_leaderboard()
            return

        # Check food
        head = self.snake.body[0]
        head_rect = pygame.Rect(head[0], head[1], self.snake.block_size, self.snake.block_size)
        
        # Check collision with any food
        eaten_pos = None
        for pos in self.food.positions:
            food_rect = pygame.Rect(pos[0], pos[1], self.food.block_size, self.food.block_size)
            if head_rect.colliderect(food_rect):
                eaten_pos = pos
                break
                
        if eaten_pos:
            self.food.remove(eaten_pos)
            self.snake.grow()
            self.score += self.config['game']['score_per_food']
            
            # Calculate food count based on score
            # Base 1, +1 for every 50 points (example)
            food_count = 1 + (self.score // 50)
            self.food.spawn(self.snake.body, food_count)
            
            if self.eat_sound:
                self.eat_sound.play()

    def check_leaderboard(self):
        leaderboard = load_leaderboard()
        # Check if score qualifies for top 10
        if len(leaderboard) < 10 or (leaderboard and self.score > leaderboard[-1]['score']):
            self.input_active = True
            self.input_text = ""
        else:
            self.input_active = False
            # Still save if list is not full? No, logic above covers it.
            # If not top 10, just don't save or maybe save without name? 
            # Requirement says "Leaderboard with names".
            pass

    def save_score(self, name):
        leaderboard = load_leaderboard()
        leaderboard.append({'name': name, 'score': self.score})
        save_leaderboard(leaderboard)

    def draw(self):
        self.screen.fill(tuple(self.config['colors']['background']))
        
        self.snake.draw(self.screen)
        self.food.draw(self.screen)
        
        # Draw Score
        score_text = self.font.render(f"Score: {self.score}", True, tuple(self.config['colors']['text']))
        self.screen.blit(score_text, (10, 10))
        
        if self.paused:
            if self.showing_leaderboard:
                # Show Leaderboard
                y_offset = 40
                leaderboard = load_leaderboard()
                leaderboard.sort(key=lambda x: x['score'], reverse=True)
                
                title_text = self.font.render("LEADERBOARD", True, tuple(self.config['colors']['text']))
                title_rect = title_text.get_rect(center=(self.width/2, self.height/2 - 50))
                self.screen.blit(title_text, title_rect)
                
                for i, entry in enumerate(leaderboard[:5]): # Show top 5
                    name = entry.get('name', 'Anonymous')
                    score = entry['score']
                    lb_text = self.font.render(f"{i+1}. {name}: {score}", True, tuple(self.config['colors']['text']))
                    rect = lb_text.get_rect(center=(self.width/2, self.height/2 + i * 30))
                    self.screen.blit(lb_text, rect)
            else:
                pause_text = self.font.render("PAUSED", True, tuple(self.config['colors']['text']))
                text_rect = pause_text.get_rect(center=(self.width/2, self.height/2))
                self.screen.blit(pause_text, text_rect)

        if self.game_over:
            if self.input_active:
                prompt_text = self.font.render("New High Score! Enter Name: " + self.input_text, True, tuple(self.config['colors']['text']))
                text_rect = prompt_text.get_rect(center=(self.width/2, self.height/2))
                self.screen.blit(prompt_text, text_rect)
            else:
                game_over_text = self.font.render("GAME OVER - Press R to Restart", True, tuple(self.config['colors']['text']))
                text_rect = game_over_text.get_rect(center=(self.width/2, self.height/2))
                self.screen.blit(game_over_text, text_rect)
                
                # Show Leaderboard
                y_offset = 40
                leaderboard = load_leaderboard()
                # Sort just in case
                leaderboard.sort(key=lambda x: x['score'], reverse=True)
                for i, entry in enumerate(leaderboard[:5]): # Show top 5
                    name = entry.get('name', 'Anonymous')
                    score = entry['score']
                    lb_text = self.font.render(f"{i+1}. {name}: {score}", True, tuple(self.config['colors']['text']))
                    rect = lb_text.get_rect(center=(self.width/2, self.height/2 + y_offset + i * 30))
                    self.screen.blit(lb_text, rect)
            
        pygame.display.flip()
