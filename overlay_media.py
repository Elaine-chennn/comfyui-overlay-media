import os
import ffmpeg
import logging
import folder_paths


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
video_extensions = ['webm', 'mp4', 'mkv', 'gif', 'mov']

def strip_path(path):
        #This leaves whitespace inside quotes and only a single "
        #thus ' ""test"' -> '"test'
        #consider path.strip(string.whitespace+"\"")
        #or weightier re.fullmatch("[\\s\"]*(.+?)[\\s\"]*", path).group(1)
        path = path.strip()
        if path.startswith("\""):
            path = path[1:]
        if path.endswith("\""):
            path = path[:-1]
        return path

def get_media_info(video_path):
    try:
        probe = ffmpeg.probe(video_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        width = int(video_stream['width'])
        height = int(video_stream['height'])
        duration = float(video_stream['duration'])
        return width, height, duration
    except ffmpeg.Error as e:
        return None, None, None

def calculate_new_size(overlay_width, overlay_height, main_width, main_height):
    overlay_aspect = overlay_width / overlay_height
    if overlay_width > main_width or overlay_height > main_height:
        if (main_width / overlay_aspect) <= main_height:
            return main_width, int(main_width / overlay_aspect)
        else:
            return int(main_height * overlay_aspect), main_height
    return overlay_width, overlay_height

def validate_and_parse_position(position, main_width, main_height):
    predefined_positions = {
        "left-top": (0, 0),
        "left-bottom": (0, main_height),
        "right-top": (main_width, 0),
        "right-bottom": (main_width, main_height),
    }
    if position in predefined_positions:
        return predefined_positions[position]
    else:
        try:
            x, y = map(int, position.split(','))
            if 0 <= x <= main_width and 0 <= y <= main_height:
                return x, y
            else:
                logging.error("Custom coordinates are out of the main video's resolution range.")
                return None
        except ValueError:
            logging.error("Invalid position format. Use 'x,y' for custom coordinates.")
            return None


class VideoUpload:
    @classmethod
    def INPUT_TYPES(s):
        input_dir = folder_paths.get_input_directory()
        files = []
        for f in os.listdir(input_dir):
            if os.path.isfile(os.path.join(input_dir, f)):
                file_parts = f.split('.')
                if len(file_parts) > 1 and (file_parts[-1].lower() in video_extensions):
                    files.append(f)
        return {"required": {
                    "video": (sorted(files),),
                    }
                }

    CATEGORY = "overlay/load video"
    OUTPUT_NODE = True
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("filepath",)
    FUNCTION = "load_video"

    def load_video(self, **kwargs):
        kwargs['video'] = folder_paths.get_annotated_filepath(strip_path(kwargs['video']))
        path = kwargs['video']
        return path
class OverlayMediaNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "main_media": ("STRING", {"forceInput": True}),
                "overlay_media": ("STRING",{"forceInput": True}),
                "overlaysize_start": ("FLOAT", {"default": 0.0}),
                "overlaysize_end": ("FLOAT", {"default": 0.0}),
                "overlay_position": ("STRING", {"default": "left-top"}),
                "start": ("FLOAT", {"default": 0.0}),
                "end": ("FLOAT", {"default": 0.0}),
            }
        }
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output_path",)
    FUNCTION = "overlay_media"
    OUTPUT_NODE = True
    CATEGORY = "overlay_media/test"

    def overlay_media(self, main_media, overlay_media, overlaysize_start, overlaysize_end, overlay_position, start, end):
        
        filename_prefix = "OverlayMedia"
        # get output information
        output_dir = folder_paths.get_output_directory()
        full_output_folder = folder_paths.get_save_image_path(filename_prefix, output_dir)
        file = "gen.mp4"
        file_path = os.path.join(full_output_folder, file)
        output_file = file_path 
        
        if not os.path.exists(main_media) or not os.path.exists(overlay_media):
            logging.error("File not found")
            return None
        overlay_size = None if overlaysize_start == 0.0 and overlaysize_end == 0.0 else (overlaysize_start, overlaysize_end)
        main_width, main_height, main_duration = get_media_info(main_media)
        overlay_width, overlay_height, overlay_duration = get_media_info(overlay_media)

        if not main_width or not main_height or not main_duration:
            return None

        end = min(end if end else main_duration, main_duration)

        if start >= end or start >= main_duration:
            logging.error("Invalid start time or overlay duration exceeds main video length.")
            return None

        if overlay_size is None:
            overlay_size = calculate_new_size(overlay_width, overlay_height, main_width, main_height)

        overlay_position = validate_and_parse_position(overlay_position, main_width, main_height)
        if overlay_position is None:
            return None

        x, y = overlay_position
        main_input = ffmpeg.input(main_media)

        loop_times = -1 if overlay_duration and (end - start) > overlay_duration else 0

        overlay_input = ffmpeg.input(overlay_media, stream_loop=loop_times).filter('scale', overlay_size[0], overlay_size[1])

        overlay_filter = ffmpeg.overlay(main_input, overlay_input, x=x, y=y, enable=f'between(t,{start},{end})')

        out_dir = os.path.dirname(output_file)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        ffmpeg.output(overlay_filter, output_file).run()
        logging.info(f"Overlay completed. Output saved to {output_file}")
        return output_file