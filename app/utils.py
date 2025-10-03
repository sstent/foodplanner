import re

def slugify(s):
    """
    Slugifies a string, converting spaces and non-alphanumeric characters to hyphens.
    """
    s = s.lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)  # Remove all non-alphanumeric characters except spaces and hyphens
    s = re.sub(r'[-\s]+', '-', s)        # Replace spaces and hyphens with a single hyphen
    s = s.strip('-')                     # Remove leading/trailing hyphens

    return s