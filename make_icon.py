"""
NEXUS 앱 아이콘 생성
1024×1024 PNG → macOS .icns + Windows .ico
"""
import math, os, struct, zlib
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent / "assets"
OUT.mkdir(exist_ok=True)

# ── 색상 ──────────────────────────────────────
BG      = (9,   9,  11, 255)   # #09090b
SURFACE = (23,  23, 27, 255)   # #17171b
ACCENT  = (79, 142, 247, 255)  # #4f8ef7
ACCENT2 = (59, 111, 212, 255)  # #3b6fd4
WHITE   = (240, 240, 248, 255) # #f0f0f8
RING    = (79, 142, 247, 180)  # 반투명 링

SIZE = 1024

def rounded_rect_mask(draw, xy, radius, fill):
    x0, y0, x1, y1 = xy
    r = radius
    draw.rectangle([x0+r, y0,   x1-r, y1],   fill=fill)
    draw.rectangle([x0,   y0+r, x1,   y1-r], fill=fill)
    draw.ellipse(  [x0,   y0,   x0+r*2, y0+r*2], fill=fill)
    draw.ellipse(  [x1-r*2, y0, x1,     y0+r*2], fill=fill)
    draw.ellipse(  [x0,   y1-r*2, x0+r*2, y1],   fill=fill)
    draw.ellipse(  [x1-r*2, y1-r*2, x1,   y1],   fill=fill)

def make_icon(size: int) -> Image.Image:
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad  = int(size * 0.04)
    r    = int(size * 0.22)      # 모서리 반지름

    # ── 배경 둥근 사각형 ──
    rounded_rect_mask(draw, (pad, pad, size-pad, size-pad), r, BG)

    # ── 미묘한 내부 광택 (surface) ──
    inner_pad = int(size * 0.055)
    inner_r   = int(size * 0.19)
    rounded_rect_mask(draw,
        (inner_pad, inner_pad, size-inner_pad, int(size*0.52)),
        inner_r, SURFACE)

    # ── 외곽 테두리 링 (accent 색상) ──
    border_w = max(3, size // 90)
    rounded_rect_mask(draw, (pad, pad, size-pad, size-pad), r, (0,0,0,0))
    for d in range(border_w):
        p = pad + d
        draw.rounded_rectangle([p, p, size-p, size-p],
                                radius=r - d,
                                outline=(*ACCENT[:3], 80), width=1)

    # ── 장식 원형 링 (왼쪽 상단, 앱 로고 모티프) ──
    cx, cy = int(size * 0.18), int(size * 0.18)
    ring_r  = int(size * 0.08)
    ring_w  = max(2, size // 160)
    draw.ellipse([cx-ring_r, cy-ring_r, cx+ring_r, cy+ring_r],
                 outline=(*ACCENT[:3], 160), width=ring_w)
    # 작은 점 (orbit)
    dot_r = max(2, size // 200)
    draw.ellipse([cx+ring_r-dot_r, cy-dot_r,
                  cx+ring_r+dot_r, cy+dot_r],
                 fill=ACCENT)

    # ── "N" 글자 ──
    font_size = int(size * 0.52)
    try:
        # 시스템 볼드 폰트 순서대로 시도
        for fname in [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/SFNSDisplay.ttf",
            "/System/Library/Fonts/SFNSText.ttf",
            "/Library/Fonts/Arial Bold.ttf",
        ]:
            if Path(fname).exists():
                font = ImageFont.truetype(fname, font_size)
                break
        else:
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    # 텍스트 중앙 정렬
    bbox  = draw.textbbox((0, 0), "N", font=font)
    tw    = bbox[2] - bbox[0]
    th    = bbox[3] - bbox[1]
    tx    = (size - tw) // 2 - bbox[0]
    ty    = (size - th) // 2 - bbox[1] + int(size * 0.03)

    # 블루 글로우 (뒤에 살짝)
    for spread in range(int(size*0.025), 0, -2):
        alpha = int(40 * (1 - spread/(size*0.025)))
        draw.text((tx, ty), "N", font=font,
                  fill=(*ACCENT[:3], alpha))

    # 메인 텍스트 (흰색)
    draw.text((tx, ty), "N", font=font, fill=WHITE)

    # ── 하단 accent 라인 ──
    line_y  = int(size * 0.86)
    line_x0 = int(size * 0.22)
    line_x1 = int(size * 0.78)
    line_h  = max(3, size // 100)

    # 그라데이션 라인 (좌→우 accent→투명)
    for i in range(line_x0, line_x1):
        t     = (i - line_x0) / (line_x1 - line_x0)
        alpha = int(220 * math.sin(math.pi * t))
        draw.rectangle([i, line_y, i+1, line_y+line_h],
                       fill=(*ACCENT[:3], alpha))

    # ── 마스크 적용 (배경 밖 제거) ──
    mask = Image.new("L", (size, size), 0)
    md   = ImageDraw.Draw(mask)
    rounded_rect_mask(md, (pad, pad, size-pad, size-pad), r, 255)
    img.putalpha(mask)

    return img


# ── macOS .icns 생성 ──────────────────────────
ICNS_SIZES = {
    "ic07": 128,
    "ic08": 256,
    "ic09": 512,
    "ic10": 1024,
    "ic11": 32,
    "ic12": 64,
    "ic13": 16,
    "ic14": 32,
}

def write_icns(master: Image.Image, path: Path):
    chunks = []
    seen_sizes: set[int] = set()
    for tag, sz in ICNS_SIZES.items():
        if sz in seen_sizes:
            continue
        seen_sizes.add(sz)
        resized = master.resize((sz, sz), Image.LANCZOS)
        import io
        buf = io.BytesIO()
        resized.save(buf, format="PNG")
        png_data = buf.getvalue()
        tag_bytes = tag.encode("ascii")
        length    = 8 + len(png_data)
        chunks.append(tag_bytes + struct.pack(">I", length) + png_data)

    total = 8 + sum(len(c) for c in chunks)
    with open(path, "wb") as f:
        f.write(b"icns")
        f.write(struct.pack(">I", total))
        for c in chunks:
            f.write(c)
    print(f"  .icns 저장: {path}  ({path.stat().st_size//1024} KB)")


# ── Windows .ico 생성 ─────────────────────────
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]

def write_ico(master: Image.Image, path: Path):
    import io
    images = []
    for sz in ICO_SIZES:
        images.append(master.resize((sz, sz), Image.LANCZOS))

    # ICO 포맷: 헤더 + 디렉토리 + PNG 데이터 (256px은 PNG 임베드 허용)
    header  = struct.pack("<HHH", 0, 1, len(images))
    dir_size = 16 * len(images)
    offset   = 6 + dir_size

    png_bufs = []
    for img in images:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_bufs.append(buf.getvalue())

    directory = b""
    cur_offset = offset
    for img, data in zip(images, png_bufs):
        w = img.width  if img.width  < 256 else 0
        h = img.height if img.height < 256 else 0
        directory += struct.pack("<BBBBHHII",
            w, h, 0, 0, 1, 32, len(data), cur_offset)
        cur_offset += len(data)

    with open(path, "wb") as f:
        f.write(header)
        f.write(directory)
        for data in png_bufs:
            f.write(data)
    print(f"  .ico  저장: {path}  ({path.stat().st_size//1024} KB)")


# ── 실행 ──────────────────────────────────────
if __name__ == "__main__":
    print("NEXUS 아이콘 생성 중...")
    master = make_icon(SIZE)

    png_path  = OUT / "icon.png"
    icns_path = OUT / "icon.icns"
    ico_path  = OUT / "icon.ico"

    master.save(png_path, "PNG")
    print(f"  .png  저장: {png_path}")

    write_icns(master, icns_path)
    write_ico(master, ico_path)

    print("완료!")
