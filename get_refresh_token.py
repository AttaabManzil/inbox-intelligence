import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.readonly'
]

def main():
    flow = InstalledAppFlow.from_client_secrets_file(
        'client_secret.json',
        SCOPES
    )
    
    creds = flow.run_local_server(port=0)
    
    print("\n" + "="*50)
    print("✅ SUCCESS! Add these to your .env file:")
    print("="*50)
    
    with open('client_secret.json', 'r') as f:
        client_data = json.load(f)
        client_info = client_data['installed']
    
    print(f"\nGMAIL_CLIENT_ID={client_info['client_id']}")
    print(f"GMAIL_CLIENT_SECRET={client_info['client_secret']}")
    print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")
    print("\n" + "="*50)

if __name__ == '__main__':
    main()