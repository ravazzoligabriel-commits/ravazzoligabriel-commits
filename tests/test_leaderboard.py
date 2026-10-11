import unittest
from community.render import leaderboard

class LeaderboardTests(unittest.TestCase):
    def test_all_time_counts_exclude_rejections_and_merge_login_case(self):
        ledger={str(i):dict(player='Alice',status='applied') for i in range(220)}
        ledger['220']=dict(player='alice',status='applied')
        ledger['221']=dict(player='Bob',status='rejected')
        self.assertEqual(leaderboard(ledger),[dict(rank=1,player='Alice',commands=221,profile='https://github.com/Alice')])

    def test_top_ten_sort_by_count_then_username(self):
        ledger={str(i):dict(player=f'player-{i:02}',status='applied') for i in range(12)}
        ledger['extra']=dict(player='player-11',status='applied')
        result=leaderboard(ledger)
        self.assertEqual(len(result),10)
        self.assertEqual(result[0]['player'],'player-11')
        self.assertEqual(result[0]['commands'],2)
        self.assertEqual(result[1]['player'],'player-00')
        self.assertEqual(result[-1]['rank'],10)

    def test_empty_ranking_has_no_invented_players(self):
        self.assertEqual(leaderboard({}),[])
