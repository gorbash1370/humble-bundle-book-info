bing_api_key = "your_key_here"

############## CUSTOM EXCEPTIONS ##############
class EmptyDictionaryError(Exception):
    """
    Exception raised when the books_data dictionary is empty.
    
    Typically indicates that web scraping failed, possibly due to an incorrect URL or an incompatible Humble Bundle webpage structure.
    
    Check the URL and the expected HTML structure relative to the HTML fields parsed for Publisher, Title, Author(s), Blurb.
    """
    pass

class MismatchError(Exception):
    """
    Exception raised when the counts of titles, authors, and blurbs parsed from the Humble Bundle HTML content do not match.
    
    This mismatch prevents the creation of a coherent books_data dictionar. Script termination is enacted to avoid erroneous API calls or misleading txt file content
    
    Ensure the webpage structure is compatible with the HTML parsing logic.
    """
    pass