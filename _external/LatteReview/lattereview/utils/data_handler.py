import pandas as pd
import re
import asyncio
import os
from typing import Optional, Dict, List, Any


async def ris_to_dataframe(input_file: str, output_csv: Optional[str] = None) -> pd.DataFrame:
    """
    Convert a RIS file to a pandas DataFrame with each article as a separate row
    and their fields as columns.

    Parameters:
    -----------
    input_file : str
        Path to the RIS file to convert
    output_csv : Optional[str], default=None
        Path to save the resulting DataFrame as a CSV file. If None, the DataFrame is not saved.

    Returns:
    --------
    pd.DataFrame
        DataFrame containing the parsed RIS data with one row per article
    """
    # Define field mappings (RIS tags to readable column names)
    field_mapping = {
        "TY": "type",
        "AU": "authors",
        "TI": "title",
        "AB": "abstract",
        "PY": "year",
        "DA": "date",
        "JO": "journal",
        "JA": "journal_abbrev",
        "VL": "volume",
        "IS": "issue",
        "SP": "start_page",
        "EP": "end_page",
        "DO": "doi",
        "UR": "url",
        "KW": "keywords",
        "N1": "notes",
        "N2": "abstract_note",
        "PB": "publisher",
        "CY": "city",
        "AD": "author_address",
        "SN": "issn",
        "L1": "file_attachments",
        "L2": "file_url",
        # Add more mappings as needed
    }

    # Asynchronously read the file
    async def read_file(file_path: str) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: open(file_path, "r", encoding="utf-8").read())

    # Parse RIS content into list of articles
    async def parse_ris_content(content: str) -> List[Dict[str, Any]]:
        # Split the content by record separator
        # The standard RIS format uses "ER  - " to indicate end of reference
        # and each reference typically starts with "TY  - "
        references = []
        current_ref = []

        for line in content.split("\n"):
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Check if this is the start of a new reference
            if line.startswith("TY  - ") and current_ref:
                # Save the previous reference
                references.append("\n".join(current_ref))
                current_ref = [line]
            # Check if this is the end of the current reference
            elif line == "ER  - ":
                current_ref.append(line)
                references.append("\n".join(current_ref))
                current_ref = []
            else:
                current_ref.append(line)

        # Add the last reference if it exists and wasn't terminated with ER
        if current_ref:
            references.append("\n".join(current_ref))

        all_articles = []
        for ref_text in references:
            if not ref_text.strip():
                continue

            article = {}
            current_tag = None

            for line in ref_text.split("\n"):
                line = line.strip()
                if not line:
                    continue

                # Check if this line starts a new field (standard RIS format is "XX  - value")
                if re.match(r"^[A-Z][A-Z0-9]\s\s-\s", line):
                    parts = line.split("  - ", 1)  # Split on the RIS delimiter
                    if len(parts) == 2:
                        tag, value = parts
                        current_tag = tag

                        # Initialize the field if it doesn't exist
                        if tag not in article:
                            article[tag] = []

                        # Add value if not empty
                        if value.strip():
                            article[tag].append(value.strip())
                elif current_tag:  # This is a continuation line
                    # Some RIS files have continuation lines with or without indentation
                    if article.get(current_tag):
                        article[current_tag][-1] += f" {line.strip()}"
                    else:
                        article[current_tag] = [line.strip()]

            # Skip empty articles or those without a type
            if not article or "TY" not in article:
                continue

            # Convert to readable format using the mapping
            formatted_article = {}
            for tag, values in article.items():
                column_name = field_mapping.get(tag, tag)
                if len(values) == 1:
                    formatted_article[column_name] = values[0]
                else:
                    formatted_article[column_name] = "; ".join(values)

            all_articles.append(formatted_article)

        return all_articles

    # Main execution
    try:
        # Verify the file exists
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"The file {input_file} does not exist")

        # Read the file content
        file_content = await read_file(input_file)

        # Parse the content
        articles = await parse_ris_content(file_content)

        if not articles:
            print("Warning: No articles were found in the RIS file")
            return pd.DataFrame()

        # Create DataFrame
        df = pd.DataFrame(articles)

        # Save to CSV if output path is provided
        if output_csv:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: df.to_csv(output_csv, index=False, encoding="utf-8-sig")
            )
            print(f"Data saved to {output_csv}")

        return df

    except Exception as e:
        print(f"Error processing RIS file: {e}")
        raise


# Example usage
async def main():
    # Replace with your actual file path
    ris_file = "test.ris"
    output_file = "test.csv"

    try:
        df = await ris_to_dataframe(ris_file, output_file)
        print(f"Successfully processed {len(df)} articles")
        print(df.head())
    except Exception as e:
        print(f"Failed to process file: {e}")


if __name__ == "__main__":
    asyncio.run(main())
