import pygame
import sys
import os
from snake import Snake, Direction
from food import Food
from utils import load_config, load_leaderboard, save_leaderboard
from network import SnakeNetwork
import time

# Game States
STATE_MENU = 0
STATE_HOST_SETUP = 1
STATE_JOIN_SETUP = 2
STATE_PLAYING = 3
STATE_GAME_OVER = 4

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
        
        self.reset_game(full_reset=True)
        
        # Load sounds
        self.eat_sound = None
        if self.config['audio']['enabled']:
            sound_path = os.path.join('assets', 'eat.wav')
            if os.path.exists(sound_path):
                self.eat_sound = pygame.mixer.Sound(sound_path)
                self.eat_sound.set_volume(self.config['audio']['volume'])
            else:
                print(f"Warning: Sound file {sound_path} not found.")

    def reset_game(self, full_reset=False):
        if full_reset:
            self.state = STATE_MENU
            self.network = None
            self.is_server = False
        
        self.snakes = {}
        self.local_player_id = 0
        
        # Default start pos, will be updated by server or logic
        start_pos = (self.width // 2, self.height // 2)
        
        if self.state == STATE_PLAYING and not self.network:
            # Single Player
            self.snakes[self.local_player_id] = Snake(self.config, start_pos, self.local_player_id, "Player 1")
        
        self.food = Food(self.config)
        if self.local_player_id in self.snakes:
            self.food.spawn(self.snakes[self.local_player_id].body)
            
        self.score = 0
        self.game_over = False
        self.paused = False
        self.input_active = False # For leaderboard or IP entry
        self.input_text = ""
        self.showing_leaderboard = False
        
        # Menu/Connection UI vars
        self.menu_options = ["Single Player", "Host Game", "Join Game", "Quit"]
        self.menu_index = 0
        self.connection_ip = "127.0.0.1"
        self.connection_port = "5555"
        self.player_name = "Player"

    def run(self):
        while True:
            self.handle_events()
            
            if self.state == STATE_PLAYING:
                if not self.game_over and not self.paused:
                    self.update()
            
            self.draw()
            
            # Speed control
            # Always run at 60 FPS for consistency, handle legacy speed in update if needed
            self.clock.tick(60)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if self.state == STATE_MENU:
                    if event.key == pygame.K_UP:
                        self.menu_index = (self.menu_index - 1) % len(self.menu_options)
                    elif event.key == pygame.K_DOWN:
                        self.menu_index = (self.menu_index + 1) % len(self.menu_options)
                    elif event.key == pygame.K_RETURN:
                        self.handle_menu_selection()
                        
                elif self.state in [STATE_HOST_SETUP, STATE_JOIN_SETUP]:
                    # Handle text input for IP/Port/Name
                    if event.key == pygame.K_ESCAPE:
                        self.state = STATE_MENU
                    elif event.key == pygame.K_RETURN:
                        # Confirm connection
                        self.start_multiplayer()
                    elif event.key == pygame.K_BACKSPACE:
                        if self.input_active: # Using input_active to track which field?
                            # Simplify: One field for now or toggle?
                            # Let's say: Join -> Enter IP. Host -> Enter Port.
                            self.input_text = self.input_text[:-1]
                    else:
                        if self.input_active and len(self.input_text) < 20:
                            self.input_text += event.unicode

                elif self.state == STATE_PLAYING:
                    if self.game_over:
                        if self.input_active:
                            if event.key == pygame.K_RETURN:
                                self.save_score(self.input_text)
                                self.input_active = False
                                self.input_text = ""
                                if self.network: # Disconnect/return to menu
                                    self.reset_game(full_reset=True)
                            elif event.key == pygame.K_BACKSPACE:
                                self.input_text = self.input_text[:-1]
                            else:
                                if len(self.input_text) < 10:
                                    self.input_text += event.unicode
                        elif event.key == pygame.K_r:
                            if self.network:
                                pass # Remote restart not implemented yet
                            else:
                                self.reset_game() # Restart single player
                        elif event.key == pygame.K_ESCAPE:
                            self.reset_game(full_reset=True)
                    else:
                        if event.key == pygame.K_ESCAPE:
                            self.reset_game(full_reset=True)
                        elif event.key == pygame.K_p:
                            self.paused = not self.paused
                            self.showing_leaderboard = False 
                        elif event.key == pygame.K_l:
                            if not self.showing_leaderboard:
                                self.paused = True
                                self.showing_leaderboard = True
                            else:
                                self.paused = False
                                self.showing_leaderboard = False
                        elif not self.paused:
                            if self.local_player_id in self.snakes:
                                self.snakes[self.local_player_id].handle_input(event)
                                
                                # Send input to server
                                if self.network and not self.is_server:
                                    key_map = {
                                        pygame.K_UP: "UP", pygame.K_DOWN: "DOWN",
                                        pygame.K_LEFT: "LEFT", pygame.K_RIGHT: "RIGHT"
                                    }
                                    if event.key in key_map:
                                        self.network.send_input({"type": "input", "dir": key_map[event.key]})

    def update(self):
        # Network Handling
        if self.network:
            events = self.network.get_events()
            
            if self.is_server:
                # Process remote inputs
                for event in events:
                    if event['type'] == 'input':
                        pid = event['player_id']
                        direction_str = event['dir']
                        if pid in self.snakes:
                            # We need to manually trigger handle_input equivalent logic
                            # Or update snake class to accept abstract Direction
                            direction = Direction[direction_str]
                            self.snakes[pid].next_direction = direction # Simplified, no safety check?
                            # Better: use proper input handling to prevent 180 turns
                            # Reuse logic...
                            curr = self.snakes[pid].direction
                            if (direction.value[0] * -1 != curr.value[0] or 
                                direction.value[1] * -1 != curr.value[1]):
                                self.snakes[pid].next_direction = direction
                                
                    elif event['type'] == 'init':
                         # New player requested join (handshake part 2?)
                         pass

                # Add new players for new connections
                # NetworkManager handles connection accepting.
                # We need to check self.network.clients for IDs not in game
                with self.network.lock:
                    connected_ids = list(self.network.clients.keys())
                
                for pid in connected_ids:
                    if pid not in self.snakes:
                        # Spawn new snake
                        start_pos = (self.width // 2 + pid * 20, self.height // 2 + pid * 20) # Offset
                        self.snakes[pid] = Snake(self.config, start_pos, pid, f"Player {pid}")
                
            else: # Client
                # Process Server State
                for event in events:
                    if event['type'] == 'state':
                        # Update Snakes
                        server_snakes = event['snakes']
                        current_ids = []
                        for s_data in server_snakes:
                            sid = s_data['id']
                            current_ids.append(sid)
                            if sid not in self.snakes:
                                # Create new
                                self.snakes[sid] = Snake.from_dict(s_data, self.config)
                            else:
                                # Update
                                self.snakes[sid].update_from_dict(s_data)
                        
                        # Remove disconnected snakes
                        to_remove = [k for k in self.snakes if k not in current_ids]
                        for k in to_remove:
                            del self.snakes[k]
                            
                        # Update Food
                        self.food.positions = [tuple(p) for p in event['food']]
                        self.score = event['scores'].get(str(self.local_player_id), 0)
                        
                        # Update my ID if just assigned (handled in network.py but we need to know local_player_id)
                        if self.network.my_id is not None:
                            self.local_player_id = self.network.my_id

        # Update Logic (Server Only or Single Player)
        if not self.network or self.is_server:
            # Update all snakes
            dead_snakes = []
            
            for snake_id, snake in self.snakes.items():
                snake.update()
                
                # Check collision (Walls and Self)
                if snake.check_collision():
                    dead_snakes.append(snake_id)
                    continue
                
                # Check collision with other snakes
                head = snake.body[0]
                head_rect = pygame.Rect(head[0], head[1], snake.block_size, snake.block_size)
                
                for other_id, other_snake in self.snakes.items():
                    if snake_id == other_id:
                        continue
                    
                    # Check collision with other snake's body
                    for segment in other_snake.body:
                        seg_rect = pygame.Rect(segment[0], segment[1], other_snake.block_size, other_snake.block_size)
                        if head_rect.colliderect(seg_rect):
                            dead_snakes.append(snake_id)
                            break
                
                if snake_id in dead_snakes:
                    continue
    
                # Check food
                # Check collision with any food
                eaten_pos = None
                for pos in self.food.positions:
                    food_rect = pygame.Rect(pos[0], pos[1], self.food.block_size, self.food.block_size)
                    if head_rect.colliderect(food_rect):
                        eaten_pos = pos
                        break
                        
                if eaten_pos:
                    self.food.remove(eaten_pos)
                    snake.grow()
                    # Score update
                    if snake_id == self.local_player_id:
                         self.score += self.config['game']['score_per_food']
                    
                    # Spawn new food
                    all_bodies = []
                    for s in self.snakes.values():
                        all_bodies.extend(s.body)
                    
                    self.food.spawn(all_bodies, 1)
    
                    if self.eat_sound:
                        self.eat_sound.play()
    
            # Handle deaths
            for snake_id in dead_snakes:
                if snake_id == self.local_player_id:
                    self.game_over = True
                    self.check_leaderboard() # Only save score for local player?
                
                # Respawn remote players? Or Permanent Death? requirements say "Last man standing ends game"
                # "当最後一個人往生之後遊戲結束"
                if snake_id in self.snakes:
                    del self.snakes[snake_id] # Eliminate them
            
            # Check Last Man Standing (if MP)
            if self.network and len(self.snakes) <= 1:
                # If only 1 left and we had more than 1 start... 
                # For now just let it run until they die too or manually quit.
                pass
            
            # Broadcast State (Server)
            if self.is_server and self.network:
                state = {
                    "type": "state",
                    "snakes": [s.to_dict() for s in self.snakes.values()],
                    "food": self.food.positions,
                    "scores": {str(sid): len(s.body) for sid, s in self.snakes.items()} # Or separate score dict
                }
                self.network.send_update(state)

    def handle_menu_selection(self):
        choice = self.menu_options[self.menu_index]
        if choice == "Single Player":
            self.state = STATE_PLAYING
            self.reset_game(full_reset=False) # Setup single player
        elif choice == "Host Game":
            self.state = STATE_HOST_SETUP
            self.input_text = "5555" # Default port
            self.input_active = True
        elif choice == "Join Game":
            self.state = STATE_JOIN_SETUP
            self.input_text = "127.0.0.1" # Default IP
            self.input_active = True
        elif choice == "Quit":
            pygame.quit()
            sys.exit()

    def start_multiplayer(self):
        if self.state == STATE_HOST_SETUP:
            try:
                port = int(self.input_text)
                self.network = SnakeNetwork(side="server")
                self.network.start_host(port)
                self.is_server = True
                self.local_player_id = 0
                self.snakes = {}
                start_pos = (self.width // 2, self.height // 2)
                self.snakes[0] = Snake(self.config, start_pos, 0, "Host")
                self.state = STATE_PLAYING
                self.input_active = False
            except ValueError:
                print("Invalid Port")
        elif self.state == STATE_JOIN_SETUP:
            ip = self.input_text
            self.network = SnakeNetwork(side="client")
            if self.network.connect(ip, 5555): # Hardcoded port for join for simplicity or split input
                 self.is_server = False
                 self.state = STATE_PLAYING
                 self.input_active = False
                 # Wait for ID assignment / State
                 self.snakes = {} 
            else:
                 print("Connection Failed")
                 self.state = STATE_MENU

    def draw_menu(self):
        self.screen.fill((0, 0, 0))
        title = self.font.render("SNAKE MULTIPLAYER", True, (0, 255, 0))
        self.screen.blit(title, (self.width//2 - 100, 100))
        
        for i, option in enumerate(self.menu_options):
            color = (255, 255, 0) if i == self.menu_index else (255, 255, 255)
            text = self.font.render(option, True, color)
            self.screen.blit(text, (self.width//2 - 50, 200 + i * 40))

    def draw_setup(self):
        self.screen.fill((0, 0, 0))
        msg = "Enter Port:" if self.state == STATE_HOST_SETUP else "Enter IP:"
        text = self.font.render(msg, True, (255, 255, 255))
        self.screen.blit(text, (self.width//2 - 50, 200))
        
        input_s = self.font.render(self.input_text, True, (0, 255, 0))
        self.screen.blit(input_s, (self.width//2 - 50, 240))
        
        hint = self.font.render("Press Enter to Start", True, (100, 100, 100))
        self.screen.blit(hint, (self.width//2 - 60, 300))

    # Updated draw to handle states
    def draw(self):
        if self.state == STATE_MENU:
            self.draw_menu()
        elif self.state in [STATE_HOST_SETUP, STATE_JOIN_SETUP]:
            self.draw_setup()
        else:
            self.screen.fill(tuple(self.config['colors']['background']))
            
            for snake in self.snakes.values():
                snake.draw(self.screen)
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
