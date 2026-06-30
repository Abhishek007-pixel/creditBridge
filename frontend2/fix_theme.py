import os
import re
import glob

directory = 'C:/Users/ankur/Downloads/OpenSource/UCO/final/creditBridge/frontend2/src'

bg_map = {
    'bg-neutral-950': 'bg-neutral-50 dark:bg-neutral-950',
    'bg-neutral-900': 'bg-white dark:bg-neutral-900',
    'bg-neutral-850': 'bg-neutral-100 dark:bg-neutral-850',
    'bg-neutral-800': 'bg-neutral-100 dark:bg-neutral-800',
    'bg-black': 'bg-white dark:bg-black',
}

text_map = {
    'text-neutral-500': 'text-neutral-600 dark:text-neutral-500',
    'text-neutral-400': 'text-neutral-500 dark:text-neutral-400',
    'text-neutral-300': 'text-neutral-700 dark:text-neutral-300',
    'text-neutral-200': 'text-neutral-800 dark:text-neutral-200',
    'text-white': 'text-neutral-900 dark:text-white',
    'text-black': 'text-neutral-900 dark:text-white',
}

border_map = {
    'border-neutral-850': 'border-neutral-200 dark:border-neutral-850',
    'border-neutral-800': 'border-neutral-200 dark:border-neutral-800',
    'border-neutral-750': 'border-neutral-200 dark:border-neutral-750',
    'border-neutral-700': 'border-neutral-300 dark:border-neutral-700',
    'border-neutral-600': 'border-neutral-300 dark:border-neutral-600',
}

hover_map = {
    'hover:bg-neutral-900': 'hover:bg-neutral-100 dark:hover:bg-neutral-900',
    'hover:bg-neutral-850': 'hover:bg-neutral-100 dark:hover:bg-neutral-850',
    'hover:bg-neutral-800': 'hover:bg-neutral-200 dark:hover:bg-neutral-800',
    'hover:bg-neutral-750': 'hover:bg-neutral-200 dark:hover:bg-neutral-750',
    'hover:text-white': 'hover:text-neutral-900 dark:hover:text-white',
}

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    for i, line in enumerate(lines):
        colored_bg = bool(re.search(r'\bbg-(blue|indigo|emerald|rose|red|green|primary)-\d{3}\b', line))
        colored_bg = colored_bg or 'bg-gradient-to-r' in line or 'from-' in line or 'to-' in line

        def replacer(match):
            cls = match.group(0)
            
            # Check for modifiers like /40 or /50
            base_cls = cls
            opacity = ''
            if '/' in cls:
                base_cls, opacity = cls.split('/', 1)
                opacity = '/' + opacity

            if base_cls.startswith('dark:'):
                return cls
                
            if base_cls in bg_map:
                mapped = bg_map[base_cls]
                # append opacity to both parts if it exists
                if opacity:
                    mapped = ' '.join(p + opacity for p in mapped.split())
                return mapped
                
            if base_cls in border_map:
                mapped = border_map[base_cls]
                if opacity:
                    mapped = ' '.join(p + opacity for p in mapped.split())
                return mapped
                
            if base_cls in text_map:
                if (base_cls == 'text-white' or base_cls == 'text-neutral-100') and colored_bg:
                    return cls
                mapped = text_map[base_cls]
                if opacity:
                    mapped = ' '.join(p + opacity for p in mapped.split())
                return mapped
                
            if base_cls in hover_map:
                if base_cls == 'hover:text-white' and colored_bg:
                    return cls
                mapped = hover_map[base_cls]
                if opacity:
                    mapped = ' '.join(p + opacity for p in mapped.split())
                return mapped

            return cls

        lines[i] = re.sub(r'[a-zA-Z0-9_:-]+(?:/[0-9]+)?', replacer, line)

    new_content = '\n'.join(lines)

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filepath}")

for filepath in glob.glob(directory + '/**/*.tsx', recursive=True):
    process_file(filepath)
for filepath in glob.glob(directory + '/**/*.ts', recursive=True):
    process_file(filepath)

print("Done fixing theme colors!")
