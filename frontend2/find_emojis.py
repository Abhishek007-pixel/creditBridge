import glob
import re

def find_emojis():
    for filepath in glob.glob('src/**/*.tsx', recursive=True):
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
        emojis = set(re.findall(r'[^\x00-\x7F©—’”–‘®™]', text))
        if emojis:
            res = []
            for e in emojis:
                res.append(e.encode('unicode_escape').decode('utf-8'))
            print(f'{filepath}: {" ".join(res)}')

if __name__ == '__main__':
    find_emojis()
