from pathlib import Path

import cv2
import json

ROOT = Path(__file__).parent.parent

IMAGE_DIR = ROOT / "images"
OUTPUT_DIR = ROOT / "figures"

OUTPUT_DIR.mkdir(exist_ok=True)


def extract_figures():

    images = sorted(IMAGE_DIR.glob("*.png"))
    # Remove old extracted figures
   

    print(f"Found {len(images)} page images\n")

    for file in OUTPUT_DIR.glob("*.png"):
        file.unlink()

    metadata = []

    for image in images:

        print(f"Processing {image.name}")

        img = cv2.imread(str(image))

        gray = cv2.cvtColor(
            img,
            cv2.COLOR_BGR2GRAY,
        )

        # Invert so dark content becomes white
        thresh = cv2.threshold(
            gray,
            240,
            255,
            cv2.THRESH_BINARY_INV,
        )[1]

        horizontal = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (60,5)
        )

        vertical = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (5,60)
        )

        mask1 = cv2.dilate(thresh, horizontal)

        mask2 = cv2.dilate(mask1, vertical)

        mask = cv2.morphologyEx(
            mask2,
            cv2.MORPH_CLOSE,
            horizontal,
        )

        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        figure = 1

        for contour in contours:

            x, y, w, h = cv2.boundingRect(contour)
            # Ignore page header/footer strips
            if w > img.shape[1] * 0.75 and h < 120:
                continue
            aspect = w / h

            if aspect > 8:
                continue

            area = w * h

            if w < 120 or h < 80:
                continue

            # Ignore tiny objects
            if area < 6000:
                continue

            if 150 <= w <= 190 and 70 <= h <= 100:
                continue

            PAD = 40

            x1 = max(0, x-PAD)
            y1 = max(0, y-PAD)

            x2 = min(img.shape[1], x+w+PAD)
            y2 = min(img.shape[0], y+h+PAD)

            crop = img[y1:y2, x1:x2]

            crop_gray = gray[y1:y2, x1:x2]

            binary = cv2.threshold(
                crop_gray,
                180,
                255,
                cv2.THRESH_BINARY_INV
            )[1]

            num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary)

            components = 0

            for i in range(1, num_labels):   # Skip background
                if stats[i, cv2.CC_STAT_AREA] >= 40:
                    components += 1

            if components <= 2:
                continue


            dark_pixels = cv2.countNonZero(binary)

            crop_area = crop.shape[0] * crop.shape[1]


            if crop_area == 0:
                continue

            dark_ratio = dark_pixels / crop_area

            print(
                f"{image.name} | "
                f"w={w} h={h} "
                f"area={area} "
                f"dark={dark_ratio:.4f}"
            )

            if dark_ratio > 0.7:
                continue

            if dark_ratio < 0.01:
                continue

            filename = (
                f"{image.stem}_figure_{figure:02}.png"
            )

            cv2.imwrite(
                str(OUTPUT_DIR / filename),
                crop,
            )


            metadata.append({
                "page": int(image.stem.split("_")[1]),
                "figure": figure,
                "filename": filename,
            })

            print(
                f"   Saved {filename} ({w}x{h})"
            )

            figure += 1

    with open(
        OUTPUT_DIR / "metadata.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            metadata,
            f,
            indent=4,
        )

    print("\nDone")


if __name__ == "__main__":
    extract_figures()