@REM create the different sized pngs for mac. This needs to be done on windows because my mac is too old and throws an error.
set inkscape="C:\Program Files\Inkscape\bin\inkscape.exe"
%inkscape% -o stitcher-icon.iconset/icon_16x16.png -w 16 -h 16 stitcher-icon.svg
%inkscape% -o stitcher-icon.iconset/icon_16x16@2x.png"   -w   32 -h   32  stitcher-icon.svg
%inkscape% -o stitcher-icon.iconset/icon_32x32.png"      -w   32 -h   32  stitcher-icon.svg
%inkscape% -o stitcher-icon.iconset/icon_32x32@2x.png"   -w   64 -h   64  stitcher-icon.svg
%inkscape% -o stitcher-icon.iconset/icon_128x128.png"    -w  128 -h  128  stitcher-icon.svg
%inkscape% -o stitcher-icon.iconset/icon_128x128@2x.png" -w  256 -h  256  stitcher-icon.svg
%inkscape% -z -e stitcher-icon.iconset/icon_256x256.png"    -w  256 -h  256  stitcher-icon.svg
%inkscape% -z -e stitcher-icon.iconset/icon_256x256@2x.png" -w  512 -h  512  stitcher-icon.svg
%inkscape% -z -e stitcher-icon.iconset/icon_512x512.png"    -w  512 -h  512  stitcher-icon.svg
%inkscape% -z -e stitcher-icon.iconset/icon_512x512@2x.png" -w 1024 -h 1024  stitcher-icon.svg

@REM on mac: iconutil -c icns "$output_name.iconset"

@REM for windows, it's a bit easier
magick convert -background none stitcher-icon.svg -define icon:auto-resize stitcher-icon.ico