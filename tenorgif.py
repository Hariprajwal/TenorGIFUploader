import yt_dlp
import os
import math
import subprocess
import time
import webbrowser
import pyautogui
import pyperclip
import google.generativeai as genai
import platform
import sys
import re

# Global variables
N = 0  # Will be set dynamically based on number of GIFs created
TAGS = []  # Will store generated tags

def sanitize_filename(name):
    """
    Sanitize filename to remove invalid characters and limit length
    """
    # Remove invalid characters for Windows filenames
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '')
    
    # Limit length to avoid Windows path issues
    if len(name) > 100:
        name = name[:100]
    
    # Remove any leading/trailing spaces or dots
    name = name.strip().strip('.')
    
    return name

def download_video_from_url(url):
    """
    Downloads the best quality video from a given URL using yt-dlp.
    Returns the path to the downloaded video file and the video title.
    """
    
    # Define the directory to save the file
    download_dir = "D:\\downloads"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    # Define the options for yt-dlp
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', 
        'outtmpl': os.path.join(download_dir, '%(title)s [%(id)s].%(ext)s'),
        'noprogress': False, 
        'noplaylist': True,
    }

    print(f"Attempting to download: {url}")
    
    try:
        # Use YoutubeDL to get video info and download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract video info to get the filename and title
            info = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info)
            video_title = info.get('title', 'Unknown_Title')
            video_description = info.get('description', '')
            video_tags = info.get('tags', [])
        
        print("\n✅ Download complete!")
        return downloaded_file, video_title, video_description, video_tags

    except yt_dlp.utils.DownloadError as e:
        print(f"\n❌ An error occurred during download: {e}")
        return None, None, None, None
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
        return None, None, None, None

def video_to_gifs(video_path, output_dir, clip_length=3, fps=15):
    """
    Converts a video file to multiple GIF clips.
    Returns the number of GIFs created.
    """
    global N
    
    # Ensure output folder exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"📂 Created output directory: {output_dir}")
    else:
        print(f"📂 Using existing output directory: {output_dir}")

    # Get video duration using ffprobe
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    try:
        duration = float(result.stdout.strip())
    except ValueError:
        print("❌ Could not read video duration. Check ffmpeg installation.")
        return 0

    print(f"Video length: {duration:.2f} seconds")

    # Number of GIFs to create
    num_clips = math.ceil(duration / clip_length)
    N = num_clips  # Set global N
    print(f"Creating {num_clips} GIF clips of {clip_length} seconds each...")

    for i in range(num_clips):
        start = i * clip_length
        output_path = os.path.join(output_dir, f"output_{i+1}.gif")

        # ffmpeg command
        command = [
            "ffmpeg", "-y",             
            "-ss", str(start),          
            "-t", str(clip_length),     
            "-i", video_path,           
            "-vf", f"fps={fps},scale=480:-1:flags=lanczos", 
            output_path
        ]

        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        print(f"✅ Saved: {output_path}")
    
    return num_clips

def setup_gemini(video_title, video_description, video_tags):
    """Configure the Gemini AI for tag generation using gemini-2.0-flash-exp based on YouTube video content"""
    global TAGS
    
    try:
        genai.configure(api_key="YOR API KEY ")
        
        # Use the specified model
        model_name = "gemini-2.0-flash-exp"
        print(f"✅ Using model: {model_name}")
        model = genai.GenerativeModel(model_name=model_name)
        
        # Generate tags based on YouTube video content
        print("🤖 Generating tags with Gemini AI based on YouTube video content...")
        
        # Prepare context from YouTube video
        context = f"Video Title: {video_title}"
        if video_description:
            # Limit description length to avoid token limits
            short_description = video_description[:500] + "..." if len(video_description) > 500 else video_description
            context += f"\nVideo Description: {short_description}"
        if video_tags:
            context += f"\nVideo Tags: {', '.join(video_tags[:10])}"  # Limit to first 10 tags
        
        prompt = f"""
        Based on this YouTube video content:
        {context}
        
        Generate 14 short, SEO-friendly hashtags specifically relevant to this video's content. 
        Focus on tags that would be appropriate for GIF clips from this video.
        Include a mix of:
        - Specific tags related to the video content
        - Trending/viral tags
        - Entertainment/comedy tags
        - Popular culture tags
        
        Only output the tags separated by commas, no other text.
        """
        
        response = model.generate_content(prompt)
        text_response = response.text.strip()
        TAGS = [tag.strip() for tag in text_response.replace("\n", "").split(",") if tag.strip()]
        
        # Ensure we have exactly 14 tags
        if len(TAGS) < 14:
            print(f"⚠️  Generated only {len(TAGS)} tags, adding some defaults...")
            default_tags = ["#gif", "#animation", "#funny", "#meme", "#trending", "#viral", "#entertainment", "#comedy", "#dance", "#viralvideo", "#fun", "#lol", "#popular", "#fyp"]
            # Add defaults without duplicates
            for tag in default_tags:
                if tag not in TAGS and len(TAGS) < 14:
                    TAGS.append(tag)
        else:
            TAGS = TAGS[:14]
            
        print("✅ Tags generated based on YouTube content:", TAGS)
        return True
        
    except Exception as e:
        print(f"❌ Gemini AI setup failed: {e}")
        # Fallback to video-based tags or defaults
        if video_tags:
            TAGS = [f"#{tag.replace(' ', '')}" for tag in video_tags[:14]]
            if len(TAGS) < 14:
                TAGS.extend(["#gif", "#animation", "#funny", "#meme", "#trending", "#viral"])
                TAGS = TAGS[:14]
        else:
            TAGS = ["#gif", "#animation", "#funny", "#meme", "#trending", "#viral", "#entertainment", "#comedy", "#dance", "#viralvideo", "#fun", "#lol", "#popular", "#fyp"]
        print("✅ Using fallback tags:", TAGS)
        return False

def navigate_to_tenor():
    """Navigate to Tenor upload page and click the specified buttons"""
    print("🌐 Opening Tenor GIF Maker...")
    url = "https://tenor.com/gif-maker?utm_source=nav-bar&utm_medium=internal&utm_campaign=gif-maker-entrypoints"

    if platform.system() == "Windows":
        subprocess.Popen(f'start opera "{url}"', shell=True)
    elif platform.system() == "Darwin":  # macOS
        subprocess.Popen(['open', '-a', 'Opera', url])
    else:  # Linux
        subprocess.Popen(['opera', url])
    
    # Wait for browser to open and ensure Opera is in focus
    print("⏳ Waiting 7 seconds for Opera to load...")
    time.sleep(7)
    
    # Ensure Opera window is active
    pyautogui.click(960, 540)  # Click center of screen to focus Opera
    time.sleep(1)
    
    # FIRST CLICK: Click at (1303, 672)
    print("🖱 FIRST CLICK at (1303, 672)...")
    pyautogui.click(1303, 672)
    
    # Wait for 3 seconds
    print("⏳ Waiting 3 seconds...")
    time.sleep(3)
    
    # SECOND CLICK: Click at (1846, 968)
    print("🖱 SECOND CLICK at (1846, 968)...")
    pyautogui.click(1846, 968)
    time.sleep(2)

def click_upload_area():
    """Click on the upload area coordinates"""
    print("🖱 Clicking upload area...")
    pyautogui.click(1312, 700)
    time.sleep(2)

def open_files_batch_new(start, end, output_dir, batch_num):
    """Open files from start to end index - navigate to GIF directory and select files"""
    print(f"📁 Opening files: output_{start}.gif to output_{end}.gif")
    
    try:
        from pywinauto.application import Application
        
        # Ensure we're in Opera window
        pyautogui.click(960, 540)  # Click to focus Opera
        time.sleep(1)
        
        app = Application().connect(title="Open")
        dlg = app.window(title="Open")
        
        # Only navigate to directory for BATCH 1
        if batch_num == 0:  # First batch (batch_num starts at 0)
            # Type the full output directory path directly
            print(f"📂 Navigating to GIF directory: {output_dir}")
            
            # Clear any existing text and type the directory path
            dlg["Edit"].set_text("")
            time.sleep(0.5)
            dlg["Edit"].type_keys(output_dir, with_spaces=True)
            time.sleep(1)
            pyautogui.press('enter')
            
            # Wait 2 seconds as requested
            print("⏳ Waiting 2 seconds after navigation...")
            time.sleep(2)
        else:
            # For batch 2 onwards, already in the directory, just select files
            print("📂 Already in directory, selecting files directly...")
        
        # Now type the specific file names
        file_names = ' '.join([f'"output_{i}.gif"' for i in range(start, end + 1)])
        print(f"📄 Typing file names: {file_names}")
        
        # Clear the filename field and type the file names
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.3)
        pyperclip.copy(file_names)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(1)
        
        # Click Open button
        print("🖱 Clicking Open button...")
        dlg["Open"].click()
        
        # Wait for files to open - REDUCED TO 5 SECONDS
        print("⏳ Waiting 5 seconds for files to process...")
        time.sleep(5)
        return True
        
    except Exception as e:
        print(f"❌ Error opening files: {e}")
        return False

def paste_tags_at_coordinates():
    """Paste ALL 14 TAGS at each of the 4 coordinates - same tags for all files (including safety coordinate)"""
    print("🏷 Pasting ALL 14 tags at each coordinate...")
    
    # Wait 10 seconds before starting tag pasting
    print("⏳ Waiting 10 seconds before pasting tags...")
    time.sleep(1)
    
    # Convert all tags to a single string separated by spaces
    all_tags_string = " ".join(TAGS)
    print(f"📋 Tags to paste: {all_tags_string}")
    
    # Updated coordinates for 4 tag fields (3 main + 1 safety)
    coordinates = [
        (567, 311),  # Tag field 1
        (561, 509),  # Tag field 2
        (564, 709),  # Tag field 3
        (558, 898),  # Tag field 4 (SAFETY - EXTRA STEP)
    ]
    
    # Paste ALL 14 tags at EACH coordinate (4 times total - including safety)
    for i in range(4):
        if i == 3:
            print(f"🏷 SAFETY STEP: Pasting ALL 14 tags at coordinate {i+1}: ({coordinates[i][0]}, {coordinates[i][1]})")
        else:
            print(f"🏷 Pasting ALL 14 tags at coordinate {i+1}: ({coordinates[i][0]}, {coordinates[i][1]})")
        
        # Click on tag field
        pyautogui.click(coordinates[i][0], coordinates[i][1])
        time.sleep(1)
        
        # Paste ALL tags
        pyperclip.copy(all_tags_string)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(1)
    
    print("✅ ALL 14 tags pasted at all 4 coordinates successfully (including safety step)!")
    
    # INCREASED WAIT TIME TO 10 SECONDS AFTER 4TH SAFETY TAG
    print("⏳ Waiting 10 seconds after 4th safety tag...")
    time.sleep(1)
    
    # Click upload/submit button immediately after waiting
    print("🖱 Clicking Submit button at (1562, 709)...")
    pyautogui.click(1562, 709)
    
    # Wait 10 seconds after upload
    print("⏳ Waiting 10 seconds after upload...")
    time.sleep(13)

def wait_and_refresh():
    """Navigate back to Tenor page for next batch with proper loading"""
    print("🔄 Navigating back to Tenor page for next batch...")
    
    # Navigate to Tenor page in Opera
    tenor_url = "https://tenor.com/gif-maker?utm_source=nav-bar&utm_medium=internal&utm_campaign=gif-maker-entrypoints"
    
    # Click at the new address bar location (283, 79) and select all
    print("📍 Clicking address bar at (283, 79)...")
    pyautogui.click(283, 79)
    time.sleep(1)
    
    # Select all text in address bar
    print("📝 Selecting all text in address bar...")
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.5)
    
    # Paste the Tenor URL
    print("📋 Pasting Tenor URL...")
    pyperclip.copy(tenor_url)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(1)
    pyautogui.press('enter')
    
    # Wait 5 seconds for page to load
    print("⏳ Waiting 5 seconds for Tenor page to load...")
    time.sleep(5)
    
    print("✅ Tenor page loaded successfully!")
    
    # FIRST CLICK: Click at (1303, 672) - REQUIRED FOR EVERY BATCH
    print("🖱 FIRST CLICK at (1303, 672)...")
    pyautogui.click(1303, 672)
    
    # Wait for 3 seconds
    print("⏳ Waiting 3 seconds...")
    time.sleep(3)
    
    # SECOND CLICK: Click at (1846, 968) - REQUIRED FOR EVERY BATCH
    print("🖱 SECOND CLICK at (1846, 968)...")
    pyautogui.click(1846, 968)
    time.sleep(2)
    
    print("✅ Ready for next batch upload!")

def process_tenor_upload(output_dir, video_title, video_description, video_tags):
    """Main Tenor upload automation - batches of 3 with remainder handling"""
    global N
    
    print(f"🚀 Starting Tenor upload automation for {N} GIFs...")
    print(f"📁 GIF Directory: {output_dir}")
    
    # Setup Gemini for tags with YouTube video content
    setup_gemini(video_title, video_description, video_tags)
    
    # Navigate to Tenor and click the specified buttons
    navigate_to_tenor()
    
    # Calculate batches - 3 files per batch
    batch_size = 3
    total_batches = math.ceil(N / batch_size)  # This handles remainder automatically
    
    print(f"📦 Total batches to process: {total_batches}")
    print(f"📊 Breakdown: {N} GIFs ÷ 3 = {N // 3} full batches + {N % 3} remainder")
    
    for batch_num in range(total_batches):
        print(f"\n{'='*50}")
        print(f"📦 Processing Batch {batch_num + 1}/{total_batches}")
        print(f"{'='*50}")
        
        # Ensure Opera is focused
        pyautogui.click(960, 540)
        time.sleep(1)
        
        # Calculate file range for this batch
        start_file = (batch_num * batch_size) + 1
        end_file = min((batch_num + 1) * batch_size, N)
        
        files_in_batch = end_file - start_file + 1
        print(f"📄 This batch contains {files_in_batch} file(s)")
        
        # Click upload area
        click_upload_area()
        
        # Open files batch with new navigation method
        if open_files_batch_new(start_file, end_file, output_dir, batch_num):
            print(f"✅ Successfully opened files {start_file} to {end_file}")
            
            # Click next coordinate
            pyautogui.click(1844, 978)
            time.sleep(3)
            
            # Paste ALL 14 tags at all 3 coordinates (same tags for every batch)
            paste_tags_at_coordinates()
            
            # If not the last batch, navigate back to Tenor page
            if batch_num < total_batches - 1:
                wait_and_refresh()
            else:
                print("🎉 All batches processed! Upload completed.")
        else:
            print(f"❌ Failed to open batch {batch_num + 1}")

# --- Main Program Execution ---
if __name__ == "__main__":
    
    # Step 1: Download video from URL
    print("🎥 VIDEO DOWNLOADER & GIF CONVERTER")
    print("=" * 40)
    
    video_link = input("Paste the video URL and press Enter: ").strip()

    if not video_link:
        print("No URL provided. Exiting.")
        exit()

    # Download the video and get the title, description, and tags
    downloaded_video_path, video_title, video_description, video_tags = download_video_from_url(video_link)
    
    if not downloaded_video_path or not os.path.exists(downloaded_video_path):
        print("❌ Video download failed. Exiting.")
        exit()

    print(f"📁 Downloaded video: {downloaded_video_path}")
    print(f"🎬 Video title: {video_title}")
    if video_description:
        print(f"📝 Video description: {video_description[:100]}...")
    if video_tags:
        print(f"🏷 Video tags: {', '.join(video_tags[:5])}...")
    
    # Step 2: Convert to GIFs
    print("\n" + "=" * 40)
    print("🔄 CONVERTING TO GIFS")
    print("=" * 40)
    
    # Create folder name from video title (sanitized) - without underscores, with .gifs extension
    folder_name = sanitize_filename(video_title.replace(" ", "")) + ".gifs"
    final_output_dir = os.path.join(r"C:\Users\harip\ALL TEST", folder_name)
    
    print(f"🎯 Creating GIFs in: {final_output_dir}")
    
    # Convert the downloaded video to GIFs
    video_to_gifs(downloaded_video_path, final_output_dir)
    
    print(f"\n📊 Total GIFs created: {N}")
    
    # Step 3: Automatic Tenor upload start after 10 seconds
    print("\n" + "=" * 50)
    print("🤖 TENOR UPLOAD AUTOMATION")
    print("=" * 50)
    
    print("⚠  WARNING: Do not move mouse or keyboard during automation!")
    print("🚀 Starting Tenor automation in 10 seconds...")
    
    # Countdown
    for i in range(10, 0, -1):
        print(f"Starting in {i} seconds...")
        time.sleep(1)
    
    print("🎬 Starting automation NOW!")
    
    # Safety settings for pyautogui
    pyautogui.FAILSAFE = True
    
    try:
        # Start Tenor upload automation with YouTube video context
        process_tenor_upload(final_output_dir, video_title, video_description, video_tags)
        
        print("\n🎉 All processes completed successfully!")
        print(f"📁 Video downloaded to: {downloaded_video_path}")
        print(f"📁 GIFs saved to: {final_output_dir}")
        print(f"📊 Total GIFs created: {N}")
        if TAGS:
            print(f"🏷  Tags generated: {', '.join(TAGS)}")
            
    except KeyboardInterrupt:
        print("\n🛑 Automation interrupted by user!")
    except Exception as e:
        print(f"\n❌ Unexpected error during automation: {e}")
        print("💡 Tip: If automation failed, check if all required packages are installed.")
    
    finally:
        print("\n🔒 Automation session ended.")
