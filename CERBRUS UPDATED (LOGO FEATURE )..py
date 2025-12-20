from pytubefix import YouTube
from pytubefix.cli import on_progress
import os
import math
import subprocess
import time
import webbrowser
import pyautogui
import pyperclip
import platform
import sys
import re

# Install and import Cerebras SDK
try:
    from cerebras.cloud.sdk import Cerebras
except ImportError:
    print("Installing Cerebras SDK...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "cerebras-cloud-sdk"])
    from cerebras.cloud.sdk import Cerebras

# Global variables
N = 0  # Will be set dynamically based on number of GIFs created
TAGS = []  # Will store generated tags
CURRENT_VIDEO_INDEX = 0  # Track current video being processed
ALL_VIDEO_URLS = []  # Store all video URLs
UNIVERSAL_TAG = "#HariPrajwal"  # Universal tag to be added to all GIFs
LOGO_PATH = "KRHP LOGO .png"  # Path to your logo file

def extract_urls_from_input(user_input):
    """
    Extract multiple URLs from user input using space or comma separation
    AND handle continuous links without separators
    """
    urls = []
    
    # First, try to find URLs using regex pattern
    url_pattern = r'https?://[^\s,]+'
    found_urls = re.findall(url_pattern, user_input)
    
    if found_urls:
        # If regex found URLs, use them
        urls = found_urls
    else:
        # Fallback: split by both commas and spaces
        raw_urls = re.split(r'[,\s]+', user_input)
        
        for url in raw_urls:
            url = url.strip()
            # Basic URL validation
            if url and (url.startswith('http://') or url.startswith('https://')):
                urls.append(url)
    
    return urls

def check_existing_gifs(output_dir):
    """
    Check if GIF files already exist in the output directory
    Returns: (bool_exists, int_count)
    """
    if not os.path.exists(output_dir):
        return False, 0
    
    try:
        gif_files = [f for f in os.listdir(output_dir) if f.endswith('.gif') and f.startswith('output_')]
        
        if gif_files:
            print(f"📁 Found {len(gif_files)} existing GIF files in directory")
            return True, len(gif_files)
        
        return False, 0
    except Exception as e:
        print(f"⚠️  Error checking existing GIFs: {e}")
        return False, 0

def sanitize_filename(name):
    """
    Sanitize filename to remove invalid characters and limit length
    MORE ROBUST HANDLING FOR COMPLEX FILENAMES
    """
    if not name:
        return "Unknown_Video"
    
    # Replace multiple spaces with single space
    name = re.sub(r'\s+', ' ', name)
    
    # Remove invalid characters for Windows filenames
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '')
    
    # Limit length to avoid Windows path issues - INCREASED FOR LONG NAMES
    if len(name) > 150:  # Increased from 100 to 150
        # Try to keep important parts of the name
        name = name[:150]
    
    # Remove any leading/trailing spaces, dots, or hyphens
    name = name.strip().strip('.').strip('-')
    
    # If name becomes empty after sanitization, use default
    if not name:
        name = "Unknown_Video"
    
    return name

def robust_directory_creation(directory_path):
    """
    More robust directory creation that handles various edge cases
    """
    try:
        if not os.path.exists(directory_path):
            os.makedirs(directory_path, exist_ok=True)
            print(f"📂 Created directory: {directory_path}")
        else:
            print(f"📂 Using existing directory: {directory_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to create directory {directory_path}: {e}")
        # Fallback: try to create in a simpler location
        try:
            fallback_dir = r"C:\Users\harip\ALL TEST\Fallback_GIFs"
            os.makedirs(fallback_dir, exist_ok=True)
            print(f"📂 Using fallback directory: {fallback_dir}")
            return fallback_dir
        except:
            print("❌ Critical: Could not create any directory")
            return False

def download_video_from_url(url):
    """
    Downloads the best quality video from a given URL using pytubefix.
    Returns the path to the downloaded video file and the video title.
    """
    
    # Define the directory to save the file
    download_dir = "D:\\downloads"
    if not robust_directory_creation(download_dir):
        return None, None, None, None

    print(f"🎥 Attempting to download: {url}")
    
    try:
        # Create YouTube object
        yt = YouTube(url, on_progress_callback=on_progress)
        
        # Get the highest resolution stream
        stream = yt.streams.get_highest_resolution()
        
        # Sanitize filename
        safe_filename = sanitize_filename(yt.title)
        filename = f"{safe_filename} [{yt.video_id}].mp4"
        file_path = os.path.join(download_dir, filename)
        
        # Download the video
        print("📥 Downloading video...")
        stream.download(output_path=download_dir, filename=filename)
        
        video_title = yt.title
        video_description = yt.description
        video_tags = yt.keywords if hasattr(yt, 'keywords') else []
        
        print("✅ Download complete!")
        return file_path, video_title, video_description, video_tags

    except Exception as e:
        print(f"❌ An error occurred during download: {e}")
        return None, None, None, None

def video_to_gifs(video_path, output_dir, clip_length=3, fps=15):
    """
    Converts a video file to multiple GIF clips with KRHP logo watermark.
    Returns the number of GIFs created.
    """
    global N
    
    # Ensure output folder exists with robust creation
    if not robust_directory_creation(output_dir):
        return 0

    # Check if logo file exists
    if not os.path.exists(LOGO_PATH):
        print(f"⚠️  Logo file '{LOGO_PATH}' not found! GIFs will be created without watermark.")
        use_logo = False
    else:
        use_logo = True
        print(f"✅ Logo file found: {LOGO_PATH}")
        print("🖼️  Adding KRHP logo watermark to all GIFs (50% opacity, bottom center)...")

    # Get video duration using ffprobe
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        duration = float(result.stdout.strip())
    except (ValueError, subprocess.SubprocessError) as e:
        print(f"❌ Could not read video duration: {e}")
        return 0

    print(f"⏱ Video length: {duration:.2f} seconds")
    
    # SKIP FIRST 5 SECONDS AND LAST 5 SECONDS
    usable_duration = duration - 10  # Subtract 10 seconds (5 from start + 5 from end)
    
    if usable_duration <= 0:
        print("❌ Video is too short after skipping first and last 5 seconds")
        return 0
        
    print(f"🎯 Usable duration (after skipping first/last 5s): {usable_duration:.2f} seconds")

    # Number of GIFs to create
    num_clips = math.ceil(usable_duration / clip_length)
    N = num_clips  # Set global N
    print(f"🔄 Creating {num_clips} GIF clips of {clip_length} seconds each...")

    successful_conversions = 0
    for i in range(num_clips):
        start = (i * clip_length) + 5  # ADD 5 SECONDS TO SKIP THE BEGINNING
        output_path = os.path.join(output_dir, f"output_{i+1}.gif")
        
        if use_logo:
            # ffmpeg command with logo watermark (50% opacity, bottom center)
            command = [
                "ffmpeg", "-y",
                "-ss", str(start),
                "-t", str(clip_length),
                "-i", video_path,
                "-i", LOGO_PATH,  # Add logo as second input
                "-filter_complex", 
                # Scale video, then overlay logo with 50% opacity at bottom center
                "[0:v]fps=15,scale=480:-1:flags=lanczos[bg];"
                "[1:v]scale=150:-1[logo_scaled];"  # Scale logo to 150px width (adjustable)
                "[logo_scaled]colorchannelmixer=aa=0.5[logo_transparent];"  # 50% opacity
                "[bg][logo_transparent]overlay=(main_w-overlay_w)/2:(main_h-overlay_h-20)",
                output_path
            ]
        else:
            # Original ffmpeg command without logo
            command = [
                "ffmpeg", "-y",             
                "-ss", str(start),          
                "-t", str(clip_length),     
                "-i", video_path,           
                "-vf", f"fps={fps},scale=480:-1:flags=lanczos", 
                output_path
            ]

        try:
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode == 0:
                if use_logo:
                    print(f"✅ Saved with logo: output_{i+1}.gif")
                else:
                    print(f"✅ Saved: output_{i+1}.gif")
                successful_conversions += 1
            else:
                print(f"⚠️  Failed to create: output_{i+1}.gif - {result.stderr[:100]}")
                # Try fallback without logo if logo failed
                if use_logo:
                    print("🔄 Trying fallback without logo...")
                    fallback_command = [
                        "ffmpeg", "-y",             
                        "-ss", str(start),          
                        "-t", str(clip_length),     
                        "-i", video_path,           
                        "-vf", f"fps={fps},scale=480:-1:flags=lanczos", 
                        output_path
                    ]
                    fallback_result = subprocess.run(fallback_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    if fallback_result.returncode == 0:
                        print(f"✅ Saved (fallback): output_{i+1}.gif")
                        successful_conversions += 1
                    
        except Exception as e:
            print(f"❌ Error creating output_{i+1}.gif: {e}")
    
    if use_logo and successful_conversions > 0:
        print(f"🎨 KRHP logo successfully added to {successful_conversions} GIFs!")
    print(f"📊 Successfully created {successful_conversions}/{num_clips} GIFs")
    return successful_conversions

def setup_cerebras(video_title, video_description, video_tags):
    """Configure the Cerebras AI for tag generation using llama-3.3-70b based on YouTube video content"""
    global TAGS, UNIVERSAL_TAG
    
    try:
        # Initialize Cerebras client with your API key
        client = Cerebras(
            api_key=""
        )
        
        # Generate tags based on YouTube video content
        print("🤖 Generating tags with Cerebras AI based on YouTube video content...")
        
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
        Focus on tags that would be appropriate for GIF clips from this video. Ensure it has movie name as first, then the heroine, then the hero, and then follow the most popular part of that movie.
        
        IMPORTANT FORMATTING RULES:
        1. Output ONLY the 14 tags separated by commas
        2. Each tag should be a single hashtag (e.g., #MovieName, #ActressName, #ActorName)
        3. Do not combine multiple tags into one string
        4. No additional text, explanations, or formatting
        5. Example format: #RRR, #AliaBhatt, #RamCharan, #NaatuNaatu, #Dance, #Trending, #Viral, #TeluguMovie, #Blockbuster, #Oscar, #Music, #Action, #Epic, #IndianCinema
        
        Generate exactly 14 tags in this format.
        """
        
        # Create a chat completion with Cerebras
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b",
            max_completion_tokens=1024,
            temperature=0.2,
            top_p=1,
            stream=False
        )
        
        text_response = completion.choices[0].message.content.strip()
        
        # DEBUG: Print the raw response to see what the AI is returning
        print(f"🔍 RAW AI RESPONSE: '{text_response}'")
        
        # MORE ROBUST TAG PARSING
        # Step 1: Clean up the response
        cleaned_response = text_response.strip()
        
        # Step 2: Remove common prefixes/suffixes that might cause issues
        prefixes_to_remove = ["Here are the tags:", "Tags:", "Generated tags:", "The tags are:"]
        for prefix in prefixes_to_remove:
            if cleaned_response.startswith(prefix):
                cleaned_response = cleaned_response[len(prefix):].strip()
        
        # Step 3: Try multiple splitting strategies
        tags_list = []
        
        # Strategy 1: Split by comma (primary method)
        if ',' in cleaned_response:
            temp_tags = [tag.strip() for tag in cleaned_response.split(',') if tag.strip()]
            if temp_tags:
                tags_list = temp_tags
                print(f"📝 Parsed {len(tags_list)} tags using comma separation")
        
        # Strategy 2: If comma splitting failed or gave too few tags, try space splitting
        if len(tags_list) < 5 and ' ' in cleaned_response:
            temp_tags = [tag.strip() for tag in cleaned_response.split() if tag.strip() and tag.strip().startswith('#')]
            if len(temp_tags) > len(tags_list):
                tags_list = temp_tags
                print(f"📝 Parsed {len(tags_list)} tags using space separation (hashtag detection)")
        
        # Strategy 3: If still having issues, extract hashtags using regex
        if len(tags_list) < 3:
            import re
            hashtag_pattern = r'#\w+'
            hashtags = re.findall(hashtag_pattern, cleaned_response)
            if hashtags:
                tags_list = hashtags
                print(f"📝 Parsed {len(tags_list)} tags using regex hashtag extraction")
        
        # Step 4: Clean and validate individual tags
        validated_tags = []
        for tag in tags_list:
            # Remove any trailing punctuation
            tag = tag.rstrip('.,;:!?')
            
            # Ensure it starts with #
            if not tag.startswith('#'):
                tag = '#' + tag
            
            # Remove any internal problematic characters
            tag = tag.replace(' ', '').replace('-', '').replace('_', '')
            
            # Limit tag length
            if len(tag) > 30:
                tag = tag[:30]
            
            # Add to validated list if not a duplicate
            if tag and tag not in validated_tags:
                validated_tags.append(tag)
        
        # Step 5: Ensure we have exactly 14 tags (excluding the universal tag)
        print(f"📊 Generated {len(validated_tags)} unique tags after validation")
        
        if len(validated_tags) < 14:
            print(f"⚠️  Generated only {len(validated_tags)} tags, adding some defaults...")
            default_tags = [
                "#gif", "#animation", "#funny", "#meme", "#trending", 
                "#viral", "#entertainment", "#comedy", "#dance", 
                "#viralvideo", "#fun", "#lol", "#popular", "#fyp"
            ]
            # Add defaults without duplicates
            for tag in default_tags:
                if tag not in validated_tags and len(validated_tags) < 14:
                    validated_tags.append(tag)
        
        # Take only first 14 tags
        validated_tags = validated_tags[:14]
        
        # Step 6: ADD UNIVERSAL TAG AT THE END (making total 15 tags)
        # Remove the universal tag if it already exists in the list to avoid duplicates
        if UNIVERSAL_TAG in validated_tags:
            validated_tags.remove(UNIVERSAL_TAG)
            print(f"⚠️  Removed duplicate {UNIVERSAL_TAG} from AI-generated tags")
        
        # Add the universal tag as the last tag
        validated_tags.append(UNIVERSAL_TAG)
        
        TAGS = validated_tags
        
        print(f"✅ FINAL TAGS ({len(TAGS)} total): {', '.join(TAGS)}")
        print(f"🌟 Universal tag '{UNIVERSAL_TAG}' added to all GIFs!")
        return True
        
    except Exception as e:
        print(f"❌ Cerebras AI setup failed: {e}")
        # Fallback to video-based tags or defaults with universal tag
        if video_tags:
            TAGS = [f"#{tag.replace(' ', '')}" for tag in video_tags[:14]]
            if len(TAGS) < 14:
                TAGS.extend(["#gif", "#animation", "#funny", "#meme", "#trending", "#viral"])
                TAGS = TAGS[:14]
        else:
            TAGS = [
                "#gif", "#animation", "#funny", "#meme", "#trending", 
                "#viral", "#entertainment", "#comedy", "#dance", 
                "#viralvideo", "#fun", "#lol", "#popular", "#fyp"
            ]
            TAGS = TAGS[:14]
        
        # Add universal tag (remove if already exists to avoid duplicate)
        if UNIVERSAL_TAG in TAGS:
            TAGS.remove(UNIVERSAL_TAG)
        TAGS.append(UNIVERSAL_TAG)
        
        print("✅ Using fallback tags with universal tag:", ", ".join(TAGS))
        return False

def navigate_to_tenor():
    """Navigate to Tenor upload page using Chrome in new tab"""
    print("🌐 Opening Tenor GIF Maker in Chrome...")
    url = "https://tenor.com/gif-maker?utm_source=nav-bar&utm_medium=internal&utm_campaign=gif-maker-entrypoints"

    # Open in Chrome using new tab
    try:
        # This opens in a new tab in Chrome
        chrome_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
        if os.path.exists(chrome_path):
            subprocess.Popen([chrome_path, "--new-tab", url])
        else:
            # Fallback: use webbrowser with Chrome
            webbrowser.get('chrome').open_new_tab(url)
    except:
        # Final fallback: use default browser
        webbrowser.open_new_tab(url)
    
    # Wait for browser to open and ensure Chrome is in focus
    print("⏳ Waiting 7 seconds for Chrome to load...")
    time.sleep(10)
    
    # Ensure Chrome window is active
    pyautogui.click(960, 540)  # Click center of screen to focus Chrome
    time.sleep(2)
    
    # FIRST CLICK: Click at (1303, 672)
    print("🖱 FIRST CLICK at (1303, 672)...")
    pyautogui.click(1303, 672)
    
    # Wait for 3 seconds
    print("⏳ Waiting 3 seconds...")
    time.sleep(3)
    
    # SECOND CLICK: Click at (1846, 968)
    

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
        
        # Ensure we're in Chrome window
        pyautogui.click(960, 540)  # Click to focus Chrome
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
            
            # MORE ROBUST PATH HANDLING - Use clipboard for complex paths
            pyperclip.copy(output_dir)
            dlg["Edit"].type_keys("^v")  # Ctrl+V to paste
            
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
        time.sleep(7)
        return True
        
    except Exception as e:
        print(f"❌ Error opening files: {e}")
        return False

def paste_tags_at_coordinates():
    """Paste ALL TAGS (including universal tag) at each of the 5 coordinates - same tags for all files"""
    print("🏷 Pasting ALL tags at each coordinate...")
    
    # Wait 10 seconds before starting tag pasting
    print("⏳ Waiting 10 seconds before pasting tags...")
    time.sleep(1)
    
    # Convert all tags to a single string separated by spaces
    all_tags_string = " ".join(TAGS)
    print(f"📋 Tags to paste (total {len(TAGS)} tags): {all_tags_string}")
    print(f"🌟 Universal tag included: {UNIVERSAL_TAG}")
    
    # Updated coordinates for 5 tag fields (3 main + 2 safety)
    coordinates = [
        (567, 311),   # Tag field 1
        (561, 509),   # Tag field 2
        (564, 709),   # Tag field 3
        (558, 898),   # Tag field 4 (SAFETY - EXTRA STEP)
        (567, 1064)   # Tag field 5 (SAFETY - EXTRA STEP)
    ]
    
    # Paste ALL tags at EACH coordinate (5 times total - including safety)
    for i in range(5):
        if i >= 3:
            print(f"🏷 SAFETY STEP: Pasting ALL {len(TAGS)} tags at coordinate {i+1}: ({coordinates[i][0]}, {coordinates[i][1]})")
        else:
            print(f"🏷 Pasting ALL {len(TAGS)} tags at coordinate {i+1}: ({coordinates[i][0]}, {coordinates[i][1]})")
        
        # Click on tag field
        pyautogui.click(coordinates[i][0], coordinates[i][1])
        time.sleep(1)
        
        # Paste ALL tags
        pyperclip.copy(all_tags_string)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(1)

        # --- NEW: press ESC immediately after pasting for step 4 and 5 ---
        # i is 0-based: step 4 -> i == 3, step 5 -> i == 4
        if i in (3, 4):
            print(f"🔒 Safety action: pressing ESC after pasting on step {i+1}...")
            pyautogui.press('esc')
            time.sleep(0.5)
        # -----------------------------------------------------------------
    
    print("✅ ALL tags pasted at all 5 coordinates successfully (including safety steps)!")
    print(f"🌟 Universal tag '{UNIVERSAL_TAG}' included in all GIF uploads!")
    
    # INCREASED WAIT TIME TO 10 SECONDS AFTER 5TH SAFETY TAG
    print("⏳ Waiting 10 seconds after 5th safety tag...")
    time.sleep(1)
    
    
    # Click upload/submit button immediately after waiting
    print("🖱 Clicking Submit button at (1562, 709)...")
    pyautogui.click(1562, 709)
    
    # Wait 10 seconds after upload
    print("⏳ Waiting 10 seconds after upload...")
    time.sleep(20)

def wait_and_refresh():
    """Navigate back to Tenor page for next batch with proper loading"""
    print("🔄 Navigating back to Tenor page for next batch...")
    
    # Navigate to Tenor page in Chrome
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
    time.sleep(15)
    
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
    
    # Setup Cerebras for tags with YouTube video content
    setup_cerebras(video_title, video_description, video_tags)
    
    # Navigate to Tenor and click the specified buttons
    navigate_to_tenor()
    
    # Calculate batches - 3 files per batch
    batch_size = 2
    total_batches = math.ceil(N / batch_size)  # This handles remainder automatically
    
    print(f"📦 Total batches to process: {total_batches}")
    print(f"📊 Breakdown: {N} GIFs ÷ 2 = {N // 2} full batches + {N % 2} remainder")
    
    for batch_num in range(total_batches):
        print(f"\n{'='*50}")
        print(f"📦 Processing Batch {batch_num + 1}/{total_batches}")
        print(f"{'='*50}")
        
        # Ensure Chrome is focused
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
            
            # Paste ALL tags at all 5 coordinates (same tags for every batch)
            paste_tags_at_coordinates()
            
            # If not the last batch, navigate back to Tenor page
            if batch_num < total_batches - 1:
                wait_and_refresh()
            else:
                print("🎉 All batches processed! Upload completed.")
        else:
            print(f"❌ Failed to open batch {batch_num + 1}")

def process_single_video(url, total_videos, current_index):
    """Process a single video: download, convert to GIFs, and upload to Tenor"""
    global N, CURRENT_VIDEO_INDEX
    
    print(f"\n{'='*60}")
    print(f"🎬 PROCESSING VIDEO {current_index + 1} OF {total_videos}")
    print(f"🔗 URL: {url}")
    print(f"{'='*60}")
    
    # Step 1: Download video from URL
    print("🎥 VIDEO DOWNLOADER & GIF CONVERTER")
    print("=" * 40)
    
    # Download the video and get the title, description, and tags
    downloaded_video_path, video_title, video_description, video_tags = download_video_from_url(url)
    
    if not downloaded_video_path or not os.path.exists(downloaded_video_path):
        print("❌ Video download failed. Skipping to next video.")
        return False

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
    
    # CHECK IF GIFs ALREADY EXIST - NEW FEATURE
    gifs_exist, existing_gif_count = check_existing_gifs(final_output_dir)
    
    if gifs_exist:
        print(f"✅ GIFs already exist! Found {existing_gif_count} GIF files.")
        print("🚀 Proceeding directly to Tenor upload...")
        N = existing_gif_count  # Set global N to existing count
    else:
        # Convert the downloaded video to GIFs WITH LOGO
        video_to_gifs(downloaded_video_path, final_output_dir)
        print(f"📊 Total GIFs created: {N}")
    
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
        
        print(f"\n🎉 Video {current_index + 1} processing completed successfully!")
        print(f"📁 Video downloaded to: {downloaded_video_path}")
        print(f"📁 GIFs saved to: {final_output_dir}")
        print(f"📊 Total GIFs created: {N}")
        if TAGS:
            print(f"🏷 Tags generated ({len(TAGS)} total): {', '.join(TAGS)}")
            print(f"🌟 Universal tag '{UNIVERSAL_TAG}' added to all GIFs!")
        return True
            
    except KeyboardInterrupt:
        print("\n🛑 Automation interrupted by user!")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error during automation: {e}")
        print("💡 Tip: If automation failed, check if all required packages are installed.")
        return False

# --- Main Program Execution ---
if __name__ == "__main__":
    
    print("🎥 MULTI-VIDEO DOWNLOADER & GIF CONVERTER")
    print("=" * 50)
    print(f"🌟 Universal tag configured: {UNIVERSAL_TAG}")
    print(f"🖼️  Logo watermark configured: {LOGO_PATH}")
    print("💡 Make sure 'KRHP LOGO .png' is in the same folder as this script!")
    
    # Check if logo exists
    if not os.path.exists(LOGO_PATH):
        print(f"⚠️  WARNING: Logo file '{LOGO_PATH}' not found!")
        print("   GIFs will be created without watermark.")
        print("   Please place 'KRHP LOGO .png' in the same folder as this script.")
    else:
        print(f"✅ Logo file found! GIFs will have KRHP logo watermark.")
    
    # Get multiple video links from user
    video_links_input = input("Paste video URL(s) (separated by spaces or commas) and press Enter: ").strip()

    if not video_links_input:
        print("No URL provided. Exiting.")
        exit()

    # Extract multiple URLs from input - WITH CONTINUOUS LINK SUPPORT
    ALL_VIDEO_URLS = extract_urls_from_input(video_links_input)
    
    if not ALL_VIDEO_URLS:
        print("❌ No valid URLs found. Please provide valid YouTube links.")
        exit()
    
    print(f"📋 Found {len(ALL_VIDEO_URLS)} video URL(s) to process:")
    for i, url in enumerate(ALL_VIDEO_URLS):
        print(f"  {i+1}. {url}")
    
    # Process each video one by one
    successful_processed = 0
    
    for i, url in enumerate(ALL_VIDEO_URLS):
        CURRENT_VIDEO_INDEX = i
        
        if process_single_video(url, len(ALL_VIDEO_URLS), i):
            successful_processed += 1
            
        # If there are more videos, wait before starting next one
        if i < len(ALL_VIDEO_URLS) - 1:
            next_video_num = i + 2
            print(f"\n⏳ Preparing for next video ({next_video_num}/{len(ALL_VIDEO_URLS)}) in 5 seconds...")
            time.sleep(5)
    
    # Final summary
    print(f"\n{'='*60}")
    print("📊 PROCESSING SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Successfully processed: {successful_processed}/{len(ALL_VIDEO_URLS)} videos")
    print(f"❌ Failed: {len(ALL_VIDEO_URLS) - successful_processed}/{len(ALL_VIDEO_URLS)} videos")
    print(f"🌟 Universal tag '{UNIVERSAL_TAG}' added to all GIFs!")
    if os.path.exists(LOGO_PATH):
        print(f"🖼️  KRHP logo watermark added to all GIFs!")
    else:
        print(f"⚠️  No logo watermark added (logo file not found)")
    print("🎉 All operations completed!")
