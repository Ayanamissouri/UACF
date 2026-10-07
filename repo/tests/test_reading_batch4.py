import unittest
from uacf.reading import units
class ReadingUnits(unittest.TestCase):
 def test_lossless_offsets_and_budget(self):
  text='如果要改。'+('长段内容'*100)+'；但是原文不能丢。\n另一点是语音问题。'
  u=units(text,64)
  self.assertEqual(''.join(x['literal'] for x in u),text)
  self.assertTrue(all(text[x['start']:x['end']]==x['literal'] and len(x['literal'])<=64 for x in u))
  self.assertTrue(any('但是' in x['cues'] for x in u))
  self.assertTrue(all(not x['semantic_verified'] for x in u))
  self.assertEqual(len({x['id'] for x in u}),len(u))
  # A different budget cannot silently make an old unit ID refer to new text.
  changed={x['id']:x['literal'] for x in units(text,80)}
  self.assertTrue(all(x['id'] not in changed or changed[x['id']]==x['literal'] for x in u))
if __name__=='__main__':unittest.main()
