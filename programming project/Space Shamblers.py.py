# 1. IMPORTS & INITIALISATION                                                 
import pygame, sys, os, random, math            # core libraries: graphics/audio, system exit, file ops, RNG, trig
pygame.init()                                    # initialise Pygame’s video subsystem
pygame.mixer.init()                              # initialise Pygame’s audio mixer


# 2. GLOBAL CONFIGURATION CONSTANTS                                           

WIDTH, HEIGHT, FPS = 1200, 900, 60              # window resolution and target frames‑per‑second
PLAYER_SPEED, LASER_SPEED, ENEMY_LASER = 5, 7, 4 # movement speed & projectile velocities

DIFFS = ["Easy", "Normal", "Hard"]              # ordered list of difficulty names
diff_idx = 0                                    # index into DIFFS (0=Easy)
difficulty = DIFFS[diff_idx]                    # current difficulty string

START_HEARTS = {                                # starting life points per difficulty
    "Easy":   10,
    "Normal": 5,
    "Hard":   3
}

HP_TABLE = {                                    # enemy HP by difficulty & type
    "Easy":   {1:1, 2:2, 3:3},
    "Normal": {1:2, 2:3, 3:5},
    "Hard":   {1:3, 2:5, 3:10}
}

# Two alternative keyboard layouts

SCHEMES = [
    {"name":"Arrows+Space",                     # scheme 0   ↑ ↓ ← →  +  Space
     "left":pygame.K_LEFT,  "right":pygame.K_RIGHT,
     "up":pygame.K_UP,     "down":pygame.K_DOWN,
     "shoot":pygame.K_SPACE},
    {"name":"WASD+Space",                       # scheme 1   WASD  +  Space
     "left":pygame.K_a,     "right":pygame.K_d,
     "up":pygame.K_w,      "down":pygame.K_s,
     "shoot":pygame.K_SPACE}
]
scheme_idx = 0                                  # active control‑scheme index


# 3. HANDY RGB COLOUR CONSTANTS                                               

WHITE=(255,255,255); BLACK=(0,0,0)              # basic colours
RED=(255,0,0); GREEN=(0,255,0); BLUE=(0,0,255)
YELL=(255,255,0); MAG=(255,0,255); PURP=(128,0,128); GRAY=(100,100,100)


# 4. DISPLAY OBJECTS & TEXT UTILITIES                                         

screen = pygame.display.set_mode((WIDTH, HEIGHT))   # create the main window surface
pygame.display.set_caption("Space Shamblers")       # window title text
clock  = pygame.time.Clock()                        # helper to cap frame‑rate
Font   = pygame.font.SysFont                        # alias for font factory

def blit_mid(text, y, size=36, color=WHITE, alpha=255):
    """Render *text* centred horizontally at vertical pos *y*."""
    surf = Font(None, size).render(text, True, color)  # create text surface
    surf.set_alpha(alpha)                              # apply transparency (for fades)
    screen.blit(surf, ((WIDTH - surf.get_width()) // 2, y))  # draw centred

def fit(button, pad=24, min_w=120):
    """Resize a Button’s rect so its label never clips."""
    w = Font(None, 30).size(button.txt)[0] + pad       # desired width incl. padding
    button.rect.w = max(min_w, w)                      # enforce minimum width


# 5. GENERIC ASSET‑LOADING HELPERS                                            

ASSET_DIR = "assets"                              # root folder for all art & audio

def _find(stem):
    """Search *ASSET_DIR* recursively for a file whose stem matches *stem*."""
    stem = stem.lower()                             # case‑insensitive search
    for root, _, files in os.walk(ASSET_DIR):       # walk directory tree
        for f in files:
            if os.path.splitext(f)[0].lower() == stem:   # compare stems
                return os.path.join(root, f)             # return full path
    return None                                         # not found

def load_image(stem, size, fallback_col=(255,0,0)):
    """Load & scale an image, else return a coloured rectangle surface."""
    path = _find(stem)                                  # locate file
    if path:
        try:
            img = pygame.image.load(path).convert_alpha()   # load image w/ alpha
            if img.get_size() != size:                      # scale if needed
                img = pygame.transform.smoothscale(img, size)
            return img
        except Exception as e:
            print("[WARN] bad image:", path, e)         # invalid file logged
    # fallback if missing or failed
    surf = pygame.Surface(size, pygame.SRCALPHA); surf.fill(fallback_col)
    print(f"[WARN] fallback for {stem}")
    return surf

def load_sound(stem):
    """Return a Sound object or None if missing/invalid."""
    path = _find(stem)
    if path:
        try:
            return pygame.mixer.Sound(path)
        except Exception as e:
            print("[WARN] sound bad:", path, e)
    print(f"[WARN] no sound for {stem}")
    return None


# 6. LOAD IMAGE RESOURCES                                                     

img_player = load_image("main character", (50, 50), BLUE)      # protagonist sprite
img_e1     = load_image("enemy 1",        (40, 40), RED)       # enemy type‑1 sprite
img_e2     = load_image("enemy 2",        (40, 40), GREEN)     # enemy type‑2 sprite
img_boss   = load_image("enemy 3 design", (120,60), PURP)      # boss sprite
img_heart  = load_image("heart",          (20, 20), RED)       # UI heart icon

bg_menu = load_image("main menu back ground", (WIDTH, HEIGHT), BLACK)  # menu background
bg1     = load_image("stage 1 back ground",   (WIDTH, HEIGHT), BLACK)  # stage 1 backdrop
bg2     = load_image("stage 2 back ground",   (WIDTH, HEIGHT), BLACK)  # stage 2 backdrop
bg3     = load_image("stage 3 back ground",   (WIDTH, HEIGHT), BLACK)  # stage 3 backdrop


# 7. LOAD AUDIO RESOURCES                                                     

menu_music   = _find("main menu ost")             # path to menu music file
pause_music  = _find("pause menu ost")            # music during pause/settings
gameover_music = _find("game over menu")          # music for victory/defeat
stage_music  = {                                   # per‑stage background tracks
    1: _find("stage 1"),
    2: _find("stage 2"),
    3: _find("stage 3")
}

snd_click  = load_sound("button click")            # UI click SFX
snd_deathE = load_sound("death sound (enemies)")   # enemy destroyed SFX
snd_deathP = load_sound("death sound")             # player destroyed SFX
snd_e12    = load_sound("enemies shooting sound (1,2)")  # shot from type 1/2
snd_boss   = load_sound("enemy 3 shooting sound")  # boss shot SFX
snd_power  = load_sound("power ups sound")         # power‑up acquired SFX


# Music helpers
muted = False                                      # global mute flag

def play_music(path, loop=-1):
    """Play *path* on the music channel (looping) unless muted/None."""
    pygame.mixer.music.stop()                      # stop anything currently playing
    if not muted and path:
        pygame.mixer.music.load(path)
        pygame.mixer.music.play(loop)

def ensure_music(path):
    """Restart *path* if it has stopped unintentionally."""
    if not muted and path and not pygame.mixer.music.get_busy():
        play_music(path)

def click():
    """Play the button click sound (respecting mute)."""
    if not muted and snd_click:
        snd_click.play()


# 8. BUTTON CLASS (UI WIDGET)                                                 

class Button:
    """Simple text button rendered as a filled rounded rectangle."""
    def __init__(self, txt, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)        # clickable rectangle
        self.txt  = txt                            # label text
    def draw(self):
        pygame.draw.rect(screen, GRAY, self.rect, border_radius=4)       # draw box
        lab = Font(None, 30).render(self.txt, True, WHITE)               # render label
        screen.blit(lab, (
            self.rect.x + (self.rect.w - lab.get_width()) // 2,          # centre X
            self.rect.y + (self.rect.h - lab.get_height()) // 2))        # centre Y
    def hit(self, pos):
        """Return True if *pos* (x,y) collides with the button."""
        return self.rect.collidepoint(pos)


# 9. REST OF THE UI – PRE‑INSTANTIATED BUTTONS                                

# Main menu buttons
start_btn, settings_btn = (
    Button("Start",    WIDTH//2-60, HEIGHT//2-90, 120, 40),
    Button("Settings", WIDTH//2-60, HEIGHT//2-30, 120, 40)
)
diff_btn = Button(f"Difficulty: {difficulty}", WIDTH//2-60, HEIGHT//2+30, 120, 40)
fit(diff_btn)                                        # adjust width to label
quit_btn = Button("Quit", WIDTH//2-60, HEIGHT//2+90, 120, 40)

# Settings screen buttons (both from menu and pause)
scheme_btn = Button(f"Controls: {SCHEMES[scheme_idx]['name']}", WIDTH//2-100, HEIGHT//2-50, 200, 40)
fit(scheme_btn, 200)                                 # wider min width
mute_btn   = Button("Mute", WIDTH//2-100, HEIGHT//2+10, 200, 40)
back_btn   = Button("Back", WIDTH//2-100, HEIGHT//2+70, 200, 40)

# In‑game HUD & pause
pause_btn  = Button("Pause", WIDTH//2-50, 10, 100, 30)
resume_btn = Button("Resume", WIDTH//2-60, HEIGHT//2-120, 120, 40)
settings_in= Button("Settings", WIDTH//2-60, HEIGHT//2-60, 120, 40)
restart_btn= Button("Restart", WIDTH//2-60, HEIGHT//2,     120, 40)
menu_btn   = Button("Menu",   WIDTH//2-60, HEIGHT//2+60,  120, 40)
quit_game  = Button("Quit",   WIDTH//2-60, HEIGHT//2+120, 120, 40)


#10. ENTITY CLASSES – PLAYER & ENEMY                                          

class Player:
    """Handles player sprite, movement, shooting and health."""
    def __init__(self):
        self.img   = img_player                                           # sprite image
        self.rect  = self.img.get_rect(midbottom=(WIDTH//2, HEIGHT-90))   # starting position
        self.speed = PLAYER_SPEED                                         # movement speed
        self.hearts= START_HEARTS[difficulty]                             # life points
        self.cool  = 1000                                                 # cooldown (ms) between shots
        self.last  = 0                                                    # time of last shot
        self.lasers= []                                                   # active player lasers (list of Rects)
        self.flash_until = 0                                              # time until which sprite flashes white

    def move(self, keys):
        sc = SCHEMES[scheme_idx]                                          # current control scheme mapping
        if keys[sc["left"]]  and self.rect.left  > 0:             self.rect.x -= self.speed
        if keys[sc["right"]] and self.rect.right < WIDTH:         self.rect.x += self.speed
        if keys[sc["up"]]    and self.rect.top   > HEIGHT-250:    self.rect.y -= self.speed
        if keys[sc["down"]]  and self.rect.bottom< HEIGHT:         self.rect.y += self.speed

    def shoot(self):
        """Spawn a new laser if enough time has elapsed."""
        if pygame.time.get_ticks() - self.last >= self.cool:
            self.lasers.append(pygame.Rect(self.rect.centerx-2, self.rect.top, 4, 10))
            self.last = pygame.time.get_ticks()

    def draw(self):
        # flash white overlay if recently hit
        if pygame.time.get_ticks() < self.flash_until:
            tint = pygame.Surface(self.img.get_size(), pygame.SRCALPHA)
            tint.fill((255, 255, 255, 180))                               # semi‑transparent white
            screen.blit(self.img, self.rect); screen.blit(tint, self.rect)
        else:
            screen.blit(self.img, self.rect)
        # draw every laser
        for l in self.lasers:
            pygame.draw.rect(screen, YELL, l)

class Enemy:
    """Base class for all enemy types (1, 2, boss=3)."""
    def __init__(self, x, y, t):
        self.t    = t                                                    # enemy type
        self.img  = img_e1 if t==1 else img_e2 if t==2 else img_boss      # choose sprite
        self.rect = self.img.get_rect(topleft=(x, y))                     # position
        self.hp   = HP_TABLE[difficulty][t]                               # hit points
        self.dmg  = 1 if t==1 else 2 if t==2 else 3                       # damage inflicted
        self.dir  = 1                                                    # horizontal direction (type 2 zig‑zag)
        self.lasers = []                                                 # active enemy projectiles
        self.last   = 0                                                  # last shot time
        self.delay  = 1000 if t!=3 else 3000                              # cooldown between shots (boss slower)

    def move(self, group):
        """Only type 2 moves horizontally (zig‑zag)."""
        if self.t == 2:
            nxt = self.rect.move(self.dir, 0)
            # bounce off edges or other enemies
            if (nxt.left <= 0 or nxt.right >= WIDTH or
                any(o is not self and nxt.colliderect(o.rect) for o in group)):
                self.dir *= -1
            else:
                self.rect = nxt

    def shoot(self, target):
        """Different shooting logic per enemy type."""
        if pygame.time.get_ticks() - self.last < self.delay:
            return  # not yet ready
        if self.t == 3:
            # boss – shoot a homing orb (circle with velocity components)
            dx, dy = target.centerx - self.rect.centerx, target.centery - self.rect.centery
            dist   = max(1, math.hypot(dx, dy))
            self.lasers.append([self.rect.centerx, self.rect.bottom, dx/dist*3, dy/dist*3])
            if not muted and snd_boss: snd_boss.play()
        else:
            chance = 0.05 if self.t == 2 else 0.1                       # type 2 shoots less frequently
            if random.random() < chance:
                self.lasers.append(pygame.Rect(self.rect.centerx, self.rect.bottom, 4, 10))
                if not muted and snd_e12: snd_e12.play()
        self.last = pygame.time.get_ticks()                              # reset cooldown timer

    def draw(self):
        screen.blit(self.img, self.rect)                                 # sprite
        for l in self.lasers:
            if self.t == 3:
                pygame.draw.circle(screen, MAG, (int(l[0]), int(l[1])), 6)  # boss orb
            else:
                pygame.draw.rect(screen, RED, l)                          # linear laser


#11. FUNCTION TO BUILD WAVES / STAGES                                         


def spawn(stage):
    """Return a list of Enemy objects appropriate for *stage* (1…3)."""
    e  = []                                       # resulting list
    cx = WIDTH // 2                               # horizontal centre
    if stage == 1:                                # basic grid (24 foes)
        for r in range(4):                        # 4 rows
            for c in range(6):                    # 6 columns
                e.append(Enemy(cx-240+c*80, 110+r*60, 1))
    elif stage == 2:                              # mix of types 1 & 2
        mid = cx - 160
        for r in range(4):
            y = 110 + r*60
            e.append(Enemy(mid-80,  y, 2)); e.append(Enemy(mid+320, y, 2))
            for c in range(4):                    # inner type‑1s
                e.append(Enemy(mid+c*80, y, 1))
    else:                                         # stage 3 – boss + escorts
        mid = cx - 160
        for r in range(4):
            y = 110 + r*60
            e.append(Enemy(mid-80,  y, 2)); e.append(Enemy(mid+320, y, 2))
            e.append(Enemy(mid-40,  y, 1)); e.append(Enemy(mid+280, y, 1))
        boss = Enemy(cx-60, 200, 3); e.append(boss)                     # central boss
        for i in range(6):                                               # extra minions under boss
            e.append(Enemy(cx-200+i*80, boss.rect.bottom+70, 1))
    return e


#12. HIGH‑LEVEL STATE VARIABLES                                              

state = "logo"                                   # current top‑level screen
logo_start = pygame.time.get_ticks()              # timestamp for splash fade

player  = Player()                                # single player instance
enemies = spawn(1)                                # initial wave (stage 1)
stage   = 1                                       # stage index

start_time  = pygame.time.get_ticks()             # game timer baseline
paused_time = 0                                   # total pause duration
pause_start = None                                # timestamp when pause started

ability_msg  = None                               # power‑up banner text
ability_time = 0                                  # time banner appeared

#13. MAIN LOOP                                                                
while True:
    dt  = clock.tick(FPS)                         # delay to keep FPS; also yields delta time (unused)
    now = pygame.time.get_ticks()                 # current time in ms

    #  EVENT HANDLING 
    for ev in pygame.event.get():                 # iterate over pending events
        if ev.type == pygame.QUIT:                # window closed
            pygame.quit(); sys.exit()
        if ev.type == pygame.KEYDOWN:             # key pressed
            if ev.key == pygame.K_ESCAPE and state == "game":  # pause hotkey
                state = "paused"; pause_start = now; play_music(pause_music)
            if ev.key == pygame.K_m:              # mute/unmute toggle
                muted = not muted
                mute_btn.txt = "Unmute" if muted else "Mute"
                if muted: pygame.mixer.music.stop()
        if ev.type == pygame.MOUSEBUTTONDOWN:     # mouse click
            pos = ev.pos                          # click position
            # Splash → Menu
            if state == "logo":
                click(); state = "menu"; play_music(menu_music)

            # Main menu logic
            elif state == "menu":
                if start_btn.hit(pos):
                    click(); player = Player(); enemies = spawn(1); stage = 1
                    state = "game"; start_time = now; paused_time = 0
                    play_music(stage_music[1])
                elif settings_btn.hit(pos):
                    click(); state = "settings_menu"
                elif diff_btn.hit(pos):
                    click(); diff_idx = (diff_idx+1) % 3; difficulty = DIFFS[diff_idx]
                    diff_btn.txt = f"Difficulty: {difficulty}"; fit(diff_btn)
                elif quit_btn.hit(pos):
                    click(); pygame.quit(); sys.exit()

            # Settings from main
            elif state == "settings_menu":
                if scheme_btn.hit(pos):
                    click(); scheme_idx = (scheme_idx+1) % len(SCHEMES)
                    scheme_btn.txt = f"Controls: {SCHEMES[scheme_idx]['name']}"; fit(scheme_btn, 200)
                elif mute_btn.hit(pos):
                    click(); muted = not muted; mute_btn.txt = "Unmute" if muted else "Mute"
                    if muted: pygame.mixer.music.stop()
                elif back_btn.hit(pos):
                    click(); state = "menu"

            # HUD pause button
            elif state == "game" and pause_btn.hit(pos):
                click(); state = "paused"; pause_start = now; play_music(pause_music)

            # Pause menu buttons
            elif state == "paused":
                if resume_btn.hit(pos):
                    click(); state = "game"; paused_time += now - pause_start
                    play_music(stage_music[stage])
                elif settings_in.hit(pos):
                    click(); state = "settings_pause"
                elif restart_btn.hit(pos):
                    click(); player = Player(); enemies = spawn(1); stage = 1
                    state = "game"; start_time = now; paused_time = 0; play_music(stage_music[1])
                elif menu_btn.hit(pos):
                    click(); state = "menu"; play_music(menu_music)
                elif quit_game.hit(pos):
                    click(); pygame.quit(); sys.exit()

            # Settings during pause
            elif state == "settings_pause":
                if scheme_btn.hit(pos):
                    click(); scheme_idx = (scheme_idx+1) % len(SCHEMES)
                    scheme_btn.txt = f"Controls: {SCHEMES[scheme_idx]['name']}"; fit(scheme_btn, 200)
                elif mute_btn.hit(pos):
                    click(); muted = not muted; mute_btn.txt = "Unmute" if muted else "Mute"
                    if muted: pygame.mixer.music.stop()
                elif back_btn.hit(pos):
                    click(); state = "paused"

            # Victory / Game‑over screens
            elif state in ("victory", "game_over"):
                if restart_btn.hit(pos):
                    click(); player = Player(); enemies = spawn(1); stage = 1
                    state = "game"; start_time = now; paused_time = 0; play_music(stage_music[1])
                elif menu_btn.hit(pos):
                    click(); state = "menu"; play_music(menu_music)
                elif quit_game.hit(pos):
                    click(); pygame.quit(); sys.exit()

    # Capture currently held keys (for movement & shooting)
    keys = pygame.key.get_pressed()

    #  SCREEN‑SPECIFIC UPDATES 

    # Splash (logo) screen with timed fade effect
    if state == "logo":
        elapsed = now - logo_start
        screen.blit(bg_menu, (0,0))
        # compute alpha: fade in 0‑0.5s, solid 0.5‑1.5s, fade out 1.5‑2.5s
        if elapsed < 500:
            alpha = int(255 * elapsed / 500)
        elif elapsed < 1500:
            alpha = 255
        else:
            alpha = int(255 * max(0, 2500 - elapsed) / 1000)
        blit_mid("SPACE SHAMBLERS", HEIGHT//2-40, 64, WHITE, alpha)
        pygame.display.flip()
        if elapsed >= 2500:                       # auto‑advance to menu
            state = "menu"; play_music(menu_music)
        continue                                  # skip rest of loop

    # Settings screens (two contexts: from menu or from pause)
    if state in ("settings_menu", "settings_pause"):
        ensure_music(pause_music if state == "settings_pause" else menu_music)
        bg_current = bg1 if stage==1 else bg2 if stage==2 else bg3
        screen.blit(bg_menu if state=="settings_menu" else bg_current, (0,0))
        if state == "settings_pause":
            player.draw(); [e.draw() for e in enemies]      # show paused game behind menu
        blit_mid("SETTINGS", HEIGHT//2 - 130, 48)
        scheme_btn.draw(); mute_btn.draw(); back_btn.draw()
        if state == "settings_pause":
            secs = (now - start_time - paused_time) // 1000
            timer = Font(None, 28).render(f"{secs//60:02}:{secs%60:02}", True, WHITE)
            screen.blit(timer, (10,10))
            hx = (WIDTH - player.hearts*30) // 2
            for i in range(player.hearts): screen.blit(img_heart, (hx+i*30, 45))
        pygame.display.flip(); continue

    # Main menu
    if state == "menu":
        ensure_music(menu_music)
        screen.blit(bg_menu, (0,0))
        blit_mid("SPACE SHAMBLERS", HEIGHT//2 - 200, 48)
        start_btn.draw(); settings_btn.draw(); diff_btn.draw(); quit_btn.draw()
        pygame.display.flip(); continue

    # Draw current background for game/pause
    current_bg = bg1 if stage==1 else bg2 if stage==2 else bg3
    screen.blit(current_bg, (0,0))

    #  GAMEPLAY (not paused) 
    if state == "game":
        ensure_music(stage_music[stage])
        player.move(keys)                          # handle movement
        if keys[SCHEMES[scheme_idx]["shoot"]]:    # handle shooting
            player.shoot()

        # Update player lasers: move up & remove when off‑screen
        for l in player.lasers[:]:                 # iterate over a copy
            l.y -= LASER_SPEED
            if l.y < 0: player.lasers.remove(l)

        # Update enemies
        for en in enemies[:]:
            en.move(enemies)                       # zig‑zag movement (type 2)
            en.shoot(player.rect)                  # maybe fire

            # Enemy projectiles hit player
            for proj in en.lasers[:]:
                rect = pygame.Rect(proj[0]-6, proj[1]-6, 12, 12) if en.t == 3 else proj
                if en.t == 3:                      # move boss orb
                    proj[0] += proj[2]; proj[1] += proj[3]
                else:
                    proj.y += ENEMY_LASER          # move linear laser
                if rect.colliderect(player.rect):  # collision test
                    player.hearts -= en.dmg        # apply damage
                    player.flash_until = now + 120 # brief flash effect
                    en.lasers.remove(proj)         # delete projectile

            # Player lasers hit enemy
            for l in player.lasers[:]:
                if l.colliderect(en.rect):
                    en.hp -= 1; player.lasers.remove(l)       # damage enemy & remove laser
                    if en.hp <= 0:                            # enemy destroyed
                        enemies.remove(en)
                        if not muted and snd_deathE: snd_deathE.play()
                    break                                      # stop checking this laser

        # Stage cleared when no enemies remain
        if not enemies:
            if stage == 1:                          # grant rapid‑fire power‑up
                player.cool //= 2; ability_msg, ability_time = "Rapid Fire", now
                if not muted and snd_power: snd_power.play()
            elif stage == 2:                        # grant speed boost
                player.speed *= 2; ability_msg, ability_time = "Hermes Boots", now
                if not muted and snd_power: snd_power.play()
            if stage < 3:                           # advance to next stage
                stage += 1; enemies = spawn(stage); play_music(stage_music[stage])
            else:                                   # game finished – victory
                state = "victory"; play_music(gameover_music)

        # Player death check
        if player.hearts <= 0:
            if not muted and snd_deathP: snd_deathP.play()
            state = "game_over"; play_music(gameover_music)

    #  RENDER / DRAW PHASE 
    player.draw(); [e.draw() for e in enemies]     # always draw actors (game & pause)

    # HUD (timer, hearts, pause button)
    if state in ("game", "paused"):
        secs = (now - start_time - paused_time) // 1000
        timer_surf = Font(None, 28).render(f"{secs//60:02}:{secs%60:02}", True, WHITE)
        screen.blit(timer_surf, (10,10))
        hx = (WIDTH - player.hearts*30) // 2
        for i in range(player.hearts):
            screen.blit(img_heart, (hx + i*30, 45))
        if state == "game": pause_btn.draw()

    # Ability banner (fade out after 3 seconds)
    if ability_msg:
        el = now - ability_time
        if el < 3000:
            alpha = int(255 * (1 - el / 3000))
            blit_mid(f"New ability unlocked: {ability_msg}", HEIGHT//2 - 220, 32, YELL, alpha)
        else:
            ability_msg = None

    # Overlay menus (pause/victory/death)
    if state == "paused":
        blit_mid("PAUSED", HEIGHT//2 - 170, 60)
        resume_btn.draw(); settings_in.draw(); restart_btn.draw(); menu_btn.draw(); quit_game.draw()
    if state == "victory":
        blit_mid("VICTORY!", HEIGHT//2 - 170, 60, GREEN)
        restart_btn.draw(); menu_btn.draw(); quit_game.draw()
    if state == "game_over":
        blit_mid("GAME OVER", HEIGHT//2 - 170, 60, RED)
        restart_btn.draw(); menu_btn.draw(); quit_game.draw()

    pygame.display.flip()                          # push frame to the screen

    # The Actual code for the game is 400 lines roughly but because of the spacing for more clearnce and better reading and understanding of the code is why there is so many lines