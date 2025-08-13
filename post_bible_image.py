import os
import requests
from datetime import datetime
from dotenv import load_dotenv

# --- Step 1: Load Environment Variables from .env file ---
# This line looks for a .env file and loads the variables from it.
load_dotenv()

# --- Step 2: Configuration ---
# The script will now read the secrets loaded from your .env file.
PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN")

IMAGES_DIR = "images"
CAPTION_TEMPLATE = "📖 Bible Story - {}"
STATE_FILE = "last_posted.txt"

def get_next_image():
    """Finds the next sequential image to post based on the state file."""
    try:
        # List and sort files by the number in their filename
        files = sorted(
            [f for f in os.listdir(IMAGES_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg"))],
            key=lambda x: int(''.join(filter(str.isdigit, x)))
        )
    except FileNotFoundError:
        print(f"❌ Error: The directory '{IMAGES_DIR}' was not found.")
        return None, None, None
    except ValueError:
        print(f"❌ Error: Could not sort images. Ensure filenames contain numbers (e.g., 'story1.png').")
        return None, None, None

    if not files:
        print(f"❌ Error: No images found in the '{IMAGES_DIR}' directory.")
        return None, None, None

    # Read the index of the last image that was successfully posted
    last_posted_index = -1 # Start at -1, so the first image to post is index 0
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            try:
                last_posted_index = int(f.read().strip())
            except (ValueError, TypeError):
                print(f"⚠️ Warning: Could not read {STATE_FILE}. Starting from the beginning.")
                last_posted_index = -1

    next_index_to_post = last_posted_index + 1

    # Get next file (if one exists)
    if next_index_to_post < len(files):
        next_file = files[next_index_to_post]
        print(f"✅ Found next image to post: {next_file} (Index: {next_index_to_post})")
        return next_file, os.path.join(IMAGES_DIR, next_file), next_index_to_post
    else:
        print("✅ All images have been posted. Nothing new to post.")
        return None, None, None

def update_state_file(last_successful_index):
    """Saves the index of the last successfully posted image."""
    print(f"💾 Saving state. Next run will look for image at index {last_successful_index + 1}.")
    with open(STATE_FILE, "w") as f:
        f.write(str(last_successful_index))

def post_image():
    """Fetches the next image and posts it to the Facebook page."""
    # Check if credentials were loaded correctly
    if not PAGE_ID or not ACCESS_TOKEN:
        print("="*50)
        print("❌ FATAL ERROR: Credentials not found.")
        print("Please ensure you have a .env file in the same directory as the script,")
        print("and it contains your FACEBOOK_PAGE_ID and FACEBOOK_ACCESS_TOKEN.")
        print("="*50)
        return

    image_name, image_path, image_index = get_next_image()
    if not image_path:
        return # Stop if there are no new images

    caption = CAPTION_TEMPLATE.format(datetime.now().strftime("%B %d, %Y"))
    print(f"📤 Preparing to post '{image_name}' with caption: '{caption}'")

    url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/photos"
    params = {
        "caption": caption,
        "access_token": ACCESS_TOKEN
    }

    try:
        with open(image_path, 'rb') as img_file:
            files = {"source": img_file}
            response = requests.post(url, params=params, files=files, timeout=300)

        # This will raise an error for bad responses like 400 (bad request) or 403 (permission error)
        response.raise_for_status()
        
        response_data = response.json()
        print(f"✅✅✅ SUCCESS! Image posted to Facebook.")
        print(f"   Post ID: {response_data.get('post_id')}")
        
        # IMPORTANT: Only update the state file on a successful post
        update_state_file(image_index)

    except FileNotFoundError:
        print(f"❌ Error: Image file not found at path: {image_path}")
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP ERROR: Failed to post to Facebook. The API returned an error.")
        print(f"   Status Code: {e.response.status_code}")
        print(f"   Response from Facebook: {e.response.json()}")
        print("   Check your Access Token permissions and Page ID.")
    except requests.exceptions.RequestException as e:
        print(f"❌ NETWORK ERROR: Could not connect to Facebook. Check your internet connection.")
        print(f"   Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


# --- Step 3: Run the main function ---
if __name__ == "__main__":
    print("--- Starting Bible Story Poster ---")
    post_image()
    print("--- Script finished ---")