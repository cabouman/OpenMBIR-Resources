"""Gather the OpenMBIR usage counts into usage_data.json.

Sources: the conda-forge download counts of svmbir (anaconda.org API), the
daily PyPI downloads of svmbir, mbirjax, and mbirtorch with mirrors excluded
(pypistats.org, the most recent six months), and the GitHub star dates and
repository counts (GitHub API; set GITHUB_TOKEN to raise the rate limit).

Run:  python3 fetch_usage_data.py
"""

import datetime as dt
import json
import os
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PYPI_PACKAGES = ['svmbir', 'mbirjax', 'mbirtorch']
GITHUB_REPOS = ['svmbir', 'mbirjax', 'mbirtorch', 'mbircone', 'mbirhelical', 'xcal']
STAR_REPOS = ['svmbir', 'mbirjax', 'mbircone', 'mbirhelical']


def get(url, headers=None, retries=3):
    h = {'User-Agent': 'OpenMBIR-usage-page'}
    h.update(headers or {})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=120) as r:
                return json.load(r), r.headers
        except urllib.error.HTTPError as e:
            # The workflow token is refused for some public read endpoints;
            # the same request works anonymously, within the anonymous rate limit.
            if e.code == 403 and 'Authorization' in h:
                del h['Authorization']
                continue
            if attempt == retries - 1:
                raise
            time.sleep(10)
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(10)


def github_headers():
    h = {'Accept': 'application/vnd.github+json'}
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        h['Authorization'] = f'Bearer {token}'
    return h


def main():
    data = {'generated': dt.date.today().isoformat()}

    # PyPI daily downloads, mirrors excluded.
    data['pypi_daily'] = {}
    for p in PYPI_PACKAGES:
        rows, _ = get(f'https://pypistats.org/api/packages/{p}/overall?mirrors=false')
        data['pypi_daily'][p] = {r['date']: r['downloads'] for r in rows['data']}

    # conda-forge svmbir: one record per published file.
    d, _ = get('https://api.anaconda.org/package/conda-forge/svmbir')
    data['conda_files'] = [dict(version=f['version'], subdir=f['attrs'].get('subdir'),
                                python=f['attrs'].get('python'), upload_time=f.get('upload_time'),
                                ndownloads=f.get('ndownloads', 0)) for f in d['files']]

    # GitHub stars and repository counts.
    data['github_stars'] = {}
    for repo in STAR_REPOS:
        dates = []
        page = 1
        while True:
            rows, _ = get(f'https://api.github.com/repos/cabouman/{repo}/stargazers?per_page=100&page={page}',
                          headers={**github_headers(), 'Accept': 'application/vnd.github.star+json'})
            dates += [r['starred_at'][:10] for r in rows]
            if len(rows) < 100:
                break
            page += 1
        data['github_stars'][repo] = sorted(dates)
    data['github'] = {}
    for repo in GITHUB_REPOS:
        r, _ = get(f'https://api.github.com/repos/cabouman/{repo}', headers=github_headers())
        data['github'][repo] = {'stars': r['stargazers_count'], 'forks': r['forks_count'],
                                'created': r['created_at'][:7]}

    with open(os.path.join(HERE, 'usage_data.json'), 'w') as f:
        json.dump(data, f, indent=1)
    print('usage_data.json written for', data['generated'])


if __name__ == '__main__':
    main()
