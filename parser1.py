import pandas as pd

# Read all columns as strings to preserve original formatting
df = pd.read_csv('merged_books.csv', encoding='latin-1', dtype=str)

# Fill NaN values with empty strings
df = df.fillna('')

# Remove .0 from any numeric-looking strings
for col in df.columns:
    df[col] = df[col].astype(str).str.replace(r'\.0$', '', regex=True)

df.to_csv('books_zotero.csv', index=False, encoding='utf-8')
print("✓ Fixed .0 issue - all columns treated as strings")