import time
import gspread
from google.oauth2.service_account import Credentials

# Set up the credentials
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
client = gspread.authorize(creds)

# Open the Google Sheets workbook by ID
sheet_id = "1PgOr0aQ-i1d4NjZzdYMl6To_WphmHYM3RpAPkPb1IbQ"
workbook = client.open_by_key(sheet_id)

def process_payment_methods_for_fiat(fiat_currency):
    try:
        # Try to access the worksheet
        sheet = workbook.worksheet(fiat_currency)
        
        # Read all data from the sheet
        data = sheet.get_all_values()
        
        # Debugging: Print the data fetched from the sheet
        # print(f"Data from '{fiat_currency}' worksheet: {data}")

        if not data or len(data) < 2:  # Ensure there is data to process
            print(f"No data found in the worksheet for currency '{fiat_currency}'.")
            return
        
        # Initialize a dictionary to store unique payment methods and their total amounts
        payment_methods = {}

        # Process each row, skipping the header
        for row in data[1:]:
            amount_str = row[2]  # Column index for available amount (3rd column)
            methods = row[3].split(',') if len(row) > 3 else []  # Last column containing payment methods
            
            try:
                # Remove commas from amount and convert to float
                amount = float(amount_str.replace(',', '')) if amount_str else 0  
            except ValueError:
                print(f"Invalid amount '{amount_str}' found in row: {row}")
                continue  # Skip this row if the amount is invalid

            counted_bank = False  # Flag to check if bank amount has been counted

            for method in methods:
                method = method.strip()  # Clean whitespace
                
                # Check if the method includes "bank"
                if "bank" in method.lower():
                    if not counted_bank:  # Only count once for bank methods
                        payment_methods["Bank Transfer"] = payment_methods.get("Bank Transfer", 0) + amount
                        counted_bank = True  # Set flag to True after counting
                else:
                    # Add the amount to other payment methods
                    if method:  # Only add non-empty methods
                        payment_methods[method] = payment_methods.get(method, 0) + amount

        # Prepare to write results to column I (payment options) and column J (amount summary)
        sorted_methods = sorted(payment_methods.items(), key=lambda x: x[1], reverse=True)

        # Prepare the data for batch update
        update_data = [[method, amount] for method, amount in sorted_methods]

        # Clear the entire columns I and J before writing new values
        sheet.batch_clear(['I:I', 'J:J'])  # Clear columns I and J

        # Write the titles in the first row
        sheet.update('I1', [['Payment Options', 'Amount Summary']])

        # Write all sorted payment methods and their amounts to the sheet at once
        if update_data:  # Ensure there's data to update
            retries = 3  # Number of retries
            for attempt in range(retries):
                try:
                    sheet.update('I2:J' + str(len(update_data) + 1), update_data)
                    print(f"Processing completed for currency: {fiat_currency}")
                    break  # Exit the retry loop on success
                except Exception as e:
                    print(f"Attempt {attempt + 1} failed to update 'Main' sheet: {e}")
                    if attempt < retries - 1:  # If this isn't the last attempt
                        print("Retrying in 5 seconds...")
                        time.sleep(5)  # Wait before retrying

    except gspread.exceptions.WorksheetNotFound:
        print(f"Worksheet for currency '{fiat_currency}' not found.")
    except Exception as e:
        print(f"An error occurred for currency '{fiat_currency}': {e}")


def update_single_fiat_payment_methods(fiat_currency):

    """Update the 'Available Payment Methods' column in the 'Main' sheet for a single fiat currency."""
    try:
        # Open the "Main" sheet
        main_sheet = workbook.worksheet('Main')
        
        # Fetch all data from the "Main" sheet
        main_data = main_sheet.get_all_values()

        # Get the index for the "Available Payment Methods" column (assume it's column H, which is index 7)
        available_payment_methods_col_idx = 7

        # Loop through each row in the "Main" sheet (skip the header)
        for row_idx, row in enumerate(main_data[1:], start=2):
            # Check if the row corresponds to the specified fiat currency
            if row[1] == fiat_currency:  # Assuming column B contains the fiat currency
                try:
                    # Open the corresponding fiat currency sheet
                    fiat_sheet = workbook.worksheet(fiat_currency)

                    # Get payment methods and amounts from the fiat worksheet (columns I and J)
                    payment_data = fiat_sheet.get_all_values()

                    # Prepare the formatted string for the "Available Payment Methods"
                    available_payment_methods = []
                    for payment_row in payment_data[1:]:  # Skip the header row
                        method = payment_row[8]  # Column I (Payment Options)
                        amount = payment_row[9]  # Column J (Amount Summary)
                        if method and amount:
                            available_payment_methods.append(f"{method} ({amount})")

                    # Join all payment methods into a single string, separated by commas
                    available_payment_methods_str = ', '.join(available_payment_methods)

                    # Clear the existing value in the "Available Payment Methods" column (H)
                    main_sheet.update_cell(row_idx, available_payment_methods_col_idx + 1, "")

                    # Update the "Available Payment Methods" column with new value
                    main_sheet.update_cell(row_idx, available_payment_methods_col_idx + 1, available_payment_methods_str)

                    print(f"Updated 'Available Payment Methods' for {fiat_currency} in row {row_idx}.")
                    return  # Exit after updating the desired currency

                except gspread.WorksheetNotFound:
                    print(f"Worksheet for {fiat_currency} not found. Skipping...")
                    return  # Exit if the fiat currency sheet is not found

    except Exception as e:
        print(f"An error occurred while updating the 'Main' sheet: {e}")
