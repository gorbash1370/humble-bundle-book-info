bing_api_key = "your_key_here"

############## CUSTOM EXCEPTION ##############
class EmptyDictionaryError(Exception):
    """Raised when the books_data dictionary is empty. This suggests the web scraping has totally failed, which is likely due to an incorrect URL or an incompatible Humble Bunde webpage structure relative to this script."""
    pass