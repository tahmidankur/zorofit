ZoroFit logo kit
================

Which file to use
-----------------
wordmark/   The main logo ("ZoroFit" with the split Z). Use it wherever there is room: website header,
            app store listing, slides, documents.
symbol/     The split Z on its own: chat avatar, social profile picture, small spaces.
            - zorofit-symbol-small-green.svg is the small-size cut. Use it below 32 px.
            - zorofit-symbol-white.svg is drawn about 4% lighter, because white on dark looks heavier.
            - zorofit-symbol-square-green.svg has built-in padding for avatars and social profiles.
stacked/    Symbol above the wordmark: splash screen, merch, square spaces.
app-icon/   App icon (white Z on Zoro Green). For the App Store and Play Store upload the square
            zorofit-app-icon-store-1024.png / -512.png (no rounded corners, no transparency; the stores
            round the corners themselves). The rounded zorofit-app-icon files are for previews and slides.
web-icons/  Favicon and web-app (PWA) icons. Copy every file into your web app's public folder (in a
            React + Vite app, that is public/), then paste head-snippet.html into the <head> of index.html.
            site.webmanifest is included; merge its "icons" list into your existing manifest if you have one.

Each folder has SVG files (use these whenever possible) and a png/ folder for places that need images.

Colours
-------
Zoro Green        #0E6B47   RGB 14 107 71     primary; the logo colour on white or Chalk
Zoro Green Light  #43D693   RGB 67 214 147    the logo on Iron or other dark backgrounds
Iron              #0B1220   RGB 11 18 32      dark neutral; text and dark backgrounds
Chalk             #F4F6F9   RGB 244 246 249   light neutral; backgrounds
Deep Blue         #0C2F86   RGB 12 47 134     supporting colour for the app, never behind the logo

CMYK and Pantone values for print should be confirmed with a printed proof (see the usage guide).

Approved pairs
--------------
Green logo on white or Chalk. White logo on Zoro Green or Iron. Light green logo on Iron.
Black logo on white when only one colour is available.
Never: green on Iron or on Deep Blue (too little contrast), or any colour outside this list.

Type
----
The wordmark letters are Archivo ExtraBold (SIL Open Font License), converted to outlines, so no font
install is needed to use the logo. The split Z is custom-drawn.
