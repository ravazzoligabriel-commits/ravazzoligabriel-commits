import unittest
from community.github import GitHub

class DurableQueueTests(unittest.TestCase):
    def test_queue_paginates_and_excludes_prs_and_unrelated_issues(self):
        client=GitHub('owner/repo','not-a-real-token')
        page1=[dict(number=n,title='[gba] A') for n in range(1,101)]
        page1[1]['pull_request']={}
        page1[2]['title']='Unrelated task'
        page2=[dict(number=101,title='[gba] LEFT'),dict(number=102,title='[gba-test] RIGHT')]
        paths=[]
        def request(method,path,data=None):
            paths.append(path)
            return page2 if 'page=2' in path else page1
        client.request=request
        queue=client.queue()
        self.assertEqual(len(queue),99)
        self.assertEqual(queue[-1]['number'],101)
        self.assertEqual(len(paths),2)
        self.assertNotIn(2,[i['number'] for i in queue])
        self.assertNotIn(3,[i['number'] for i in queue])

    def test_development_queue_does_not_consume_production_turns(self):
        client=GitHub('owner/repo','not-a-real-token')
        client.request=lambda *args:[dict(number=1,title='[gba] A'),dict(number=2,title='[gba-test] B')]
        self.assertEqual([i['number'] for i in client.queue('[gba-test]')],[2])

    def test_closed_command_is_still_available_for_processing(self):
        client=GitHub('owner/repo','not-a-real-token')
        def request(method,path,data=None):
            self.assertIn('state=all',path)
            return [dict(number=9,title='[gba] A 12',state='closed')]
        client.request=request
        self.assertEqual(client.queue()[0]['number'],9)

if __name__=='__main__':
    unittest.main()
