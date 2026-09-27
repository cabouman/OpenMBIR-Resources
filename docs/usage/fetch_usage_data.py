"""Gather the OpenMBIR usage counts into usage_data.json.

Sources: the conda-forge download counts of svmbir (anaconda.org API), the
daily PyPI downloads of svmbir, mbirjax, and mbirtorch with mirrors excluded
(pypistats.org, the most recent six months), and the GitHub star dates and
repository counts (GitHub API, read anonymously).

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
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(10)


def github_headers():
    # Anonymous reads: this script makes about ten GitHub requests per run,
    # well inside the anonymous limit, and the workflow token was refused by
    # some of these endpoints.
    return {'Accept': 'application/vnd.github+json'}


def star_dates(repo):
    """Return the star dates of a repository, or None if GitHub refuses both APIs."""
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        return None
    auth = {'Authorization': f'Bearer {token}'}
    try:
        dates, page = [], 1
        while True:
            rows, _ = get(f'https://api.github.com/repos/cabouman/{repo}/stargazers?per_page=100&page={page}',
                          headers={**auth, 'Accept': 'application/vnd.github.star+json'}, retries=1)
            dates += [r['starred_at'][:10] for r in rows]
            if len(rows) < 100:
                return dates
            page += 1
    except Exception:
        pass
    try:
        dates, cursor = [], None
        while True:
            after = f', after: "{cursor}"' if cursor else ''
            query = ('{ repository(owner: "cabouman", name: "%s") { stargazers(first: 100%s) '
                     '{ pageInfo { hasNextPage endCursor } edges { starredAt } } } }' % (repo, after))
            body = json.dumps({'query': query}).encode()
            req = urllib.request.Request('https://api.github.com/graphql', data=body,
                                         headers={**auth, 'User-Agent': 'OpenMBIR-usage-page',
                                                  'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=120) as r:
                out = json.load(r)
            sg = out['data']['repository']['stargazers']
            dates += [e['starredAt'][:10] for e in sg['edges']]
            if not sg['pageInfo']['hasNextPage']:
                return dates
            cursor = sg['pageInfo']['endCursor']
    except Exception:
        return None


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

    # GitHub star dates.  The stargazers endpoint needs a token.  The REST
    # endpoint is tried first, then GraphQL; if both are refused (the workflow
    # token cannot read other repositories through REST), the dates from the
    # previous snapshot are kept so the rest of the page still refreshes.
    previous = {}
    try:
        previous = json.load(open(os.path.join(HERE, 'usage_data.json'))).get('github_stars', {})
    except Exception:
        pass
    data['github_stars'] = {}
    for repo in STAR_REPOS:
        dates = star_dates(repo)
        if dates is None:
            dates = previous.get(repo, [])
            print(f'{repo}: star dates kept from the previous snapshot')
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
