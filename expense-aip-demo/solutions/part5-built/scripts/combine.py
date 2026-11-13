'''Combine the exact-check result with the judgement verdicts.

Pure computation on the state given on stdin. auto_ok is true only when every exact check holds
and every judgement rule was answered clear with enough confidence. Touches no files, no
network and no credentials.
'''
import json
import sys

BAR = 0.8


def val(x):
    if isinstance(x, dict) and 'value' in x:
        return x['value']
    return x


def conf(x):
    if isinstance(x, dict):
        c = x.get('confidence')
        if isinstance(c, (int, float)):
            return float(c)
    return None


def is_true(x):
    v = val(x)
    return v is True or (isinstance(v, str) and v.lower() == 'true')


def main():
    s = json.load(sys.stdin).get('state', {})
    rules = s.get('rules') or []
    verdicts = s.get('verdicts') or []
    issues = []
    exact_ok = is_true(s.get('exact_ok'))
    if not exact_ok:
        issues.append('exact checks: ' + str(s.get('exact_notes', 'not all hold')))
    if len(verdicts) < len(rules):
        issues.append('judgement rules: fewer verdicts than rules')
    for i, item in enumerate(verdicts):
        v = item.get('verdict', item) if isinstance(item, dict) else item
        f = v.get('follows') if isinstance(v, dict) else v
        rule = str(rules[i]) if i < len(rules) else 'rule ' + str(i + 1)
        c = conf(f)
        if not is_true(f):
            issues.append('judgement rule not clearly met: ' + rule)
        elif c is not None and c < BAR:
            issues.append('judgement doubtful (confidence ' + str(c) + '): ' + rule)
    summary = s.get('judgement_summary')
    summary_ok = isinstance(summary, dict) and is_true(summary.get('all_clear'))
    if not summary_ok and not any(x.startswith('judgement') for x in issues):
        issues.append('judgement rules not all clearly held')
    auto_ok = bool(exact_ok and summary_ok and not issues)
    print(json.dumps({'auto_ok': auto_ok, 'issues': '; '.join(issues) if issues else 'none'}))


main()
