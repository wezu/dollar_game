from setuptools import setup

setup(
    name="thg",
    options = {
        'build_apps': {
            'include_patterns': [
                '*.png',
                '*.ttf',
                '*.bam',
                '*.json',
                '*.ini',
                '*.jpg',
                '*.glsl',
                '*.ogg',
                '*.ico',
                '*.md'
            ],
            'gui_apps': {
                'game': 'main.py',
            },
            'log_filename': 'log.txt',
            'log_append': False,
            'plugins': [
                'pandagl',
                'p3openal_audio',
            ],
            'platforms': [
                'win_amd64',
                'win32',
                'manylinux1_x86_64'
            ],
        }
    }
)
