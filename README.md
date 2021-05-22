# Pixave's Journey
Python game made for a contest.
Pixave's Journey is a simple platformer set in outer space where Pixave, the protagonist, is set
on a mission to explore space. They move around via platforms (officially named "conveniently placed platforms").
Most of the platforms are safe for Pixave's traversal. Some of them, however, include obstacles that
may kill poor Pixave (then they are called "inconveniently placed platforms"). If Pixave dies, the
game shuts down and the window is closed (Might change this later to a "game over" screen).

# Controls
Jump with space (You can double jump), negate gravity with "s".

# Goal
Traverse as much distance as possible. Currently the most reliable way to measure this is via the star background.

# How to run
There must be an OpenGL >= 3.3 driver present in the system. If the program doesn't work with normal Python, try IDE. The
main reason why the program might not start with normal Python seems to be related to the pyopengl\pyopengl_accelerate
modules (i. e. https://stackoverflow.com/questions/61495735/unable-to-load-numpy-formathandler-accelerator-from-opengl-accelerate).
Also Pixave's Journey depends on some packages. They can be installed by pip (or any analogue package manager) via the commands:
pip install pyopengl pyopengl_accelerate
pip install glfw
pip install euclid
pip install imageio
pip install pyopenal
pip install pyogg
pip install numpy
