"""
档案图像预处理管线

处理目标：
- 泛黄纸张增强对比度
- 去噪（扫描底纹、椒盐噪声）
- 倾斜校正
- 自适应二值化
- 可选超分辨率（低分辨率模糊名册）

用法:
  python train/ocr/preprocess.py --input data/raw/ --output data/processed/
"""

import argparse
import os
import sys
from pathlib import Path

try:
    import cv2
    import numpy as np
except ImportError:
    print("请安装 opencv-python: pip install opencv-python numpy")
    sys.exit(1)


def preprocess_archive(
    img_path: str,
    do_denoise: bool = True,
    do_clahe: bool = True,
    do_deskew: bool = True,
    do_binarize: bool = True,
    target_dpi: int = 300,
) -> np.ndarray:
    """完整的档案图像预处理"""
    img = cv2.imread(img_path)
    if img is None:
        raise ValueError(f"无法读取图像: {img_path}")

    # 1. 灰度化
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    # 2. 去噪 — 针对档案扫描的底纹噪声
    if do_denoise:
        gray = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)

    # 3. CLAHE 自适应对比度增强 — 解决泛黄/褪色
    if do_clahe:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

    # 4. 倾斜校正
    if do_deskew:
        gray = _deskew(gray)

    # 5. 自适应二值化
    if do_binarize:
        gray = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2,
        )

    return gray


def _deskew(gray: np.ndarray) -> np.ndarray:
    """基于文本行的倾斜校正"""
    # 二值化
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # 找所有非零像素坐标
    coords = np.column_stack(np.where(binary > 0))
    if len(coords) < 100:
        return gray  # 太少的像素，跳过

    # 最小外接矩形 → 角度
    rect = cv2.minAreaRect(coords.astype(np.float32))
    angle = rect[-1]

    # 调整角度范围
    if angle < -45:
        angle = 90 + angle
    if abs(angle) < 0.3:
        return gray  # 角度太小，不校正

    h, w = gray.shape
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(gray, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    return rotated


def batch_preprocess(
    input_dir: str,
    output_dir: str,
    extensions: tuple = (".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"),
) -> int:
    """批量预处理"""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    count = 0
    image_files = [f for f in input_path.rglob("*") if f.suffix.lower() in extensions]

    print(f"📂 找到 {len(image_files)} 个图像文件")

    for img_file in image_files:
        try:
            processed = preprocess_archive(str(img_file))

            # 保持相对路径结构
            rel_path = img_file.relative_to(input_path)
            out_file = output_path / rel_path.with_suffix(".png")
            out_file.parent.mkdir(parents=True, exist_ok=True)

            cv2.imwrite(str(out_file), processed)
            count += 1

            if count % 50 == 0:
                print(f"  ⏳ 已处理 {count}/{len(image_files)}")

        except Exception as e:
            print(f"  ❌ {img_file.name}: {e}")

    print(f"✅ 完成: {count} 个文件 → {output_dir}")
    return count


def main():
    parser = argparse.ArgumentParser(description="档案图像预处理")
    parser.add_argument("--input", "-i", required=True, help="原始图像目录")
    parser.add_argument("--output", "-o", required=True, help="输出目录")
    parser.add_argument("--no-denoise", action="store_true")
    parser.add_argument("--no-clahe", action="store_true")
    parser.add_argument("--no-deskew", action="store_true")
    parser.add_argument("--no-binarize", action="store_true")

    args = parser.parse_args()

    # 单文件演示模式
    input_path = Path(args.input)
    if input_path.is_file():
        out_file = Path(args.output) / f"processed_{input_path.name}"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        processed = preprocess_archive(
            str(input_path),
            do_denoise=not args.no_denoise,
            do_clahe=not args.no_clahe,
            do_deskew=not args.no_deskew,
            do_binarize=not args.no_binarize,
        )
        cv2.imwrite(str(out_file), processed)
        print(f"✅ 单文件处理完成: {out_file}")
        print(f"   原始/处理后: {input_path} → {out_file}")
        return

    batch_preprocess(args.input, args.output)


if __name__ == "__main__":
    main()
