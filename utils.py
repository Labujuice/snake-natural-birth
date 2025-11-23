import json
import os

CONFIG_FILE = 'config.json'
LEADERBOARD_FILE = 'leaderboard.json'

def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Config file {CONFIG_FILE} not found. Using defaults.")
        # Return a safe default config if file is missing
        return {
            "window": {"width": 800, "height": 600, "title": "Snake DIY"},
            "colors": {"snake": [0, 255, 0], "food": [255, 0, 0], "background": [0, 0, 0], "text": [255, 255, 255]},
            "game": {"speed": 10, "block_size": 20, "solid_walls": True, "score_per_move": 1, "score_per_food": 10},
            "audio": {"volume": 0.5, "enabled": True}
        }

def load_leaderboard():
    if not os.path.exists(LEADERBOARD_FILE):
        return []
    try:
        with open(LEADERBOARD_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_leaderboard(scores):
    # Keep top 10
    scores.sort(key=lambda x: x['score'], reverse=True)
    scores = scores[:10]
    with open(LEADERBOARD_FILE, 'w') as f:
        json.dump(scores, f, indent=4)
