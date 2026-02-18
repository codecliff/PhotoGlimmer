# ###############################################################################
# This File is part of the PhotoGlimmer project on github
# Maintainer : Rahul Singh
# URL        : https://github.com/codecliff/PhotoGlimmer
# License    : LGPL
# Email      : 8oaf978oh@mozmail.com
# Disclaimer : No warranties, stated or implied.
# ###############################################################################


# #######################################################################
# We laod exif data right when we load an image , and flush it onto final image
# We discard any binary exif data, even thumbnails.  
# #######################################################################

import piexif
import logging
import gc

logger = logging.getLogger(__name__)

class ExifEngine:
    """
    Handles extraction and sanitization of image metadata.
    Ensures file handles are closed and binary blobs are purged from RAM.
    """
    
    @staticmethod
    def load_safe_exif(path, strip_gps=False):
        """
        Loads and filters EXIF data. 
        Guaranteed to release file handles and discard thumbnails.
        """
        # 1. Initialize empty safe template
        clean_exif = {
            "0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None
        }

        # We use a localized scope for the 'raw' data to ensure it is 
        # eligible for GC the moment we return.
        raw_data = None
        
        try:
            # By reading the file into bytes first, we ensure the OS file handle 
            # is closed immediately after the 'with' block.
            with open(path, 'rb') as f:
                raw_bytes = f.read()
            
            # Load metadata from bytes rather than the path to avoid 
            # piexif keeping a hidden file pointer.
            raw_data = piexif.load(raw_bytes)
            
            # Explicitly kill the bytes now that piexif has its dict
            del raw_bytes

            # 2. Extract 0th (Identity)
            if isinstance(raw_data.get("0th"), dict):
                for tag in [piexif.ImageIFD.Make, piexif.ImageIFD.Model]:
                    if tag in raw_data["0th"]:
                        clean_exif["0th"][tag] = raw_data["0th"][tag]

            # 3. Extract Exif (Technical Settings)
            if isinstance(raw_data.get("Exif"), dict):
                # Common technical tags: Exposure, F-Stop, ISO, Date, Focal Length, Lens
                tech_tags = [33434, 33437, 34855, 36867, 37386, 42036]
                for tag in tech_tags:
                    if tag in raw_data["Exif"]:
                        clean_exif["Exif"][tag] = raw_data["Exif"][tag]

            # 4. Extract GPS (Location) - respect the privacy flag
            if not strip_gps and isinstance(raw_data.get("GPS"), dict):
                # Copying GPS data if user allows
                clean_exif["GPS"] = raw_data["GPS"].copy()

        except Exception as e:
            logger.warning(f"ExifEngine: Metadata extraction failed for {path}: {e}")
        
        finally:
            # Ensure the massive raw_data dictionary (with thumbnails) is killed
            if raw_data:
                raw_data.clear() # Clear internal dicts
                del raw_data
            gc.collect() # Immediate reclamation of the raw header RAM

        # 5. Final Normalization (Branding & Orientation)
        clean_exif["0th"][piexif.ImageIFD.Software] = "Photoglimmer"
        clean_exif["0th"][piexif.ImageIFD.Orientation] = 1 
        
        return clean_exif

    @staticmethod
    def get_bytes(exif_dict):
        """Converts the clean dict back to bytes for saving."""
        try:
            return piexif.dump(exif_dict)
        except Exception as e:
            logger.error(f"ExifEngine: Failed to serialize metadata: {e}")
            return None
        
        