import os
import requests
from datetime import datetime
from dotenv import load_dotenv
import schedule
import time
import threading
from flask import Flask

# --- Step 1: Load Environment Variables ---
load_dotenv()

# --- Step 2: Configuration ---
PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN")
IMAGES_DIR = "images"
CAPTION_TEMPLATE = "📖 Bible Story - {}"

# Use Render's persistent disk path if available, otherwise use the local folder
STATE_DIR = os.getenv("RENDER_DISK_MOUNT_PATH", ".")
STATE_FILE = os.path.join(STATE_DIR, "last_posted.txt")

# --- Step 3: All Your Posting Logic (Functions remain the same) ---
def get_next_image():
    """Finds the next sequential image to post based on the state file."""
    try:
        files = sorted(
            [f for f in os.listdir(IMAGES_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg"))],
            key=lambda x: int(''.join(filter(str.isdigit, x)))
        )
    except FileNotFoundError:
        print(f"❌ Error: The directory '{IMAGES_DIR}' was not found.")
        return None, None, None
    if not files:
        print(f"❌ Error: No images found in the '{IMAGES_DIR}' directory.")
        return None, None, None
    last_posted_index = -1
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            try:
                last_posted_index = int(f.read().strip())
            except (ValueError, TypeError):
                last_posted_index = -1
    next_index_to_post = last_posted_index + 1
    if next_index_to_post < len(files):
        next_file = files[next_index_to_post]
        return next_file, os.path.join(IMAGES_DIR, next_file), next_index_to_post
    else:
        print("✅ All images have been posted.")
        return None, None, None

def update_state_file(last_successful_index):
    """Saves the index of the last successfully posted image."""
    print(f"💾 Saving state. Next run will look for index {last_successful_index + 1}.")
    with open(STATE_FILE, "w") as f:
        f.write(str(last_successful_index))

def post_image():
    """Fetches the next image and posts it to the Facebook page."""
    print("--- ⏰ Scheduler triggered! Checking for image to post... ---")
    if not PAGE_ID or not ACCESS_TOKEN:
        print("❌ Error: Facebook credentials not set in environment variables.")
        return
    image_name, image_path, image_index = get_next_image()
    if not image_path:
        return
    caption = CAPTION_TEMPLATE.format(datetime.now().strftime("%B %d, %Y"))
    print(f"📤 Posting '{image_name}' with caption: '{caption}'")
    url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/photos"
    params = {"caption": caption, "access_token": ACCESS_TOKEN}
    try:
        with open(image_path, 'rb') as img_file:
            files = {"source": img_file}
            response = requests.post(url, params=params, files=files, timeout=300)
        response.raise_for_status()
        print(f"✅✅✅ SUCCESS! Post ID: {response.json().get('post_id')}")
        update_state_file(image_index)
    except Exception as e:
        print(f"❌ FAILED to post to Facebook: {e}")

# --- Step 4: The Web Server for Pinging ---
app = Flask(__name__)

@app.route('/')
def home():
    """This is the endpoint that UptimeRobot will ping."""
    return "I'm alive!"

# --- Step 5: The Scheduler running in a background thread ---
def run_schedule():
    """Continuously runs the scheduler."""
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # Configure the schedule
    # Set your desired posting time in UTC. 02:30 UTC is 8:00 AM IST.
    schedule.every().day.at("02:30").do(post_image)
    print("Scheduler configured. Starting background thread.")

    # Start the scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_schedule)
    scheduler_thread.daemon = True
    scheduler_thread.start()

    # Start the Flask web server
    # The 'port' is read from an environment variable set by Render.
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting web server on port {port} to keep alive.")
    app.run(host='0.0.0.0', port=port)