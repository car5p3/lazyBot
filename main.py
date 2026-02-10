from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import time
import os
import requests
import re
import csv
from urllib.parse import urljoin

# Main output directory
os.makedirs('scraped_products', exist_ok=True)

def sanitize_folder_name(name):
    """Sanitize product name to create a valid folder name"""
    # Remove or replace invalid characters for folder names
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # Replace multiple spaces with single space
    name = re.sub(r'\s+', ' ', name)
    # Remove leading/trailing spaces
    name = name.strip()
    # Limit length to avoid issues with long paths
    if len(name) > 100:
        name = name[:100]
    return name

def download_image(image_url, filename):
    """Download image from URL and save it locally"""
    try:
        response = requests.get(image_url, timeout=10)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"✓ Downloaded: {filename}")
            return True
    except Exception as e:
        print(f"✗ Failed to download {filename}: {str(e)}")
    return False

def setup_driver():
    """Setup Chrome WebDriver with options"""
    options = webdriver.ChromeOptions()
    # Uncomment the line below to run in headless mode
    # options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--start-maximized')
    
    driver = webdriver.Chrome(options=options)
    return driver

def main():
    # ============================================================
    # CONFIGURATION: Set how many products to scrape
    # ============================================================
    NUMBER_OF_PRODUCTS_TO_SCRAPE = 224  # Change this number to scrape more products
    # ============================================================
    
    driver = setup_driver()
    wait = WebDriverWait(driver, 15)
    
    try:
        # Navigate to the URL
        url = "https://www.la-z-boy.com/b/living-room-recliners/_/N-musa9i?intpromo=header.Recliner#/b/living-room-recliners/_/N-musa9i?intpromo=header.Recliner&No=213&Nrpp=36&plpaction=loadmore"
        print(f"Navigating to: {url}")
        driver.get(url)
        
        # Wait for page to load
        time.sleep(3)
        
        # Find all product tiles
        print("\nSearching for product tiles...")
        product_tiles = wait.until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "product-tile"))
        )
        total_products_found = len(product_tiles)
        print(f"Found {total_products_found} product tiles on the page")
        
        # Determine how many products to process
        products_to_process = min(NUMBER_OF_PRODUCTS_TO_SCRAPE, total_products_found)
        print(f"Will scrape {products_to_process} product(s) as configured\n")
        
        # Process the specified number of product tiles
        for index, tile in enumerate(product_tiles[:products_to_process], 1):
            print(f"{'='*60}")
            print(f"Processing Product #{index}")
            print(f"{'='*60}")
            
            try:
                # Scroll the product tile into view
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tile)
                time.sleep(1)
                
                # ===== EXTRACT PRODUCT NAME FIRST =====
                print("\n[EXTRACTING PRODUCT NAME]")
                try:
                    product_name_element = tile.find_element(By.CLASS_NAME, "product-name")
                    product_name = product_name_element.text.strip()
                    
                    if not product_name:
                        product_name = f"Product_{index}"
                        print(f"⚠ Product name is empty, using default: {product_name}")
                    else:
                        print(f"✓ Product Name: {product_name}")
                    
                    # Sanitize the product name for folder creation
                    folder_name = sanitize_folder_name(product_name)
                    product_folder = os.path.join('scraped_products', folder_name)
                    
                    # Create product-specific folder
                    os.makedirs(product_folder, exist_ok=True)
                    print(f"✓ Created folder: {product_folder}")
                    
                except NoSuchElementException:
                    print("✗ Could not find product-name element, using default name")
                    product_name = f"Product_{index}"
                    folder_name = product_name
                    product_folder = os.path.join('scraped_products', folder_name)
                    os.makedirs(product_folder, exist_ok=True)
                
                # ===== STEP #01: Extract main image =====
                print("\n[STEP 1] Extracting main product image...")
                try:
                    img_wrapper = tile.find_element(By.CLASS_NAME, "img-wrapper")
                    img_element = img_wrapper.find_element(By.TAG_NAME, "img")
                    main_image_url = img_element.get_attribute("src") or img_element.get_attribute("data-src")
                    
                    if main_image_url:
                        main_image_filename = os.path.join(product_folder, "main_image.jpg")
                        download_image(main_image_url, main_image_filename)
                    else:
                        print("✗ Main image URL not found")
                        
                except NoSuchElementException:
                    print("✗ Could not find img-wrapper or image element")
                
                # ===== STEP #02: Click color swatches and extract images =====
                print("\n[STEP 2] Processing color swatches...")
                try:
                    # Find all cover swatch buttons
                    swatch_lists = tile.find_elements(By.CLASS_NAME, "cover-swatch-list")
                    
                    if swatch_lists:
                        # Get all swatch buttons within the swatch lists
                        swatch_buttons = []
                        for swatch_list in swatch_lists:
                            buttons = swatch_list.find_elements(By.TAG_NAME, "button")
                            swatch_buttons.extend(buttons)
                        
                        print(f"Found {len(swatch_buttons)} color swatches")
                        
                        for swatch_index, button in enumerate(swatch_buttons, 1):
                            try:
                                # Scroll button into view
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                                time.sleep(0.5)
                                
                                # Click the swatch button
                                print(f"\n  Clicking swatch #{swatch_index}...")
                                try:
                                    button.click()
                                except ElementClickInterceptedException:
                                    # Try JavaScript click if regular click fails
                                    driver.execute_script("arguments[0].click();", button)
                                
                                time.sleep(1.5)  # Wait for image to update
                                
                                # Extract the updated image
                                img_wrapper = tile.find_element(By.CLASS_NAME, "img-wrapper")
                                img_element = img_wrapper.find_element(By.TAG_NAME, "img")
                                swatch_image_url = img_element.get_attribute("src") or img_element.get_attribute("data-src")
                                
                                if swatch_image_url:
                                    swatch_image_filename = os.path.join(product_folder, f"swatch_{swatch_index}.jpg")
                                    download_image(swatch_image_url, swatch_image_filename)
                                    
                            except Exception as e:
                                print(f"  ✗ Error processing swatch #{swatch_index}: {str(e)}")
                                continue
                    else:
                        print("No color swatches found for this product")
                        
                except NoSuchElementException:
                    print("✗ Could not find cover-swatch-list elements")
                
                # ===== STEP #03: Extract product details to CSV file =====
                print("\n[STEP 3] Extracting product details...")
                try:
                    # Extract item-detail text
                    item_detail = tile.find_element(By.CLASS_NAME, "item-detail")
                    detail_text = item_detail.text
                    
                    # Extract item-pricing text
                    pricing_text = ""
                    try:
                        item_pricing = tile.find_element(By.CLASS_NAME, "item-pricing")
                        pricing_text = item_pricing.text
                        print(f"✓ Found pricing information")
                    except NoSuchElementException:
                        print("⚠ No pricing information found for this product")
                    
                    csv_filename = os.path.join(product_folder, "product_details.csv")
                    
                    # Parse the detail text into structured data
                    # Split by lines and create key-value pairs
                    detail_lines = detail_text.strip().split('\n')
                    pricing_lines = pricing_text.strip().split('\n') if pricing_text else []
                    
                    # Write to CSV
                    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                        writer = csv.writer(csvfile)
                        
                        # Write header
                        writer.writerow(['Field', 'Value'])
                        
                        # Write product name first
                        writer.writerow(['Product Name', product_name])
                        
                        # Write pricing information
                        if pricing_lines:
                            writer.writerow(['=== PRICING ===', ''])
                            for i, line in enumerate(pricing_lines, 1):
                                line = line.strip()
                                if line:  # Only write non-empty lines
                                    # Try to split by colon if it exists (for key: value pairs)
                                    if ':' in line:
                                        parts = line.split(':', 1)
                                        writer.writerow([parts[0].strip(), parts[1].strip()])
                                    else:
                                        # If no colon, treat the whole line as a value
                                        writer.writerow([f'Price {i}', line])
                        
                        # Write detail information
                        writer.writerow(['=== DETAILS ===', ''])
                        for i, line in enumerate(detail_lines, 1):
                            line = line.strip()
                            if line:  # Only write non-empty lines
                                # Try to split by colon if it exists (for key: value pairs)
                                if ':' in line:
                                    parts = line.split(':', 1)
                                    writer.writerow([parts[0].strip(), parts[1].strip()])
                                else:
                                    # If no colon, treat the whole line as a value
                                    writer.writerow([f'Detail {i}', line])
                    
                    print(f"✓ Saved product details to: {csv_filename}")
                    print(f"\nProduct Details Preview:\n{'-'*40}")
                    if pricing_text:
                        print(f"PRICING:\n{pricing_text}\n")
                    print(f"DETAILS:\n{detail_text[:150] + '...' if len(detail_text) > 150 else detail_text}")
                    
                except NoSuchElementException:
                    print("✗ Could not find item-detail element")
                
                print(f"\n{'='*60}")
                print(f"Completed Product #{index}: {product_name}")
                print(f"All files saved in: {product_folder}")
                print(f"{'='*60}\n")
                
            except Exception as e:
                print(f"✗ Error processing product #{index}: {str(e)}")
                continue
        
        print("\n" + "="*60)
        print("Bot execution completed successfully!")
        print("="*60)
        print(f"\nProcessed {products_to_process} product(s)")
        print(f"All products saved in: ./scraped_products/")
        print(f"Each product has its own folder named after the product name")
        print(f"  - main_image.jpg - Main product image")
        print(f"  - swatch_X.jpg - Color variant images")
        print(f"  - product_details.csv - Product information in CSV format")
        
    except TimeoutException:
        print("✗ Timeout: Could not load product tiles")
    except Exception as e:
        print(f"✗ An error occurred: {str(e)}")
    finally:
        # Exit
        print("\nClosing browser...")
        time.sleep(2)
        driver.quit()
        print("Browser closed. Exiting.")

if __name__ == "__main__":
    main()