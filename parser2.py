import csv
import io

def convert_to_zotero_format(input_csv_content):
    # Create a string buffer for output
    output = io.StringIO()
    
    # Write UTF-8 BOM
    output.write('\ufeff')
    
    # Create CSV writer with exact zotero format settings
    writer = csv.writer(output, 
                       quoting=csv.QUOTE_ALL,  # Quote all fields
                       lineterminator='\n')    # Use \n as line terminator
    
    # Read the input CSV
    reader = csv.reader(io.StringIO(input_csv_content))
    rows = list(reader)
    
    # Write all rows with quoting
    writer.writerows(rows)
    
    return output.getvalue()

# Example usage:
if __name__ == "__main__":
    # Read your current_format.csv file
    with open('books_zotero.csv', 'r', encoding='utf-8') as f:
        current_content = f.read()
    
    # Convert to zotero format
    zotero_formatted_content = convert_to_zotero_format(current_content)
    
    # Write to output file
    with open('current_format_zotero.csv', 'w', encoding='utf-8') as f:
        f.write(zotero_formatted_content)
    
    print("Conversion completed! File saved as 'current_format_zotero.csv'")