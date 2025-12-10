import os
import sys
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered

def pdf_to_markdown(pdf_path, output_dir="output_md"):
    """
    Converts a research paper PDF into clean Markdown with LaTeX math using the
    Marker v1.0+ API and saves accompanying image assets.

    Args:
        pdf_path (str): Path to the PDF file.
        output_dir (str): Directory where markdown and images will be saved.

    Returns:
        dict: Dictionary containing the extracted markdown text, metadata,
              markdown file path, image directory, and saved image paths.
    """
    if not os.path.exists(pdf_path):
        print(f"Error: File '{pdf_path}' not found.")
        return None

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print("Loading AI models (this may take a moment first time)...")
    
    # 1. Load models using the new create_model_dict function
    # You can force device='cpu' or 'cuda'/'mps' here if needed.
    model_dict = create_model_dict() 
    
    # 2. Initialize the converter class
    converter = PdfConverter(
        artifact_dict=model_dict
    )
    
    print(f"Converting {pdf_path}...")
    
    # 3. Run the conversion
    # The converter returns a 'rendered' object, not just text
    rendered = converter(pdf_path)
    
    # 4. Extract text and images from the rendered object
    # text_from_rendered returns (text, metadata, images)
    full_text, metadata, images = text_from_rendered(rendered)

    # Define output filenames
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_file = os.path.join(output_dir, f"{base_name}.md")

    # Save the Markdown
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(full_text)

    # Save extracted images
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    saved_image_paths = []
    
    for filename, image in images.items():
        image_save_path = os.path.join(images_dir, filename)
        image.save(image_save_path)
        saved_image_paths.append(image_save_path)

    print(f"Success! Markdown saved to: {output_file}")
    print(f"Extracted {len(images)} images to: {images_dir}")

    return {
        "markdown_text": full_text,
        "metadata": metadata,
        "markdown_path": output_file,
        "images_dir": images_dir,
        "image_paths": saved_image_paths
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pdf_to_md.py <path_to_paper.pdf>")
    else:
        pdf_to_markdown(sys.argv[1])
