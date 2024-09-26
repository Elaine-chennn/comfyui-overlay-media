from .overlay_media import OverlayMediaNode, VideoUpload

NODE_CLASS_MAPPINGS = {
    "OverlayMediaNode": OverlayMediaNode,
    "VideoUpload": VideoUpload,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    'OverlayMediaNode': 'Overlay Media Node',
    'VideoUpload':'Upload Media',
}


__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']