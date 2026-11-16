# -*- coding: utf-8 -*-
"""Fill the generated Xcode project's AppIcon.appiconset from icon.png (1024).
Usage: python3 set_icon.py <search_root> <icon_png>
Safe to run when no appiconset exists yet: creates one under the first
Assets.xcassets found; if none exists either, exits 0 with a warning."""
import glob, json, os, sys

from PIL import Image

SIZES = [  # (points, scale, idiom)
    (1024, 1, "ios-marketing"),
    (180, 1, "iphone"), (120, 1, "iphone"), (167, 1, "ipad"), (152, 1, "ipad"),
    (87, 1, "iphone"), (80, 1, "iphone"), (58, 1, "iphone"), (40, 1, "iphone"),
    (60, 1, "iphone"), (76, 1, "ipad"), (29, 1, "iphone"), (20, 1, "iphone"),
]


def main():
    root, src = sys.argv[1], sys.argv[2]
    sets = glob.glob(os.path.join(root, "**", "AppIcon.appiconset"), recursive=True)
    if not sets:
        assets = glob.glob(os.path.join(root, "**", "Assets.xcassets"), recursive=True)
        if not assets:
            print("WARN: no Assets.xcassets found — icon skipped")
            return
        target = os.path.join(assets[0], "AppIcon.appiconset")
        os.makedirs(target, exist_ok=True)
    else:
        target = sets[0]
    im = Image.open(src).convert("RGB")
    images = []
    for px, _scale, idiom in SIZES:
        name = f"icon_{px}.png"
        im.resize((px, px), Image.LANCZOS).save(os.path.join(target, name))
        images.append({"size": f"{px}x{px}", "idiom": idiom,
                       "filename": name, "scale": "1x"})
    with open(os.path.join(target, "Contents.json"), "w") as f:
        json.dump({"images": images, "info": {"version": 1, "author": "xcode"}}, f, indent=2)
    print("icon set written to", target)


if __name__ == "__main__":
    main()
