import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
import time
import os

BASE_URL = "https://books.toscrape.com/"


def get_all_book_urls(limit=20):
    """Navigates through pages to find book links with correct URL joining."""
    book_urls = []
    current_url = BASE_URL

    while current_url and len(book_urls) < limit:
        response = requests.get(current_url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all books on current page
        for link in soup.select('article.product_pod h3 a'):
            href = link.get('href')

            # FIXED URL LOGIC:
            # On the homepage, links look like "catalogue/book_name/index.html"
            # On subsequent pages, they might look different.
            # This logic ensures we always get a clean, absolute URL.
            if "catalogue/" in href:
                full_url = BASE_URL + href
            else:
                full_url = BASE_URL + "catalogue/" + href

            book_urls.append(full_url)
            if len(book_urls) >= limit: break

        # Find the 'Next' button
        next_btn = soup.select('.next a')
        if next_btn and len(book_urls) < limit:
            next_url = next_btn[0].get('href')
            # Handle next page URL correctly
            if "catalogue/" in next_url:
                current_url = BASE_URL + next_url
            else:
                current_url = BASE_URL + "catalogue/" + next_url
        else:
            current_url = None

    return book_urls


def save_book_to_pdf(url, folder="book_data"):
    """Scrapes a single book page and saves to PDF with error handling."""
    if not os.path.exists(folder): os.makedirs(folder)

    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.text, 'html.parser')

        # 1. Safer Title Extraction
        title_tag = soup.h1
        if not title_tag:
            print(f"Skipping {url}: Title not found")
            return
        title = title_tag.text.strip()

        # 2. Safer Description Extraction
        # Sometimes the structure varies, so we find the ID 'product_description'
        # which is right above the paragraph we need.
        desc_header = soup.find('div', id='product_description')
        if desc_header:
            # The actual description is the next sibling paragraph
            description = desc_header.find_next_sibling('p').text
        else:
            description = "No description available for this book."

        # Replace invalid filename characters
        clean_title = "".join([c for c in title if c.isalnum() or c == ' ']).rstrip()

        # 3. Create PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, title, ln=True)
        pdf.ln(5)  # Add a little space
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, description)

        pdf.output(f"{folder}/{clean_title}.pdf")
        print(f"Successfully saved: {clean_title}")

    except Exception as e:
        print(f"Error processing {url}: {e}")


# Main execution
if __name__ == "__main__":
    print("Starting Crawler...")
    links = get_all_book_urls(limit=10)  # Change limit to 1000 for full site
    for link in links:
        save_book_to_pdf(link)
        time.sleep(0.5)  # Be polite to the server!