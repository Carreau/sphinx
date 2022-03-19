import json
import subprocess

begin = -1
ranges = []

for i in range(65536):
    # Get all non 'word' codepoints. This means skipping all alphanumerics and
    # '_' (U+0095), matching the `\w` character class in `re`. We also skip
    # 0xd800-0xdfff, the surrogate pair area.
    if not (chr(i).isalnum() or i == 95) and not (0xd800 <= i <= 0xdfff):
        if begin == -1:
            begin = i
    elif begin != -1:
        ranges.append((begin, i))
        begin = -1


# fold json within almost 80 chars per line
def fold(json_data, splitter):
    code = json.dumps(json_data)
    lines = []
    while True:
        if len(code) < 75:
            lines.append('    ' + code)
            break
        index = code.index(splitter, 74)
        lines.append('    ' + code[:index + len(splitter)])
        code = code[index + len(splitter):]
    lines[0] = lines[0][4:]
    return '\n'.join(lines)


# JavaScript code
js_src = '''\
const splitChars = new Set(
    ''' + fold(ranges, "],") + '''.map(
        ([start, end]) => Array(end - start).fill(0).map((_, i) => start + i)
    ).flat()
)

const splitQuery = (query) => {
    const result = [];
    let start = null;
    for (let i = 0; i < query.length; i++) {
        if (splitChars.has(query.charCodeAt(i))) {
            if (start !== null) {
                result.push(query.slice(start, i));
                start = null;
            }
        } else {
            if (start === null) start = i;
            if (i === query.length - 1) {
                result.push(query.slice(start));
            }
        }
    }
    return result;
}
'''

js_test_src = f'''\
// This is regression test for https://github.com/sphinx-doc/sphinx/issues/3150
// generated by compat_regexp_generator.py
// it needs node.js for testing
const assert = require('assert');

{js_src}

console.log("test splitting English words")
assert.deepEqual(['Hello', 'World'], splitQuery('   Hello    World   '));
console.log('   ... ok\\n')

console.log("test splitting special characters")
assert.deepEqual(['Pin', 'Code'], splitQuery('Pin-Code'));
console.log('   ... ok\\n')

console.log("test splitting Chinese characters")
assert.deepEqual(['Hello', 'from', '中国', '上海'], splitQuery('Hello from 中国 上海'));
console.log('   ... ok\\n')

console.log("test splitting Emoji (surrogate pair) characters. It should keep emojis.")
assert.deepEqual(['😁😁'], splitQuery('😁😁'));
console.log('   ... ok\\n')

console.log("test splitting umlauts. It should keep umlauts.")
assert.deepEqual(
    ['Löschen', 'Prüfung', 'Abändern', 'ærlig', 'spørsmål'],
    splitQuery('Löschen Prüfung Abändern ærlig spørsmål'));
console.log('   ... ok\\n')

'''


python_src = '''\
"""Provides Python compatible word splitter to JavaScript

DO NOT EDIT. This is generated by utils/jssplitter_generator.py
"""

splitter_code = """
{js_src}
"""
'''

with open('../sphinx/search/jssplitter.py', 'w', encoding="utf-8") as f:
    f.write(python_src)

with open('./regression_test.js', 'w', encoding="utf-8") as f:
    f.write(js_test_src)

print("starting test...")
raise SystemExit(subprocess.call(['node', './regression_test.js']))
