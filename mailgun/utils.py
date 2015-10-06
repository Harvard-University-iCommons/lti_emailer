

def replace_non_ascii(self, s, replacement='_'):
        return ''.join(i if ord(i) < 128 else replacement for i in s)
