bing_api_key = "your_key_here"

############## DEVELOPER DEBUG ##############
"""Leave this flag set to False unless you are a developer and need to see the ouput of all functions for debugging purposes. This will produce a LOT of files.

If debugging multiple Bundles, specify a subdirectory i.e. './debug/BundleName' to keep one bundle's files from overwriting previous ones (some filenames will be identical between bundles)."""
debug_directory = './debug/BundleName' # '.' = current directory
debug_flag = False # True or False

############## CUSTOM EXCEPTION ##############
class EmptyDictionaryError(Exception):
    """Raised when the books_data dictionary is empty. This suggests the web scraping has totally failed, which is likely due to an incorrect URL or an incompatible Humble Bunde webpage structure relative to this script."""
    pass