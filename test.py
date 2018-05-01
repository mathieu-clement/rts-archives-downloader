#!/usr/bin/env python3

from download import Downloader
import unittest
from pprint import pprint # Debug

class DownloaderTestCase(unittest.TestCase):

    master_playlist_url = 'https://rtsvodww-vh.akamaihd.net/i/1998/vers/vers_19980407_standard_vers_1998-04-07_Arch00_094728-,100k,700k,1200k,.mp4.csmil/master.m3u8'
    index_playlist_url = 'https://rtsvodww-vh.akamaihd.net/i/1998/vers/vers_19980407_standard_vers_1998-04-07_Arch00_094728-,100k,700k,1200k,.mp4.csmil/index_2_av.m3u8'

    def setUp(self):
        self.downloader = Downloader()
    
    def test_get_master_playlist_url(self):
        page_url = 'https://www.rts.ch/archives/tv/culture/verso/4716197-gribouille-en-metro.html'
        self.assertEqual(self.downloader.get_master_playlist_url(page_url), 
                         self.master_playlist_url)

    def test_get_index_playlist_url(self):
        self.assertEqual(
            self.downloader.get_index_playlist_url(self.master_playlist_url),
            self.index_playlist_url
            )

    def test_get_segment_urls(self):
        urls = self.downloader.get_segment_urls(self.index_playlist_url)
        num_segments = 33
        self.assertEqual(len(urls), num_segments)

        for i in range(num_segments):
            self.assertEqual(urls[i], 'https://rtsvodww-vh.akamaihd.net/i/1998/vers/vers_19980407_standard_vers_1998-04-07_Arch00_094728-,100k,700k,1200k,.mp4.csmil/segment' + str(i+1) + '_2_av.ts')


if __name__ == '__main__':
    unittest.main()
