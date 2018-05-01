#!/usr/bin/env python3

from bs4 import BeautifulSoup
import os
import requests
import shutil
import subprocess
import tempfile

class Downloader:

    def download_video(self, page_url, output_filename):
        """
        Given a page from the RTS Archives website, downloads the video in
        the highest quality that can be streamed from within that page.
        The second argument is the output file ('.mp4' extension recommended).

        More specifically, it fetches all the individual segments used for 
        streaming purposes, and reassembles them into a single video file
        using ffmpeg. The original audio and video formats are preserved.

        Use `pipes.quote(output_filename)` if not trusted, otherwise
        malicious shell commands could be executed.
        """
        master_playlist_url = self.get_master_playlist_url(page_url)
        index_playlist_url = self.get_index_playlist_url(master_playlist_url)
        segment_urls = self.get_segment_urls(index_playlist_url)

        num_segments = len(segment_urls)
        print('%d segments' % (num_segments))

        segment_files = []

        for i, url in enumerate(segment_urls):
            sys.stdout.write('\rDownloading segment %d/%d (%.1f %)' % (i+1, num_segments, (i+1)/num_segments))
            segment_file = self.__download_to_tempfile(url)
            segment_files.append(segment_file)

        print()

        concat_file = tempfile.NamedTemporaryFile(suffix='.ts', 
                                                  mode='wb',
                                                  delete=False)
        try:
            self.__concatenate_files__(segment_files, concat_file)
            concat_file.close() # Windows probably needs this here

            # Free resources, and also:
            # close() deletes temporary files by default.
            # Note: would be done upon garbage collection anyway.
            for segment_file in segment_files:
                segment_file.close()

            command = 'ffmpeg -i %s -acodec copy -vcodec copy %s' % \
                      (concat_file.name, output_filename)
            subprocess.check_call(command.split())
        finally:
            os.remove(concat_file.name)

    def get_segment_urls(self, index_playlist_url):
        text = requests.get(index_playlist_url).text
        lines = text.split('\n')[:-1] # TODO f.readlines?
        urls = [line for line in lines if not line.startswith('#')]
        urls = [self.__strip_query_params__(url) for url in urls]
        return urls

    def get_master_playlist_url(self, page_url):
        "Returns the playlist with all quality settings. Can be used in VLC."
        page_html = requests.get(page_url).text
        video_id = self.__get_video_id__(page_html)
        chapters_json = self.__get_chapters_json__(video_id)
        hd_resource_url = self.__get_hd_resource_url__(chapters_json, video_id)
        return hd_resource_url

    def get_index_playlist_url(self, master_playlist_url):
        """
        Given a master playlist, returns the so-called 'index playlist'
        which is a playlist of segments. The highest quality (HD) is selected.
        Can be used directly for streaming within VLC.
        """

        master_text = requests.get(master_playlist_url).text
        lines = master_text.split('\n') # TODO f.readlines?
        # skip first line and trim last empty line
        lines = lines[1:-1]

        # Find URL with max bandwith, i.e. max quality
        max_bandwidth = 0
        max_url = None

        # FYI [::2] => [begin:end:step]
        for meta, url in zip(lines[::2], lines[1::2]):
            assert meta.startswith('#')
            assert url.startswith('http')
        
            # Remove preamble
            meta = meta.replace('#EXT-X-STREAM-INF:', '')

            meta_attrs = self.__to_dict__(meta)
            bandwidth = int(meta_attrs['BANDWIDTH'])
            if bandwidth > max_bandwidth:
                max_bandwidth = bandwidth
                max_url = url

        max_url = self.__strip_query_params__(max_url)

        return max_url

    def __download_to_tempfile(self, url):
        tmp_file = tempfile.NamedTemporaryFile()
        r = requests.get(url)
        tmp_file.write(r.content)
        tmp_file.flush()
        return tmp_file

    def __concatenate_files__(self, infiles, outfile):
        # outfile must be opened in 'wb' mode
        # infiles must be opened in 'rb' or 'w+b' (which is different 
        # from 'wb') modes

        for f in infiles:
            shutil.copyfileobj(open(f.name, mode='rb'), outfile)

    def __strip_query_params__(self, url):
        return url.split('?')[0] if '?' in url else url

    def __to_dict__(self, meta_str):
        d = {}
        for meta_item in meta_str.split(','):
            try:
                meta_name, meta_value = meta_item.strip().split('=')
                assert meta_name not in d
                d[meta_name] = meta_value
            except ValueError: # comes from "  CODECS="a, b"  "
                               # which gets incorrectly splitted
                               # I'm too lazy to fix it.
                pass
        return d


    def __get_video_id__(self, page_html):
        return BeautifulSoup(page_html, 'lxml')\
               .find('meta', attrs={'name':'dcterms.identifier'})['content']

    def __get_chapters_json__(self, video_id):
        chapters_url = 'https://il.srgssr.ch/integrationlayer/2.0/mediaComposition/byUrn/urn:rts:video:' + video_id + '.json'
        return requests.get(chapters_url).json()

    def __get_hd_resource_url__(self, chapters_json, video_id):
        if 'chapterList' not in chapters_json:
            raise Exception("Doesn't seem to be a *video* archive.")

        chapters =  [
                        c for c
                        in chapters_json['chapterList']
                        if c['analyticsMetadata']['media_segment_id'] == video_id
                    ]
        assert len(chapters) == 1
        chapter = chapters[0]

        resources = [
                        f for f 
                        in chapter['resourceList'] 
                        if f['quality'] == 'HD' 
                        and f['mimeType'] == 'application/x-mpegURL'
                    ]
        assert len(resources) == 1

        return resources[0]['url']


if __name__ == '__main__':
    import re
    import sys

    def default_filename(url):
        html_filename = url.split('/')[-1]
        basename, _ = html_filename.split('.html')
        # 3452662-le-metro-de-l-expo   =>   le-metro-de-l-expo
        basename = re.match('\d+-(.*)', basename).group(1)
        return basename + '.mp4'
        

    if len(sys.argv) < 2:
        print('Usage: %s page_url [output_filename.mp4]' % (sys.argv[0]), 
              file=sys.stderr)
        sys.exit(1)
    page_url = sys.argv[1]
    output_filename = sys.argv[2] if len(sys.argv) > 2 else default_filename(page_url)
    print('Output filename:', output_filename)
    Downloader().download_video(page_url, output_filename)
