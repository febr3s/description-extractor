import csv
import requests
import time
import difflib
from typing import List, Dict, Optional

class BookDescriptionEnricher:
    def __init__(self, csv_file_path: str, output_file: str = None):
        self.csv_file_path = csv_file_path
        self.output_file = output_file or csv_file_path.replace('.csv', '_enriched.csv')
        self.rows = []
        self.fieldnames = []
    
    def read_csv(self) -> List[Dict]:
        """Read and parse the CSV file"""
        with open(self.csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            self.fieldnames = reader.fieldnames
            self.rows = list(reader)
        return self.rows
    
    def normalize_title(self, title: str) -> str:
        """Normalize title for comparison: lowercase, remove extra spaces, handle colons"""
        if not title:
            return ""
        # Remove everything after colon for comparison purposes
        base_title = title.split(':')[0].split(';')[0]
        # Normalize spaces and case
        return ' '.join(base_title.lower().split())
    
    def authors_match(self, authors1: List[str], authors2: List[str]) -> bool:
        """Check if author lists are similar (same primary author)"""
        if not authors1 or not authors2:
            return False
        
        # Compare first author (most important)
        primary1 = authors1[0].lower()
        primary2 = authors2[0].lower()
        
        # Simple check - if first author matches, consider it good enough
        return primary1 in primary2 or primary2 in primary1
    
    def search_google_books(self, title: str, author: str = None) -> List[Dict]:
        """Search Google Books API and return multiple results"""
        time.sleep(1)  # Basic rate limiting
        
        try:
            response = requests.get(
                "https://www.googleapis.com/books/v1/volumes",
                params={
                    'q': f"{title} {author}" if author else title,
                    'maxResults': 5,  # Get more results to cycle through
                    'langRestrict': 'en'  # Prefer English results
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get('items'):
                return []
            
            # Process all results
            results = []
            for item in data['items']:
                volume_info = item.get('volumeInfo', {})
                results.append({
                    'title': volume_info.get('title', ''),
                    'description': volume_info.get('description', ''),
                    'authors': volume_info.get('authors', []),
                    'year': volume_info.get('publishedDate', '')[:4] if volume_info.get('publishedDate') else '',
                    'publisher': volume_info.get('publisher', ''),
                    'pageCount': volume_info.get('pageCount', '')
                })
            
            return results
            
        except Exception as e:
            print(f"API error for '{title}': {e}")
            return []
    
    def should_auto_accept(self, original_title: str, original_author: str, 
                          match_title: str, match_authors: List[str]) -> bool:
        """Determine if we should auto-accept without prompting"""
        # Normalize titles for comparison
        norm_original = self.normalize_title(original_title)
        norm_match = self.normalize_title(match_title)
        
        # Case 1: Exact normalized match (handles colons)
        if norm_original == norm_match:
            return True
        
        # Case 2: Very similar titles AND matching authors
        if original_author and match_authors:
            similarity = difflib.SequenceMatcher(None, norm_original, norm_match).ratio()
            if similarity > 0.9 and self.authors_match([original_author], match_authors):
                return True
        
        return False
    
    def prompt_for_match(self, original_title: str, original_author: str, matches: List[Dict]) -> Optional[Dict]:
        """Prompt user to select from multiple matches, or skip"""
        for i, match in enumerate(matches, 1):
            print(f"\n--- Match {i}/{len(matches)} ---")
            print(f"Title: {match['title']}")
            if match['authors']:
                print(f"Authors: {', '.join(match['authors'])}")
            if match['year']:
                print(f"Year: {match['year']}")
            if match['publisher']:
                print(f"Publisher: {match['publisher']}")
            if match['pageCount']:
                print(f"Pages: {match['pageCount']}")
            
            # Show description preview
            if match['description']:
                preview = match['description'][:200] + "..." if len(match['description']) > 200 else match['description']
                print(f"Description: {preview}")
            
            while True:
                response = input("\nUse this description? [y]es / [n]ext / [s]kip: ").lower().strip()
                if response in ['y', 'yes']:
                    return match
                elif response in ['n', 'next']:
                    break  # Move to next match
                elif response in ['s', 'skip']:
                    return None
                else:
                    print("Please enter y, n, or s")
        
        # If we've gone through all matches and user didn't select any
        print("No more matches available")
        return None
    
    def process_books(self):
        """Main processing loop"""
        books = self.read_csv()
        if not books:
            print("No books found or error reading CSV")
            return
        
        updated_count = 0
        no_match_count = 0
        auto_accepted_count = 0
        
        print(f"Processing {len(books)} books...")
        
        for i, book in enumerate(books, 1):
            # Skip if Notes already has content
            if book.get('Notes', '').strip():
                continue
            
            title = book.get('Title', '').strip()
            author = book.get('Author', '').strip()
            original_year = book.get('Publication Year', '').strip()
            
            if not title:
                continue
            
            print(f"\n[{i}/{len(books)}] Processing: {title}")
            if author:
                print(f"  Author: {author}")
            if original_year:
                print(f"  Year: {original_year}")
            
            # Search Google Books - get multiple results
            matches = self.search_google_books(title, author)
            
            if not matches:
                print("  No results found")
                # ADDED: Add "no description available" message
                book['Notes'] = '<div class="comment">\n<p>This book needs an abstract or excerpt, and it doesn\'t have a Google Books description available to use. For a customized abstract or excerpt, add a note to the item in the \n<a href="github.com/{{github}}/{{BASE_URL}}">Zotero library</a></p>\n</div>'
                no_match_count += 1
                continue
            
            # Check first match for auto-accept
            first_match = matches[0]
            if self.should_auto_accept(title, author, first_match['title'], first_match['authors']):
                book['Notes'] = first_match['description']
                # ADDED: Add Google Books attribution
                book['Notes'] += '\n\n<div class="comment">\n<p>This description was automatically added from \n<a href="https://books.google.com/books?id=JK8VXK7QMNAC">Google Books</a>. \nFor a customized abstract or excerpt, add a note to the item in the \n<a href="github.com/{{github}}/{{BASE_URL}}">Zotero library</a></p>\n</div>'
                updated_count += 1
                auto_accepted_count += 1
                print(f"  ✓ Auto-added description (similar title + author match)")
                print(f"     Original: '{title}'")
                print(f"     Google:   '{first_match['title']}'")
            else:
                # Show all matches and let user choose
                print(f"\n  Found {len(matches)} potential matches:")
                selected_match = self.prompt_for_match(title, author, matches)
                
                if selected_match:
                    book['Notes'] = selected_match['description']
                    # ADDED: Add Google Books attribution
                    book['Notes'] += '\n\n<div class="comment">\n<p>This description was automatically added from \n<a href="https://books.google.com/books?id=JK8VXK7QMNAC">Google Books</a>. \nFor a customized abstract or excerpt, add a note to the item in the \n<a href="github.com/{{github}}/{{BASE_URL}}">Zotero library</a></p>\n</div>'
                    updated_count += 1
                    print("  ✓ Added description")
                else:
                    print("  ✗ Skipped book")
                    # ADDED: Add "no description available" message
                    book['Notes'] = '<div class="comment">\n<p>This book needs an abstract or excerpt, and it doesn\'t have a Google Books description available to use. For a customized abstract or excerpt, add a note to the item in the \n<a href="github.com/{{github}}/{{BASE_URL}}">Zotero library</a></p>\n</div>'
                    no_match_count += 1
            
            # Save progress after each book
            self.save_progress()
        
        # Final summary
        print(f"\n" + "="*50)
        print(f"PROCESSING COMPLETE")
        print(f"Books updated: {updated_count}")
        print(f"  - Auto-accepted: {auto_accepted_count}")
        print(f"  - Manual accept: {updated_count - auto_accepted_count}")
        print(f"No match/skipped: {no_match_count}")
        print(f"Output file: {self.output_file}")
    
    def save_progress(self):
        """Save current state to output CSV"""
        try:
            with open(self.output_file, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=self.fieldnames)
                writer.writeheader()
                writer.writerows(self.rows)
        except Exception as e:
            print(f"Error saving progress: {e}")

def main():
    """Main function to run the enrichment process"""
    # SET YOUR CSV FILE PATH HERE
    csv_file_path = "books.csv"  # ← Change this to your CSV file path
    
    enricher = BookDescriptionEnricher(csv_file_path)
    enricher.process_books()

if __name__ == "__main__":
    main()