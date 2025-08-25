import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
from pathlib import Path

def scrape_drikpanchang_calendar(year):
    """Scrape events from Drik Panchang calendar for a specific year"""
    url = f"https://www.drikpanchang.com/calendars/indian/indiancalendar.html?year={year}"
    
    try:
        # Add headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print(f"Fetching data for year {year}...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        events = []
        
        # Find all event containers
        event_containers = soup.find_all('div', class_='dpEventInfo')
        
        print(f"  Found {len(event_containers)} event containers")
        
        for container in event_containers:
            try:
                # Extract event name and type
                event_name_div = container.find('div', class_=lambda x: x and 'dpEventName' in x and 'EventColor' in x)
                if event_name_div:
                    # Get event name
                    event_name = event_name_div.get_text(strip=True)
                    
                    # Get event type from class
                    class_names = event_name_div.get('class', [])
                    event_type = "Other"
                    for class_name in class_names:
                        if 'EventColor' in class_name:
                            event_type = class_name.replace('dpEventName', '').replace('EventColor', '').replace('dp', '').strip()
                            break
                    
                    # Extract date
                    date_div = container.find('div', class_='dpEventGregDate')
                    date = date_div.get_text(strip=True) if date_div else "Unknown Date"
                    
                    events.append({
                        'year': year,
                        'date': date,
                        'event': event_name,
                        'type': event_type
                    })
                    
            except Exception as e:
                print(f"    Error parsing event: {e}")
                continue
        
        return events
        
    except Exception as e:
        print(f"Error fetching year {year}: {e}")
        return []

def main():
    """Main function to scrape all years and create Excel"""
    years = [2020, 2021, 2022, 2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030]
    all_events = []
    
    print(f"Starting to scrape {len(years)} years from Drik Panchang...")
    
    for year in years:
        events = scrape_drikpanchang_calendar(year)
        all_events.extend(events)
        print(f"  Year {year}: {len(events)} events extracted")
        
        # Add delay between requests to be respectful
        if year != years[-1]:  # Don't wait after the last year
            time.sleep(2)
    
    if not all_events:
        print("No events found!")
        return
    
    # Create DataFrame
    df = pd.DataFrame(all_events)
    
    # Sort by year and date
    df = df.sort_values(['year', 'date'])

    # Save to CSV
    output_file = "Holidays_2025_2029.csv"
    df.to_csv(output_file, index=False)

    print(f"\nScraping complete!")
    print(f"Total events extracted: {len(all_events)}")
    print(f"Output saved to: {output_file}")
    
    # Display sample data
    print("\nSample data:")
    print(df.head(10).to_string(index=False))
    
    # Display summary by year
    print("\nEvents by year:")
    year_counts = df['year'].value_counts().sort_index()
    for year, count in year_counts.items():
        print(f"  {year}: {count} events")
    
    # Display summary by type
    print("\nEvents by type:")
    type_counts = df['type'].value_counts()
    for event_type, count in type_counts.items():
        print(f"  {event_type}: {count} events")

if __name__ == "__main__":
    main()
