[app]

# App title and package info
title = Pest Repeller
package.name = pestrepeller
package.domain = org.pestrepeller

# Source code location (relative to buildozer.spec)
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,wav

# App version
version = 1.0.0

# Requirements — must include all Python deps + Kivy/KivyMD
requirements = python3,
    kivy==2.3.0,
    kivymd==1.2.0,
    numpy,
    android,
    pillow

# Entry point
source.main = main.py

# Orientation
orientation = portrait

# Android permissions
android.permissions = RECORD_AUDIO, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, INTERNET

# Android API levels
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33

# Architecture — include both for wider device support
android.archs = arm64-v8a, armeabi-v7a

# Gradle dependencies
android.gradle_dependencies =

# Enable AndroidX
android.enable_androidx = True

# App icon (place a 512x512 icon.png in your project root)
# icon.filename = %(source.dir)s/icon.png

# Fullscreen
fullscreen = 0

# Android logcat filters for debugging
android.logcat_filters = *:S python:D

# Accept Android SDK licenses automatically
android.accept_sdk_license = True

[buildozer]

# Buildozer log level (0=error, 1=info, 2=debug)
log_level = 2

# Warn on root user
warn_on_root = 1

