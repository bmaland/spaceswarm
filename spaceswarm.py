#!/usr/bin/env python

import random, os, sys, time, math, pygame
from vector2 import Vector2
from pygame.locals import *

SPACESWARM_VERSION = (0, 1, 0)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

WINDOWWIDTH, WINDOWHEIGHT = 800, 600
TEXTCOLOR = WHITE
BACKGROUNDCOLOR = BLACK
FPS = 40

random.seed()
pygame.init()
pygame.mouse.set_visible(False) # we blit the mouse instead
screen = pygame.display.set_mode((WINDOWWIDTH, WINDOWHEIGHT))
pygame.display.set_caption('Space Swarm!')

def load_image(name):
    fullname = os.path.join('data', name)
    image = pygame.image.load(fullname)
    if image.get_alpha is None:
        image = image.convert()
    else:
        image = image.convert_alpha()
    return image

def load_sound(name):
    class NoneSound:
        def play(self): pass
    if not pygame.mixer: return NoneSound()
    fullname=os.path.join('data', name)
    return pygame.mixer.Sound(fullname)

def terminate():
    pygame.quit()
    sys.exit()

def wait_for_player():
    while True:
        for event in pygame.event.get():
            if event.type == QUIT:
                terminate()
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    terminate()
                return

def get_n_points_on_circle(center, radius, n=10):
    alpha = math.pi * 2. / n
    points = list(range(n))
    for i in points:
        theta = alpha * i
        point_on_circle = Vector2(math.cos(theta) * radius,
                                  math.sin(theta) * radius)
        points[i] = center + point_on_circle
    return points

def draw_text(text, font, surface, x, y, color=TEXTCOLOR):
    text = font.render(text, 1, color)
    rect = text.get_rect()
    rect.topleft = (x, y)
    surface.blit(text, rect)

class GameObject(object):
    def __init__(self, image, location, destination=None):
        self._image = image
        self.location = location
        self.destination = destination

    def render(self, surface):
        surface.blit(self._image, self.location)

    def move(self, time_passed_seconds, speed):
        dv = Vector2(self.destination)
        lv = Vector2(self.location.x, self.location.y)
        heading = Vector2.from_points(lv, dv)
        heading.normalize()
        new_position = lv + heading * time_passed_seconds * speed
        self.location.x = new_position.x
        self.location.y = new_position.y

class Explosion(GameObject):
    image = load_image("explosion.png")

    def __init__(self, location):
        GameObject.__init__(self, Explosion.image, location)
        self._ttl = 5 # number of frames explosion should be visible

    def move(self):
        raise

    def render(self, surface):
        super(Explosion, self).render(surface)
        self._ttl -= 1

    def is_finished(self):
        return self._ttl == 0

class Alien(GameObject):
    image = load_image("alien.png")
    width, height = image.get_size()

    def __init__(self, speed=100, img=None):
        if img is None: img = Alien.image
        GameObject.__init__(self, img,
                            self._random_spawn_location(),
                            (WINDOWWIDTH/2, WINDOWHEIGHT/2))
        self._speed = speed

    def speed(self):
        """ Gives a slight random variation in speed for every alien """
        return self._speed + random.randint(-5, 5)

    def _random_spawn_location(self):
        """
        Figures out where the alien should be spawned, which should be somewhere
        along the edges of the screen.
        """
        spawn_loc = random.randint(0, 3)
        x,y = 0,0
        if spawn_loc == 0: # top
            x = random.randint(0, WINDOWWIDTH)
            y = 0
        elif spawn_loc == 1: # right
            x = WINDOWWIDTH
            y = random.randint(0, WINDOWHEIGHT)
        elif spawn_loc == 2: # bottom
            x = random.randint(0, WINDOWWIDTH)
            y = WINDOWHEIGHT
        elif spawn_loc == 3: # left
            x = 0
            y = random.randint(0, WINDOWHEIGHT)

        return pygame.Rect(x, y, Alien.width, Alien.height)

    def move(self, time_passed_seconds):
        super(Alien, self).move(time_passed_seconds, self.speed())

class SmartAlien(Alien):
    image = load_image("smart_alien.png")
    width, height = image.get_size()

    def __init__(self, speed=100):
        Alien.__init__(self, speed, SmartAlien.image)
        self._true_destination = self.destination
        self._new_destination()

    def _new_destination(self):
        lv = Vector2(self.location.x, self.location.y)
        candidates = get_n_points_on_circle(lv, 75)
        random.shuffle(candidates)
        for i in candidates:
            # find first point that is closer
            if i.get_distance_to(self._true_destination) < \
                   lv.get_distance_to(self._true_destination):
                self.destination = (i.x, i.y)
                break

    def move(self, time_passed_seconds):
        super(Alien, self).move(time_passed_seconds, self.speed())
        lv = Vector2(self.location.x, self.location.y)
        dv = Vector2(self.destination)
        if lv.get_distance_to(dv) < 2:
            self._new_destination()

class Bullet(GameObject):
    image = load_image("bullet.png")
    width, height = image.get_size()

    def __init__(self, location):
        GameObject.__init__(self, Bullet.image,
                            pygame.Rect(WINDOWWIDTH/2, WINDOWHEIGHT/2,
                                        Bullet.width, Bullet.height),
                            self._calculate_destination(location))

    def _calculate_destination(self, mouse_pos):
        """
        Figure out the destination coords for the bullet, starting from the
        center of the screen through the point the player click, to the edge
        of the screen.
        """
        dx,dy = mouse_pos

        step = Vector2.from_points((WINDOWWIDTH/2,WINDOWHEIGHT/2),
                                   (dx,dy)) * 0.1
        while True:
            if dx > WINDOWWIDTH or dy > WINDOWHEIGHT or dx < 1 or dy < 1:
                dx += step.x; dy += step.y
                break
            dx += step.x; dy += step.y

        return (dx, dy)

def new_level(level):
    """
    Creates various settings for a given level, e.g. spawn rate of aliens.
    """
    alien_speed = min(200, 100 + (level*5))
    spawn_rate = max(15, 50 - (level*6))
    if level < 4:
        alien_multiplier = 1
    elif level < 8:
        alien_multiplier = 2
        spawn_rate *= 2
    elif level < 10:
        alien_multiplier = 3
        spawn_rate *= 3
    elif level < 12:
        alien_multiplier = 4
        spawn_rate *= 3
    elif level < 14:
        alien_multiplier = 5
        spawn_rate *= 3
    remaining_aliens = 3 + (level*2)
    return (spawn_rate, alien_speed, alien_multiplier, remaining_aliens)

bg = load_image("bg.jpg")
clock = pygame.time.Clock()
bullet_speed = 400

# Fonts
title_font = pygame.font.SysFont(None, 48)
font = pygame.font.SysFont(None, 32)

# Load resources
player_image = load_image("player.png")
scope_image = load_image("scope.png")
weapon_sound = load_sound("weapon.wav")
alien_killed_sound = load_sound("alienkilled.wav")
game_over_sound = load_sound("gameover.wav")
levelup_sound = load_sound("levelup.wav")
pygame.mixer.music.load("data/background.mid")

# show the "Start" screen
screen.blit(bg, (0,0))
draw_text('Space Swarm!', title_font, screen, 20,
         20, RED)
draw_text('To defend Earth, fend off the aliens with your missiles.',
         font, screen, 20, 60)
draw_text('Press any key to start.', font, screen, 20, 90)
draw_text("v"+".".join([str(x) for x in SPACESWARM_VERSION]), font, screen,
          20, WINDOWHEIGHT-40)
pygame.display.update()
wait_for_player()

# Place player in origo
player = pygame.Rect(WINDOWWIDTH / 2, WINDOWHEIGHT / 2, 50, 50)
screen.blit(player_image, player)

while True:
    # setup
    game_over = False
    aliens, bullets, explosions = [], [], []
    aliens.append(Alien())
    aliens_killed = 0
    alien_spawn_timer = 0
    score = 0
    level = 1
    spawn_rate, alien_speed, \
                alien_multiplier, \
                remaining_aliens = new_level(level)
    pygame.mixer.music.play(-1, 0.0)

    while True: # Game loop
        for event in pygame.event.get():
            if event.type is MOUSEBUTTONDOWN: # weapon fired
                weapon_sound.play()
                score -= 5 * level # each bullet costs score
                if score < 0: score = 0
                bullets.append(Bullet(pygame.mouse.get_pos()))
            elif event.type is KEYDOWN:
                if event.key == K_ESCAPE:
                    terminate()
            elif event.type is QUIT:
                terminate()

        alien_spawn_timer += 1
        if alien_spawn_timer == spawn_rate: # spawning time!
            alien_spawn_timer = 0
            if remaining_aliens:
                for i in range(alien_multiplier):
                    aliens.append(Alien())
                    remaining_aliens -= 1
                    if not remaining_aliens: break

        time_passed = clock.tick(FPS)
        time_passed_seconds = clock.tick(FPS) / 1000.

        for a in aliens: # move all aliens closer towards player
            a.move(time_passed_seconds, alien_speed)
            if player.colliderect(a.location):
                game_over = True
                break
        if game_over: break

        for b in bullets:
            b.move(time_passed_seconds, bullet_speed)

            for a in aliens:
                if b.location.colliderect(a.location): # alien shot down!
                    aliens_killed += 1
                    score += 10 * level # increase kill score as we progress
                    alien_killed_sound.play()
                    aliens.remove(a)
                    explosions.append(Explosion(a.location))
                    bullets.remove(b)
                    if remaining_aliens == 0 and len(aliens) == 0:
                        levelup_sound.play()
                        level += 1
                        spawn_rate, alien_speed, alien_multiplier, \
                                    remaining_aliens = new_level(level)
                        alien_spawn_timer = 0

            if not screen.get_rect().contains(b.location):
                bullets.remove(b)

        # Redraw screen
        screen.blit(bg, (0,0))
        draw_text('Level: %s' % (level), font, screen, 0, 0)
        draw_text('Remaining aliens: %s' % (remaining_aliens),
                 font, screen, 0, 20)
        draw_text('Aliens killed: %s' % (aliens_killed),
                 font, screen, WINDOWWIDTH/2, 0)
        draw_text('Score: %s' % (score), font, screen, WINDOWWIDTH/2, 20)

        for b in bullets: b.render(screen)
        for a in aliens: a.render(screen)
        for e in explosions:
            if e.is_finished():
                explosions.remove(e)
            else:
                e.render(screen)
        screen.blit(player_image, player)
        screen.blit(scope_image, pygame.mouse.get_pos())
        pygame.display.update()

    # broken out of game loop, show game over screen
    pygame.mixer.music.stop()
    game_over_sound.play()
    draw_text('GAME OVER', title_font, screen, (WINDOWWIDTH / 3),
             (WINDOWHEIGHT / 3), RED)
    draw_text('Press any key to play again, or Esc to quit.', font,
             screen, (WINDOWWIDTH / 3) - 80, (WINDOWHEIGHT / 3) + 50)
    pygame.display.update()
    wait_for_player()
