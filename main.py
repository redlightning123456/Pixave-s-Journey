#Make sure you have the numpy, imageio, pyogg, pyopenal, glfw, pyopengl, and euclid modules installed in order to run this program.
#To any future readers: this code is an absolute mess because I thought the turning in date was 03.06.2021 while it was actually 13.05.2021. Realized that on 07.05.2021.
#There is a lot of stuff to improve. A few examples:
#1. Collision detection isn't continuous, so a bullet that moves very fast can pass through other objects without colliding with them.
#2. Collideable objects aren't grouped into optimized structures e. g. octree or bvh.
#3. Lack of features that were present in my original vision.

with_sound = True

import glfw
from OpenGL.GL import *
from euclid import *
from enum import Enum
import copy
import random
if with_sound:
    from openal import *
import imageio
import numpy
import ctypes
import datetime

def rotate(v, angle):
    return Vector2(v.x * math.cos(angle) - v.y * math.sin(angle), v.x * math.sin(angle) + v.y * math.cos(angle))


def draw_vertex(x, y):
    glVertex2f(x / 1920, y / 1080)

def sign(x):
    return 1 if x > 0 else -1

def point_is_not_under_ray(p, l):
    if l.x == 0:
        return True
    return p.y >= l.y + l.y / l.x * p.x

def point_is_not_above_ray(p, l):
    if l.x == 0:
        return True
    return p.y <= l.y + l.y / l.x * p.x

class Game:
    class World:
        def update(self):
            if self.player.has_lost():
                if self._first_losing_iter:
                    if with_sound:
                        self.background_music.stop()
                        self.losing_sound.play()
                    self._first_losing_iter = False

                if (self.current_time - self.player.time_lost).total_seconds() > 2:
                    self.reset()

                self.player.do_gravity(40 * self.delta_time)
                self.player.rect.pos += self.player.rect.velocity * self.delta_time
            else:
                self.score = self.player.rect.pos.x / 100
                if with_sound:
                    if self.background_music.get_state() != AL_PLAYING:
                        self.background_music.play()
                if (self.timer >= 240) and (not self._beat_dropped):
                    self.platform_texture.change_to("platform_on.png")
                    self._beat_dropped = True
                self.player.rect.velocity.x = 300
                self.player.respond_to_user_input()
                self.player.do_gravity(self.delta_time)

                self.remove_out_of_range_columns()
                if (self.platforms[-1].rect.pos.x - self.player.rect.pos.x < 6000):
                    self.generate_column()
                correction = Vector2(0, 0)
                for platform in self.platforms:
                    if self.player.get_aabb().will_collide_with(platform.get_aabb(), self.delta_time):
                        correction = self.player.get_aabb().collision_correction_vector(platform.get_aabb(), self.delta_time)
                        self.player.rect.pos += correction
                        self.player.jumps_left = 2

                for obstacle in self.obstacles:
                    if self.player.get_aabb().will_collide_with(obstacle.get_aabb(), self.delta_time):
                        self.player.lose(self.current_time)
              
                self.player.rect.pos += self.player.rect.velocity * self.delta_time
            
                if correction.x != 0:
                    self.player.rect.velocity.x = 0
                if correction.y != 0:
                    self.player.rect.velocity.y = 0
                self.cam.pos = self.player.rect.pos + Vector2(1800, 0)
            self.timer += self.delta_time
            new_time = datetime.datetime.now()
            self.delta_time = (new_time - self.current_time).total_seconds() * 10
            self.current_time = new_time
        class AABB:
            def _min_vec2(a, b):
                return Vector2(min(a.x, b.x), min(a.y, b.y))
            def _max_vec2(a, b):
                return Vector2(max(a.x, b.x), max(a.y, b.y))
            def __init__(self, start, end, velocity):
                self._start = copy.copy(start)
                self._end = copy.copy(end)
                self._velocity = copy.copy(velocity)
                if self._start.x > self._end.x:
                    self_end_x_copy = self._end.x
                    self._end.x = self._start.x
                    self._start.x = self_end_x_copy

                if self._start.y > self._end.y:
                    self_end_y_copy = self._end.y
                    self._end.y = self._start.y
                    self._start.y = self_end_y_copy
            def _distance_between_intervals(s_1, e_1, s_2, e_2):
                if s_1 < s_2:
                    return s_2 - e_1
                else:
                    return s_1 - e_2
            def will_collide_with(self, other, delta_time):
                return (not (self._end.x + self._velocity.x * delta_time <= other._start.x + other._velocity.x * delta_time or other._end.x + other._velocity.x * delta_time <= self._start.x + self._velocity.x * delta_time)) and (not (self._end.y + self._velocity.y * delta_time <= other._start.y + other._velocity.y * delta_time or other._end.y + other._velocity.y * delta_time <= self._start.y + self._velocity.y * delta_time))
            def collision_correction_vector(self, other, delta_time):
                bounds = Game.World.AABB(Game.World.AABB._min_vec2(self._start, self._start + (self._velocity - other._velocity) * delta_time), Game.World.AABB._max_vec2(self._end, self._end + (self._velocity - other._velocity) * delta_time), 0)
                x_correction = Game.World.AABB._distance_between_intervals(bounds._start.x, bounds._end.x, other._start.x, other._end.x)
                y_correction = Game.World.AABB._distance_between_intervals(bounds._start.y, bounds._end.y, other._start.y, other._end.y)


                self_center = (self._start + self._end) / 2
                other_center = (other._start + other._end) / 2

                
                min_interval_distance = abs(x_correction)
                axis = Vector2(1, 0)

                if self_center.x < other_center.x:
                    axis = -axis
                
                if abs(y_correction) < min_interval_distance:
                    min_interval_distance = abs(y_correction)
                    axis = Vector2(0, 1)
                    if self_center.y < other_center.y:
                        axis = -axis
                
                return min_interval_distance * axis

        class Cam:
            def __init__(self, pos, scale):
                self.pos = pos
                self.scale = scale
            def send_vertex(self, v):
                draw_vertex((v.x - self.pos.x) / self.scale.x, (v.y - self.pos.y) / self.scale.y)
        
        class Rectangle:
            def __init__(self, pos, size, velocity = Vector2(0, 0)):
                self.pos = pos
                self.size = size
                self.velocity = velocity
            def get_aabb(self):
                return Game.World.AABB(self.pos - self.size, self.pos + self.size, self.velocity)
            def draw(self, color, cam):
                glColor(color)
                glBegin(GL_TRIANGLES)
                cam.send_vertex(Vector2(self.pos.x - self.size.x, self.pos.y - self.size.y))
                cam.send_vertex(Vector2(self.pos.x - self.size.x, self.pos.y + self.size.y))
                cam.send_vertex(Vector2(self.pos.x + self.size.x, self.pos.y - self.size.y))

                cam.send_vertex(Vector2(self.pos.x + self.size.x, self.pos.y + self.size.y))
                cam.send_vertex(Vector2(self.pos.x - self.size.x, self.pos.y + self.size.y))
                cam.send_vertex(Vector2(self.pos.x + self.size.x, self.pos.y - self.size.y))
                glEnd()


        class Texture:
            def __init__(self, filename):
                self.ID = glGenTextures(1)
                glPixelStorei(GL_UNPACK_ALIGNMENT, 4)
                glBindTexture(GL_TEXTURE_2D, self.ID)
                image = imageio.imread(filename)
                image = numpy.flip(image, 0)
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, image.shape[1], image.shape[0], 0, GL_RGBA, GL_UNSIGNED_BYTE, image)

                
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
                
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

                
                glBindTexture(GL_TEXTURE_2D, 0)
            def change_to(self, filename):
                image = imageio.imread(filename)
                image = numpy.flip(image, 0)
                glBindTexture(GL_TEXTURE_2D, self.ID)
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, image.shape[1], image.shape[0], 0, GL_RGBA, GL_UNSIGNED_BYTE, image)
            def __del__(self):
                glDeleteTextures(1, [self.ID])
            
        class TexturedRectangle:
            def _check_shader_compile_errors(shader, shader_type):
                if shader_type == "linked":
                    compilation_successful = glGetProgramiv(shader, GL_LINK_STATUS)
                    if not compilation_successful:
                        print("Shader compilation failed! Shader_type: " + shader_type)
                else:
                    compilation_successful = glGetShaderiv(shader, GL_COMPILE_STATUS)
                    if not compilation_successful:
                        print("Shader compilation failed! Shader type: " + shader_type)
            def enable_drawing():
                vertices = [
                    -1.0, -1.0,
                     1.0, -1.0,
                    -1.0,  1.0,

                     1.0,  1.0,
                     1.0, -1.0,
                    -1.0,  1.0
                    ]
                vertices_ptr = (GLfloat * len(vertices))(*vertices)
                Game.World.TexturedRectangle.vbo = glGenBuffers(1)
                Game.World.TexturedRectangle.vao = glGenVertexArrays(1)

                glBindVertexArray(Game.World.TexturedRectangle.vao)
                
                glBindBuffer(GL_ARRAY_BUFFER, Game.World.TexturedRectangle.vbo)
                glBufferData(GL_ARRAY_BUFFER, len(vertices) * sizeof(GLfloat), vertices_ptr, GL_STATIC_DRAW)
                glEnableVertexAttribArray(0)
                glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 2 * sizeof(GLfloat), ctypes.c_void_p(0))
                glBindBuffer(GL_ARRAY_BUFFER, 0)

                glBindVertexArray(0)
                
                vertex_shader = glCreateShader(GL_VERTEX_SHADER)
                fragment_shader = glCreateShader(GL_FRAGMENT_SHADER)
                glShaderSource(vertex_shader,
                               """
#version 330
layout (location = 0) in vec2 rectangleVertexPos;
uniform vec2 rectanglePos;
uniform vec2 rectangleSize;
uniform vec2 camPos = vec2(0, 0);
uniform vec2 camScale = vec2(1, 1);
uniform vec2 factors = vec2(1, 1);
out vec2 texturePos;
void main()
{
    gl_Position = vec4((rectanglePos + factors * rectangleSize * rectangleVertexPos - camPos) / camScale / vec2(1920, 1080), 0, 1);
    texturePos = (rectangleVertexPos + 1) / 2;
}
""")
                glShaderSource(fragment_shader,
                               """
#version 330
uniform sampler2D tex;
uniform vec2 textureFactors = vec2(1, 1);
uniform vec2 textureCenter = vec2(0, 0);
out vec4 fragColor;
in vec2 texturePos;
void main()
{
    fragColor = texture(tex, texturePos * textureFactors + textureCenter);
}
""")
                glCompileShader(vertex_shader)
                Game.World.TexturedRectangle._check_shader_compile_errors(vertex_shader, "vertex")
                glCompileShader(fragment_shader)
                Game.World.TexturedRectangle._check_shader_compile_errors(fragment_shader, "fragment")
                Game.World.TexturedRectangle.shader_program = glCreateProgram()
                glAttachShader(Game.World.TexturedRectangle.shader_program, vertex_shader)
                glAttachShader(Game.World.TexturedRectangle.shader_program, fragment_shader)
                glLinkProgram(Game.World.TexturedRectangle.shader_program)
                Game.World.TexturedRectangle._check_shader_compile_errors(Game.World.TexturedRectangle.shader_program, "linked")
                
                glDeleteShader(vertex_shader)
                glDeleteShader(fragment_shader)
            def __init__(self, pos, size, texture, velocity = Vector2(0, 0)):
                self.pos = pos
                self.size = size
                self.texture = texture
                self.velocity = velocity
            def get_aabb(self):
                return Game.World.AABB(self.pos - self.size, self.pos + self.size, self.velocity)
            def draw(self, cam, rectangle_factors = Vector2(1, 1), texture_center = Vector2(0, 0), texture_factors = Vector2(1, 1)):
                glUseProgram(Game.World.TexturedRectangle.shader_program)
                glUniform2f(glGetUniformLocation(Game.World.TexturedRectangle.shader_program, "rectanglePos"), self.pos.x, self.pos.y)
                glUniform2f(glGetUniformLocation(Game.World.TexturedRectangle.shader_program, "rectangleSize"), self.size.x, self.size.y)
                glUniform2f(glGetUniformLocation(Game.World.TexturedRectangle.shader_program, "camPos"), cam.pos.x, cam.pos.y)
                glUniform2f(glGetUniformLocation(Game.World.TexturedRectangle.shader_program, "camScale"), cam.scale.x, cam.scale.y)
                glUniform2f(glGetUniformLocation(Game.World.TexturedRectangle.shader_program, "factors"), rectangle_factors.x, rectangle_factors.y)
                glUniform2f(glGetUniformLocation(Game.World.TexturedRectangle.shader_program, "textureFactors"), texture_factors.x, texture_factors.y)
                glUniform2f(glGetUniformLocation(Game.World.TexturedRectangle.shader_program, "textureCenter"), texture_center.x, texture_center.y)
                
                glActiveTexture(GL_TEXTURE0)
                glBindTexture(GL_TEXTURE_2D, self.texture.ID)
                glUniform1i(glGetUniformLocation(Game.World.TexturedRectangle.shader_program, "tex"), 0)
                
                glBindVertexArray(Game.World.TexturedRectangle.vao)
                glDrawArrays(GL_TRIANGLES, 0, 6)
                glBindVertexArray(0)
                glUseProgram(0)
        class Player:
            jump_sound = None
            _first_instance = True
            time_lost = None
            def __init__(self, pos, size, window):
                if Game.World.Player._first_instance:
                    if with_sound:
                        Game.World.Player.jump_sound = oalOpen("beep.ogg")
                    Game.World.Player._first_instance = False
                self._has_lost = False
                self.rect = Game.World.TexturedRectangle(pos, size, Game.World.Texture("player_idle.png"), Vector2(0, 0))
                self.window = window
                self._just_jumped = False
                self._just_swapped_gravity = False
                self.gravity_direction = -1
                self.jumps_left = 0
            def respond_to_user_input(self):
                if glfw.get_key(self.window.handle, glfw.KEY_S):
                    if not self._just_swapped_gravity:
                        self.gravity_direction = -self.gravity_direction
                        self._just_swapped_gravity = True
                else:
                    self._just_swapped_gravity = False
                
                if glfw.get_key(self.window.handle, glfw.KEY_SPACE):
                    if (not self._just_jumped) and self.jumps_left > 0:
                        self.jump()
                        if with_sound:
                            Game.World.Player.jump_sound.play()
                        self._just_jumped = True
                else:
                    self._just_jumped = False
            def do_gravity(self, delta_time):
                self.rect.velocity += delta_time * Vector2(0, self.gravity_direction * 9.8)
            def jump(self):
                self.rect.velocity.y = -400 * self.gravity_direction
                self.jumps_left -= 1
            def get_aabb(self):
                return self.rect.get_aabb()
            def draw(self, cam):
                self.rect.draw(cam, Vector2(1, -self.gravity_direction))
            def lose(self, time):
                self.time_lost = time
                self.rect.velocity = Vector2(0, -500 * self.gravity_direction)
                self._has_lost = True
                self.rect.texture.change_to("player_dead.png")
            def reset(self):
                self._has_lost = False
                self.time_lost = None
                self.rect.texture.change_to("player_idle.png")
            def has_lost(self):
                return self._has_lost
        class Platform:
            def __init__(self, pos, size, texture):
                self.rect = Game.World.TexturedRectangle(pos, size, texture)
            def get_aabb(self):
                return self.rect.get_aabb()
            def draw(self, cam):
                self.rect.draw(cam)

        class Obstacle:
            def __init__(self, pos, size, texture):
                self.rect = Game.World.TexturedRectangle(pos, size, texture)
            def get_aabb(self):
                return self.rect.get_aabb()
            def draw(self, cam):
                self.rect.draw(cam)

        
        def draw(self):
            for x in range(-1, 2):
                for y in range(-1, 2):
                    self.background_stars.pos = 128 * Vector2(1920 * 2 * 2 * ((self.cam.pos.x * 64) // (128 * 2 * 2 * 64 * 1920) + x), 1080 * 2 * ((self.cam.pos.y * 64) // (128 * 1080 * 2 * 64) + y))
                    self.background_stars.draw(self.Cam(self.cam.pos, self.cam.scale * 64))
            self.player.draw(self.cam)
            for obstacle in self.obstacles:
                obstacle.draw(self.cam)
            for platform in self.platforms:
                platform.draw(self.cam)
            if self.timer >= 225 and self.timer <= 240:
                self.Rectangle(Vector2(0, 0), Vector2(1920, 1080)).draw(((self.timer - 225) / 15, (self.timer - 225) / 15, (self.timer - 225) / 15, (self.timer - 225) / 15), self.Cam(Vector2(0, 0), Vector2(1, 1)))

            self.screen.draw(self.Cam(Vector2(0, 0), Vector2(1, 1)))
            self._draw_score()
            
        def _draw_score(self):
            self.score_message.draw(self.Cam(Vector2(0, 0), Vector2(1, 1)), Vector2(6, 1), Vector2(0, 0), Vector2(6/16, 1))
            score = int(self.score)

            digits = []

            if score == 0:
                digits = [0]
                
            while score > 0:
                digits.append(score % 10)
                score //= 10

            self.score_message.pos += Vector2(4 * 8 * 6, 0)
                
            for digit in digits[::-1]:
                self.score_message.draw(self.Cam(Vector2(0, 0), Vector2(1, 1)), Vector2(1, 1), Vector2((6+digit)/16, 0), Vector2(1/16, 1))
                self.score_message.pos += Vector2(4 * 8 * 2, 0)
            self.score_message.pos -= Vector2(4 * 8 * (6+2*len(digits)), 0)
        
        def __init__(self, window):
            self._beat_dropped = False
            self.timer = 0
            self.delta_time = 0
            self.score = 0
            self.current_time = datetime.datetime.now()
            self.cam = self.Cam(Vector2(0, 0), Vector2(2, 2))
            self.player = self.Player(Vector2(0, -500), 10 * Vector2(10, 9), window)

            self.background_music = oalOpen("into_the_depths_of_space.ogg")
            self.losing_sound = oalOpen("sad_beep.ogg")

            self._first_losing_iter = True
            
            self.TexturedRectangle.enable_drawing()


            self.platform_texture = self.Texture("platform_off.png")
            self.platform_danger_texture = self.Texture("platform_danger.png")
            self.laser_beam_vertical_texture = self.Texture("laser_beam_vertical.png")
            self.force_field_texture = self.Texture("force_field.png")
            self.background_stars = self.TexturedRectangle(Vector2(0, 0), Vector2(1920 * 2, 1080) * 128, self.Texture("background_stars.png"))
            self.score_message = self.TexturedRectangle(Vector2(1260, 700), 4 * Vector2(8, 10), self.Texture("score_message.png"))
            self.screen = self.TexturedRectangle(Vector2(1408, 700), 16 * Vector2(32, 20), self.Texture("screen.png"))
            
            self.platforms = []
            self.platforms.append(self.Platform(Vector2(0, -1000), 10 * Vector2(30, 16), self.platform_texture))
            self.platforms.append(self.Platform(Vector2(600, -1000), 10 * Vector2(30, 16), self.platform_texture))
            self.platforms.append(self.Platform(Vector2(1200, -1000), 10 * Vector2(30, 16), self.platform_texture))
            self.platforms.append(self.Platform(Vector2(1800, -1000), 10 * Vector2(30, 16), self.platform_texture))
            self.platforms.append(self.Platform(Vector2(2400, -1000), 10 * Vector2(30, 16), self.platform_texture))
            self.platforms.append(self.Platform(Vector2(3000, -1000), 10 * Vector2(30, 16), self.platform_texture))
            self.platforms.append(self.Platform(Vector2(3600, -1000), 10 * Vector2(30, 16), self.platform_texture))
            self.platforms.append(self.Platform(Vector2(4200, -1000), 10 * Vector2(30, 16), self.platform_texture))
            self.platforms.append(self.Platform(Vector2(4800, -1000), 10 * Vector2(30, 16), self.platform_texture))
            self.platforms.append(self.Platform(Vector2(5400, -1000), 10 * Vector2(30, 16), self.platform_texture))
            self.platforms.append(self.Platform(Vector2(6000, -1000), 10 * Vector2(30, 16), self.platform_texture))

            self.obstacles = []

        def generate_column(self):
            last_platform = self.platforms[-1]
            self.generate_platform(self.Platform(Vector2(last_platform.rect.pos.x + 600, self.player.rect.pos.y + 320 * random.randint(-72, -56)), 10 * Vector2(30, 16), self.platform_texture))
            self.generate_platform(self.Platform(Vector2(last_platform.rect.pos.x + 600, self.player.rect.pos.y + 320 * random.randint(-56, -40)), 10 * Vector2(30, 16), self.platform_texture))
            self.generate_platform(self.Platform(Vector2(last_platform.rect.pos.x + 600, self.player.rect.pos.y + 320 * random.randint(-40, -24)), 10 * Vector2(30, 16), self.platform_texture))
            self.generate_platform(self.Platform(Vector2(last_platform.rect.pos.x + 600, self.player.rect.pos.y + 320 * random.randint(-24, -8)), 10 * Vector2(30, 16), self.platform_texture))
            self.generate_platform(self.Platform(Vector2(last_platform.rect.pos.x + 600, self.player.rect.pos.y + 320 * random.randint(-8, 8)), 10 * Vector2(30, 16), self.platform_texture))
            self.generate_platform(self.Platform(Vector2(last_platform.rect.pos.x + 600, self.player.rect.pos.y + 320 * random.randint(8, 24)), 10 * Vector2(30, 16), self.platform_texture))
            self.generate_platform(self.Platform(Vector2(last_platform.rect.pos.x + 600, self.player.rect.pos.y + 320 * random.randint(24, 40)), 10 * Vector2(30, 16), self.platform_texture))
            self.generate_platform(self.Platform(Vector2(last_platform.rect.pos.x + 600, self.player.rect.pos.y + 320 * random.randint(40, 56)), 10 * Vector2(30, 16), self.platform_texture))
            self.generate_platform(self.Platform(Vector2(last_platform.rect.pos.x + 600, self.player.rect.pos.y + 320 * random.randint(56, 72)), 10 * Vector2(30, 16), self.platform_texture))
        def generate_platform(self, platform):
            dangerous = False
            if self._beat_dropped:
                if random.randint(0, 10) == 0:
                    self.obstacles.append(self.Obstacle(platform.rect.pos, 2 * platform.rect.size, self.force_field_texture))
                    dangerous = True
                if random.randint(0, 20) == 0:
                    self.obstacles.append(self.Obstacle(platform.rect.pos, 10 * Vector2(8, 128), self.laser_beam_vertical_texture))
                    dangerous = True
            if dangerous:
                self.platforms.append(self.Platform(platform.rect.pos, platform.rect.size, self.platform_danger_texture))
            else:
                self.platforms.append(platform)
        def remove_out_of_range_columns(self):
            try:
                while self.player.rect.pos.x - self.platforms[0].rect.size.x - self.platforms[0].rect.pos.x > 6000:
                    self.platforms.pop(0)
            except IndexError:
                pass
            try:
                while self.player.rect.pos.x - self.obstacles[0].rect.size.x - self.obstacles[0].rect.pos.x > 6000:
                    self.obstacles.pop(0)
            except IndexError:
                pass
        def reset(self):
            self._beat_dropped = False
            self.timer = 0
            self.delta_time = 0
            self.score = 0
            self.current_time = datetime.datetime.now()
            self.cam = self.Cam(Vector2(0, 0), Vector2(2, 2))
            self.player.rect.pos = Vector2(0, -500)
            self.player.rect.velocity = Vector2(0, 0)
            self.player.gravity_direction = -1
            self._first_losing_iter = True
            self.player.reset()

            self.platform_texture.change_to("platform_off.png")
            
            self.platforms = []
            self.platforms.append(self.Platform(Vector2(0, -1000), 10 * Vector2(30, 16), self.platform_texture))
            self.platforms.append(self.Platform(Vector2(600, -1000), 10 * Vector2(30, 16), self.platform_texture))
            self.platforms.append(self.Platform(Vector2(1200, -1000), 10 * Vector2(30, 16), self.platform_texture))
            self.platforms.append(self.Platform(Vector2(1800, -1000), 10 * Vector2(30, 16), self.platform_texture))
            self.platforms.append(self.Platform(Vector2(2400, -1000), 10 * Vector2(30, 16), self.platform_texture))
            self.platforms.append(self.Platform(Vector2(3000, -1000), 10 * Vector2(30, 16), self.platform_texture))
            self.platforms.append(self.Platform(Vector2(3600, -1000), 10 * Vector2(30, 16), self.platform_texture))
            self.platforms.append(self.Platform(Vector2(4200, -1000), 10 * Vector2(30, 16), self.platform_texture))
            self.platforms.append(self.Platform(Vector2(4800, -1000), 10 * Vector2(30, 16), self.platform_texture))
            self.platforms.append(self.Platform(Vector2(5400, -1000), 10 * Vector2(30, 16), self.platform_texture))
            self.platforms.append(self.Platform(Vector2(6000, -1000), 10 * Vector2(30, 16), self.platform_texture))

            self.obstacles = []
    class Window:
        class Mode(Enum):
            windowed = 0
            borderless = 1
            full_screen = 2

        def __init__(self, mode):
            if mode == self.Mode.borderless:
                video_mode = glfw.get_video_mode(glfw.get_primary_monitor())
                glfw.window_hint(glfw.RED_BITS, video_mode.bits.red)
                glfw.window_hint(glfw.GREEN_BITS, video_mode.bits.green)
                glfw.window_hint(glfw.BLUE_BITS, video_mode.bits.blue)
                glfw.window_hint(glfw.REFRESH_RATE, video_mode.refresh_rate)
                self.handle = glfw.create_window(video_mode.size.width, video_mode.size.height, "Pixave's Journey", glfw.get_primary_monitor(), None)

        def is_invalid(self):
            return not self.handle

    
    def __init__(self):
        self.window = self.Window(self.Window.Mode.borderless)
        if self.window.is_invalid():
            glfw.terminate()
            return
        glfw.make_context_current(self.window.handle)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self.world = self.World(self.window)
    def start_loop(self):
        self.world.current_time = datetime.datetime.now()
        while not glfw.window_should_close(self.window.handle):
            self.update()
        if with_sound:
            oalQuit()

    def update(self):
        self.world.update()

        glClear(GL_COLOR_BUFFER_BIT)

        self.world.draw()

        glfw.swap_buffers(self.window.handle)
        glfw.poll_events()

def main():
    if not glfw.init():
        return
    game = Game()
    game.start_loop()
    glfw.terminate()
if __name__ == "__main__":
    main()
