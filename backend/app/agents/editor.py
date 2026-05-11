import os
import re
import uuid
from typing import List, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai
from ..config import settings

# System handwriting font lookup paths for macOS
SYSTEM_FONTS = [
    "/System/Library/Fonts/Supplemental/Chalkboard.ttc",
    "/System/Library/Fonts/Supplemental/Noteworthy.ttc",
    "/System/Library/Fonts/Supplemental/Comic Sans MS.ttf",
    "/System/Library/Fonts/Supplemental/MarkerFelt.ttc",
    "/Library/Fonts/Arial.ttf"  # Standard fallback
]

def load_handwriting_font(size: int = 32) -> ImageFont.FreeTypeFont:
    """Attempts to load a beautiful handwriting/chalkboard system font on macOS, with fallback."""
    for font_path in SYSTEM_FONTS:
        if os.path.exists(font_path):
            try:
                # Some .ttc files contain multiple fonts, index 0 is usually standard/regular
                return ImageFont.truetype(font_path, size, index=0)
            except Exception:
                try:
                    return ImageFont.truetype(font_path, size)
                except Exception:
                    continue
    return ImageFont.load_default()

def run_gemini_transliteration(raw_text: str, location: str) -> str:
    """
    Uses Gemini 1.5 Flash to rewrite raw stories into hyper-relatable, authentic colloquial Tanglish.
    Also handles automatic PII stripping and redaction of company/university names.
    """
    if not settings.GEMINI_API_KEY:
        # Fallback Mock transliterator for testing without API keys
        return mock_tanglish_transliteration(raw_text, location)

    genai.configure(api_key=settings.GEMINI_API_KEY)
    
    system_instruction = f"""
    You are 'Swayam-Editor', an elite social media content editor specializing in NRI (Non-Resident Indian) confessions.
    Your job is to rewrite raw confessions into natural, spoken "Tanglish" (a highly colloquial blend of English and Telugu).

    Target Audience: Telugu NRIs (Non-Resident Indians) in locations like the US (Dallas, New Jersey, Bay Area), UK, Australia.
    Target Tone Location: {location} (Incorporate regional context or slang related to this location if appropriate).

    CRITICAL RULES:
    1. LINGUISTIC AUTHENTICITY: Blend English and Telugu naturally, exactly how an MS student or IT techie would speak to their friends.
       - Use slang like: "bhayya", "mava", "frustrations", "onsite", "h1b active", "roommates gola", "pelli proposals", "daridram", "sankanaaki poyindi".
       - Example input: "My manager scolded me because I made a small mistake in the codebase."
       - Example rewrite: "Manager toh warning highly active aindi bhayya. Chinna error select chesa codebase lo, daanike full gola chesadu."
    2. ABSOLUTE ANONYMITY: Redact all specific company names, real names, and specific apartment numbers. Replace them with generic terms inside brackets.
       - e.g., 'Infosys' -> '[Service-Based Company]', 'Apple' -> '[FAANG Company]', 'Suresh' -> '[My Roommate]'.
    3. KEEP IT FIRST-PERSON: The text must feel like an authentic, personal diary confession.
    4. NO BULLET POINTS / NO INTROS: Return ONLY the rewritten story text. No explanations, no greeting.
    """

    try:
        model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=system_instruction)
        response = model.generate_content(raw_text)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API error, falling back to mock transliteration: {e}")
        return mock_tanglish_transliteration(raw_text, location)

def mock_tanglish_transliteration(raw_text: str, location: str) -> str:
    """Fallback generator to simulate Tanglish translation for offline testing."""
    # Redact common company patterns as a fallback safety
    redacted = re.sub(r'\b(Google|Apple|Microsoft|Amazon|Infosys|TCS|Wipro|Cognizant)\b', r'[\1 Company]', raw_text, flags=re.IGNORECASE)
    
    words = redacted.split()
    if len(words) < 5:
        return f"Dhadham entry ready mava! {redacted} #DallasNRI"
        
    # Inject funny Telugu/Tanglish phrases into the raw text
    header = f"Frustrations peak unnay bhayya in {location}...\n\n"
    body = " ".join(words[:15]) + " and then standard gola aindi. " + " ".join(words[15:35]) + "..."
    footer = "\n\nEnd lo em cheptham, life sankanaaki poyindi anthe."
    
    return header + body + footer

def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    """Wraps text into lines that do not exceed max_width."""
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = " ".join(current_line + [word])
        # Using bbox to measure text width
        left, top, right, bottom = font.getbbox(test_line)
        width = right - left
        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                # If a single word is too long for the page, force it
                lines.append(word)
    if current_line:
        lines.append(" ".join(current_line))
    return lines

def render_confession_slides(adapted_text: str, review_id: str) -> List[str]:
    """
    Renders the adapted confession text onto high-quality programmatic 1:1 square notebook pages.
    Supports multi-slide splitting if the text is too long for a single image.
    Saves generated slides to public/assets and returns a list of local file paths.
    """
    # Canvas properties for Instagram 1:1
    W, H = 1080, 1080
    
    # Margin settings
    margin_left = 120
    margin_right = 100
    margin_top = 140
    margin_bottom = 120
    max_text_width = W - margin_left - margin_right
    
    # Notebook lines vertical spacing
    line_spacing = 48
    max_lines_per_slide = (H - margin_top - margin_bottom) // line_spacing
    
    # Font setup
    font = load_handwriting_font(34)
    
    # Split text into paragraphs and wrap each
    paragraphs = adapted_text.split('\n')
    all_wrapped_lines = []
    for paragraph in paragraphs:
        if paragraph.strip() == "":
            all_wrapped_lines.append("")  # Empty line for paragraph break
        else:
            all_wrapped_lines.extend(wrap_text(paragraph, font, max_text_width))
            
    # Group wrapped lines into chunks for slides (Multi-page carousel support)
    slide_chunks = []
    current_chunk = []
    for line in all_wrapped_lines:
        current_chunk.append(line)
        if len(current_chunk) >= max_lines_per_slide:
            slide_chunks.append(current_chunk)
            current_chunk = []
    if current_chunk:
        slide_chunks.append(current_chunk)
        
    # Render each slide
    generated_paths = []
    total_slides = len(slide_chunks)
    
    for slide_idx, chunk in enumerate(slide_chunks):
        # 1. Create Ivory Notebook Canvas
        # Background color #FAF8F5 (Soft ivory linen texture look)
        img = Image.new("RGB", (W, H), "#FAF8F5")
        draw = ImageDraw.Draw(img)
        
        # 2. Draw ruled notebook lines
        # Blue notebook lines: #E1EAF2
        for y in range(margin_top, H - margin_bottom + 1, line_spacing):
            draw.line([(margin_left - 40, y), (W - 50, y)], fill="#E1EAF2", width=2)
            
        # 3. Draw Red Margin guide line
        # Red line: #F5C6C6
        draw.line([(margin_left - 30, 0), (margin_left - 30, H)], fill="#F5C6C6", width=3)
        
        # 4. Write text on the notebook lines
        current_y = margin_top - 38  # Adjust text slightly above the blue lines
        for line in chunk:
            if line:  # Skip drawing empty line spacers, just increment Y
                # Draw handwriting text with dark navy ink: #1E2530
                draw.text((margin_left, current_y), line, fill="#1E2530", font=font)
            current_y += line_spacing
            
        # 5. Add Page numbering if it is a multi-slide post
        if total_slides > 1:
            page_text = f"Slide {slide_idx + 1}/{total_slides}  -> swipe"
            # Draw tiny page indicator
            mini_font = load_handwriting_font(22)
            left, top, right, bottom = mini_font.getbbox(page_text)
            text_width = right - left
            draw.text((W - text_width - 80, H - 70), page_text, fill="#7A8B9E", font=mini_font)
            
        # 6. Save image to assets directory
        file_name = f"slide_{review_id}_{slide_idx + 1}.jpg"
        save_path = os.path.join(settings.ASSETS_DIR, file_name)
        img.save(save_path, "JPEG", quality=95)
        generated_paths.append(save_path)
        
    return generated_paths

def process_and_create_confession(raw_text: str, location: str, raw_story_id: str = None) -> Dict[str, Any]:
    """Full pipeline: rewrites text into Tanglish and renders images."""
    review_id = str(uuid.uuid4())
    
    # 1. Adapt text
    adapted_text = run_gemini_transliteration(raw_text, location)
    
    # 2. Render Graphic Slides
    graphic_paths = render_confession_slides(adapted_text, review_id)
    
    # 3. Generate captions (simulated in editor)
    caption_options = [
        f"Life gola in {location} 🤦‍♂️. What do you guys think? \n\n#nri #telugu #confessions #{location.lower()}",
        f"Just NRI frustrations bhayya... Tag that friend who relates! 👇\n\n#hyderabad #usatelugu #telugumemes",
        f"Prasad warning details strictly confidential. Read slides for full gossip! 🤫\n\n#telugunri #telugucomedy #btech"
    ]
    
    return {
        "id": review_id,
        "raw_story_id": raw_story_id,
        "adapted_text": adapted_text,
        "tone_location": location,
        "graphic_urls": graphic_paths,
        "caption_options": caption_options
    }

if __name__ == "__main__":
    # Standard testing script to verify image creation
    test_text = "I moved to Dallas for my MS. My roommates are very bad. They do not clean the house and eat my food from the fridge. I am feeling very lonely and depressed here."
    result = process_and_create_confession(test_text, "Dallas")
    print("Editor Pipeline complete! Generated assets:")
    for path in result["graphic_urls"]:
        print("-", path)
