"""
setup.py for Claude Usage Monitor
Build macOS .app bundle using py2app
"""

from setuptools import setup

APP = ['main.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'strip': True,
    'optimize': 2,
    'iconfile': 'icon.icns',
    'plist': {
        # App Metadata
        'CFBundleName': 'Claude Usage Monitor',
        'CFBundleDisplayName': 'Claude Usage Monitor',
        'CFBundleGetInfoString': 'Monitor your Claude.ai usage in real-time',
        'CFBundleIdentifier': 'com.claude.usage.monitor',
        'CFBundleVersion': '1.2.0',
        'CFBundleShortVersionString': '1.2.0',
        'NSHumanReadableCopyright': 'Copyright © 2025 Claude Usage Monitor Contributors. MIT License.',
        
        # Menu Bar App Settings
        'LSUIElement': True,  # Hide from Dock (menu bar only app)
        'LSMinimumSystemVersion': '10.14.0',
        
        # Permissions (if needed in future)
        'NSAppleEventsUsageDescription': 'Claude Usage Monitor needs to send notifications.',
    },
    
    # Include required packages
    'packages': ['rumps', 'requests', 'certifi'],

    # Include all dependencies
    'includes': [
        'rumps',
        'requests',
        'json',
        're',
        'datetime',
        'os',
        'sys',
        'time',
        '_ssl',
        '_hashlib',
        'certifi',
    ],
    
    # Exclude unnecessary packages to reduce size
    'excludes': [
        'tkinter',
        'unittest',
        'test',
        'distutils',
        'setuptools',
    ],

    # Build fully standalone app with all frameworks
    'semi_standalone': False,
    'site_packages': True,
    'frameworks': [],  # Will auto-detect and include necessary frameworks
}

setup(
    name='Claude Usage Monitor',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    install_requires=[
        'rumps>=0.4.0',
        'requests>=2.31.0',
    ],
)
