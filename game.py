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
STATE_NAME_INPUT = 5
STATE_LOBBY = 6


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

        self.colors = [
            (0, 255, 0),    # Green (P1)
            (255, 0, 255),  # Magenta/Purple (P2) - Replaced Red
            (0, 0, 255),    # Blue (P3)
            (255, 255, 0),  # Yellow (P4)
        ]

    def reset_game(self, full_reset=False, soft_reset=False):
        if full_reset:
            self.state = STATE_MENU
            self.network = None
            self.is_server = False
        
        # Soft reset: Keep network, clear game state
        
        self.snakes = {}
        self.local_player_id = 0
        if self.network:
            if self.is_server:
                self.local_player_id = 0
            elif self.network.my_id is not None:
                self.local_player_id = self.network.my_id

        # Update snake init to use correct ID if creating immediately
        # But for Lobby, we wait for update loop.
        
        # Default start pos, will be updated by server or logic
        start_pos = (self.width // 2, self.height // 2)
        
        if self.state == STATE_PLAYING and not self.network:
            # Single Player
            self.snakes[self.local_player_id] = Snake(self.config, start_pos, self.local_player_id, "Player 1")
        
        self.food = Food(self.config)
        if self.local_player_id in self.snakes:
            self.food.spawn(self.snakes[self.local_player_id].body)
            
        self.score = 0 # This line is removed as per instruction 1, score is now in Snake object
        self.game_over = False
        self.paused = False
        self.spectating = False
        self.dead_players = set() # Track dead players to prevent respawn
        self.input_active = False # For leaderboard or IP entry
        self.input_text = ""
        self.showing_leaderboard = False
        
        # Menu/Connection UI vars (Keep if soft reset?)
        if not soft_reset:
             self.menu_options = ["Single Player", "Host Game", "Join Game", "Quit"]
             self.menu_index = 0
             self.connection_ip = "127.0.0.1"
             self.connection_port = "5555"
             self.player_name = "Player"
             self.lobby_players = [] # List of strings "ID: Name"
        self.spectating = False

    def run(self):
        while True:
            self.handle_events()
            
            if self.state == STATE_PLAYING or self.state == STATE_LOBBY:
                if not self.paused:
                    self.update()
            
            self.draw()
            
            # Speed control
            # Always run at 60 FPS for consistency, handle legacy speed in update if needed
            self.clock.tick(60)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit_game()
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
                
                elif self.state == STATE_NAME_INPUT:
                    if event.key == pygame.K_RETURN:
                        if self.input_text.strip():
                            self.player_name = self.input_text
                            self.input_active = False
                            # Proceed to text selection
                            # Simplify: Name Input -> Main Menu ? No, we need menu first.
                            # Flow: Menu -> [Single/Host/Join] -> If Host/Join -> Name Input -> Host/Join Setup
                            
                            # Let's say we store 'next_state'
                            if hasattr(self, 'next_state'):
                                self.state = self.next_state
                                if self.state == STATE_HOST_SETUP:
                                    self.input_text = "5555"
                                    self.input_active = True
                                elif self.state == STATE_JOIN_SETUP:
                                    self.input_text = "127.0.0.1:5555"
                                    self.input_active = True
                            else:
                                self.state = STATE_MENU
                                
                    elif event.key == pygame.K_BACKSPACE:
                        self.input_text = self.input_text[:-1]
                    else:
                        if len(self.input_text) < 15:
                            self.input_text += event.unicode

                elif self.state == STATE_LOBBY:
                    if event.key == pygame.K_ESCAPE:
                        self.state = STATE_MENU
                        self.network = None # Disconnect
                        self.reset_game(full_reset=True)
                    elif event.key == pygame.K_RETURN:
                        if self.is_server:
                            # Start Game
                            # Start Game
                            if self.network:
                                # Spawn initial food ensuring it doesn't hit snakes
                                all_bodies = []
                                for s in self.snakes.values():
                                    all_bodies.extend(s.body)
                                self.food.spawn(all_bodies, 1)
                                
                                self.network.send_update({"type": "start_game"}) # Broadcast start
                                self.state = STATE_PLAYING
                                # Should receive its own message?
                                # For local host, force state change
                                pass

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
                                if self.is_server:
                                    # Server Restart -> Broadcast and return to Lobby
                                    self.network.send_update({"type": "restart"})
                                    self.reset_game(soft_reset=True)
                                    self.state = STATE_LOBBY
                                    
                                    # Fix: Re-add Host Snake after soft reset so it appears in Lobby
                                    start_pos = (self.width // 2, self.height // 2)
                                    self.snakes[0] = Snake(self.config, start_pos, 0, self.player_name)
                                    self.snakes[0].color = self.colors[0]
                                    
                                    # Clients will rejoin via update loop logic (polling network)
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
                            # BUG FIX 2: Validate against *physical* direction (direction)
                            # to firmly prevent 180 turns even with fast input queuing
                            curr_dir = self.snakes[pid].direction
                            
                            # 180 degree check
                            if (direction.value[0] * -1 != curr_dir.value[0] or 
                                direction.value[1] * -1 != curr_dir.value[1]):
                                self.snakes[pid].next_direction = direction
                                
                    elif event['type'] == 'accel':
                        pid = event['player_id']
                        if pid in self.snakes:
                            self.snakes[pid].accelerating = event['state']

                    elif event['type'] == 'init':
                         # New player requested join (handshake part 2?)
                         pass

                # Add new players for new connections
                # NetworkManager handles connection accepting.
                # We need to check self.network.clients for IDs not in game
                with self.network.lock:
                    connected_ids = list(self.network.clients.keys())
                
                for pid in connected_ids:
                    if pid not in self.snakes and pid not in self.dead_players:
                        # Spawn new snake
                        start_pos = (self.width // 2 + pid * 20, self.height // 2 + pid * 20) # Offset
                        name = f"Player {pid}"
                        self.snakes[pid] = Snake(self.config, start_pos, pid, name)
                        # Assign color
                        color_idx = pid % len(self.colors)
                        self.snakes[pid].color = self.colors[color_idx]
                        
                        # Add to lobby list
                        if pid not in [p['id'] for p in self.lobby_players if isinstance(p, dict)]:
                            self.lobby_players.append({'id': pid, 'name': name})
                
                # Handling Lobby Start
                if self.state == STATE_LOBBY:
                    # Host just broadcasts lobby state?
                    # Or we just rely on 'state' updates which contain snakes?
                    # Snakes are created upon join. So 'snakes' dict exists.
                    # Send lobby-specific update?
                    lobby_data = {
                        "type": "lobby",
                        "players": [{"id": s.id, "name": s.name} for s in self.snakes.values()]
                    }
                    self.network.send_update(lobby_data)
                
            else: # Client
                # Process Server State
                for event in events:
                    if event['type'] == 'lobby':
                        self.lobby_players = event['players']
                    elif event['type'] == 'start_game':
                        self.state = STATE_PLAYING
                    elif event['type'] == 'restart':
                        # Host reset game
                        self.reset_game(soft_reset=True)
                        self.state = STATE_LOBBY
                    elif event['type'] == 'state':
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
                        
                        # Check if I died (was in game, now not)
                        if self.local_player_id not in self.snakes and self.state == STATE_PLAYING:
                            self.spectating = True
                            
                        # Update Food
                        self.food.positions = [tuple(p) for p in event['food']]
                        # BUG FIX: If dead, score is missing from update. Keep last known score.
                        self.score = event['scores'].get(str(self.local_player_id), self.score)
                        
                        # Update my ID if just assigned
                        if self.network.my_id is not None:
                            self.local_player_id = self.network.my_id

                    elif event['type'] == 'game_over':
                         self.game_over = True
                         self.check_leaderboard()


        # Client-Side Dead Reckoning (Prediction)
        # Run physics for all snakes to smooth out jitter
        if self.network and not self.is_server and self.state == STATE_PLAYING and not self.paused:
             for snake_id, snake in self.snakes.items():
                  # For Client, 'is_local' means "Can I accelerate it?"
                  # Only MY snake (local_player_id) should read MY keyboard.
                  # Other snakes (remote) should just move at base speed.
                  is_local = (snake_id == self.local_player_id)
                  snake.update(is_local=is_local)
                  
                  # Check for acceleration state change to sync
                  if is_local:
                      if snake.accelerating != getattr(self, 'last_accel_state', False):
                           self.last_accel_state = snake.accelerating
                           self.network.send_input({"type": "accel", "state": snake.accelerating})

        # Update Logic (Server Only or Single Player)
        # Only run physics/logic if we are actually PLAYING
        if self.state == STATE_PLAYING and (not self.network or self.is_server):
            # Update all snakes
            dead_snakes = []
            
            for snake_id, snake in self.snakes.items():
                # BUG FIX: Only allow acceleration input for local player
                # On Server: Local is ID 0. Others are remote.
                # On Client (if we ran this block, which we usually don't): Local is self.local_player_id.
                
                is_local = (snake_id == self.local_player_id)
                snake.update(is_local=is_local)
                
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
                    self.food.remove(eaten_pos)
                    snake.grow()
                    # Score update
                    # Fix: Update the snake's score object, then local score if it's us
                    snake.score += self.config['game']['score_per_food']
                    
                    if snake_id == self.local_player_id:
                         self.score = snake.score
                    
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
                    if not self.network:
                        # Single Player -> Immediate Game Over
                        self.game_over = True
                        self.check_leaderboard() 
                    else:
                        # Multiplayer -> Spectate
                        self.spectating = True
                
                # Remove from game
                if snake_id in self.snakes:
                    del self.snakes[snake_id]
                    self.dead_players.add(snake_id)

            # Check Game Over (Server)
            if self.is_server and self.network and self.state == STATE_PLAYING:
                 if len(self.snakes) == 0:
                     # All dead
                     self.game_over = True
                     self.network.send_update({"type": "game_over"})
                     self.check_leaderboard()
            
            # Broadcast State (Server)
            if self.is_server and self.network:
                state = {
                    "type": "state",
                    "snakes": [s.to_dict() for s in self.snakes.values()],
                    "food": self.food.positions,
                    "type": "state",
                    "snakes": [s.to_dict() for s in self.snakes.values()],
                    "food": self.food.positions,
                    "scores": {str(sid): s.score for sid, s in self.snakes.items()} # Fix: Broadcast actual scores
                }
                self.network.send_update(state)

                self.network.send_update(state)

    def check_leaderboard(self):
        leaderboard = load_leaderboard()
        # Check if score qualifies for top 10
        if len(leaderboard) < 10 or (leaderboard and self.score > leaderboard[-1]['score']):
            self.input_active = True
            self.input_text = ""
        else:
            self.input_active = False

    def save_score(self, name):
        leaderboard = load_leaderboard()
        leaderboard.append({'name': name, 'score': self.score})
        save_leaderboard(leaderboard)

    def handle_menu_selection(self):
        choice = self.menu_options[self.menu_index]
        if choice == "Single Player":
            self.state = STATE_PLAYING
            self.reset_game(full_reset=False) # Setup single player
        elif choice == "Host Game":
            self.next_state = STATE_HOST_SETUP
            self.state = STATE_NAME_INPUT
            self.input_text = self.player_name
            self.input_active = True
        elif choice == "Join Game":
            self.next_state = STATE_JOIN_SETUP
            self.state = STATE_NAME_INPUT
            self.input_text = self.player_name
            self.input_active = True
        elif choice == "Quit":
            self.quit_game()

    def quit_game(self):
        if self.network:
            self.network.stop()
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
                # Host is ID 0
                self.snakes[0] = Snake(self.config, start_pos, 0, self.player_name)
                self.snakes[0].color = self.colors[0]
                
                self.state = STATE_LOBBY
                self.input_active = False
            except ValueError:
                print("Invalid Port")
        elif self.state == STATE_JOIN_SETUP:
            # parsing ip:port
            target = self.input_text
            ip = "127.0.0.1"
            port = 5555
            if ":" in target:
                parts = target.split(":")
                ip = parts[0]
                try:
                    port = int(parts[1])
                except:
                    pass
            else:
                ip = target
            
            self.network = SnakeNetwork(side="client")
            if self.network.connect(ip, port):
                 self.is_server = False
                 self.state = STATE_LOBBY # Wait in lobby
                 self.input_active = False
                 # Send Init with Name
                 self.network.send_input({"type": "init", "name": self.player_name})
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
        if self.state == STATE_NAME_INPUT:
            msg = "Enter Your Name:"
        elif self.state == STATE_HOST_SETUP:
            msg = "Enter Port:" 
        else:
            msg = "Enter IP:Port (e.g. 127.0.0.1:5555)"
            
        text = self.font.render(msg, True, (255, 255, 255))
        self.screen.blit(text, (self.width//2 - 100, 200))
        
        input_s = self.font.render(self.input_text, True, (0, 255, 0))
        self.screen.blit(input_s, (self.width//2 - 100, 240))
        
        hint = self.font.render("Press Enter to Confirm", True, (100, 100, 100))
        self.screen.blit(hint, (self.width//2 - 80, 300))

    def draw_lobby(self):
        self.screen.fill((0, 0, 0))
        title = self.font.render("LOBBY - Waiting for Players", True, (255, 255, 0))
        self.screen.blit(title, (self.width//2 - 120, 50))
        
        # Display connected players
        # For Host: uses self.snakes or self.network clients?
        # self.snakes should be populated for Host.
        # For Client: uses self.lobby_players (received from server)
        
        players_to_show = []
        if self.is_server:
            players_to_show = [{"name": s.name, "id": s.id} for s in self.snakes.values()]
        else:
            players_to_show = self.lobby_players if self.lobby_players else [{"name": "Connecting...", "id": -1}]
            
        for i, p in enumerate(players_to_show):
             # Calculate color based on ID
             pid = p['id']
             if pid == -1:
                 color = (255, 255, 255)
             else:
                 color_idx = pid % len(self.colors)
                 color = self.colors[color_idx]
                 
             p_text = self.font.render(f"P{p['id']}: {p['name']}", True, color)
             self.screen.blit(p_text, (self.width//2 - 50, 150 + i * 30))
             
        if self.is_server:
            hint = self.font.render("Press ENTER to Start Game", True, (0, 255, 0))
            self.screen.blit(hint, (self.width//2 - 100, 400))
        else:
            hint = self.font.render("Waiting for Host to Start...", True, (100, 100, 100))
            self.screen.blit(hint, (self.width//2 - 100, 400))

    # Updated draw to handle states
    def draw(self):
        if self.state == STATE_MENU:
            self.draw_menu()
        elif self.state in [STATE_HOST_SETUP, STATE_JOIN_SETUP, STATE_NAME_INPUT]:
            self.draw_setup()
        elif self.state == STATE_LOBBY:
            self.draw_lobby()
        else:
            self.screen.fill(tuple(self.config['colors']['background']))
            
            for snake in self.snakes.values():
                snake.draw(self.screen)
            self.food.draw(self.screen)
            
            # Draw Score
            score_text = self.font.render(f"Score: {self.score}", True, tuple(self.config['colors']['text']))
            self.screen.blit(score_text, (10, 10))
            
            if self.spectating and not self.game_over:
                spec_text = self.font.render("SPECTATING - Waiting for others...", True, (200, 200, 200))
                self.screen.blit(spec_text, (self.width//2 - 150, 50))
            
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
