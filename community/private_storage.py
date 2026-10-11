"""Reject public cartridge repositories before opening proprietary files."""
import os
import urllib.error
import urllib.request
from community.github import GitHub


def verify_private(repository, token=None):
    if token:
        info = GitHub(repository, token).request('GET', '/repos/' + repository)
        if not info['private']:
            raise ValueError('FireRed storage repository must be private')
        return
    # A repository-scoped SSH deploy key handles checkout and push. Successful
    # checkout proves existence/access; the unauthenticated API must hide it.
    request = urllib.request.Request('https://api.github.com/repos/' + repository,
                                     headers={'User-Agent': 'community-gba'})
    try:
        with urllib.request.urlopen(request, timeout=30):
            raise ValueError('FireRed storage repository is publicly visible')
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise


if __name__ == '__main__':
    verify_private(os.environ['PRIVATE_REPOSITORY'], os.environ.get('PRIVATE_TOKEN'))
