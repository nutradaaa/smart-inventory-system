import pytesseract
from PIL import Image
import re

pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"

def extract_text_from_image(image_path):
    image = Image.open(image_path)
    custom_config = r"--psm 6"
    text = pytesseract.image_to_string(image, lang="eng", config=custom_config)
    return text

def find_date_in_text(text):
    patterns = [
        r"(\d{4})-(\d{2})-(\d{2})",
        r"(\d{2})/(\d{2})/(\d{4})",
        r"(\d{2})-(\d{2})-(\d{4})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            if len(groups[0]) == 4:
                year, month, day = groups
            else:
                day, month, year = groups
            return f"{year}-{month}-{day}"

    return None