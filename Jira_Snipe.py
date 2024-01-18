import json
import os
import requests

def search_snipe_it_assets(email, category_id, headers, snipe_it_api_url):
    # Function to search for assets assigned to a user's email in a given category
    response = requests.get(
        f"{snipe_it_api_url}/hardware?search={email}&category_id={category_id}",
        headers=headers
    )
    serial_numbers = []

    if response.status_code == 200:
        data = response.json()
        for item in data.get('rows', []):
            assigned_to_data = item.get('assigned_to')
            if assigned_to_data and assigned_to_data.get('email').lower() == email.lower():
                serial_numbers.append(item.get('serial'))
    
    else:
        print(f"Failed to fetch data for category {category_id}: {response.status_code}")
    
    return serial_numbers

def lambda_handler(event, context):
    # Parse the JIRA webhook data
    jira_data = json.loads(event['body'])
    
    # Extract the custom fields from the JIRA issue
    personal_email = jira_data['issue']['fields'].get('customfield_11814')
    if personal_email is None or not personal_email.lower().endswith('@traderepublic.com'):
        return {
            'statusCode': 400,
            'body': json.dumps('Invalid email domain or email not provided.')
        }
    personal_email = personal_email.lower()
    
    # Authenticate with Snipe-IT
    snipe_it_api_url = os.environ['SNIPE_IT_API_URL']
    headers = {
        'Authorization': 'Bearer ' + os.environ['SNIPE_IT_API_TOKEN'],
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    # Search for hardware assigned to the user's email
    hardware_serials = search_snipe_it_assets(personal_email, 2, headers, snipe_it_api_url)  # Category ID for hardware
    
    # Search for locker keys (Category ID 25)
    locker_key_serials = search_snipe_it_assets(personal_email, 25, headers, snipe_it_api_url)
    
    # Search for access cards (Category ID 26)
    access_card_serials = search_snipe_it_assets(personal_email, 26, headers, snipe_it_api_url)
    
    # Convert the lists of serial numbers to comma-separated strings or set to "None" if empty
    hardware_serials_text = ', '.join(hardware_serials) if hardware_serials else "None Found"
    locker_key_serials_text = ', '.join(locker_key_serials) if locker_key_serials else "None Found"
    access_card_serials_text = ', '.join(access_card_serials) if access_card_serials else "None Found"
    
    # Update the JIRA issue with hardware, locker key, and access card serial numbers
    jira_api_url = os.environ['JIRA_API_URL']
    response = requests.put(
        f"{jira_api_url}/issue/{jira_data['issue']['key']}",
        headers={
            'Authorization': 'Basic ' + os.environ['JIRA_API_TOKEN'],
            'Content-Type': 'application/json'
        },
        json={
            'fields': {
                'customfield_10374': hardware_serials_text,  # Custom field ID for hardware (comma-separated serials)
                'customfield_11817': locker_key_serials_text,  # Custom field for locker key
                'customfield_11823': access_card_serials_text  # Custom field for access card
            }
        }
    )
    
    if response.status_code != 204:
        print(f"Failed to update JIRA issue: {response.status_code}")  # Debugging statement
        print(f"Response content: {response.text}")  # Log the response content for debugging
        return {
            'statusCode': 400,
            'body': json.dumps('Failed to update JIRA issue.')
        }
        
    return {
        'statusCode': 200,
        'body': json.dumps(f"JIRA issue updated successfully with hardware serials: {hardware_serials_text}, locker keys: {locker_key_serials_text}, and access cards: {access_card_serials_text}")
    }
