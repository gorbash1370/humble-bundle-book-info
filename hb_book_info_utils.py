############# HUMBLE BOOK BUNDLE INFO - UTILITY FUNCTIONS ############# 

from bs4 import BeautifulSoup
from datetime import datetime as dt
import json
import os
import re
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.expected_conditions import presence_of_element_located
import time
from urllib.parse import quote
import webbrowser

from config import EmptyDictionaryError


############### CHECK / CREATE OUTPUT FOLDER FUNCTIONALITY #################

def make_output_directory(output_directory, debug_flag, debug_directory):
    if debug_flag == True:
        if not os.path.exists(debug_directory):
            os.makedirs(debug_directory, exist_ok=True)
        else:
            pass
    if not os.path.exists(output_directory):
        os.makedirs(output_directory, exist_ok=True)


############### HELPER FUNCTION #################
def sanitize_filename(title):
    # List of characters to replace with '-'
    chars_to_replace = [':', '/', '?', '!', '"', "'", "|", '\\', '*', '<', '>']
    for char in chars_to_replace:
        title = title.replace(char, '-')
    # Replace spaces with underscores
    title = title.replace(' ', '_')
    return title


############### HUMBLE BUNDLE WEBPAGE RETRIEVAL FUNCTIONALITY #################

def hb_webpage_requests(url_hb, debug_flag, debug_directory):
    """ 
    Retrieve HumbleBundle webpage via requests (non JavaScript content)
    """
    try: 
        response = requests.get(url_hb)
        html_content1 = response.text
        soup1 = BeautifulSoup(html_content1, 'html.parser')
    
        # Debug Section
        if debug_flag == True:
            output_filename = 'hb_page_html_content_requests_no_js.txt'
            with open(os.path.join(debug_directory, output_filename), 'w', encoding='utf-8') as file:
                file.write(html_content1)

    except Exception as e:
        print(f"Error during requests scrape of HumbleBundle webpage. Error: {e}\n")

    return soup1


def hb_webpage_selenium(url_hb, selenium_browser, debug_flag, debug_directory):
    """
    Retrieve HumbleBundle webpage JavaScript content using Selenium.

    This function can be substituted by providing a path to txt file containing the body outer html (i.e. manual copy-paste from browser).

    Accepts: Chrome or Firefox as browser selection (tested). Should also accept Safari, Opera, Edge, and Internet Explorer (untested).

    Dependencies: Requires a browser and its WebDriver to be installed, e.g. Chrome and chromedriver, Firefox and geckodriver, etc. See README.md.
    """

    # Sanity check browser selection
    if selenium_browser.lower() in ['firefox', 'chrome', 'safari', 'opera', 'edge', 'internet explorer']:
        pass
    else:
        raise ValueError(f'Unsupported browser: {selenium_browser}.')

    try:
        if selenium_browser.lower() == 'internet explorer':
            options_class = getattr(webdriver, "IeOptions")
        else:
            options_class = getattr(webdriver, f"{selenium_browser.capitalize()}Options")
        options = options_class()
        options.headless = True

    except Exception as e:
        print(f"Error attempting to instanciate Selenium browser. Error: {e} for {selenium_browser}.\n")
        return False
    
    try:
        with getattr(webdriver, selenium_browser)(options=options) as driver:
            # Fetch the webpage
            driver.get(url_hb)

            # Get the outer HTML of the body
            wait = WebDriverWait(driver, 10)
            wait.until(presence_of_element_located((By.TAG_NAME, 'body')))
            body = driver.find_element(By.TAG_NAME, 'body')
            body_outer_html = body.get_attribute('outerHTML')
     
            soup2 = BeautifulSoup(body_outer_html, 'html.parser')

            # Debug Section
            if debug_flag == True:
                output_filename = 'hb_page_js_content_selenium.txt'
                with open(os.path.join(debug_directory, output_filename), 'w', encoding='utf-8') as file:
                    file.write(body_outer_html)

            return soup2
        
    except Exception as e:
        print(f"Error during Selenium scrape of HumbleBundle webpage. Error: {e} for {selenium_browser}.\n")
        return False


############### HUMBLE BUNDLE WEBPAGE PARSING FUNCTIONALITY #################

def parse_hb_webpage(soup1, soup2):
    """Parse HumbleBunde webpage for book data"""

    # Translation table for removing invalid characters from web-retreived strings (HumbleBundle titles often contain :,  which will corrupt filename)
    invalid_chars = '<>:"/\\|?*'
    replace_with = '-'  # can only be a single character
    trans_table = str.maketrans(invalid_chars, replace_with * len(invalid_chars))

    try:
        # Parse the HTML content retrieved by requests using BeautifulSoup
        bundle_data = soup1.find('script', {'id': 'webpack-bundle-page-data'})
        json_content = json.loads(bundle_data.string)

        # Extract publisher
        bundle_publisher = json_content['bundleData']['author'].translate(trans_table)
        print(f"Publisher: {bundle_publisher}")

        # Extract bundle name
        bundle_name = json_content['bundleData']['basic_data']['human_name'].translate(trans_table)
        print(f"Bundle name: {bundle_name}")

        if not bundle_name: # another method for bundle name
            bundle_name_pattern = soup1.find('script', {'type': 'application/ld+json'})
            json_content = json.loads(bundle_name_pattern.string)
            bundle_name = json_content['name'].translate(trans_table)


        # Parse the HTML-js content retrieved by Selenium using BeautifulSoup
        # Extract book titles
        title_pattern = re.compile(r'item-title') 
        titles = soup2.find_all('span', {'class': title_pattern})
        # print(f"Titles: {titles}") # delete me

        # Extract authors
        author_pattern = re.compile(r'publishers-and-developers') 
        authors = soup2.find_all('div', {'class': author_pattern})
        # print(f"Authors: {authors}") # delete me

        # Filtering authors to only include those with 'Author:' or 'Authors:'
        refined_authors = [author for author in authors if 'Author:' in str(author) or 'Authors:' in str(author)]
        # print(f"Refined authors: {refined_authors}") # delete me

        # Extract blurbs
        blurb_pattern = re.compile(r'description')
        blurbs = soup2.find_all(['p', 'section'], {'class': blurb_pattern})

    except Exception as e:
        print(f"Error during parsing of HumbleBundle HTML and JavaScript content. Error: {e}")

    return bundle_name, bundle_publisher, titles, refined_authors, blurbs


def catalogue_book_data(bundle_name, bundle_publisher, titles, refined_authors, blurbs, url_hb, debug_flag, debug_directory):
    """Catalogue the basic book data retrieved from HumbleBundle webpage into a dictionary structure. Dictionary sets up space for the data from Google Books and Bing Search API ."""
    # Processing date stamp
    processing_date = dt.now().strftime("%Y-%m-%d")

    # Create a data structure to hold the extracted information
    books_data = []
    try:
        for index, (title, author, blurb) in enumerate(zip(titles, refined_authors, blurbs), 1):
            author_text = ', '.join([span.get_text().strip() for span in author.find_all('span')])
            book_data_dict = {
            "Index" : str(index).zfill(2), # zero-padded index
            "Title" : title.get_text().strip(),
            "Author(s)" : author_text,
            "Blurb" : blurb.get_text().strip(),
            "Published Date Google" : "", # placeholder awaiting later API calls
            "Page Count Google" : "", # placeholder 
            "ISBN_10" : "", # placeholder
            "ISBN_13" : "", # placeholder
            "Amazon" : {
                    "ASIN" : "", # placeholder
                    "Amazon.com URL" :"", # placeholder
                    "Amazon.com Review Rating of 5" : "", # placeholder
                    "Amazon.com Reviews Num" : "", # placeholder
                    "Amazon.com Price ebook USD" : "",
                    "Amazon UK URL" :"", # placeholder
                    "Amazon UK Review Rating of 5" : "", # placeholder
                    "Amazon UK Reviews Num" : "", # placeholder
                    "Amazon UK Price ebook GBP" : "",
            },
            "Google Books" : {
                "Google Books ID" : "", # placeholder
                "Google Books URL" : "", # placeholder
                "Google Price ebook" : "", # placeholder
            },  
            "Bundle Name" : bundle_name,
            "Bundle Date" : processing_date,
            "Bundle Publisher" : bundle_publisher,
            "Bundle URL" : url_hb,
            }
            
            books_data.append(book_data_dict)
    
        # Debug Section
        if debug_flag == True:
            output_filename = 'books_dict_from_hb_webpage_only.txt'
            with open(os.path.join(debug_directory, output_filename), 'w', encoding='utf-8') as file:
                json.dump(books_data, file, ensure_ascii=False, indent=4)
    
    
    except Exception as e:
            print(f"Error during books_data dictionary construction with data from HumbleBundle webpage. Error: {e} for Book {index}.\n")

    return books_data


############### GOOGLE BOOKS API CALL & PARSING FUNCTIONALITY #################

def google_books_api_call(books_data, debug_flag, debug_directory):
    """ Call Google Books API to retrieve additional book data for each title.
    Limitation: The script only searches the first returned Google Books result for each book. 

    """
    response_data = {}
    try:
        for book in books_data:
            book_title = book['Title']
            book_author = book['Author(s)']

            query = f'intitle:{book_title}+inauthor:{book_author}'
            query = quote(query)
            print(f"Google Books API query string: {query}\n")

            url = f'https://www.googleapis.com/books/v1/volumes?q={query}'
            
            response = requests.get(url)

            # Debug Section
            if debug_flag == True:
                with open(os.path.join(debug_directory, "google_books_response_raw.txt"), 'w', encoding='utf-8') as file:
                    file.write(response.text)

            book_response_data = {book['Index']: response.json()}  # New dictionary just for this book

            response_data.update(book_response_data)  # Update the main dictionary with the new book's data

            data = response.json() # Parse the response as JSON

            # Debug Section
            if debug_flag == True:
                safe_title = sanitize_filename(book['Title'])
                try:
                    output_filename = f'{book['Index']}_{safe_title}_google_books_data.txt'
                    with open(os.path.join(debug_directory, output_filename), 'w', encoding='utf-8') as file:
                        json.dump(data, file, ensure_ascii=False, indent=4)
                except Exception as e:
                    print(f"Error during writing of Google Books data to file.\n Sanitized file name was: {safe_title}.\nError: {e} for {book['Index']}.\n")

            # Update books_data with Google Books data. This could be improved by not chaining the get() methods, which would allow for a default value (i.e. "None found") to be set for the books_data dictionary entry instead of '{}/None. However, the get method avoids KeyErrors if a key is not found in the searched data.
            if data.get('items'):
                book_info = data['items'][0].get('volumeInfo', {})
                book['Published Date Google'] = book_info.get('publishedDate')
                book['Page Count Google'] = book_info.get('pageCount')

                identifiers = book_info.get('industryIdentifiers', [{}])
                book['ISBN_13'] = identifiers[0].get('identifier')
                book['ISBN_10'] = identifiers[1].get('identifier') if len(identifiers) > 1 else None

                book['Google Books']['Google Books ID'] = data['items'][0].get('id')
                book['Google Books']['Google Books URL'] = book_info.get('previewLink')
                
                # Extract the price and currency code
                price_info = data.get('items', [{}])[0].get('saleInfo', {}).get('retailPrice', {})
                price = price_info.get('amount')
                currency_code = price_info.get('currencyCode')
                # Combine the price and currency code into a single string
                price_with_currency = f'{currency_code} {price}' if price and currency_code else "None found"
                # Update the book data
                book['Google Books']['Google Price ebook'] = price_with_currency
            else:
                print(f"No Google Book results found for Book {book['Index']}")

    except Exception as e:
        print(f"Error during Google Books API call or parsing of retrieved data. Error: {e} for Book {book['Index']}\n")

    # Debug Section
    try: 
        if debug_flag == True:
            with open(os.path.join(debug_directory, f'books_dict_after_google_{book["Bundle Name"]}.txt'), 'w', encoding='utf-8') as file:
                json.dump(books_data, file, ensure_ascii=False, indent=4)
            
            with open(os.path.join(debug_directory, "google_books_search_data_all.txt"), 'w', encoding='utf-8') as file:
                json.dump(response_data, file, ensure_ascii=False, indent=4)

    except Exception as e:
        print(f"Debug Process Error during writing of books_data dictionary to file after Google Books API call. Error: {e}\n")

    return books_data


############# BING SEARCH API CALL & PARSING FUNCTIONALITY #############

def bing_search_for_reviews(books_data, bing_api_key, debug_flag, debug_directory):
    response_data = {}
    """ Call Bing Search API to retrieve search results for each book. These usually include Amazon URLs, which can later be parsed to retrieve review and price information etc."""

    try:
        for book in books_data:
            # NB: this could be split into Amazon.co.uk and Amazon.com searches
            book_to_search = f"{book['Title']} - {book['Author(s)']}"

            search_term = book_to_search + " amazon" + " ebook"
            print(f"Bing Search query: {search_term}\n")

            url = "https://api.bing.microsoft.com/v7.0/search"

            headers = {"Ocp-Apim-Subscription-Key": bing_api_key}
            params  = {"q": search_term, "count" : 5, "textDecorations": True, "textFormat": "HTML"}

            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status() # raises exception if response code != 200

            # Debug Section
            if debug_flag == True:
                with open(os.path.join(debug_directory, "bing_response_raw.txt"), 'w', encoding='utf-8') as file:
                    file.write(response.text)

            book_response_data = {book['Index']: response.json()}  # New dictionary just for this book

            response_data.update(book_response_data)  # Update the main dictionary with the new book's data

            # Debug Section
            if debug_flag == True:
                safe_title = sanitize_filename(book['Title'])
                try:
                    with open(os.path.join(debug_directory, f'{book['Index']}_{safe_title}_bing_search_json.txt'), 'w', encoding='utf-8') as file:
                        json.dump(book_response_data, file, ensure_ascii=False, indent=4)
                except Exception as e:
                    print(f"Error during writing of Bing Search data to file.\n Sanitized file name was: {safe_title}.\n Error: {e} for {book['Index']}.\n")

            time.sleep(0.5)
    
    except Exception as e:
        print(f"Error during Bing Search API request. Error: {e} for {book['Index']}\n")

    # Debug Section
    try: 
        if debug_flag == True:
            with open(os.path.join(debug_directory, "bing_response_raw.txt"), 'w', encoding='utf-8') as file:
                json.dump(response_data, file, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Debug Process Error during writing of Bing Search API data to file. Error: {e}\n")

    return response_data


def bing_search_for_reviews_parse(books_data, response_data, debug_flag, debug_directory):
    """ 
    Parse the Bing Search API response data to attempt to retrieve Amazon URLs, review ratings, review counts, Kindle prices and ASINs for each book.
    """
    try:
        for book in books_data:
            data = response_data[book['Index']] # Response data for individual book

            # Temporary variables to store dynamically store Bing API data. Final values to be written to books_data dictionary at end of loop 
            url_amazon_com = None
            url_amazon_uk = None
            rating_value_amazon_com = None
            rating_value_amazon_uk = None
            review_count_amazon_com = None
            review_count_amazon_uk = None
            price_amazon_com = None
            price_amazon_uk = None

            # NB: URL and Ratings will always be paired as coming from the same page entry. The price however can come from any page (necessary because price appearances are very rare.) Earlier entries are prioritised (i.e. not overwritten by later ones) as they are more likely to have a more recent crawl date.

            found_url_uk_and_ratings = False
            found_uk_price = False
            for page in data.get('webPages', {}).get('value', []):
                # Check to exit the loop if both URL/ratings and Kindle price have been found
                if found_url_uk_and_ratings and found_uk_price:
                    break
                # Safely get 'url', then check if it starts with the Amazon UK URL
                url = page.get('url', '')
                if url.startswith("https://www.amazon.co.uk/"):
                    # If no .co.uk URL has been stored yet, store this one
                    if url_amazon_uk is None:
                        url_amazon_uk = url

                    # Check for 'about' key only if we haven't found URL and ratings yet
                    if not found_url_uk_and_ratings:
                        # Safely get the first 'about' item, or default to an empty dict if 'about' is missing or empty
                        about = next(iter(page.get('about', [])), {})
                        aggregateRating = about.get('aggregateRating', None)
                        if aggregateRating:
                            # If 'aggregateRating' exists, overwrite the URL with this one, as it has ratings
                            url_amazon_uk = url # Overwrite the URL with this one, as it has ratings
                            rating_value_amazon_uk = aggregateRating.get('ratingValue', "")
                            review_count_amazon_uk = aggregateRating.get('reviewCount', "")
                            found_url_uk_and_ratings = True

                    # Check for 'richFacts' and 'Kindle Price' only if we haven't found the UK price yet
                    if not found_uk_price:
                        for fact in page.get('richFacts', []):
                            label_text = fact.get('label', {}).get('text', "")
                            if label_text == 'Kindle Price':
                                # Attempt to get the first 'text' from 'items' that has 'text', defaulting to None if not found
                                price_amazon_uk = next((item.get('text') for item in fact.get('items', []) if item.get('text')), None)
                                if price_amazon_uk is not None:
                                    found_uk_price = True
                                    break

                                    
            found_url_com_and_ratings = False
            found_com_price = False
            for page in data.get('webPages', {}).get('value', []):
                if found_url_com_and_ratings and found_com_price:
                    break
                # Find the first Amazon.com URL
                url = page.get('url', '')
                if url.startswith("https://www.amazon.com/"):
                    # If no .com URL has been stored yet, store this one
                    if url_amazon_com is None:
                        url_amazon_com = url
                    
                    # Target the 'about' key immediately after the 'url' key above
                    if not found_url_com_and_ratings:
                        about = next(iter(page.get('about', [])), {})
                        aggregateRating = about.get('aggregateRating', None)
                        if aggregateRating:
                            url_amazon_com = url  # Overwrite the URL with this one, as it has ratings
                            rating_value_amazon_com = aggregateRating.get('ratingValue')
                            review_count_amazon_com = aggregateRating.get('reviewCount')
                            found_url_com_and_ratings = True

                    # Checking 'richFacts' for 'Kindle Price'
                    if not found_com_price:
                        for fact in page.get('richFacts', []):
                            label_text = fact.get('label', {}).get('text', '')
                            if label_text == 'Kindle Price':
                                items_text = next((item.get('text') for item in fact.get('items', []) if item.get('text')), None)
                                if items_text:
                                    price_amazon_com = items_text
                                    found_com_price = True
                                    break                                      
                
            # Update books_data with Bing API retrieved Amazon URLs for UK and com, including attempt to extract ASIN. Amazon.com is processed first so that the ASIN is usually for .com, to match the headline review ratings in text file coming from .com (vs co.uk)
            if url_amazon_com is None:
                book['Amazon']['Amazon.com URL'] = "No Amazon.com URL found"

            if url_amazon_com is not None:
                try:
                    book['Amazon']['Amazon.com URL'] = url_amazon_com
                    if book['Amazon']['ASIN'] == "":
                        try:
                            asin = re.search(r'/dp/(\w+)', url_amazon_com).group(1)
                            asin = asin.upper()
                            if asin == book['ISBN_10'] or asin == book['ISBN_13']:
                                pass # skip if url ID matches ISBN
                            else:   
                                book['Amazon']['ASIN'] = asin
                        except AttributeError:
                            book['Amazon']['ASIN'] = "No ASIN found"
                except Exception as e:
                    print(f"Error: {e} for {book['Index']}")                    

            if url_amazon_uk is None:
                book['Amazon']['Amazon UK URL'] = "No Amazon.co.uk URL found"
            

            if url_amazon_uk is not None:
                try:
                    book['Amazon']['Amazon UK URL'] = url_amazon_uk
                    if book['Amazon']['ASIN'] == "":
                        try:
                            asin = re.search(r'/dp/(\w+)', url_amazon_uk).group(1)
                            asin = asin.upper()
                            if asin == book['ISBN_10'] or asin == book['ISBN_13']:
                                pass # skip if url ID matches ISBN
                            else:   
                                book['Amazon']['ASIN'] = asin
                        except AttributeError:
                            book['Amazon']['ASIN'] = "No ASIN found"
                except Exception as e:
                    print(f"Error: {e} for {book['Index']}")
            else:
                print('No ASIN found in url.')


            # Update books_data with Bing API retrieved review rating for UK and com
            if rating_value_amazon_uk is not None:
                try:
                    book['Amazon']['Amazon UK Review Rating of 5'] = rating_value_amazon_uk
                    print(f'Rating Value: {rating_value_amazon_uk}')
                except Exception as e:
                    print(f"Error: {e} for {book['Index']}")
                                
            else:
                try: 
                    book['Amazon']['Amazon UK Review Rating of 5'] = "None found"
                    print('No Amazon UK rating value found.')
                except Exception as e:
                    print(f"Error: {e} for {book['Index']}")

            if rating_value_amazon_com is not None:
                try:
                    book['Amazon']['Amazon.com Review Rating of 5'] = rating_value_amazon_com
                    print(f'Rating Value: {rating_value_amazon_com}')
                except Exception as e:
                    print(f"Error: {e} for {book['Index']}")

            else:
                try:
                    book['Amazon']['Amazon.com Review Rating of 5'] = "None found"
                    print('No Amazon.com rating value found.')
                except Exception as e:
                    print(f"Error: {e} for {book['Index']}")

            # Update books_data with Bing API retrieved review count for UK and com
            if review_count_amazon_uk is not None:
                try:
                    book['Amazon']['Amazon UK Reviews Num'] = review_count_amazon_uk
                    print(f'Review Count: {review_count_amazon_uk}')
                except Exception as e:
                    print(f"Error: {e} for {book['Index']}")
                    
            else:
                try:
                    book['Amazon']['Amazon UK Reviews Num'] = "None found"
                    print('No Amazon UK review count found.')
                except Exception as e:
                    print(f"Error: {e} for {book['Index']}")

            if review_count_amazon_com is not None:
                try:
                    book['Amazon']['Amazon.com Reviews Num'] = review_count_amazon_com
                    print(f'Review Count: {review_count_amazon_com}')
                except Exception as e:
                    print(f"Error: {e} for {book['Index']}")
            else:
                try:
                    book['Amazon']['Amazon.com Reviews Num'] = "None found"
                    print('No Amazon.com review count found.')
                except Exception as e:
                    print(f"Error: {e} for {book['Index']}")

            # Update books_data with Bing API retrieved price for UK and com
            if price_amazon_uk is not None:
                try:
                    book['Amazon']['Amazon UK Price ebook GBP'] = price_amazon_uk
                    print(f'Price: {price_amazon_uk}')
                except Exception as e:
                    print(f"Error: {e} for {book['Index']}")
            else:
                try:
                    book['Amazon']['Amazon UK Price ebook GBP'] = "None found"
                    print('No Amazon UK price found.')
                except Exception as e:
                    print(f"Error: {e} for {book['Index']}")

            if price_amazon_com is not None:
                try:
                    book['Amazon']['Amazon.com Price ebook USD'] = price_amazon_com
                    print(f'Price: {price_amazon_com}')
                except Exception as e:
                    print(f"Error: {e} for {book['Index']}")
            else:
                try:
                    book['Amazon']['Amazon.com Price ebook USD'] = "None found"
                    print('No Amazon.com price found.')
                except Exception as e:
                    print(f"Error: {e} for {book['Index']}")     

            # Debug Section
            if debug_flag == True:
                safe_title = sanitize_filename(book['Title'])
                try:
                    with open(os.path.join(debug_directory, f'bing_search_data_{book['Index']}_{safe_title}.txt'), 'w', encoding='utf-8') as file:
                        json.dump(data, file, ensure_ascii=False, indent=4)
                except Exception as e:
                    print(f"Error during writing of parsed Bing Search data to file.\n Sanitized file name was: {safe_title}.\n Error: {e} for {book['Index']}.\n")
                    
    except Exception as e:
        print(f"Error during parsing of Bing Search API data. Error: {e} for {book['Index']}")

    # Debug Section
    try:
        if debug_flag == True:
             with open(os.path.join(debug_directory, f'books_dict_after_bing_{book['Bundle Name']}.txt'), 'w', encoding='utf-8') as file:
                json.dump(books_data, file, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Debug Process Error during writing of books_data dictionary to file after Bing Search API call. Error: {e}\n")

    return books_data


############# TEXT OUTPUT FORMATTING FUNCTIONS #############


def book_data_formatted_txt_verbose(books_data, output_directory):
    """Extract book_data dictionary info, format and output to txt file (verbose)."""
    # Check if books_data is not empty
    if not books_data:
        raise EmptyDictionaryError("Error whilst attempting to write to file: books_data is empty which indicates that no data has been retrieved from even the first interaction with the Humble Bundle Webpage. It is therefore likely that targeted Humble Book Bundle webpage is not in a compatible format for this script, or that the URL is incorrect.")
    
    format_date = books_data[0]["Bundle Date"][2:7].replace('-', ' ')
    output_filename = f'{books_data[0]["Bundle Name"]} ({format_date}, verbose).txt'

    try:
        with open(os.path.join(output_directory, output_filename), 'w', encoding='utf-8') as file:

            # Opening 'header' of Bundle name, publisher, processing date
            file.write(f"{books_data[0]["Bundle Name"]} - {books_data[0]["Bundle Publisher"]}\n"
                    f"Processing date: {books_data[0]["Bundle Date"]}\n"
                    f"Data retrieved from: {books_data[0]["Bundle URL"]}\n\n")

            # Summary list of titles, authors & Amazon.com reviews
            for book in books_data:
                file.write(f"Book {book['Index']} - {book['Title']} - {book['Author(s)']} - {book['Amazon']['Amazon.com Review Rating of 5']} out of 5 ({book['Amazon']['Amazon.com Reviews Num']} reviews)\n")
            file.write('\n' + '-' * 50 + '\n')

            # Detailed information section for each book
            file.write(f"Book Details (Full)\n")
            file.write('-' * 25 + '\n\n')
            for book in books_data:
                file.write(f'Book {book['Index']}:\n')
                file.write(f"Title: {book['Title']}\n")
                file.write(f"Author(s): {book['Author(s)']}\n")
                file.write('-' * 3 + '\n')
                file.write(f"ISBN-10: {book['ISBN_10']} - ISBN-13: {book['ISBN_13']} - ASIN: {book['Amazon']['ASIN']}\n")
                file.write(f"Published Date: {book['Published Date Google']}\n")
                file.write(f"Page Count: {book['Page Count Google']}\n")
                file.write('-' * 3 + '\n')
                file.write(f"Google Books Price: {book['Google Books']['Google Price ebook']}\n")
                file.write(f"Google Books URL: {book['Google Books']['Google Books URL']}\n")
                file.write('-' * 3 + '\n')
                file.write(f"Amazon.com Price: {book['Amazon']['Amazon.com Price ebook USD']}\n")
                file.write(f"Amazon.com Reviews: {book['Amazon']['Amazon.com Review Rating of 5']} of 5 ({book['Amazon']['Amazon.com Reviews Num']} reviews)\n")
                file.write(f"Amazon.com URL: {book['Amazon']['Amazon.com URL']}\n")    
                file.write('-' * 3 + '\n')
                file.write(f"Amazon.co.uk Price: {book['Amazon']['Amazon UK Price ebook GBP']}\n")
                file.write(f"Amazon.co.uk Reviews: {book['Amazon']['Amazon UK Review Rating of 5']} of 5 ({book['Amazon']['Amazon UK Reviews Num']} reviews)\n")
                file.write(f"Amazon.co.uk URL: {book['Amazon']['Amazon UK URL']}\n")        
                file.write('-' * 3 + '\n')
                file.write(f"HB Blurb: {book['Blurb']}\n")
                file.write('-' * 50 + '\n\n')
        
             # URLs Section
            file.write(f"URLs Collection\n")
            file.write('-' * 25 + '\n\n')
            for book in books_data:
                file.write(f"Book {book['Index']} - {book['Title']}\n")
                file.write(f"{book['Amazon']['Amazon.com URL']}\n")
                file.write(f"{book['Amazon']['Amazon UK URL']}\n")
                file.write(f"{book['Google Books']['Google Books URL']}\n\n")
        
        print(f"\nVerbose version of book data written to {output_filename}.\n")
    
    except Exception as e:
        print(f"Error: {e} for {book['Index']}")
        return False
    
    return True

#%%
def book_data_formatted_txt_short(books_data, output_directory):
    """Extract book_data dictionary info, format and output to txt file (short)."""
    if not books_data:
        raise EmptyDictionaryError("Error whilst attempting to write to file: books_data is empty which indicates that no data has been retrieved from even the first interaction with the Humble Bundle Webpage. It is therefore likely that targeted Humble Book Bundle webpage is not in a compatible format for this script, or that the URL is incorrect.")

    format_date = books_data[0]["Bundle Date"][2:7].replace('-', ' ')
    output_filename = f'{books_data[0]["Bundle Name"]} ({format_date}, short).txt'

    try:
        with open(os.path.join(output_directory, output_filename), 'w', encoding='utf-8') as file:

            # Opening 'header' of Bundle name, publisher, processing date
            file.write(f"{books_data[0]["Bundle Name"]} - {books_data[0]["Bundle Publisher"]}\n"
                    f"Processing date: {books_data[0]["Bundle Date"]}\n"
                    f"Data retrieved from: {books_data[0]["Bundle URL"]}\n\n")

            # Summary list of titles, authors & Amazon.com reviews
            for book in books_data:
                file.write(f"Book {book['Index']} - {book['Title']} - {book['Author(s)']} - {book['Amazon']['Amazon.com Review Rating of 5']} out of 5 ({book['Amazon']['Amazon.com Reviews Num']} reviews)\n")
            file.write('\n' + '-' * 50 + '\n')

            # Detailed information section for each book, reduced vs verbose
            file.write(f"Book Details (Short)\n")
            file.write('-' * 25 + '\n\n')
            for book in books_data:
                file.write(f'Book {book['Index']}:\n')
                file.write(f"Title: {book['Title']}\n")
                file.write(f"Author(s): {book['Author(s)']}\n")
                file.write('-' * 3 + '\n')
                file.write(f"ISBN-10: {book['ISBN_10']} - ISBN-13: {book['ISBN_13']} - ASIN: {book['Amazon']['ASIN']}\n")
                file.write(f"Published Date: {book['Published Date Google']}\n")
                file.write('-' * 3 + '\n')
                file.write(f"HB Blurb: {book['Blurb']}\n")
                file.write('-' * 50 + '\n\n')

            # URLs Section
            file.write(f"URLs Collection\n")
            file.write('-' * 25 + '\n\n')
            for book in books_data:
                file.write(f"Book {book['Index']} - {book['Title']}\n")
                file.write(f"{book['Amazon']['Amazon.com URL']}\n")
                file.write(f"{book['Amazon']['Amazon UK URL']}\n")
                file.write(f"{book['Google Books']['Google Books URL']}\n\n")

            print(f"Short version of book data written to {output_filename}.\n")

    except Exception as e:
        print(f"Error: {e} for {book['Index']}")
        return False
    
    return True

def generate_txt_file(txt_file_version, books_data, output_directory, bundle_name):
    """Coordinates the generation of the txt file output, based upon user's selection of verbose or short format. Default is verbose.
    
    If the entire operation has been unsuccessful (from the Humble Bundle webpage processing stage), a custom Exception is raised and the script attempts to create a text file prepended with 'unsuccessful_' in the output directory.
    
    """
    try: 
        if txt_file_version == "verbose":
            book_data_formatted_txt_verbose(books_data, output_directory)
            return True
        elif txt_file_version == "short":
            book_data_formatted_txt_short(books_data, output_directory)
            return True
        elif txt_file_version == "both":
            book_data_formatted_txt_verbose(books_data, output_directory)
            book_data_formatted_txt_short(books_data, output_directory)
            return True
        else:
            print("Error: incorrect txt file version value supplied. Generating verbose version.")
            book_data_formatted_txt_verbose(books_data, output_directory)
            return False

    except EmptyDictionaryError as e:
        print(e)
        try:
            unsuccessful_output_filename = f'unsuccessful_{dt.now().strftime("%y-%m")}_{bundle_name}.txt'
            with open(os.path.join(output_directory, unsuccessful_output_filename), 'w') as file:
                file.write(f"Error: {e}")
        except Exception as e:
            print(f"Error while attempting to create unsuccessful_ file: {e}")
    except Exception as e:
        print(f"Error: {e}")
        return False


############# OPTIONAL BROWSER TABS FUNCTIONALITY #############

def open_amazon_uk_urls(books_data):
    """Opens all the Amazon.co.uk URLs in new browser tabs.
    Good for inspecting each book's Amazon page, double-checking any review metrics from the API and for adding to a reading or wishlist. """
    try:
        for book in books_data:
            url = book['Amazon']['Amazon UK URL']
            if url:  # Check if the URL is not empty
                webbrowser.open_new_tab(url)
                time.sleep(0.25)
            else:
                print(f"No Amazon.co.uk URL found for {book['Title']}.Skipping to next title.")
    except Exception as e:
        print(f"Error: Unable to open Amazon.co.uk book URLs - {e}")
       

def open_amazon_com_urls(books_data):
    """"Opens all the Amazon.com URLs in new browser tabs.
    Good for inspecting each book's Amazon page, double-checking any review metrics from the API and for adding to a reading or wishlist."""
    try: 
        for book in books_data:
            url = book['Amazon']['Amazon.com URL']
            if url:  # Check if the URL is not empty
                webbrowser.open_new_tab(url)
                time.sleep(0.25)
            else:
                print(f"No Amazon.com URL found for {book['Title']}.Skipping to next title.")
    except Exception as e:
        print(f"Error: Unable to open Amazon.com book URLs - {e}")


def open_google_books_urls(books_data):
    """Opens all the Google Books preview URLs in new browser tabs.
    Good for inspecting each book's Google Books page."""
    try: 
        for book in books_data:
            url = book['Google Books']['Google Books URL']
            if url:  # Check if the URL is not empty
                webbrowser.open_new_tab(url)
                time.sleep(0.25)
            else:
                print(f"No Google Books URL found for {book['Title']}.Skipping to next title.")
    except Exception as e:
        print(f"Error: Unable to open Google Books URLs - {e}")


def open_browser_tabs(google_or_amzuk_or_amzcom_urls, books_data):
    if google_or_amzuk_or_amzcom_urls == "amzuk":
        open_amazon_uk_urls(books_data)
        return True
    if google_or_amzuk_or_amzcom_urls == "amzcom":
        open_amazon_com_urls(books_data)
        return True
    if google_or_amzuk_or_amzcom_urls == "google":
        open_google_books_urls(books_data)
        return True
    else:
        print("Error: Please select 'google', 'amzuk' or 'amzcom' for the URL selection.")
        return False

############# MASTER COORDINATION FUNCTION #############


def main(output_directory, url_hb, selenium_browser, bing_api_key, txt_file_version, debug_flag, debug_directory):
    make_output_directory(output_directory, debug_flag, debug_directory)
    soup1 = hb_webpage_requests(url_hb, debug_flag, debug_directory)
    soup2 = hb_webpage_selenium(url_hb, selenium_browser, debug_flag, debug_directory)
    bundle_name, bundle_publisher, titles, refined_authors, blurbs = parse_hb_webpage(soup1, soup2)
    books_data = catalogue_book_data(bundle_name, bundle_publisher, titles, refined_authors, blurbs, url_hb, debug_flag, debug_directory)
    books_data = google_books_api_call(books_data, debug_flag, debug_directory)
    response_data = bing_search_for_reviews(books_data, bing_api_key, debug_flag, debug_directory) 
    books_data = bing_search_for_reviews_parse(books_data, response_data, debug_flag, debug_directory)
    generate_txt_file(txt_file_version, books_data, output_directory, bundle_name)
    return books_data