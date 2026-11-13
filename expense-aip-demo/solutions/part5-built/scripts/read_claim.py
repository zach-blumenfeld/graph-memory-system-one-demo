'''Read one expense claim and the receipt text file it names.

Reads <claims_folder>/<claim_id>.json and the receipt file named in it, from the same folder,
read-only. Writes nothing. Touches no network, no credentials and no files outside the claims
folder given as input.
'''
import json
import os
import sys

RECEIPT_KEYS = ('receipt', 'receipt_file', 'receipt_path', 'receipt_name', 'receipt_filename')


def receipt_name(claim):
    for key in RECEIPT_KEYS:
        val = claim.get(key)
        if isinstance(val, dict):
            val = val.get('file') or val.get('path') or val.get('name')
        if isinstance(val, str) and val.strip():
            return val.strip()
    for val in claim.values():
        if isinstance(val, str) and val.strip().lower().endswith('.txt'):
            return val.strip()
    return ''


def main():
    state = json.load(sys.stdin).get('state', {})
    folder = str(state.get('claims_folder', ''))
    claim_id = str(state.get('claim_id', ''))
    claim = {}
    text = ''
    name = ''
    problems = []
    path = os.path.join(folder, claim_id + '.json')
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            claim = data
        else:
            problems.append('claim file ' + path + ' is not a JSON object')
    except FileNotFoundError:
        problems.append('claim file ' + path + ' is missing')
    except (OSError, ValueError) as e:
        problems.append('claim file ' + path + ' is unreadable: ' + str(e))
    if claim:
        name = receipt_name(claim)
        if name:
            rpath = os.path.join(folder, os.path.basename(name))
            try:
                with open(rpath, encoding='utf-8') as f:
                    text = f.read()
            except FileNotFoundError:
                problems.append('receipt file ' + rpath + ' is missing')
            except (OSError, ValueError) as e:
                problems.append('receipt file ' + rpath + ' is unreadable: ' + str(e))
    print(json.dumps({'claim': claim, 'receipt_text': text, 'receipt_file': name,
                      'load_problems': '; '.join(problems)}))


main()
