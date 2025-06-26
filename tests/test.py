#!/usr/bin/env python
import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))


from util import log
lg = log.get(__name__)

class TestBase(unittest.TestCase):

    def test(self):
        from conf import envs
        p = 'upload/encoded-video/f9e23a5d-ea0f-4cb4-ad46-eab391483bed/64/2b/642b913b-28a7-479b-9f9a-a1f527da05d0.mp4'
        r = envs.pth.base(p)

        lg.info(f'p[{p}] -> {r}')

        pass


if __name__ == "__main__":
    unittest.main()
