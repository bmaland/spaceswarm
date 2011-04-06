#!/usr/bin/env python

import random, os, sys, time, math, pygame
from vector2 import Vector2
from pygame.locals import *

SPACESWARM_VERSION = (0, 2, 1)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

WINDOWWIDTH, WINDOWHEIGHT = 800, 600
TEXTCOLOR = WHITE
BACKGROUNDCOLOR = BLACK
FPS = 40

EASY = -10
MEDIUM = 0
HARD = 10

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
    return image, image.get_rect()

def load_sound(name):
    class NoneSound:
        def play(self): pass
    if not pygame.mixer.get_init(): return NoneSound()
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
                return event.key

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


class GameObject(pygame.sprite.Sprite):
    def __init__(self, image, rect, destination=None):
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.image = image[0]
        self.rect = rect
        self.destination = destination

    def move(self, time_passed_seconds, speed):
        dv = Vector2(self.destination)
        lv = Vector2(self.rect.x, self.rect.y)
        heading = Vector2.from_points(lv, dv)
        heading.normalize()
        d = heading * time_passed_seconds * speed
        self.rect.move_ip(round(d.x), round(d.y))


class Player(GameObject):
    image = load_image("player.png")

    def __init__(self):
        rect = Player.image[1]
        rect.center = (WINDOWWIDTH / 2, WINDOWHEIGHT / 2)
        GameObject.__init__(self, Player.image, rect)

    def update(self, time_passed):
        pass

class Explosion(GameObject):
    image = load_image("explosion.png")

    def __init__(self, rect):
        GameObject.__init__(self, Explosion.image, rect)
        self._ttl = 5 # number of frames explosion should be visible

    def update(self, time_passed):
        self._ttl -= 1
        if self._ttl == 0: self.kill()


class Alien(GameObject):
    image = load_image("alien.png")
    width, height = image[0].get_size()

    def __init__(self, speed=100, img=None):
        if img is None: img = Alien.image
        GameObject.__init__(self, img,
                            self._random_spawn_rect(),
                            (WINDOWWIDTH/2, WINDOWHEIGHT/2))
        self._speed = speed

    def speed(self):
        """ Gives a slight random variation in speed for every alien """
        return self._speed + random.randint(-5, 5)

    def _random_spawn_rect(self):
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

        return pygame.Rect(x, y, type(self).width, type(self).height)

    def update(self, time_passed):
        super(Alien, self).move(time_passed, self.speed())


class TinyAlien(Alien):
    image = (pygame.transform.scale(load_image("alien.png")[0], (25,25)),)
    width, height = image[0].get_size()

    def __init__(self, speed=100):
        Alien.__init__(self, speed, TinyAlien.image)

class ChangelingAlien(Alien):
    def __init__(self, speed=100):
        Alien.__init__(self, speed)
        self._orig_speed = speed
        self._change_timer = 25

    def update(self, time_passed):
        super(ChangelingAlien, self).update(time_passed)
        self._change_timer -= 1
        if self._change_timer == 0:
            self._change_timer = 25
            if random.randint(0,4) == 0: # 20% chance for speed change
                self._speed = random.randint(0, self._orig_speed+20)
            if random.randint(0,19) == 0: # 5% chance for shape change
                if self.rect.width == Alien.width:
                    self.image = TinyAlien.image[0]
                    self.rect = pygame.Rect(self.rect.x, self.rect.y,
                                            TinyAlien.width, TinyAlien.height)
                else:
                    self.image = Alien.image[0]
                    self.rect = pygame.Rect(self.rect.x, self.rect.y,
                                            Alien.width, Alien.height)


class SmartAlien(Alien):
    image = load_image("smart_alien.png")
    width, height = image[0].get_size()

    def __init__(self, speed=100):
        Alien.__init__(self, speed, SmartAlien.image)
        self._true_destination = self.destination
        self._new_destination()

    def _new_destination(self):
        lv = Vector2(self.rect.x, self.rect.y)
        candidates = get_n_points_on_circle(lv, 75)
        random.shuffle(candidates)
        for i in candidates:
            # find first point that is closer
            if i.get_distance_to(self._true_destination) < \
                   lv.get_distance_to(self._true_destination):
                self.destination = (i.x, i.y)
                break

    def update(self, time_passed):
        super(SmartAlien, self).update(time_passed)
        lv = Vector2(self.rect.x, self.rect.y)
        dv = Vector2(self.destination)
        if lv.get_distance_to(dv) < 2:
            self._new_destination()


class Bullet(GameObject):
    image = load_image("bullet.png")
    width, height = image[0].get_size()
    speed = 200

    def __init__(self, rect):
        GameObject.__init__(self, Bullet.image,
                            pygame.Rect(WINDOWWIDTH/2, WINDOWHEIGHT/2,
                                        Bullet.width, Bullet.height),
                            self._calculate_destination(rect))

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
            if dx > WINDOWWIDTH or dy > WINDOWHEIGHT or dx < 0 or dy < 0:
                break
            dx += step.x
            dy += step.y

        return (dx, dy)

    def update(self, time_passed):
        self.move(time_passed, Bullet.speed)
        if self.rect.top <= 0 or self.rect.bottom >= WINDOWHEIGHT \
               or self.rect.left <= 0 or self.rect.right >= WINDOWWIDTH:
            self.kill()


class Spawner(object):
    def __init__(self, klass, speed, n):
        self.klass = klass
        self.speed = speed
        self.n = n

    def spawn(self, difficulty):
        self.n -= 1
        if type(self.speed) == tuple:
            return self.klass(random.randint(*self.speed) + difficulty)
        return self.klass(self.speed + difficulty)

    def empty(self):
        self.n == 0


class LevelController(object):
    def __init__(self, level=1, difficulty=MEDIUM):
        self.spawn_timer = 0
        self.difficulty = difficulty
        self.level = level # overridable for testing specific levels
        self.levels = self.instanciate_levels()

    def is_game_finished(self):
        return not self.level + 1 in self.levels.keys()

    def level_up(self):
        self.spawn_timer = 0
        self.level += 1

    def is_spawn_time(self):
        return self.current_level()['spawn_rate'] - \
               (self.difficulty) == self.spawn_timer and \
               self.current_spawner().n > 0

    def current_spawner(self):
        # FIXME this is horrible
        aliens = self.current_level()['aliens']
        if type(aliens) == list:
            if aliens[0].n > 0:
                return aliens[0]
            else:
                return aliens[1]
        return aliens

    def tick(self):
        self.spawn_timer += 1
        if self.is_spawn_time():
            self.spawn()
            self.spawn_timer = 0

    def spawn(self):
        for i in range(self.current_level()['multiplier']):
            self.current_spawner().spawn(self.difficulty)

    def current_level(self):
        return self.levels[self.level]

    def instanciate_levels(self):
        return {
            1: { 'aliens': Spawner(Alien, 55, 8),
             'spawn_rate': 80, 'multiplier': 1 },
            2: { 'aliens': Spawner(Alien, 60, 12),
                 'spawn_rate': 80, 'multiplier': 1 },
            3: { 'aliens': Spawner(Alien, 70, 14),
                 'spawn_rate': 40, 'multiplier': 1 },
            4: { 'aliens': [Spawner(Alien, 70, 10),
                            Spawner(TinyAlien, 50, 6)],
                 'spawn_rate': 50, 'multiplier': 1 },
            5: { 'aliens': Spawner(SmartAlien, 62, 20),
                 'spawn_rate': 40, 'multiplier': 2 },
            6: { 'aliens': [Spawner(ChangelingAlien, 40, 10),
                            Spawner(TinyAlien, 50, 10)],
                 'spawn_rate': 70, 'multiplier': 2 },
            7: { 'aliens': [Spawner(TinyAlien, 70, 10),
                            Spawner(ChangelingAlien, 60, 20)],
                 'spawn_rate': 130, 'multiplier': 3 },
            8: { 'aliens': Spawner(TinyAlien, 35, 24),
                 'spawn_rate': 80, 'multiplier': 2 },
            9: { 'aliens': [Spawner(Alien, 30, 27),
                            Spawner(ChangelingAlien, 55, 9)],
                 'spawn_rate': 75, 'multiplier': 3 },
            10: { 'aliens': [Spawner(SmartAlien, 60, 20),
                            Spawner(Alien, 120, 10)],
                 'spawn_rate': 80, 'multiplier': 2 },
            11: { 'aliens': [Spawner(SmartAlien, (45, 70), 20),
                            Spawner(TinyAlien, 40, 10)],
                 'spawn_rate': 70, 'multiplier': 2},
            12: { 'aliens': [Spawner(SmartAlien, (50, 80), 42),
                             Spawner(Alien, 35, 30)],
                  'spawn_rate': 90, 'multiplier': 4 },
        }


bg = load_image("bg.jpg")
clock = pygame.time.Clock()

# Fonts
title_font = pygame.font.SysFont(None, 48)
font = pygame.font.SysFont(None, 32)

# Load resources
scope_image = load_image("scope.png")[0]
weapon_sound = load_sound("weapon.wav")
alien_killed_sound = load_sound("alienkilled.wav")
game_over_sound = load_sound("gameover.wav")
levelup_sound = load_sound("levelup.wav")
if pygame.mixer.get_init():
    pygame.mixer.music.load(os.path.join("data", "background.mid"))

# show the "Start" screen
screen.blit(*bg)
draw_text('Space Swarm!', title_font, screen, 20,
         20, RED)
draw_text('To defend Earth, fend off the aliens with your missiles.',
         font, screen, 20, 60)
draw_text('Keep track of your firepower, be as accurate as possible.',
          font, screen, 20, 90)
draw_text('Burst-shots cost 100 firepower (Right click).',
          font, screen, 20, 120)
draw_text('Nukes cost 200 firepower (SPACE key).',
          font, screen, 20, 150)
draw_text('Press 1 for easy, 2 (or any key) for medium, 3 for hard.',
          font, screen, 20, 210)
draw_text("v"+".".join([str(x) for x in SPACESWARM_VERSION]), font, screen,
          20, WINDOWHEIGHT-40)
pygame.display.update()

difficulty = wait_for_player()

while True:
    # setup
    game_over, game_finished, muted = False, False, False
    aliens = pygame.sprite.Group()
    bullets = pygame.sprite.Group()
    allsprites = pygame.sprite.RenderUpdates()
    aliens_killed = 0
    firepower = 50
    shots = 0
    accuracy = 0

    if difficulty == K_1:
        difficulty = EASY
    elif difficulty == K_3:
        difficulty = HARD
    else:
        difficulty = MEDIUM

    Player.containers = allsprites
    Alien.containers = aliens, allsprites
    Bullet.containers = bullets, allsprites
    Explosion.containers = allsprites

    level_controller = LevelController(1, difficulty)
    if pygame.mixer.get_init(): pygame.mixer.music.play(-1, 0.0)

    player = Player()

    while True: # Game loop
        for event in pygame.event.get():
            if event.type is MOUSEBUTTONDOWN:
                if pygame.mouse.get_pressed() == (1,0,0) and firepower > 10:
                    if not muted: weapon_sound.play()
                    firepower -= 7.5
                    shots += 1
                    Bullet(pygame.mouse.get_pos())
                elif pygame.mouse.get_pressed() == (0,0,1) and firepower > 100:
                    if not muted: weapon_sound.play()
                    firepower -= 75
                    shots += 8
                    Bullet((0, 0)) # top left
                    Bullet((WINDOWWIDTH/2, 0)) # top middle
                    Bullet((WINDOWWIDTH, 0)) # top right
                    Bullet((WINDOWWIDTH, WINDOWHEIGHT/2)) # right
                    Bullet((WINDOWWIDTH, WINDOWHEIGHT)) # bottom right
                    Bullet((WINDOWWIDTH/2, WINDOWHEIGHT)) # bottom middle
                    Bullet((0, WINDOWHEIGHT)) # bottom left
                    Bullet((0, WINDOWHEIGHT/2)) # left

            elif event.type is KEYDOWN:
                if event.key == K_SPACE:
                    if firepower > 200: # nuke!
                        shots += 1 # FIXME nukes break accuracy
                        screen.fill(RED)
                        pygame.display.flip()
                        firepower -= 150
                        aliens_killed += len(aliens)
                        for a in aliens: a.kill()
                elif event.key == K_ESCAPE or event.key == K_q:
                    terminate()
                elif event.key == K_p:
                    wait_for_player()
                elif event.key == K_m:
                    if muted:
                        pygame.mixer.music.unpause()
                        muted = False
                    else:
                        pygame.mixer.music.pause()
                        muted = True
            elif event.type is QUIT:
                terminate()

        if firepower < 100:
            firepower += 0.15
        else:
            firepower += (30/(firepower*1.5))/2

        level_controller.tick() # spawns new aliens

        # collision detection
        if pygame.sprite.spritecollide(player, aliens, 1):
            game_over = True
            break

        # TODO ma finna ut firepower mechanics, koss ska den oka
        for a in pygame.sprite.groupcollide(aliens, bullets, 1, 1).keys():
            Explosion(a.rect)
            a.kill()
            aliens_killed += 1
            accuracy = int(round((float(aliens_killed)/shots)*100))
            if isinstance(a, SmartAlien):
                firepower += 12.5
            elif isinstance(a, TinyAlien) or isinstance(a, ChangelingAlien):
                firepower += 10
            else:
                firepower += 7.5 # regular alien
            if not muted: alien_killed_sound.play()

        # FIXME
        if level_controller.current_spawner().n == 0 and len(aliens) == 0:
            if not muted: levelup_sound.play()
            firepower += 25
            if level_controller.is_game_finished():
                game_finished = True
                break
            else:
                level_controller.level_up()

        # Redraw screen
        screen.blit(*bg)
        draw_text('Level: %s' % level_controller.level, font, screen, 0, 0)

        # Draw firepower in green if we can afford burst, red if we can afford a nuke
        fpcol = WHITE
        if firepower >= 100: fpcol = GREEN
        if firepower >= 200: fpcol = RED

        draw_text('Firepower: %s' % int(firepower), font, screen, 0, 20, fpcol)
        draw_text('Aliens killed: %s' % aliens_killed,
                 font, screen, WINDOWWIDTH/2, 0)
        draw_text('Accuracy: %s' % accuracy, font, screen, WINDOWWIDTH/2, 20)

        allsprites.update(clock.tick(FPS) / 1000.)
        allsprites.draw(screen)
        screen.blit(scope_image, pygame.mouse.get_pos())
        pygame.display.update()

    # broken out of game loop
    if pygame.mixer.get_init(): pygame.mixer.music.stop()
    if game_over:
        if not muted: game_over_sound.play()
        draw_text('GAME OVER', title_font, screen, (WINDOWWIDTH / 3),
                 (WINDOWHEIGHT / 3), RED)
        draw_text('Press any key to play again, or Esc to quit.', font,
             screen, (WINDOWWIDTH / 3) - 80, (WINDOWHEIGHT / 3) + 50)
    else:
        # TODO game won sound
        draw_text('CONGRATULATIONS!', title_font, screen,
                  (WINDOWWIDTH / 3), (WINDOWHEIGHT / 3), BLUE)
        draw_text('You have saved Earth!', title_font, screen,
                  (WINDOWWIDTH / 3), (WINDOWHEIGHT / 3) + 100, GREEN)
        draw_text('Press any key to play again, or Esc to quit.', font,
             screen, (WINDOWWIDTH / 3) - 80, (WINDOWHEIGHT / 3) + 150)
    pygame.display.update()
    difficulty = wait_for_player()
