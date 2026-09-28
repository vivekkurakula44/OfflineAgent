import pytesseract
from PIL import Image, ImageEnhance, ImageFilter


def extract_text_from_image(file_path: str) -> str:
    image = Image.open(file_path)

    # Convert to grayscale for better OCR accuracy
    image = image.convert("L")

    # Enhance contrast
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)

    # Apply sharpening filter
    image = image.filter(ImageFilter.SHARPEN)

    text = pytesseract.image_to_string(image, config="--psm 6")
    return text.strip()
