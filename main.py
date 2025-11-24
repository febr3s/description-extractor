import requests

# STEP 1: Define what we're looking for
book_title = "Introducing electronic text analysis"

# STEP 2: Make the request to Google Books
response = requests.get(
    "https://www.googleapis.com/books/v1/volumes",
    params={'q': book_title}  # 'q' stands for 'query'
)

# STEP 3: Convert the response from JSON to Python data types
data = response.json()

# STEP 4: Navigate through the data structure to find our description
# Check if we got any results first
if 'items' in data and len(data['items']) > 0:
    # Get the first search result (most relevant)
    first_result = data['items'][0]
    
    # Get the book's basic info
    book_info = first_result['volumeInfo']
    
    # STEP 5: Extract what we want
    book_id = first_result['id']
    description = book_info.get('description', 'No description available')
    
    # STEP 6: Display the results
    print(f"Book ID: {book_id}")
    print(f"Description: {description}")
else:
    print("No books found with that title.")