############## HUMBLE BOOK BUNDLE INFO - FUNCTION CALLS ##############

from hb_book_info_utils import main, open_browser_tabs

from config import bing_api_key


############## MANUAL INPUTS ##############
""" Give the URL of the Humble Book Bundle you wish to target. """
url_hb = "https://www.humblebundle.com/books/electronics-and-design-for-entrepreneurs-make-books"

""" Choose the browser you want to use for the Selenium web scraping.
Options: 'Chrome', 'Firefox', 'Safari', 'Opera', 'Edge', 'Internet Explorer'
 """
selenium_browser = 'Firefox' # enter one of the options above (spelt correctly!)

""" Enter the folder where you want to save the output files. Enter a relative path like "." for the current directory, './my_folder' for a subfolder in the current directory, or an absolute path like "C:/Users/Me/Documents" for a specific location."""
output_directory = './HumbleBundleBooks' # '.' = current directory. 
# NB: If running in debug mode, change output_directory to './debug/BundleName' to keep debug outputs separate from standard ones).


############## DEVELOPER DEBUG ##############
"""Leave this flag set to False unless you are a developer and need to see the ouput of all functions for debugging purposes. This will produce a LOT of files.

If debugging multiple Bundles, specify a subdirectory i.e. './debug/BundleName' to keep one bundle's files from overwriting previous ones (some filenames will be identical between bundles)."""
debug_directory = './debug/makers' # '.' = current directory
debug_flag = False # True or False


############## FUNCTION CALLS ##############

""" Run the main function to execute all processes and produce a text file (or two!) summarising the Bundles' books' details. 

Choose which text file version to generate (see README.md for a snapshot): "short", "verbose", or "both". Invalid selections will default to verbose.
"""
txt_file_version = "both" # "short" or "verbose" or "both"

books_data = main(output_directory, url_hb, selenium_browser, bing_api_key, txt_file_version, debug_flag, debug_directory)


############## OPEN BROWSER TABS ##################
""" Optional function to open Amazon browser tabs, or Google Books tabs, for each book title in the Bundle. Good for inspecting each book's Amazon or Google page, double-checking any review metrics from the API and for adding to a reading or wishlist.

Left commented-out by default to avoid accidental browser activation. Unncomment to run."""
google_or_amzuk_or_amzcom_urls = "amzcom" # "google", "amzuk" or "amzcom"

# open_browser_tabs(google_or_amzuk_or_amzcom_urls, books_data)



