"""Procedural meter body around an unwarped LCD crop. No photos/assets.

The returned offset is the ONLY geometric change. Caller translates all label
planes/points before applying its existing camera homography to the whole device.
These are randomized generic bodies, not measured replicas of real devices.
"""
import cv2
import numpy as np


def rounded_rect(canvas, box, radius, color):
    x0, y0, x1, y1 = map(int, box)
    r = max(1, min(int(radius), (x1-x0)//2, (y1-y0)//2))
    cv2.rectangle(canvas, (x0+r, y0), (x1-r, y1), color, -1)
    cv2.rectangle(canvas, (x0, y0+r), (x1, y1-r), color, -1)
    for x in (x0+r, x1-r):
        for y in (y0+r, y1-r):
            cv2.circle(canvas, (x, y), r, color, -1)


def compose(panel, coverage, glyph, rng, body_tone, background):
    h, w = panel.shape
    wide = w > 1.5*h
    left = int(w*rng.uniform(.10, .25))
    right = int(w*rng.uniform(.10, .25))
    top = int(h*rng.uniform(.15, .40))
    bottom = int(h*rng.uniform(.50, 1.10))
    if wide:
        # Tube-like meters place controls beside the LCD instead of below it.
        right += int(w*rng.uniform(.22, .45))
        bottom = int(h*rng.uniform(.15, .40))
    H, W = h+top+bottom, w+left+right
    mask = np.zeros((H, W), np.uint8)
    border = max(3, int(min(W, H)*.02))
    rounded_rect(mask, (border, border, W-border-1, H-border-1),
                 min(left, right, top)*rng.uniform(.8, 1.5), 255)
    # The inserted panel must never be hidden by a rounded corner.
    mask[top:top+h, left:left+w] = 255
    tone = np.linspace(-20, 20, H, dtype=np.float32)[:, None] + body_tone
    body = np.broadcast_to(np.clip(tone, 0, 255).astype(np.uint8), (H, W)).copy()
    out = np.where(mask > 0, body, background).astype(np.uint8)
    # Edge highlight and shadow give buttons/body edges competing structure.
    cv2.rectangle(out, (border+2, border+2), (W-border-3, H-border-3),
                  int(np.clip(body_tone+35, 0, 255)), 2)
    if wide:
        region = (left+w+border, top, W-2*border, top+h)
    else:
        region = (left, top+h+border, left+w, H-2*border)
    x0, y0, x1, y1 = region
    # Button count/appearance are not tied to the LCD profile or digit value.
    count = rng.randint(1, 3)
    for i in range(count):
        if wide:
            cx, cy = (x0+x1)//2, int(y0+(i+.5)*(y1-y0)/count)
            rx, ry = int((x1-x0)*.32), int((y1-y0)/count*.30)
        else:
            cx, cy = int(x0+(i+.5)*(x1-x0)/count), (y0+y1)//2
            rx, ry = int((x1-x0)/count*.30), int((y1-y0)*.28)
        rx, ry = max(5, rx), max(5, min(ry, rx))
        tone = rng.randint(25, 230)
        cv2.ellipse(out, (cx+2, cy+3), (rx, ry), 0, 0, 360, max(0, tone-40), -1)
        if rng.random() < .5:
            cv2.ellipse(out, (cx, cy), (rx, ry), 0, 0, 360, tone, -1)
        else:
            rounded_rect(out, (cx-rx, cy-ry, cx+rx, cy+ry), ry*.35, tone)
        symbol = rng.choice(["M", "S", "<", ">", "+", "-"])
        scale = max(.35, min(rx, ry)/22)
        (tw, th), _ = cv2.getTextSize(symbol, cv2.FONT_HERSHEY_SIMPLEX, scale, 2)
        cv2.putText(out, symbol, (cx-tw//2, cy+th//2), cv2.FONT_HERSHEY_SIMPLEX,
                    scale, 235 if tone < 110 else 30, 2, cv2.LINE_AA)
    if rng.random() < .7:
        text = rng.choice(["GLUCO", "METER", "CARE", "CHECK", "SCAN"])
        scale = max(.4, min(w/230, top/45))
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 2)
        cv2.putText(out, text, ((W-tw)//2, max(th+border, top//2)),
                    cv2.FONT_HERSHEY_SIMPLEX, scale,
                    230 if body_tone < 110 else 35, 2, cv2.LINE_AA)
    # Blend only the original panel's coverage, not its old outside background.
    alpha = coverage.astype(np.float32)/255
    patch = out[top:top+h, left:left+w]
    patch[:] = np.clip(panel*alpha + patch*(1-alpha), 0, 255).astype(np.uint8)
    glyph_out = np.zeros_like(out)
    glyph_out[top:top+h, left:left+w] = glyph
    out[mask == 0] = background
    return out, mask, glyph_out, (left, top)
