import re
import unicodedata

class CustomPreprocessor:
    def __init__(self, stop_dict, stem_cache):
        self.stop_dict = stop_dict
        self.stem_cache = stem_cache

    def __call__(self, s):
        s = str(s).lower()
        s = re.sub(r'^c\((.*)\)$', r'\1', s)
        s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('utf-8')
        s = re.sub(r'[^a-z\s]', ' ', s)
        tokens = s.split()
        tokens = [w for w in tokens if w not in self.stop_dict and len(w) > 2]
        tokens = [self.stem_cache.get(w, w) for w in tokens]
        return ' '.join(tokens)