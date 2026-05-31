"""
Endless Runner — a simple Mario-style side-scroller (Version 1)
================================================================

A character runs in place while the world scrolls right-to-left, giving the
feel of moving forward. Jump over rocks, cacti, and walking scorpions.

CONTROLS
    LEFT / RIGHT arrows : move back / forward (within a screen band)
    SPACE  or  UP       : jump
    R                   : restart after game over
    ESC  or  window-X   : quit

CUSTOM ART (all optional)
    Drop PNG files into an "assets" folder next to this script and they will
    be used automatically. Without them, the game draws placeholders so it
    runs immediately.
        assets/player.png      (the Mario-like avatar)
        assets/rock.png
        assets/cactus.png
        assets/scorpion.png
        assets/background.png  (a wide sky/scenery strip)

Requires: pygame   ->   pip install pygame
"""

import os
import sys
import random
import pygame

try:
    import numpy as np
except ImportError:
    np = None       # sound synthesis disabled; game still runs silently

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
WIDTH, HEIGHT = 900, 400
FPS = 60

GROUND_HEIGHT = 72                       # thickness of the ground band
GROUND_Y = HEIGHT - GROUND_HEIGHT        # y of the ground's top surface

GRAVITY = 0.8
JUMP_VELOCITY = -15.0                    # negative = upward
# Max jump height = v^2 / (2g) = 15^2 / 1.6 ≈ 140px. All obstacles stay well
# under this so every one of them is clearable with a normal jump.

PLAYER_W, PLAYER_H = 46, 64
PLAYER_SPEED = 5                         # horizontal move speed (fore/back)
PLAYER_HOME_X = 140                      # resting horizontal position
PLAYER_MIN_X = 40
PLAYER_MAX_X = WIDTH * 0.55

BASE_SPEED = 5.0                         # world scroll speed at the start
MAX_SPEED = 11.0
SPEED_RAMP = 0.0015                      # how fast difficulty grows per frame

ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

# Colors
SKY_TOP = (135, 206, 235)
SKY_BOTTOM = (200, 232, 245)
HILL_COLOR = (150, 190, 140)
GROUND_COLOR = (196, 164, 110)
GROUND_DARK = (150, 120, 75)
TEXT_COLOR = (40, 40, 50)
WHITE = (255, 255, 255)


# --------------------------------------------------------------------------
# Asset loading (graceful fallback to None when a file is missing)
# --------------------------------------------------------------------------
def load_image(filename, size=None):
    path = os.path.join(ASSET_DIR, filename)
    if not os.path.exists(path):
        return None
    try:
        img = pygame.image.load(path).convert_alpha()
        if size is not None:
            img = pygame.transform.scale(img, size)
        return img
    except pygame.error:
        return None


# --------------------------------------------------------------------------
# Placeholder drawing (used when an image asset is absent)
# --------------------------------------------------------------------------
def draw_player_placeholder(surf, x, y, w, h):
    """A tiny red-capped, blue-overalls character."""
    # shoes
    pygame.draw.rect(surf, (90, 50, 20), (x + 6, y + h - 8, 14, 8), border_radius=3)
    pygame.draw.rect(surf, (90, 50, 20), (x + w - 20, y + h - 8, 14, 8), border_radius=3)
    # overalls / body
    pygame.draw.rect(surf, (40, 90, 200), (x + 8, y + 28, w - 16, h - 34), border_radius=6)
    # arms / shirt
    pygame.draw.rect(surf, (210, 50, 50), (x + 2, y + 28, 10, 20), border_radius=4)
    pygame.draw.rect(surf, (210, 50, 50), (x + w - 12, y + 28, 10, 20), border_radius=4)
    # face
    pygame.draw.rect(surf, (255, 220, 185), (x + 12, y + 12, w - 24, 20), border_radius=6)
    # cap
    pygame.draw.rect(surf, (210, 50, 50), (x + 8, y + 4, w - 16, 12), border_radius=5)
    pygame.draw.rect(surf, (210, 50, 50), (x + 8, y + 12, w - 4, 5), border_radius=3)
    # eye
    pygame.draw.circle(surf, (30, 30, 30), (x + w - 16, y + 22), 2)


def draw_rock(surf, x, y, w, h, _frame):
    base = (120, 120, 125)
    pygame.draw.ellipse(surf, base, (x, y + h * 0.25, w, h * 0.75))
    pygame.draw.polygon(surf, base, [
        (x + w * 0.15, y + h), (x + w * 0.30, y + h * 0.15),
        (x + w * 0.55, y), (x + w * 0.80, y + h * 0.25),
        (x + w, y + h),
    ])
    pygame.draw.line(surf, (90, 90, 95), (x + w * 0.35, y + h * 0.3),
                     (x + w * 0.5, y + h * 0.7), 2)


def draw_cactus(surf, x, y, w, h, _frame):
    green = (60, 150, 70)
    stem_w = w * 0.4
    sx = x + (w - stem_w) / 2
    pygame.draw.rect(surf, green, (sx, y, stem_w, h), border_radius=6)
    # left arm
    pygame.draw.rect(surf, green, (x, y + h * 0.45, stem_w * 0.7, h * 0.18), border_radius=5)
    pygame.draw.rect(surf, green, (x, y + h * 0.2, stem_w * 0.45, h * 0.3), border_radius=5)
    # right arm
    pygame.draw.rect(surf, green, (x + w - stem_w * 0.7, y + h * 0.35, stem_w * 0.7, h * 0.18), border_radius=5)
    pygame.draw.rect(surf, green, (x + w - stem_w * 0.45, y + h * 0.1, stem_w * 0.45, h * 0.3), border_radius=5)


def draw_scorpion(surf, x, y, w, h, frame):
    body = (110, 50, 40)
    # animated legs (oscillate as it "walks")
    swing = 3 if (frame // 6) % 2 == 0 else -3
    leg_y = y + h * 0.8
    for i in range(3):
        lx = x + w * (0.25 + i * 0.18)
        pygame.draw.line(surf, body, (lx, leg_y), (lx - 4 + swing, y + h), 2)
        pygame.draw.line(surf, body, (lx, leg_y), (lx + 4 - swing, y + h), 2)
    # body segments
    pygame.draw.ellipse(surf, body, (x + w * 0.2, y + h * 0.35, w * 0.55, h * 0.5))
    pygame.draw.circle(surf, body, (int(x + w * 0.25), int(y + h * 0.6)), int(h * 0.22))
    # claws (front, facing left = direction of travel)
    pygame.draw.line(surf, body, (x + w * 0.25, y + h * 0.55), (x, y + h * 0.45), 3)
    pygame.draw.circle(surf, body, (int(x), int(y + h * 0.45)), 4)
    # curling tail with stinger
    pygame.draw.line(surf, body, (x + w * 0.7, y + h * 0.45), (x + w * 0.9, y + h * 0.15), 3)
    pygame.draw.circle(surf, (200, 60, 60), (int(x + w * 0.9), int(y + h * 0.12)), 4)


# --------------------------------------------------------------------------
# Player
# --------------------------------------------------------------------------
class Player:
    def __init__(self, image):
        self.image = image
        self.width = PLAYER_W
        self.height = PLAYER_H
        self.reset()

    def reset(self):
        self.x = PLAYER_HOME_X
        self.y = GROUND_Y - self.height
        self.vel_y = 0.0
        self.on_ground = True

    def jump(self):
        if self.on_ground:
            self.vel_y = JUMP_VELOCITY
            self.on_ground = False
            return True
        return False

    def update(self, move_dir):
        # horizontal (fore/back)
        self.x += move_dir * PLAYER_SPEED
        self.x = max(PLAYER_MIN_X, min(self.x, PLAYER_MAX_X))
        # vertical (gravity + jump)
        self.vel_y += GRAVITY
        self.y += self.vel_y
        floor = GROUND_Y - self.height
        if self.y >= floor:
            self.y = floor
            self.vel_y = 0.0
            self.on_ground = True

    @property
    def rect(self):
        # slightly tightened hitbox so near-misses feel fair
        return pygame.Rect(int(self.x + 9), int(self.y + 6),
                           self.width - 18, self.height - 10)

    def draw(self, surf):
        if self.image:
            surf.blit(self.image, (int(self.x), int(self.y)))
        else:
            draw_player_placeholder(surf, int(self.x), int(self.y),
                                    self.width, self.height)


# --------------------------------------------------------------------------
# Obstacles
# --------------------------------------------------------------------------
# Every height stays under the ~140px max jump so all are clearable.
OBSTACLE_SPECS = {
    "rock":     {"w": 52, "h": 40},
    "cactus":   {"w": 40, "h": 78},
    "scorpion": {"w": 62, "h": 34},
}
PLACEHOLDER_DRAW = {
    "rock": draw_rock,
    "cactus": draw_cactus,
    "scorpion": draw_scorpion,
}


class Obstacle:
    def __init__(self, kind, image):
        self.kind = kind
        self.image = image
        spec = OBSTACLE_SPECS[kind]
        self.width = spec["w"]
        self.height = spec["h"]
        self.x = float(WIDTH + 20)
        self.y = GROUND_Y - self.height
        self.frame = 0
        self.scored = False

    def update(self, speed):
        self.x -= speed
        self.frame += 1

    @property
    def off_screen(self):
        return self.x + self.width < 0

    @property
    def rect(self):
        return pygame.Rect(int(self.x + 4), int(self.y + 4),
                           self.width - 8, self.height - 6)

    def draw(self, surf):
        if self.image:
            surf.blit(self.image, (int(self.x), int(self.y)))
        else:
            PLACEHOLDER_DRAW[self.kind](surf, int(self.x), int(self.y),
                                        self.width, self.height, self.frame)


# --------------------------------------------------------------------------
# Spacing maths: guarantee gaps wide enough to land and re-jump
# --------------------------------------------------------------------------
def min_safe_gap(speed):
    """Horizontal distance the world travels during one full jump arc,
    plus a buffer, so consecutive obstacles can always be dodged."""
    air_frames = 2 * abs(JUMP_VELOCITY) / GRAVITY     # ~37 frames
    jump_distance = air_frames * speed
    return jump_distance + 130


# --------------------------------------------------------------------------
# Background / ground rendering with parallax scrolling
# --------------------------------------------------------------------------
def draw_sky(surf):
    for i in range(HEIGHT):
        t = i / HEIGHT
        r = int(SKY_TOP[0] + (SKY_BOTTOM[0] - SKY_TOP[0]) * t)
        g = int(SKY_TOP[1] + (SKY_BOTTOM[1] - SKY_TOP[1]) * t)
        b = int(SKY_TOP[2] + (SKY_BOTTOM[2] - SKY_TOP[2]) * t)
        pygame.draw.line(surf, (r, g, b), (0, i), (WIDTH, i))


def draw_hills(surf, offset):
    """Slow parallax hills behind the action."""
    span = 300
    start = -(offset % span) - span
    x = start
    while x < WIDTH + span:
        pygame.draw.ellipse(surf, HILL_COLOR,
                            (x, GROUND_Y - 70, span * 1.2, 160))
        x += span


def draw_clouds(surf, offset):
    span = 360
    start = -(offset % span) - span
    x = start
    y_positions = [60, 110, 80]
    idx = 0
    while x < WIDTH + span:
        cy = y_positions[idx % len(y_positions)]
        for dx, dy, rad in [(0, 0, 22), (28, 6, 26), (56, 0, 20)]:
            pygame.draw.circle(surf, WHITE, (int(x + dx), int(cy + dy)), rad)
        x += span
        idx += 1


def draw_ground(surf, offset):
    pygame.draw.rect(surf, GROUND_COLOR, (0, GROUND_Y, WIDTH, GROUND_HEIGHT))
    pygame.draw.rect(surf, GROUND_DARK, (0, GROUND_Y, WIDTH, 6))
    # scrolling texture stripes to convey motion
    tile = 48
    start = -(int(offset) % tile)
    for x in range(start, WIDTH + tile, tile):
        pygame.draw.line(surf, GROUND_DARK,
                         (x, GROUND_Y + 14), (x + tile * 0.5, GROUND_Y + 14), 2)
        pygame.draw.line(surf, GROUND_DARK,
                         (x + tile * 0.5, GROUND_Y + 38),
                         (x + tile, GROUND_Y + 38), 2)


# --------------------------------------------------------------------------
# Sound — procedurally generated music & effects (no audio files needed)
# --------------------------------------------------------------------------
SAMPLE_RATE = 44100

# Note frequencies (Hz)
_N = {
    "A3": 220.00, "C4": 261.63, "D4": 293.66, "E4": 329.63, "G4": 392.00,
    "A4": 440.00, "C5": 523.25, "D5": 587.33, "E5": 659.25, "F5": 698.46,
    "G5": 783.99, "A5": 880.00, "B5": 987.77, "C6": 1046.50, "REST": 0.0,
}


def _envelope(n, attack=0.005, release=0.04):
    """Short fade in/out so notes don't click at their edges."""
    env = np.ones(n)
    a = min(int(attack * SAMPLE_RATE), n // 2)
    r = min(int(release * SAMPLE_RATE), n // 2)
    if a > 0:
        env[:a] = np.linspace(0.0, 1.0, a)
    if r > 0:
        env[-r:] = np.linspace(1.0, 0.0, r)
    return env


def _tone(freq, dur, wave="square", vol=0.3):
    n = int(dur * SAMPLE_RATE)
    if n <= 0:
        return np.zeros(0)
    if freq <= 0:                                   # a rest
        return np.zeros(n)
    t = np.linspace(0.0, dur, n, endpoint=False)
    if wave == "square":
        w = np.sign(np.sin(2 * np.pi * freq * t))
    elif wave == "triangle":
        w = 2 * np.abs(2 * (t * freq - np.floor(0.5 + t * freq))) - 1
    elif wave == "saw":
        w = 2 * (t * freq - np.floor(0.5 + t * freq))
    else:
        w = np.sin(2 * np.pi * freq * t)
    return w * vol * _envelope(n)


def _sweep(f0, f1, dur, wave="square", vol=0.3):
    """A tone whose pitch glides from f0 to f1 (used for jump / hit)."""
    n = int(dur * SAMPLE_RATE)
    if n <= 0:
        return np.zeros(0)
    freqs = np.linspace(f0, f1, n)
    phase = 2 * np.pi * np.cumsum(freqs) / SAMPLE_RATE
    w = np.sign(np.sin(phase)) if wave == "square" else np.sin(phase)
    return w * vol * _envelope(n)


def _seq(notes, beat, wave="square", vol=0.3):
    """Concatenate a list of (note_name, beats) into one waveform."""
    parts = [_tone(_N[name], beats * beat, wave, vol) for name, beats in notes]
    return np.concatenate(parts) if parts else np.zeros(0)


def _to_sound(mono):
    """Turn a mono float waveform (-1..1) into a stereo pygame Sound."""
    mono = np.clip(mono, -1.0, 1.0)
    samples = (mono * 32767).astype(np.int16)
    stereo = np.ascontiguousarray(np.column_stack([samples, samples]))
    return pygame.sndarray.make_sound(stereo)


def _build_music():
    beat = 0.15
    lead = _seq([
        ("C5", 1), ("E5", 1), ("G5", 1), ("E5", 1), ("C5", 1), ("E5", 1), ("G5", 1), ("A5", 1),
        ("G5", 1), ("E5", 1), ("C5", 1), ("E5", 1), ("D5", 1), ("F5", 1), ("A5", 1), ("F5", 1),
        ("C5", 1), ("E5", 1), ("G5", 1), ("E5", 1), ("C5", 1), ("E5", 1), ("G5", 1), ("A5", 1),
        ("G5", 1), ("E5", 1), ("D5", 1), ("C5", 1), ("G4", 1), ("C5", 1), ("E5", 1), ("G4", 1),
    ], beat, wave="square", vol=0.32)
    bass = _seq([
        ("C4", 4), ("C4", 4), ("A3", 4), ("D4", 4),
        ("C4", 4), ("C4", 4), ("G4", 4), ("C4", 4),
    ], beat, wave="triangle", vol=0.45)
    n = min(len(lead), len(bass))
    return _to_sound((lead[:n] + bass[:n]) * 0.6)


def _build_jump():
    return _to_sound(_sweep(420, 950, 0.13, wave="square", vol=0.35))


def _build_die():
    return _to_sound(_sweep(700, 90, 0.30, wave="square", vol=0.40))


def _build_gameover():
    beat = 0.16
    jingle = _seq([("C5", 1.5), ("G4", 1.5), ("E4", 1.5), ("C4", 3)],
                  beat, wave="square", vol=0.40)
    return _to_sound(jingle)


class Audio:
    """Procedural sound that degrades gracefully.

    Falls back to silence if the mixer can't start or numpy is missing.
    Optional real files in assets/ override the synthesized versions:
        assets/music.ogg (or .wav/.mp3)
        assets/jump.wav, assets/die.wav, assets/gameover.wav (or .ogg)
    """

    def __init__(self):
        self.ok = False
        self.muted = False
        self.sfx = {}
        self.music_sound = None       # synthesized looping Sound
        self.music_channel = None
        self.music_file = None        # path, if a real music file is present
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except pygame.error:
            return                    # no audio device -> stay silent
        self.ok = True
        self._setup()

    def _setup(self):
        # Music: prefer a real file; otherwise synthesize (needs numpy).
        for name in ("music.ogg", "music.wav", "music.mp3"):
            p = os.path.join(ASSET_DIR, name)
            if os.path.exists(p):
                self.music_file = p
                break
        if self.music_file is None and np is not None:
            try:
                self.music_sound = _build_music()
            except Exception:
                self.music_sound = None

        # SFX: prefer files; otherwise synthesize.
        builders = {"jump": _build_jump, "die": _build_die, "gameover": _build_gameover}
        for key, builder in builders.items():
            snd = None
            for ext in (".wav", ".ogg"):
                p = os.path.join(ASSET_DIR, key + ext)
                if os.path.exists(p):
                    try:
                        snd = pygame.mixer.Sound(p)
                    except pygame.error:
                        snd = None
                    break
            if snd is None and np is not None:
                try:
                    snd = builder()
                except Exception:
                    snd = None
            if snd is not None:
                self.sfx[key] = snd

    def start_music(self):
        if not self.ok:
            return
        try:
            if self.music_file:
                pygame.mixer.music.load(self.music_file)
                pygame.mixer.music.set_volume(0.0 if self.muted else 0.5)
                pygame.mixer.music.play(-1)
            elif self.music_sound:
                if self.music_channel:
                    self.music_channel.stop()
                self.music_channel = self.music_sound.play(loops=-1)
                if self.music_channel:
                    self.music_channel.set_volume(0.0 if self.muted else 1.0)
        except pygame.error:
            pass

    def stop_music(self):
        if not self.ok:
            return
        try:
            if self.music_file:
                pygame.mixer.music.stop()
            elif self.music_channel:
                self.music_channel.stop()
        except pygame.error:
            pass

    def play(self, key):
        if not self.ok or self.muted:
            return
        snd = self.sfx.get(key)
        if snd:
            snd.play()

    def toggle_mute(self):
        if not self.ok:
            return
        self.muted = not self.muted
        try:
            if self.music_file:
                pygame.mixer.music.set_volume(0.0 if self.muted else 0.5)
            elif self.music_channel:
                self.music_channel.set_volume(0.0 if self.muted else 1.0)
        except pygame.error:
            pass


# --------------------------------------------------------------------------
# Main game
# --------------------------------------------------------------------------
def main():
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Endless Runner — v1")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arialrounded,arial", 26, bold=True)
    big_font = pygame.font.SysFont("arialrounded,arial", 48, bold=True)
    small_font = pygame.font.SysFont("arial", 18)

    # Load optional art
    player_img = load_image("player.png", (PLAYER_W, PLAYER_H))
    obstacle_imgs = {
        k: load_image(f"{k}.png", (OBSTACLE_SPECS[k]["w"], OBSTACLE_SPECS[k]["h"]))
        for k in OBSTACLE_SPECS
    }
    bg_img = load_image("background.png", (WIDTH, GROUND_Y))

    audio = Audio()
    audio.start_music()

    player = Player(player_img)
    obstacles = []
    state = "start"            # "start" | "play" | "gameover"
    score = 0.0
    best = 0
    speed = BASE_SPEED
    dist_to_next = 0.0
    world_offset = 0.0

    def reset_game():
        nonlocal obstacles, score, speed, dist_to_next, world_offset
        player.reset()
        obstacles = []
        score = 0.0
        speed = BASE_SPEED
        dist_to_next = random.uniform(min_safe_gap(speed), min_safe_gap(speed) + 220)
        world_offset = 0.0
        audio.start_music()

    def draw_scene():
        if bg_img:
            screen.blit(bg_img, (0, 0))
        else:
            draw_sky(screen)
            draw_clouds(screen, world_offset * 0.25)
            draw_hills(screen, world_offset * 0.5)
        draw_ground(screen, world_offset)

    running = True
    while running:
        # ---- Events ----
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_SPACE, pygame.K_UP):
                    if state == "play":
                        if player.jump():
                            audio.play("jump")
                    elif state == "start":
                        state = "play"
                        reset_game()
                    elif state == "gameover":
                        state = "play"
                        reset_game()
                elif event.key == pygame.K_r and state == "gameover":
                    state = "play"
                    reset_game()
                elif event.key == pygame.K_m:
                    audio.toggle_mute()

        # ---- Update ----
        if state == "play":
            keys = pygame.key.get_pressed()
            move_dir = 0
            if keys[pygame.K_LEFT]:
                move_dir -= 1
            if keys[pygame.K_RIGHT]:
                move_dir += 1

            speed = min(MAX_SPEED, speed + SPEED_RAMP)
            world_offset += speed
            player.update(move_dir)

            # spawn obstacles spaced by travel distance
            dist_to_next -= speed
            if dist_to_next <= 0:
                kind = random.choice(list(OBSTACLE_SPECS.keys()))
                obstacles.append(Obstacle(kind, obstacle_imgs[kind]))
                gap = min_safe_gap(speed)
                dist_to_next = random.uniform(gap, gap + 240)

            for obs in obstacles:
                obs.update(speed)
                if not obs.scored and obs.x + obs.width < player.x:
                    obs.scored = True
                    score += 1
            obstacles = [o for o in obstacles if not o.off_screen]

            # collision
            pr = player.rect
            for obs in obstacles:
                if pr.colliderect(obs.rect):
                    best = max(best, int(score))
                    state = "gameover"
                    audio.stop_music()
                    audio.play("die")
                    audio.play("gameover")
                    break

        # ---- Draw ----
        draw_scene()
        for obs in obstacles:
            obs.draw(screen)
        player.draw(screen)

        if state == "play":
            screen.blit(font.render(f"Score: {int(score)}", True, TEXT_COLOR), (16, 14))
            screen.blit(small_font.render(f"Best: {best}", True, TEXT_COLOR), (16, 44))
        elif state == "start":
            title = big_font.render("ENDLESS RUNNER", True, TEXT_COLOR)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 40)))
            tip = font.render("Press SPACE to start", True, TEXT_COLOR)
            screen.blit(tip, tip.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 10)))
            ctl = small_font.render("← → move   |   SPACE / ↑ jump   |   M mute   |   ESC quit",
                                    True, TEXT_COLOR)
            screen.blit(ctl, ctl.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 44)))
        elif state == "gameover":
            over = big_font.render("GAME OVER", True, (180, 40, 40))
            screen.blit(over, over.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 30)))
            sc = font.render(f"Score: {int(score)}   Best: {best}", True, TEXT_COLOR)
            screen.blit(sc, sc.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 14)))
            tip = small_font.render("Press R or SPACE to play again", True, TEXT_COLOR)
            screen.blit(tip, tip.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 46)))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
