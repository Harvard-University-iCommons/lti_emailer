

def replace_non_ascii(s, replacement='_'):
        return ''.join(i if ord(i) < 128 else replacement for i in s)
