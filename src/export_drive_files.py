"""
Export Google Drive files to various formats
"""

import os
import tempfile
from pathlib import Path
from google_drive_connector import GoogleDriveConnector
import pytesseract
from pdf2image import convert_from_path
from PIL import Image


def sanitize_filename(filename: str) -> str:
    """Remove or replace characters that are invalid in filenames."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename


def process_presentation_with_ocr(file_id: str, file_name: str, output_dir: str, connector) -> None:
    """
    Export Google Slides as PDF, convert to images, and extract text using OCR.

    Args:
        file_id: Google Drive file ID
        file_name: Name of the file
        output_dir: Directory to save outputs
        connector: GoogleDriveConnector instance
    """
    safe_name = sanitize_filename(file_name)

    # Step 1: Export as PDF to temporary file
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
        pdf_path = tmp_pdf.name

    connector.export_google_doc(
        file_id=file_id,
        output_path=pdf_path,
        export_format='application/pdf'
    )
    print(f"  Exported to temporary PDF")

    # Step 2: Convert PDF to images
    print(f"  Converting PDF to images...")
    images = convert_from_path(pdf_path, dpi=300)
    print(f"  Found {len(images)} slides")

    # Step 3: Extract text using OCR (without saving images)
    all_text = []
    for i, image in enumerate(images, 1):
        print(f"  Processing slide {i}/{len(images)}...")
        # Extract text using OCR
        text = pytesseract.image_to_string(image)
        all_text.append(f"=== Slide {i} ===\n{text}\n")

    # Step 4: Save all extracted text to a single file
    ocr_text_path = os.path.join(output_dir, f"{safe_name}.txt")
    with open(ocr_text_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_text))

    # Clean up temporary PDF
    os.unlink(pdf_path)

    print(f"✓ OCR text extracted: {ocr_text_path}")


def export_all_files(output_dir: str = "g-drive-docs"):
    """
    Export all files from Google Drive to appropriate formats.
    Organizes files by type into subdirectories.

    Args:
        output_dir: Directory to save exported files
    """
    # Create output directory and subdirectories if they don't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Create subdirectories for different file types
    docs_dir = os.path.join(output_dir, "docs")
    presentations_dir = os.path.join(output_dir, "presentations")
    spreadsheets_dir = os.path.join(output_dir, "spreadsheets")
    other_dir = os.path.join(output_dir, "other")

    Path(docs_dir).mkdir(parents=True, exist_ok=True)
    Path(presentations_dir).mkdir(parents=True, exist_ok=True)
    Path(spreadsheets_dir).mkdir(parents=True, exist_ok=True)
    Path(other_dir).mkdir(parents=True, exist_ok=True)

    # Initialize connector
    connector = GoogleDriveConnector()

    # Get folder ID from environment
    folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')

    print(f"Fetching files from Google Drive...")
    files = connector.list_files_in_folder(folder_id=folder_id, recursive=True)

    print(f"\nFound {len(files)} files. Starting export...\n")
    print("=" * 80)

    for i, file in enumerate(files, 1):
        file_name = file['name']
        file_id = file['id']
        mime_type = file['mimeType']
        safe_name = sanitize_filename(file_name)

        print(f"\n[{i}/{len(files)}] Processing: {file_name}")
        print(f"Type: {mime_type}")

        try:
            # Google Docs → plaintext only
            if mime_type == 'application/vnd.google-apps.document':
                txt_path = os.path.join(docs_dir, f"{safe_name}.txt")
                connector.export_google_doc(
                    file_id=file_id,
                    output_path=txt_path,
                    export_format='text/plain'
                )
                print(f"✓ Exported TXT: {txt_path}")

            # Google Sheets → CSV
            elif mime_type == 'application/vnd.google-apps.spreadsheet':
                csv_path = os.path.join(spreadsheets_dir, f"{safe_name}.csv")
                connector.export_google_doc(
                    file_id=file_id,
                    output_path=csv_path,
                    export_format='text/csv'
                )
                print(f"✓ Exported CSV: {csv_path}")

            # Google Slides → PDF + Images + OCR
            elif mime_type == 'application/vnd.google-apps.presentation':
                process_presentation_with_ocr(
                    file_id=file_id,
                    file_name=file_name,
                    output_dir=presentations_dir,
                    connector=connector
                )

            # Regular files (PDF, DOCX, etc.) → Download directly
            elif mime_type.startswith('application/'):
                # Get file extension from mime type or use original name
                extension = ''
                if mime_type == 'application/pdf':
                    extension = '.pdf'
                elif 'wordprocessingml.document' in mime_type:
                    extension = '.docx'
                elif 'spreadsheetml.sheet' in mime_type:
                    extension = '.xlsx'
                elif 'presentationml.presentation' in mime_type:
                    extension = '.pptx'
                else:
                    # Try to preserve original extension
                    if '.' in file_name:
                        extension = '.' + file_name.split('.')[-1]

                file_path = os.path.join(other_dir, f"{safe_name}{extension}")
                connector.download_file(file_id=file_id, output_path=file_path)
                print(f"✓ Downloaded: {file_path}")

            else:
                print(f"⊘ Skipping (unsupported type): {mime_type}")

        except Exception as e:
            print(f"✗ Error exporting {file_name}: {e}")

    print("\n" + "=" * 80)
    print(f"\nExport complete! Files saved to: {output_dir}/")


if __name__ == "__main__":
    export_all_files()
