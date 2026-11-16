# -*- coding: utf-8 -*-
"""Fill the generated Xcode project's icon slots from icon.png (1024+).

Two routes, both written at exact native resolutions so iOS never upscales:
1. The modern asset catalog (AppIcon.appiconset) with a CORRECT Contents.json
   (point size x scale — the previous version wrongly declared pixel sizes
   as 1x, so iOS discarded the set).
2. The legacy loose files the kivy-ios template's Info.plist points at
   (CFBundleIconFiles: AppIcon29x29 / AppIcon76x76~ipad). The template ships
   a 29x29 placeholder; left alone, iOS upscales it ~6x -> blurry icon.
   We overwrite it and add the @2x/@3x variants iOS looks for.

Usage: python3 set_icon.py <search_root> <icon_png>
Safe to run when nothing is found: exits 0 with a warning.
"""
import glob, json, os, sys

from PIL import Image

# (points, scale, idiom) — the full modern iOS icon set
CATALOG = [
    (20, 2, "iphone"), (20, 3, "iphone"),
    (29, 2, "iphone"), (29, 3, "iphone"),
    (40, 2, "iphone"), (40, 3, "iphone"),
    (60, 2, "iphone"), (60, 3, "iphone"),
    (20, 1, "ipad"), (20, 2, "ipad"),
    (29, 1, "ipad"), (29, 2, "ipad"),
    (40, 1, "ipad"), (40, 2, "ipad"),
    (76, 1, "ipad"), (76, 2, "ipad"),
    (83.5, 2, "ipad"),
    (1024, 1, "ios-marketing"),
]

# legacy loose files: filename -> exact pixels
LEGACY = {
    "AppIcon29x29.png": 29,
    "AppIcon29x29@2x.png": 58,
    "AppIcon29x29@3x.png": 87,
    "AppIcon76x76~ipad.png": 76,
    "AppIcon76x76@2x~ipad.png": 152,
}


def fmt_pt(pt):
    return str(int(pt)) if float(pt) == int(pt) else str(pt)


def write_catalog(im, root):
    sets = glob.glob(os.path.join(root, "**", "AppIcon.appiconset"), recursive=True)
    if not sets:
        assets = glob.glob(os.path.join(root, "**", "Assets.xcassets"), recursive=True)
        if not assets:
            print("WARN: no Assets.xcassets found — catalog icon skipped")
            return
        target = os.path.join(assets[0], "AppIcon.appiconset")
        os.makedirs(target, exist_ok=True)
    else:
        target = sets[0]
    images = []
    for pt, scale, idiom in CATALOG:
        px = int(round(pt * scale))
        name = "icon_{}@{}x.png".format(fmt_pt(pt), scale)
        im.resize((px, px), Image.LANCZOS).save(os.path.join(target, name))
        images.append({"size": "{0}x{0}".format(fmt_pt(pt)), "idiom": idiom,
                       "filename": name, "scale": "{}x".format(scale)})
    with open(os.path.join(target, "Contents.json"), "w") as f:
        json.dump({"images": images, "info": {"version": 1, "author": "xcode"}}, f, indent=2)
    print("catalog icon set written to", target)


def write_legacy(im, root):
    hits = glob.glob(os.path.join(root, "**", "AppIcon29x29.png"), recursive=True)
    if not hits:
        print("WARN: no loose AppIcon29x29.png found — legacy icons skipped")
        return
    folder = os.path.dirname(hits[0])
    for name, px in LEGACY.items():
        im.resize((px, px), Image.LANCZOS).save(os.path.join(folder, name))
    print("legacy icons written to", folder)


def main():
    root, src = sys.argv[1], sys.argv[2]
    im = Image.open(src).convert("RGB")
    write_catalog(im, root)
    write_legacy(im, root)


if __name__ == "__main__":
    main()
