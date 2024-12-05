import os
import typer
from typing import Optional
import fitz  # PyMuPDF
import re


def find_first_pdf_in_directory(directory: str = ".") -> Optional[str]:
    """
    Find the first PDF file in the given directory.

    Args:
        directory (str): Directory to search. Defaults to current directory.

    Returns:
        Optional[str]: Path to the first PDF found, or None if no PDF is found.
    """
    for filename in os.listdir(directory):
        if filename.lower().endswith(".pdf"):
            return os.path.join(directory, filename)
    return None


def extract_page_number(filename: str) -> int:
    """
    Extract the page number from a filename.

    Args:
        filename (str): Filename to extract page number from.

    Returns:
        int: Extracted page number.
    """
    match = re.search(r"_(\d+)\.pdf$", filename)
    return int(match.group(1)) if match else float("inf")


def split_double_spread_pdf(
    input_pdf_path: str,
    output_dir: Optional[str] = None,
    combine_output: bool = False,
) -> list[str]:
    """
    Split a PDF with double-spread pages into individual pages by cropping.

    Args:
        input_pdf_path (str): Path to the input PDF file
        output_dir (str, optional): Directory to save split pages.
                                    If None, uses the same directory as input PDF.
        combine_output (bool, optional): Combine output PDFs into a single file.
                                         Defaults to False.

    Returns:
        list: Paths of the generated PDF files
    """
    # Validate input file
    if not os.path.exists(input_pdf_path):
        raise FileNotFoundError(f"Input PDF file not found: {input_pdf_path}")

    # Determine output directory
    if output_dir is None:
        output_dir = os.path.dirname(input_pdf_path)
    os.makedirs(output_dir, exist_ok=True)

    # Get base filename without extension
    base_filename = os.path.splitext(os.path.basename(input_pdf_path))[0]

    # Open the input PDF
    pdf_document = fitz.open(input_pdf_path)

    # List to store paths of generated PDFs
    generated_pdfs: list[str] = []

    # Counter for sequential naming
    page_counter = 1

    # Process each page
    for page_num in range(len(pdf_document)):
        # Get the current page
        page = pdf_document[page_num]

        # Get page dimensions
        media_box = page.mediabox
        page_width = media_box.width
        page_height = media_box.height

        # Create two rectangular clips: left and right halves of the page
        left_clip = fitz.Rect(0, 0, page_width / 2, page_height)
        right_clip = fitz.Rect(page_width / 2, 0, page_width, page_height)

        # Create new documents for left and right pages
        left_page_doc = fitz.open()
        right_page_doc = fitz.open()

        # Create new pages with the same size as half the original page
        left_page = left_page_doc.new_page(width=page_width / 2, height=page_height)
        right_page = right_page_doc.new_page(width=page_width / 2, height=page_height)

        # Draw the left half of the page
        left_page.show_pdf_page(
            left_page.rect, page.parent, page.number, clip=left_clip
        )

        # Draw the right half of the page
        right_page.show_pdf_page(
            right_page.rect, page.parent, page.number, clip=right_clip
        )

        # Generate output filenames with sequential naming
        left_output_filename = os.path.join(
            output_dir, f"{base_filename}_{page_counter}.pdf"
        )
        right_output_filename = os.path.join(
            output_dir, f"{base_filename}_{page_counter + 1}.pdf"
        )
        page_counter += 2

        # Save the split pages
        left_page_doc.save(left_output_filename)
        right_page_doc.save(right_output_filename)

        # Add to generated PDFs list
        generated_pdfs.extend([left_output_filename, right_output_filename])

        # Close documents
        left_page_doc.close()
        right_page_doc.close()

    # Close the original PDF
    pdf_document.close()

    # If combine_output is True, merge all generated PDFs
    if combine_output:
        combined_pdf_path = os.path.join(output_dir, f"{base_filename}_combined.pdf")
        combined_document = fitz.open()

        # Sort PDFs by extracted page number
        for pdf_path in sorted(generated_pdfs, key=extract_page_number):
            pdf_to_merge = fitz.open(pdf_path)
            combined_document.insert_pdf(pdf_to_merge)
            pdf_to_merge.close()

        combined_document.save(combined_pdf_path, garbage=4, deflate=True)
        combined_document.close()

        generated_pdfs.append(combined_pdf_path)

    return generated_pdfs


def main(
    input_pdf: Optional[str] = typer.Option(
        None, "-i", "--input-pdf", help="Path to input PDF"
    ),
    output_dir: Optional[str] = typer.Option(
        None, "-o", "--output-dir", help="Output directory for split PDFs"
    ),
    combine: bool = typer.Option(
        True,
        "-c",
        "--combine/--no-combine",
        help="Combine output PDFs into a single file",
    ),
):
    """
    Split a PDF with double-spread pages into individual pages.

    If no input PDF is provided, the script will search for the first PDF in the current directory.
    If no output directory is provided, an 'out/' directory will be created in the current directory.
    """
    # If no input PDF is provided, find the first PDF in the current directory
    if input_pdf is None:
        found_pdf = find_first_pdf_in_directory()
        if found_pdf is None:
            typer.echo("No PDF found in the current directory.")
            raise typer.Abort()
    else:
        found_pdf = input_pdf

    # If no output directory is provided, create 'out/' in current directory
    final_output_dir = output_dir or os.path.join(os.getcwd(), "out")

    try:
        # Split the PDF
        split_files = split_double_spread_pdf(
            found_pdf,
            output_dir=final_output_dir,
            combine_output=combine,
        )

        # Print generated file paths
        typer.echo("Generated PDF files:")
        for file in split_files:
            typer.echo(file)

    except Exception as e:
        typer.echo(f"An error occurred: {e}")
        raise typer.Abort()


if __name__ == "__main__":
    typer.run(main)
