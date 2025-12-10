# Snake DIY
![alt text](image.png)


A classic Snake game developed in Python 3 using Pygame.

## Installation

1.  **Prerequisites**: Ensure you have Python 3 installed.
2.  **Install Pygame**:
    ```bash
    pip install pygame
    ```

## Running the Game

Run the game using the following command:

```bash
python3 main.py
```

## Configuration

You can customize the game settings in `config.json`.
- **window**: Set window size and title.
- **colors**: Set RGB colors for snake, food, background, and text.
- **game**:
    - `speed`: Base speed of the snake.
    - `block_size`: Size of each grid block.
    - `solid_walls`: `true` for game over on wall hit, `false` for wrap-around.
    - `score_per_move`: Points earned per move.
    - `score_per_food`: Points earned per food eaten.
    - `pixel_movement`: `true` for smooth movement, `false` for grid-based.
    - `pixel_speed`: Speed in pixels per frame (for smooth movement).
- **audio**: Enable/disable sound and set volume.

## Multiplayer

Enjoy Snake with friends over a local network!

1.  **Host Game**: Select "Host Game" from the menu. Enter a port number (default 5555) to start the server.
2.  **Join Game**: Select "Join Game". Enter the Host's `IP:Port` (e.g., `192.168.1.5:5555`) to connect.
3.  **Lobby**: Wait for all players to join. The Host presses **ENTER** to start the match.
4.  **Gameplay**:
    - Avoid walls (if enabled), your own body, and other snakes.
    - Last snake standing wins!
    - **Spectator Mode**: If you die, you stay in the game to watch the remaining players.
    - **Restart**: When the game ends (all players dead), the Host can press **R** to return everyone to the Lobby.

## Controls

- **Arrow Keys**: Move the snake.
- **Same Direction**: Hold the key for the current direction to accelerate (Server/Client supported).
- **P**: Pause/Resume game (Single Player).
- **L**: Toggle Leaderboard.
- **R**: Restart game (when Game Over). In Multiplayer, only Host controls this.
- **ESC**: Quit game / Disconnect from server.

## Features

- **Multiplayer (New)**: TCP/IP based networking with Authoritative Server architecture.
- **Dead Reckoning**: Client-side prediction for smooth, lag-free movement.
- **Lobby System**: Dedicated waiting room for players to gather before starting.
- **Spectator Mode**: Continue watching the action after elimination.
- **Smooth Movement**: Pixel-based movement for a fluid experience.
- **Leaderboard**: Top 10 scores saved locally.
- **Distinct Colors**: Each player gets a unique color (Green, Magenta, Blue, Yellow).
- **Configurable**: Customize settings in `config.json`.
