import re
import glob

# Mapping of emojis to Lucide icons
emoji_to_icon = {
    '🛡️': '<Shield className="w-4 h-4 inline mr-1" />',
    '🇮🇳': '<Landmark className="w-4 h-4 inline mr-1" />',
    '🧠': '<Brain className="w-4 h-4 inline mr-1" />',
    '⚡': '<Zap className="w-4 h-4 inline mr-1" />',
    '🔒': '<Lock className="w-4 h-4 inline mr-1" />',
    '🛒': '<ShoppingCart className="w-4 h-4 inline mr-1" />',
    '🏢': '<Building className="w-4 h-4 inline mr-1" />',
    '🏬': '<Store className="w-4 h-4 inline mr-1" />',
    '📍': '<MapPin className="w-4 h-4 inline mr-1" />',
    '📄': '<FileText className="w-4 h-4 inline mr-1" />',
    '💬': '<MessageSquare className="w-4 h-4 inline mr-1" />',
    '👥': '<Users className="w-4 h-4 inline mr-1" />',
    '🔧': '<Wrench className="w-4 h-4 inline mr-1" />',
    '✅': '<CheckCircle className="w-4 h-4 inline mr-1" />',
    '✓': '<Check className="w-4 h-4 inline mr-1" />',
    '❌': '<X className="w-4 h-4 inline mr-1" />',
    '✗': '<X className="w-4 h-4 inline mr-1" />',
    '🔑': '<Key className="w-4 h-4 inline mr-1" />',
    '🏦': '<Landmark className="w-4 h-4 inline mr-1" />',
    '💳': '<CreditCard className="w-4 h-4 inline mr-1" />',
    '📈': '<TrendingUp className="w-4 h-4 inline mr-1" />',
    '📉': '<TrendingDown className="w-4 h-4 inline mr-1" />',
    '⏱️': '<Clock className="w-4 h-4 inline mr-1" />',
    '📝': '<FileEdit className="w-4 h-4 inline mr-1" />',
    '🔍': '<Search className="w-4 h-4 inline mr-1" />',
    '📊': '<BarChart className="w-4 h-4 inline mr-1" />',
    '🎯': '<Target className="w-4 h-4 inline mr-1" />',
    '🔥': '<Flame className="w-4 h-4 inline mr-1" />',
    '💡': '<Lightbulb className="w-4 h-4 inline mr-1" />',
    '✨': '<Sparkles className="w-4 h-4 inline mr-1" />',
    '🚀': '<Rocket className="w-4 h-4 inline mr-1" />',
    '👑': '<Crown className="w-4 h-4 inline mr-1" />',
    '🛒': '<ShoppingCart className="w-4 h-4 inline mr-1" />',
    '🧾': '<Receipt className="w-4 h-4 inline mr-1" />',
    '⚖️': '<Scale className="w-4 h-4 inline mr-1" />',
}

# we must add these imports if used
def replace_emojis():
    for filepath in glob.glob('src/**/*.tsx', recursive=True):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        new_content = content
        used_icons = set()

        for emoji, icon_jsx in emoji_to_icon.items():
            if emoji in new_content:
                new_content = new_content.replace(emoji, icon_jsx)
                # extract icon name
                icon_name = icon_jsx.split('<')[1].split(' ')[0]
                used_icons.add(icon_name)

        if used_icons:
            # check what's already imported from lucide-react
            import_match = re.search(r"import\s+\{([^}]+)\}\s+from\s+['\"]lucide-react['\"]", new_content)
            if import_match:
                existing_icons = [i.strip() for i in import_match.group(1).split(',')]
                # Some might have 'Link as LinkIcon'
                existing_clean = [i.split(' as ')[0].strip() for i in existing_icons]
                
                missing_icons = [icon for icon in used_icons if icon not in existing_clean]
                if missing_icons:
                    new_imports = existing_icons + missing_icons
                    new_import_str = f"import {{ {', '.join(new_imports)} }} from 'lucide-react'"
                    new_content = new_content.replace(import_match.group(0), new_import_str)
            else:
                new_content = f"import {{ {', '.join(used_icons)} }} from 'lucide-react';\n" + new_content

        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f'Replaced emojis in {filepath}')

if __name__ == '__main__':
    replace_emojis()
