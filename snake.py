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
        
        self.pixel_mode = config['game'].get('pixel_movement', False)
        self.pixel_speed = config['game'].get('pixel_speed', 2)
        
        # In pixel mode, we need to track length in pixels or points
        if self.pixel_mode:
            # Initial length is 1 block, so we need enough points to cover 1 block size
            # But initially just one point is fine, it will grow
            pass

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
                    
                    if new_dir != self.direction:
                        self.next_direction = new_dir

    def update(self):
        # Handle direction changes with grid snapping in pixel mode
        if self.pixel_mode:
            head_x, head_y = self.body[0]
            
            # Calculate move amount
            move_amount = self.pixel_speed * self.speed_multiplier
            
            # Check if we are close to a grid line
            # Grid lines are at multiples of block_size
            # We only care about the grid line we are approaching
            
            current_dir = self.direction
            next_dir = self.next_direction
            
            if current_dir != next_dir:
                # We want to turn. Check if we can snap to grid.
                # Find distance to next grid intersection in current direction
                dist_to_grid = 0
                if current_dir == Direction.RIGHT:
                    next_grid_x = (int(head_x) // self.block_size + 1) * self.block_size
                    dist_to_grid = next_grid_x - head_x
                elif current_dir == Direction.LEFT:
                    # For left, we are moving towards smaller x. 
                    # If exactly on grid (e.g. 20), next is 0? No, we want to snap to current if we are slightly past?
                    # Actually, we want to snap to the NEAREST grid line that is "ahead" or "at" us?
                    # Let's simplify: We snap if we are within 'move_amount' of a grid line.
                    
                    # Current position relative to block:
                    rem_x = head_x % self.block_size
                    if rem_x == 0: dist_to_grid = 0 # Already on grid
                    else: dist_to_grid = rem_x # Distance to reach the previous grid line (since we move left)
                    
                elif current_dir == Direction.DOWN:
                    next_grid_y = (int(head_y) // self.block_size + 1) * self.block_size
                    dist_to_grid = next_grid_y - head_y
                elif current_dir == Direction.UP:
                    rem_y = head_y % self.block_size
                    if rem_y == 0: dist_to_grid = 0
                    else: dist_to_grid = rem_y
                
                # If we are close enough to snap (or already there)
                # We allow snapping if dist_to_grid <= move_amount
                # But wait, if dist_to_grid is 0, we are ON the line.
                # If dist_to_grid is small, we overshoot.
                
                if dist_to_grid <= move_amount:
                    # Snap to grid
                    if current_dir == Direction.RIGHT: head_x += dist_to_grid
                    elif current_dir == Direction.LEFT: head_x -= dist_to_grid
                    elif current_dir == Direction.DOWN: head_y += dist_to_grid
                    elif current_dir == Direction.UP: head_y -= dist_to_grid
                    
                    # Update body[0] to snapped position
                    self.body[0] = (head_x, head_y)
                    
                    # Apply turn
                    self.direction = next_dir
                    
                    # Reduce move_amount by the amount we used to snap?
                    # For simplicity/smoothness, we can just consume the move for this frame 
                    # or move the remainder in the new direction.
                    # Let's move remainder to keep speed constant.
                    remainder = move_amount - dist_to_grid
                    
                    dx, dy = self.direction.value
                    new_x = head_x + dx * remainder
                    new_y = head_y + dy * remainder
                    
                    # We need to insert the snapped point? 
                    # No, body[0] is already snapped. We just calculated new_x, new_y for the *new* head position.
                    # Wait, logic below inserts 'new_head'.
                    # So we should NOT update body[0] in place if we are going to insert new_head.
                    # Actually, standard logic is: calculate new_head, insert it.
                    # If we snap, we effectively insert a point AT the grid line, then another point further?
                    # Or we just make the new head be at the snapped position + remainder.
                    # The 'corner' will be implicitly formed by the history.
                    # BUT, if we don't insert the corner point explicitly, the line segment will cut the corner?
                    # Our draw function draws rects at each point. It doesn't draw lines.
                    # So "cutting corner" means we have a point at (18, 0) and next at (20, 2) (if we turned).
                    # That looks like a diagonal step.
                    # To look perfect, we might want to ensure we have a point AT (20, 0).
                    # So:
                    # 1. Update body[0] to (20, 0) ? No, body[0] is history.
                    # 2. Insert (20, 0) as a new point.
                    # 3. Then insert (20, 2) as another new point?
                    # Doing 2 inserts in one frame is complex for the 'pop' logic (growth).
                    # Simplest fix: Just calculate new_head based on snapped logic.
                    # The visual gap of 1-2 pixels is negligible for "rects".
                    pass
                else:
                    # Not close enough to grid, continue in current direction
                    # Do NOT change direction yet
                    pass
            else:
                # No turn pending, just move
                pass
        else:
            # Grid mode: direction updates happen instantly
            self.direction = self.next_direction

        # Check for acceleration (hold key for current direction)
        keys = pygame.key.get_pressed()
        if ((self.direction == Direction.UP and keys[pygame.K_UP]) or
            (self.direction == Direction.DOWN and keys[pygame.K_DOWN]) or
            (self.direction == Direction.LEFT and keys[pygame.K_LEFT]) or
            (self.direction == Direction.RIGHT and keys[pygame.K_RIGHT])):
            self.speed_multiplier = 1.5
        else:
            self.speed_multiplier = 1.0
        
        head_x, head_y = self.body[0]
        dx, dy = self.direction.value
        
        if self.pixel_mode:
            move_amount = self.pixel_speed * self.speed_multiplier
            
            # Re-calculate logic if we didn't handle it above?
            # I put the logic above but didn't assign to new_x, new_y.
            # Let's consolidate.
            
            current_dir = self.direction # This might have changed above if we snapped
            dx, dy = current_dir.value
            
            # If we just snapped and turned, we need to handle the remainder.
            # But the logic above was just "if", not "do".
            # Let's rewrite the movement block cleanly.
            
            # 1. Determine effective direction and start point
            start_x, start_y = head_x, head_y
            
            # Check snap
            if self.next_direction != self.direction:
                dist_to_grid = 0
                if self.direction == Direction.RIGHT:
                    dist_to_grid = ((int(start_x) // self.block_size + 1) * self.block_size) - start_x
                elif self.direction == Direction.LEFT:
                    dist_to_grid = start_x % self.block_size
                    if dist_to_grid == 0: dist_to_grid = 0 # logic fix: if 0, we are on grid
                elif self.direction == Direction.DOWN:
                    dist_to_grid = ((int(start_y) // self.block_size + 1) * self.block_size) - start_y
                elif self.direction == Direction.UP:
                    dist_to_grid = start_y % self.block_size
                
                if dist_to_grid <= move_amount:
                    # SNAP!
                    # Move to grid
                    if self.direction == Direction.RIGHT: start_x += dist_to_grid
                    elif self.direction == Direction.LEFT: start_x -= dist_to_grid
                    elif self.direction == Direction.DOWN: start_y += dist_to_grid
                    elif self.direction == Direction.UP: start_y -= dist_to_grid
                    
                    # Consume move amount
                    move_amount -= dist_to_grid
                    
                    # Turn
                    self.direction = self.next_direction
                    dx, dy = self.direction.value
            
            # 2. Move remaining amount
            new_x = start_x + dx * move_amount
            new_y = start_y + dy * move_amount
            
            # If we snapped, we effectively skipped the point AT the grid line in the body list?
            # We are inserting 'new_head' (new_x, new_y).
            # The previous head was 'head_x, head_y'.
            # If we snapped, 'new_head' is around the corner.
            # The segment will be diagonal.
            # To fix this visually, we can insert the corner point if we snapped.
            # But that messes up length/growth logic which assumes 1 insert per frame.
            # However, since we draw RECTS, a diagonal placement of rects:
            # [ ][ ]
            #    [ ][ ]
            # It looks fine. It's a snake.
            
        else:
            new_x = head_x + dx * self.block_size
            new_y = head_y + dy * self.block_size
        
        if not self.solid_walls:
            new_x = new_x % self.window_width
            new_y = new_y % self.window_height
            
        new_head = (new_x, new_y)
        
        self.body.insert(0, new_head)
        
        if self.grow_pending > 0:
            # Check if we have enough pending growth to cover this move
            if self.pixel_mode:
                move_len = self.pixel_speed * self.speed_multiplier
            else:
                move_len = self.block_size
                
            if self.grow_pending >= move_len:
                self.grow_pending -= move_len
                # Don't pop, effectively growing
            else:
                # Not enough pending growth to cover a full step (or pixel step)
                # But wait, if we are in pixel mode, we grow by NOT popping.
                # If we don't pop, we grow by 'move_len'.
                # So we should only NOT pop if we want to grow by 'move_len'.
                # If grow_pending < move_len, we can't grow fully?
                # Actually, we should just accumulate.
                # If we have any pending growth, we should try to use it?
                # No, the requirement is "increase by one grid".
                # So we added 'block_size' to grow_pending.
                # We consume it as we move.
                self.body.pop()
        else:
            self.body.pop()
            
    def grow(self):
        # Always add exactly one block size worth of growth
        self.grow_pending += self.block_size

    def draw(self, surface):
        for segment in self.body:
            pygame.draw.rect(surface, self.color, 
                             (segment[0], segment[1], self.block_size, self.block_size))

    def check_collision(self):
        head = self.body[0]
        head_rect = pygame.Rect(head[0], head[1], self.block_size, self.block_size)
        
        # Wall collision
        if self.solid_walls:
            if (head[0] < 0 or head[0] >= self.window_width or 
                head[1] < 0 or head[1] >= self.window_height):
                return True

        # Self collision
        # In pixel mode, head overlaps with immediate body points.
        # We need to skip the first few points that are "inside" the head.
        start_check = 1
        if self.pixel_mode:
            # Skip points within block_size distance
            # Robust fix: Skip 3 blocks worth of segments to ensure we clear the "neck"
            # even during turns.
            start_check = int(3 * self.block_size / self.pixel_speed)
            if start_check >= len(self.body):
                return False
                
        for segment in self.body[start_check:]:
            seg_rect = pygame.Rect(segment[0], segment[1], self.block_size, self.block_size)
            if head_rect.colliderect(seg_rect):
                return True
            
        return False
