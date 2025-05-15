from bs4 import BeautifulSoup
import arrow
from datetime import datetime


def parse_html_messages(html):
    """
    Parse messages from a Telegram HTML export file.
    Args:
        html (str): The HTML content of the Telegram export file.
    Returns:
        list: A list of dictionaries containing parsed message data.        
    """
    # Open and read the HTML file
    soup = BeautifulSoup(html, "html.parser")
        
    # Find all message divs
    messages = soup.find_all("div", class_="message default clearfix") + soup.find_all("div", class_="message default clearfix joined")
    
    # List to store parsed messages
    parsed_messages = []
    
    for message in messages:
        # Extract media file path
        media_wrap = message.find("a", href=True)
        media_path = media_wrap["href"] if media_wrap else None

        if not media_path:
            continue
        
        allowed_prefixes = ("video_files/", "photos/", "voice_messages/", "files/")
        if not media_path.startswith(allowed_prefixes):
            # Skip if the media path does not start with the expected prefixes
            continue
        
        # Extract message ID
        message_id = message.get("id").strip("message")

        # extract date
        date = message.find("div", class_="pull_right date details")["title"]
        date = datetime.strptime(date, "%d.%m.%Y %H:%M:%S UTC%z")
        date = arrow.get(date).format("YYYY-MM-DDTHH:mm:ssZZ")
        # Extract text content
        text_div = message.find("div", class_="text")
        text = text_div.get_text(strip=True) if text_div else None
        
        # Append the parsed message to the list
        parsed_messages.append({
            "id": message_id,
            "date": date,
            "text": text,
            "media_path": media_path
        })
    
    return parsed_messages
