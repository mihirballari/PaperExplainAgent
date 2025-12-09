import os
import re
import subprocess
import asyncio
from PIL import Image
from typing import Optional, List
import traceback
import sys

from src.core.parse_video import (
    get_images_from_video,
    image_with_most_non_black_space
)
from mllm_tools.vertex_ai import VertexAIWrapper
from mllm_tools.gemini import GeminiWrapper

class VideoRenderer:
    """Class for rendering and combining Manim animation videos."""

    def __init__(self, output_dir="output", print_response=False, use_visual_fix_code=False):
        """Initialize the VideoRenderer.

        Args:
            output_dir (str, optional): Directory for output files. Defaults to "output".
            print_response (bool, optional): Whether to print responses. Defaults to False.
            use_visual_fix_code (bool, optional): Whether to use visual fix code. Defaults to False.
        """
        self.output_dir = output_dir
        self.print_response = print_response
        self.use_visual_fix_code = use_visual_fix_code

    async def render_scene(self, code: str, file_prefix: str, curr_scene: int, curr_version: int, code_dir: str, media_dir: str, max_retries: int = 3, use_visual_fix_code=False, visual_self_reflection_func=None, banned_reasonings=None, scene_trace_id=None, topic=None, session_id=None):
        """Render a single scene and handle error retries and visual fixes.

        Args:
            code (str): The Manim code to render
            file_prefix (str): Prefix for output files
            curr_scene (int): Current scene number
            curr_version (int): Current version number
            code_dir (str): Directory for code files
            media_dir (str): Directory for media output
            max_retries (int, optional): Maximum retry attempts. Defaults to 3.
            use_visual_fix_code (bool, optional): Whether to use visual fix code. Defaults to False.
            visual_self_reflection_func (callable, optional): Function for visual self-reflection. Defaults to None.
            banned_reasonings (list, optional): List of banned reasoning strings. Defaults to None.
            scene_trace_id (str, optional): Scene trace identifier. Defaults to None.
            topic (str, optional): Topic name. Defaults to None.
            session_id (str, optional): Session identifier. Defaults to None.

        Returns:
            tuple: (code, error_message) where error_message is None on success
        """
        retries = 0
        while retries < max_retries:
            try:
                # Execute manim in a thread to prevent blocking
                file_path = os.path.join(code_dir, f"{file_prefix}_scene{curr_scene}_v{curr_version}.py")
                result = await asyncio.to_thread(
                    subprocess.run,
                    ["manim", "-qh", file_path, "--media_dir", media_dir, "--progress_bar", "none"],
                    capture_output=True,
                    text=True
                )

                # if result.returncode != 0, it means that the code is not rendered successfully
                # so we need to fix the code by returning the code and the error message
                if result.returncode != 0:
                    raise Exception(result.stderr)

                if use_visual_fix_code and visual_self_reflection_func and banned_reasonings:
                    # Get the rendered video path
                    video_path = os.path.join(
                        media_dir,
                        "videos",
                        f"{file_prefix}_scene{curr_scene}_v{curr_version}.mp4"
                    )
                    
                    # For Gemini/Vertex AI models, pass the video directly
                    if self.scene_model.model_name.startswith(('gemini/', 'vertex_ai/')):
                        media_input = video_path
                    else:
                        # For other models, use image snapshot
                        media_input = self.create_snapshot_scene(
                            topic, curr_scene, curr_version, return_type="path"
                        )
                        
                    new_code, log = visual_self_reflection_func(
                        code,
                        media_input,
                        scene_trace_id=scene_trace_id,
                        topic=topic,
                        scene_number=curr_scene,
                        session_id=session_id
                    )

                    with open(os.path.join(code_dir, f"{file_prefix}_scene{curr_scene}_v{curr_version}_vfix_log.txt"), "w") as f:
                        f.write(log)

                    # Check for termination markers
                    if "<LGTM>" in new_code or any(word in new_code for word in banned_reasonings):
                        break

                    code = new_code
                    curr_version += 1
                    with open(os.path.join(code_dir, f"{file_prefix}_scene{curr_scene}_v{curr_version}.py"), "w") as f:
                        f.write(code)
                    print(f"Code saved to scene{curr_scene}/code/{file_prefix}_scene{curr_scene}_v{curr_version}.py")
                    retries = 0
                    continue

                break  # Exit retry loop on success

            except Exception as e:
                print(f"Error: {e}")
                print(f"Retrying {retries+1} of {max_retries}...")

                with open(os.path.join(code_dir, f"{file_prefix}_scene{curr_scene}_v{curr_version}_error.log"), "a") as f:
                    f.write(f"\nError in attempt {retries}:\n{str(e)}\n")
                retries += 1
                return code, str(e) # Indicate failure and return error message
            
        print(f"Successfully rendered {file_path}")
        with open(os.path.join(self.output_dir, file_prefix, f"scene{curr_scene}", "succ_rendered.txt"), "w") as f:
            f.write("")

        return code, None # Indicate success

    def run_manim_process(self,
                          topic: str):
        """Run manim on all generated manim code for a specific topic.

        Args:
            topic (str): Topic name to process

        Returns:
            subprocess.CompletedProcess: Result of the final manim process
        """
        file_prefix = topic.lower()
        file_prefix = re.sub(r'[^a-z0-9_]+', '_', file_prefix)
        search_path = os.path.join(self.output_dir, file_prefix)
        # Iterate through scene folders
        scene_folders = [f for f in os.listdir(search_path) if os.path.isdir(os.path.join(search_path, f))]
        scene_folders.sort()  # Sort to process scenes in order

        for folder in scene_folders:
            folder_path = os.path.join(search_path, folder)

            # Get all Python files in version order
            py_files = [f for f in os.listdir(folder_path) if f.endswith('.py')]
            py_files.sort(key=lambda x: int(x.split('_v')[-1].split('.')[0]))  # Sort by version number

            for file in py_files:
                file_path = os.path.join(folder_path, file)
                try:
                    media_dir = os.path.join(self.output_dir, file_prefix, "media")
                    result = subprocess.run(
                        f"manim -qh {file_path} --media_dir {media_dir}",
                        shell=True,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode != 0:
                        raise Exception(result.stderr)
                    print(f"Successfully rendered {file}")
                    break  # Move to next scene folder if successful
                except Exception as e:
                    print(f"Error rendering {file}: {e}")
                    error_log_path = os.path.join(folder_path, f"{file.split('.')[0]}_error.log") # drop the extra py
                    with open(error_log_path, "w") as f:
                        f.write(f"Error:\n{str(e)}\n")
                    print(f"Error log saved to {error_log_path}")
        return result

    def create_snapshot_scene(self, topic: str, scene_number: int, version_number: int, return_type: str = "image"):
        """Create a snapshot of the video for a specific topic and scene.

        Args:
            topic (str): Topic name
            scene_number (int): Scene number
            version_number (int): Version number
            return_type (str, optional): Type of return value - "path" or "image". Defaults to "image".

        Returns:
            Union[str, PIL.Image]: Path to saved image or PIL Image object

        Raises:
            FileNotFoundError: If no mp4 files found in video folder
        """
        file_prefix = topic.lower()
        file_prefix = re.sub(r'[^a-z0-9_]+', '_', file_prefix)
        search_path = os.path.join(self.output_dir, file_prefix)
        video_folder_path = os.path.join(search_path, "media", "videos", f"{file_prefix}_scene{scene_number}_v{version_number}", "1080p60")
        os.makedirs(video_folder_path, exist_ok=True)
        snapshot_path = os.path.join(video_folder_path, "snapshot.png")
        # Get the mp4 video file from the video folder path
        video_files = [f for f in os.listdir(video_folder_path) if f.endswith('.mp4')]
        if not video_files:
            raise FileNotFoundError(f"No mp4 files found in {video_folder_path}")
        video_path = os.path.join(video_folder_path, video_files[0])
        saved_image = image_with_most_non_black_space(get_images_from_video(video_path), snapshot_path, return_type=return_type)
        return saved_image

    def combine_videos(self, topic: str):
        """Combine all videos and subtitle files for a specific topic using ffmpeg.

        Args:
            topic (str): Topic name to combine videos for

        This function will:
        - Find all scene videos and subtitles
        - Combine videos with or without audio
        - Merge subtitle files with correct timing
        - Save combined video and subtitles to output directory
        """
        file_prefix = topic.lower()
        file_prefix = re.sub(r'[^a-z0-9_]+', '_', file_prefix)
        search_path = os.path.join(self.output_dir, file_prefix, "media", "videos")

        # Create output directory if it doesn't exist
        video_output_dir = os.path.join(self.output_dir, file_prefix)
        os.makedirs(video_output_dir, exist_ok=True)

        output_video_path = os.path.join(video_output_dir, f"{file_prefix}_combined.mp4")
        output_srt_path = os.path.join(video_output_dir, f"{file_prefix}_combined.srt")
        
        if os.path.exists(output_video_path) and os.path.exists(output_srt_path):
            print(f"Combined video and subtitles already exist at {output_video_path}, not combining again.")
            return

        # Get scene count from outline
        scene_outline_path = os.path.join(self.output_dir, file_prefix, f"{file_prefix}_scene_outline.txt")
        if not os.path.exists(scene_outline_path):
            print(f"Warning: Scene outline file not found at {scene_outline_path}. Cannot determine scene count.")
            return
        with open(scene_outline_path) as f:
            plan = f.read()
        scene_outline = re.search(r'(<SCENE_OUTLINE>.*?</SCENE_OUTLINE>)', plan, re.DOTALL).group(1)
        scene_count = len(re.findall(r'<SCENE_(\d+)>[^<]', scene_outline))

        # Find all scene folders and videos
        scene_folders = []
        for root, dirs, files in os.walk(search_path):
            for dir in dirs:
                if dir.startswith(file_prefix + "_scene"):
                    scene_folders.append(os.path.join(root, dir))

        scene_videos = []
        scene_subtitles = []

        for scene_num in range(1, scene_count + 1):
            folders = [f for f in scene_folders if int(f.split("scene")[-1].split("_")[0]) == scene_num]
            if not folders:
                print(f"Warning: Missing scene {scene_num}")
                continue

            folders.sort(key=lambda f: int(f.split("_v")[-1]))
            folder = folders[-1]

            video_found = False
            subtitles_found = False
            for filename in os.listdir(os.path.join(folder, "1080p60")):
                if filename.endswith('.mp4'):
                    scene_videos.append(os.path.join(folder, "1080p60", filename))
                    video_found = True
                elif filename.endswith('.srt'):
                    scene_subtitles.append(os.path.join(folder, "1080p60", filename))
                    subtitles_found = True

            if not video_found:
                print(f"Warning: Missing video for scene {scene_num}")
            if not subtitles_found:
                scene_subtitles.append(None)

        if len(scene_videos) != scene_count:
            print("Not all videos/subtitles are found, aborting video combination.")
            return

        try:
            import ffmpeg # You might need to install ffmpeg-python package: pip install ffmpeg-python
            from tqdm import tqdm

            print("Analyzing video streams...")
            # Check if videos have audio streams
            has_audio = []
            for video in tqdm(scene_videos, desc="Checking audio streams"):
                probe = ffmpeg.probe(video)
                audio_streams = [stream for stream in probe['streams'] if stream['codec_type'] == 'audio']
                has_audio.append(len(audio_streams) > 0)

            print("Preparing video combination...")
            # If any video has audio, we need to ensure all videos have audio streams
            if any(has_audio):
                # Create list to store video and audio streams
                streams = []
                for video, has_aud in tqdm(list(zip(scene_videos, has_audio)), desc="Processing videos"):
                    if has_aud:
                        # Video has audio, use as is
                        input_vid = ffmpeg.input(video)
                        streams.extend([input_vid['v'], input_vid['a']])
                    else:
                        # Video lacks audio, add silent audio
                        input_vid = ffmpeg.input(video)
                        # Generate silent audio for the duration of the video
                        probe = ffmpeg.probe(video)
                        duration = float(probe['streams'][0]['duration'])
                        silent_audio = ffmpeg.input(f'anullsrc=channel_layout=stereo:sample_rate=44100',
                                                  f='lavfi', t=duration)['a']
                        streams.extend([input_vid['v'], silent_audio])
                    
                print("Combining videos with audio...")
                try:
                    # Concatenate all streams using optimized CPU encoding settings
                    concat = ffmpeg.concat(*streams, v=1, a=1, unsafe=True)
                    process = (
                        concat
                        .output(output_video_path,
                               **{'c:v': 'libx264',
                                  'c:a': 'aac',
                                  'preset': 'veryfast',    # Changed from ultrafast for better speed/quality balance
                                  'crf': '28',             # Same quality setting
                                  'threads': '0',          # Use all CPU threads
                                  'tune': 'fastdecode',    # Optimize for decoding speed
                                  'profile:v': 'baseline', # Simpler profile for faster encoding
                                  'level': '4.0',
                                  'x264-params': 'aq-mode=0:no-deblock:no-cabac:ref=1:subme=0:trellis=0:weightp=0',  # Added aggressive speed optimizations
                                  'movflags': '+faststart',
                                  'stats': None,
                                  'progress': 'pipe:1'})
                        .overwrite_output()
                        .run_async(pipe_stdout=True, pipe_stderr=True)
                    )
                    
                    # Process progress output
                    while True:
                        line = process.stdout.readline().decode('utf-8')
                        if not line:
                            break
                        if 'frame=' in line:
                            sys.stdout.write('\rProcessing: ' + line.strip())
                            sys.stdout.flush()
                    
                    # Wait for the process to complete and capture output
                    stdout, stderr = process.communicate()
                    print("\nEncoding complete!")
                    
                except ffmpeg.Error as e:
                    print(f"FFmpeg stdout:\n{e.stdout.decode('utf8')}")
                    print(f"FFmpeg stderr:\n{e.stderr.decode('utf8')}")
                    raise
            else:
                # No videos have audio, concatenate video streams only
                streams = []
                for video in tqdm(scene_videos, desc="Processing videos"):
                    streams.append(ffmpeg.input(video)['v'])
                
                print("Combining videos without audio...")
                try:
                    concat = ffmpeg.concat(*streams, v=1, unsafe=True)
                    process = (
                        concat
                        .output(output_video_path,
                               **{'c:v': 'libx264',
                                  'preset': 'medium',
                                  'crf': '23',
                                  'stats': None,  # Enable progress stats
                                  'progress': 'pipe:1'})  # Output progress to pipe
                        .overwrite_output()
                        .run_async(pipe_stdout=True, pipe_stderr=True)
                    )
                    
                    # Process progress output
                    while True:
                        line = process.stdout.readline().decode('utf-8')
                        if not line:
                            break
                        if 'frame=' in line:
                            sys.stdout.write('\rProcessing: ' + line.strip())
                            sys.stdout.flush()
                    
                    # Wait for the process to complete and capture output
                    stdout, stderr = process.communicate()
                    print("\nEncoding complete!")
                    
                except ffmpeg.Error as e:
                    print(f"FFmpeg stdout:\n{e.stdout.decode('utf8')}")
                    print(f"FFmpeg stderr:\n{e.stderr.decode('utf8')}")
                    raise
            
            print(f"Successfully combined videos into {output_video_path}")

            # Handle subtitle combination (existing subtitle code remains the same)
            if scene_subtitles:
                with open(output_srt_path, 'w', encoding='utf-8') as outfile:
                    current_time_offset = 0
                    subtitle_index = 1

                    for srt_file, video_file in zip(scene_subtitles, scene_videos):
                        if srt_file is None:
                            continue

                        with open(srt_file, 'r', encoding='utf-8') as infile:
                            lines = infile.readlines()
                            i = 0
                            while i < len(lines):
                                line = lines[i].strip()
                                if line.isdigit():  # Subtitle index
                                    outfile.write(f"{subtitle_index}\n")
                                    subtitle_index += 1
                                    i += 1

                                    # Time codes line
                                    time_line = lines[i].strip()
                                    start_time, end_time = time_line.split(' --> ')

                                    # Convert time codes and add offset
                                    def adjust_time(time_str, offset):
                                        h, m, s = time_str.replace(',', '.').split(':')
                                        total_seconds = float(h) * 3600 + float(m) * 60 + float(s) + offset
                                        h = int(total_seconds // 3600)
                                        m = int((total_seconds % 3600) // 60)
                                        s = total_seconds % 60
                                        return f"{h:02d}:{m:02d}:{s:06.3f}".replace('.', ',')

                                    new_start = adjust_time(start_time, current_time_offset)
                                    new_end = adjust_time(end_time, current_time_offset)
                                    outfile.write(f"{new_start} --> {new_end}\n")
                                    i += 1

                                    # Subtitle text (could be multiple lines)
                                    while i < len(lines) and lines[i].strip():
                                        outfile.write(lines[i])
                                        i += 1
                                    outfile.write('\n')
                                else:
                                    i += 1

                        # Update time offset using ffprobe
                        probe = ffmpeg.probe(video_file)
                        duration = float(probe['streams'][0]['duration'])
                        current_time_offset += duration

            print(f"Successfully combined videos into {output_video_path}")
            if scene_subtitles:
                print(f"Successfully combined subtitles into {output_srt_path}")

        except Exception as e:
            print(f"Error combining videos and subtitles: {e}")
            traceback.print_exc()