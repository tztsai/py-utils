import re
import json
import requests

symfile = 'symbols.json'
url = 'https://raw.githubusercontent.com/joom/latex-unicoder.vim/master/autoload/unicoder.vim'

try:
    with open(symfile, 'r', encoding='utf8') as f:
        symbols = json.load(f)
        
except FileNotFoundError:
    content = requests.get(url).content.decode()
            
    # read symbol dict
    content = (content.replace("'", '"').replace(' \\ ', '')
               .replace('\\\\', '\\').replace('\\', '\\\\'))
    dict_text = re.search(r'\{[\s\S]*?\}\s', content)[0]
    symbols = json.loads(dict_text)
    
    with open(symfile, 'w', encoding='utf8') as f:
        json.dump(symbols, f)


def subst(s):
    """Substitute escaped characters."""
    return symbols.get(s, s[1:])


if __name__ == "__main__":
    print(subst(r'\alpha'))
