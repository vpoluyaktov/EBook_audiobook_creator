
import os
import xml.etree.ElementTree as ET
import re
import base64
import zipfile
import html2text

class EPUBParser:

  cleanup_dictionary = [ ('\u00A0', ' ')]

  def __init__(self):
    self.TOC_max_depth = 3
    self.book_title = ''
    self.book_author = ''
    self.book_annotation = ''
    self.cover_image = b''
    self.book_chapters = []

  def parse(self, filename):
    file = zipfile.ZipFile(filename,"r");  
    root_file = self.parse_container_xml(file.read("META-INF/container.xml"))

    content_dir = os.path.split(root_file)[0]
    if content_dir != "": 
      content_dir = content_dir+"/"   

    self.book_title, self.book_author, toc = self.parse_root_file(file.read(root_file))
    self.book_chapters = self.parse_toc(file.read(content_dir + toc))
    self.book_chapters = self.fetch_chapters_text(self.book_chapters, file, content_dir)

  def parse_container_xml(self, container_xml):
    ns = {'container': 'urn:oasis:names:tc:opendocument:xmlns:container'}
    root = ET.fromstring(container_xml)
    root_file = root.find('container:rootfiles/container:rootfile', ns).attrib['full-path']
    return root_file

  def parse_root_file(self, root_file_xml):
    ns = {
      'opf': 'http://www.idpf.org/2007/opf',
      'dc': 'http://purl.org/dc/elements/1.1/',
      'dcterms': 'http://purl.org/dc/terms/',
      'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
    }
    root = ET.fromstring(root_file_xml)

    metadata = root.find('opf:metadata', ns)
    title = metadata.find('dc:title', ns).text
    author = metadata.find('dc:creator', ns).text

    toc = None
    manifest = root.find('opf:manifest', ns)
    for item in enumerate(manifest.findall('opf:item', ns)):
      if item[1].attrib["media-type"] == "application/x-dtbncx+xml" \
        and item[1].attrib["id"] in ['ncx', 'toc', 'ncxtoc']:
          toc = item[1].attrib["href"]
          break

    return title, author, toc

  def parse_toc(self, toc_file_xml):
    ns = {'ncx': 'http://www.daisy.org/z3986/2005/ncx/'}
    chapters = []
    TOC_depth = 0
    root = ET.fromstring(toc_file_xml)
    nav_map = root.find('ncx:navMap', ns)
    for nav_point in enumerate(nav_map.findall('ncx:navPoint', ns)):
      self.parse_nav_point(nav_point, chapters, TOC_depth)
    return chapters

  def parse_nav_point(self, nav_point, chapters, TOC_depth):
    TOC_depth += 1
    ns = {'ncx': 'http://www.daisy.org/z3986/2005/ncx/'}
    chapter_id = nav_point[1].attrib['id']
    chapter_title = nav_point[1].find('ncx:navLabel/ncx:text', ns).text
    chapter_title = chapter_title.rjust(TOC_depth * 4 + len(chapter_title), '\u00A0')
    chapter_content_source = nav_point[1].find('ncx:content', ns).attrib['src']
    chapters.append({'chapter_title': chapter_title, 'TOC_depth': TOC_depth, 'chapter_id': chapter_id, 'chapter_content_source': chapter_content_source})
    if TOC_depth < self.TOC_max_depth:
      for nav_point in enumerate(nav_point[1].findall('ncx:navPoint', ns)):
        self.parse_nav_point(nav_point, chapters, TOC_depth)

  def fetch_chapters_text(self, chapters, file, content_dir):
    for index, chapter in enumerate(chapters):
      chapter_content_source = chapter['chapter_content_source']
      chapter_file_name, chapter_anchor = chapter_content_source.split('#')
      chapter_html = file.read(content_dir + chapter_file_name).decode("utf-8")

      div_pos_start = None
      div_pos_end = None
      # find chapter start position
      if chapter_anchor:
        id_pos_start = chapter_html.find('id="' + chapter_anchor + '"') 
        if id_pos_start != -1:
          div_pos_start = chapter_html.rfind('<', 0, id_pos_start)

      # find chapter end position
      if index < len(chapters) -1:
        next_chapter = chapters[index + 1]
        next_chapter_content_source = next_chapter['chapter_content_source']
        next_chapter_file_name, next_chapter_anchor = next_chapter_content_source.split('#')
        if chapter_file_name == next_chapter_file_name:
          id_pos_end = chapter_html.find('id="' + next_chapter_anchor + '"') 
          if id_pos_end != -1:
            div_pos_end = chapter_html.rfind('<', 0, id_pos_end)

      chapter_html = chapter_html[div_pos_start:div_pos_end]

      chapter_text =  html2text.html2text(chapter_html, bodywidth = 0)      
      chapter['chapter_text'] = chapter_text

    return chapters  

  def cleanup_text(self, text):
    for tuple in self.cleanup_dictionary:
      text = text.replace(tuple[0], tuple[1])
    return text  

  def save_text_to_file(self, text, filename):
    file = open(filename, "w")
    file.write(text)
    file.close  

  def save_cover_image_to_file(self, path):
    cover_file_name = path + self.cover_image_name
    file = open(cover_file_name, "wb")
    file.write(base64.b64decode(self.cover_image))
    file.close 
    return cover_file_name  


      
