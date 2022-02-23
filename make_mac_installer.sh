#!/bin/bash

create-dmg \
  --volname "PDFStitcher Installer" \
  --background "pdfstitcher/resources/install_background.png" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "pdfstitcher.app" 145 185 \
  --hide-extension "pdfstitcher.app" \
  --app-drop-link 595 185 \
  "PDFStitcher-Installer.dmg" \
  "dist/pdfstitcher.app/"