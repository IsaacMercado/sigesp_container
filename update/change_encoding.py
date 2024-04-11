from pathlib import Path
from pprint import pprint

from magic import from_file

path_base = Path('/home/isaac/projects/sigesp_enterprise').resolve()


FILETYPES = {
    'ASCII font metrics',
    'ASCII text',
    'Algol 68 source',
    'BSD makefile script',
    'C source',
    'C++ source',
    'CSV text',
    'Generic INItialization configuration []',
    'HTML document',
    'ISO-8859 text',
    'JSON data',
    'Non-ISO extended-ASCII text',
    'PHP script',
    'Unicode text',
    'XML 1.0 document',
    'assembler source',
    # 'data',
    'exported SGML document',
    'news or mail',
}

types = set()
lines = set()

for path in path_base.rglob('**/*'):
    if path_base / '.git' in path.parents:
        continue
    if path.is_file():
        filetype = from_file(path).split(", ")
        if filetype[0] in FILETYPES:
            temp = []
            for f in filetype:
                if 'UTF-16' in f:
                    print(path, filetype)
                if 'with very long lines' not in f:
                    types.add(f)
                    temp.append(f)
            if temp:
                lines.add(', '.join(temp))


pprint(types)
pprint(lines)
