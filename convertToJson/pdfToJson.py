import os
import json
import pdfplumber
from pathlib import Path
from typing import Dict, Any
from datetime import datetime


class PDFToJSONConverter:
    def __init__(self, base_download_path: str = None, output_folder: str = "json_output"):
        """Initialize converter with folder paths"""
        # Default to user's Downloads directory
        self.upload_folder = r"D:\Users\BikiKumarSah\Downloads\Python_begin\HealthGenA\Backend\convertToJson\downloads"
        self.output_folder = output_folder

        # Your folder names in Downloads
        self.classifications = ["treatment", "diagnosis", "clinical_trial"]

        # Ensure output folder exists
        os.makedirs(output_folder, exist_ok=True)

    def extract_pdf_to_json(self, pdf_path: str, classification: str) -> Dict[str, Any]:
        """Extract text and tables from PDF, excluding images"""
        filename = os.path.basename(pdf_path)

        document = {
            "file_name": filename,
            "classification": classification,
            "sections": []  # following your requested format
        }

        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)

            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if not text:
                    continue

                # Extract tables
                tables_data = []
                tables = page.extract_tables()
                for table in tables:
                    if table and len(table) > 1:
                        columns = table[0]
                        rows = table[1:]
                        tables_data.append({
                            "columns": columns,
                            "rows": rows
                        })

                # Use a basic section structure (can be improved with NLP)
                section = {
                    "id": f"{Path(filename).stem}_{classification}_{page_num}",
                    "title": f"Section {page_num}",
                    "summary": text[:200].replace("\n", " ") + "...",  # simple summary (first 200 chars)
                    "key_terms": [],
                    "content": text.strip(),
                    "tables": tables_data,
                    "page_range": [page_num, page_num]
                }

                document["sections"].append(section)

        return document

    def process_single_pdf(self, pdf_path: str, classification: str) -> str:
        """Process a single PDF and save as JSON"""
        try:
            print(f"Processing: {os.path.basename(pdf_path)}")

            json_data = self.extract_pdf_to_json(pdf_path, classification)

            pdf_name = Path(pdf_path).stem
            json_filename = f"{classification}_{pdf_name}.json"
            json_path = os.path.join(self.output_folder, json_filename)

            # Save JSON
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)

            print(f"✓ Saved: {json_filename}")
            return json_path

        except Exception as e:
            print(f"✗ Error processing {os.path.basename(pdf_path)}: {e}")
            return None

    def process_all_pdfs(self):
        """Process all PDFs in classification folders"""
        stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "by_classification": {}
        }

        for classification in self.classifications:
            folder_path = os.path.join(self.upload_folder, classification)

            if not os.path.exists(folder_path):
                print(f"⚠️  Warning: Folder '{folder_path}' does not exist. Skipping...")
                continue

            pdf_files = list(Path(folder_path).glob("*.pdf"))
            print(f"\n{'=' * 60}")
            print(f"Processing {classification.upper()} folder: {len(pdf_files)} PDFs found")
            print(f"{'=' * 60}")

            classification_stats = {"total": len(pdf_files), "successful": 0, "failed": 0}

            for pdf_file in pdf_files:
                stats["total_processed"] += 1
                result = self.process_single_pdf(str(pdf_file), classification)

                if result:
                    stats["successful"] += 1
                    classification_stats["successful"] += 1
                else:
                    stats["failed"] += 1
                    classification_stats["failed"] += 1

            stats["by_classification"][classification] = classification_stats

        print(f"\n{'=' * 60}")
        print("CONVERSION SUMMARY")
        print(f"{'=' * 60}")
        print(f"Total PDFs processed: {stats['total_processed']}")
        print(f"Successful: {stats['successful']}")
        print(f"Failed: {stats['failed']}\n")

        for classification, cls_stats in stats["by_classification"].items():
            print(f"{classification}: {cls_stats['successful']}/{cls_stats['total']} successful")

        print(f"\nJSON files saved to: {self.output_folder}")
        print(f"{'=' * 60}")

        return stats


# ✅ Usage Example
if __name__ == "__main__":
    converter = PDFToJSONConverter(output_folder="json_output")

    # Process all PDFs in Downloads/{treatment, diagnosis, clinical_trail}
    converter.process_all_pdfs()
