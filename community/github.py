import json
import urllib.error
import urllib.request

class GitHub:
    def __init__(self, repository, token):
        self.repository,self.token=repository,token

    def request(self, method, path, data=None):
        req=urllib.request.Request('https://api.github.com'+path,
                data=json.dumps(data).encode() if data is not None else None,method=method,
                headers={'Authorization':'Bearer '+self.token,'Accept':'application/vnd.github+json',
                         'X-GitHub-Api-Version':'2022-11-28','User-Agent':'community-gba',
                         'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=30) as response:
            body=response.read()
            return json.loads(body) if body else None

    def queue(self, prefix='[gba]'):
        issues=[]
        page=1
        while True:
            batch=self.request('GET',f'/repos/{self.repository}/issues?state=open&sort=created&direction=asc&per_page=100&page={page}')
            issues.extend(i for i in batch if 'pull_request' not in i and i['title'].startswith(prefix))
            if len(batch)<100:
                break
            page+=1
        return sorted(issues,key=lambda i:i['number'])

    def close(self, issue):
        self.request('PATCH',f'/repos/{self.repository}/issues/{issue}',{'state':'closed'})
