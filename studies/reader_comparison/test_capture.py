import unittest
from capture import read_positions


class PositionTest(unittest.TestCase):
    def test_action_straddling_token_is_not_in_before_state(self):
        positions=read_positions(100,[3,7,10,12],5,11)
        self.assertEqual(positions['before_action'],100)
        self.assertEqual(positions['after_action'],103)
        self.assertEqual(positions['before_action_32'],68)

    def test_action_at_response_start_reads_last_prompt_token(self):
        self.assertEqual(read_positions(10,[3,7],0,6)['before_action'],9)

    def test_unfinished_action_is_rejected(self):
        with self.assertRaises(ValueError):read_positions(10,[3,7],0,8)


if __name__=='__main__':unittest.main()
