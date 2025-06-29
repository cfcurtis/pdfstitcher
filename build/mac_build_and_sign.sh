#! /usr/bin/env bash

python -m nuitka \
    --standalone \
    --macos-create-app-bundle \
    --macos-app-icon=resources/stitcher-icon.icns \
    --include-data-dir=resources/locale=resources/locale \
    --include-package-data=pdf_mangler \
    --company-name="Charlotte Curtis" \
    --product-name="PDF Stitcher" \
    --macos-app-name="PDF Stitcher" \
    --macos-app-version=v1.2 \
    --macos-signed-app-name=com.charlottecurtis.pdfstitcher \
    --macos-sign-identity="$APPLE_SIGN_IDENTITY" \
    --macos-sign-notarization \
    --assume-yes-for-downloads \
    --output-dir=build \
    --script-name=pdfstitcher/gui/app.py \
    --output-filename=pdfstitcher

# move the offending data files from MacOS to Resources, then symlink
# Important: symlinks need to be relative inside the app bundle
for dir in "resources" "babel" "pdf_mangler" "certifi"; do
    mv "build/app.app/Contents/MacOS/$dir" "build/app.app/Contents/Resources/"
    cd "build/app.app/Contents/MacOS/"
    ln -s "../Resources/$dir" "."
    cd -
done

# should be executable, but just in case, set it before redoing code signing
chmod +x build/app.app/Contents/MacOS/pdfstitcher

# rename the app. Running "mv build/app.app build/pdfstitcher.app" doesn't work, 
# it seems to treat app.app like a file and moves it inside pdfstitcher.app
cd build
mv app.app pdfstitcher.app
cd -

# redo the code signing
codesign --deep --force --options runtime --timestamp --sign "$APPLE_SIGN_IDENTITY" build/pdfstitcher.app