# Snake DIY

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
- **audio**: Enable/disable sound and set volume.

## Controls

- **Arrow Keys**: Move the snake.
- **Same Direction**: Hold the key for the current direction to accelerate.
- **R**: Restart game (when Game Over).
- **ESC**: Quit game.

## Features

- **Leaderboard**: Top 10 scores are saved in `leaderboard.json`.
- **Sound Effects**: Place an `eat.wav` file in the `assets` folder to enable sound.
