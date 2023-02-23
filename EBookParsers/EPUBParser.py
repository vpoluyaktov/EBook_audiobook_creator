
import os
import xml.etree.ElementTree as ET
import re
import base64
import zipfile
import html2text

class EPUBParser:

  def __init__(self):
    self.TOC_max_depth = 3
    self.book_title = ''
    self.book_author = ''
    self.book_annotation = ''
    self.cover_image = b''
    self.cover_image_name = ''
    self.book_chapters = []

  def parse(self, filename):
    file = zipfile.ZipFile(filename,"r");
    root_file = self.parse_container_xml(file.read("META-INF/container.xml"))

    content_dir = os.path.split(root_file)[0]
    if content_dir != "":
      content_dir = content_dir+"/"

    toc, toc_media_type, cover_href = self.parse_root_file(file.read(root_file).decode("utf-8"))
    self.book_chapters = self.parse_toc(file.read(content_dir + toc).decode("utf-8"), toc_media_type)
    self.book_chapters = self.fetch_chapters_text(self.book_chapters, file, content_dir)
    if cover_href:
      self.cover_image = file.read(content_dir + cover_href)
      self.cover_image_name = os.path.basename(cover_href)

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
    self.book_title = metadata.find('dc:title', ns).text
    self.book_author = metadata.find('dc:creator', ns).text
    annotation_element = metadata.find('dc:description', ns)
    if annotation_element != None:
      self.book_annotation = annotation_element.text

    toc = None
    manifest = root.find('opf:manifest', ns)
    for index, item in enumerate(manifest.findall('opf:item', ns)):
      if item.attrib["media-type"] in ['application/x-dtbncx+xml', 'application/xhtml+xml'] \
        and item.attrib["id"] in ['ncx', 'toc', 'ncxtoc']:
          toc = item.attrib["href"]
          toc_media_type = item.attrib["media-type"]
          break

    # get cover image
    cover_href = None
    for index, meta_tag in enumerate(metadata.findall('opf:meta', ns)):
      if meta_tag is not None and "name" in meta_tag.attrib and meta_tag.attrib['name'] == 'cover':
        cover_id = meta_tag.attrib['content']
        if cover_id != "":
          for index, item in enumerate(manifest.findall('opf:item', ns)):
            if item.attrib["id"] == cover_id \
              and item.attrib["media-type"] in ['image/jpeg', 'image/png']:
                cover_href = item.attrib["href"]
                break
        break

    return toc, toc_media_type, cover_href

  def parse_toc(self, toc_content, toc_media_type):
    if toc_media_type == 'application/x-dtbncx+xml':
      chapters = self.parse_toc_ncx(toc_content)
    elif toc_media_type == 'application/xhtml+xml':
      chapters = self.parse_toc_xhtml(toc_content)
    else:
      raise SystemExit('Unknown type of TOC file')
    return chapters

  def parse_toc_ncx(self, toc_content):
    ns = {'ncx': 'http://www.daisy.org/z3986/2005/ncx/'}
    chapters = []
    TOC_depth = 0
    root = ET.fromstring(toc_content)
    nav_map = root.find('ncx:navMap', ns)
    for index, nav_point in enumerate(nav_map.findall('ncx:navPoint', ns)):
      self.parse_nav_point_ncx(nav_point, chapters, TOC_depth)
    return chapters

  def parse_nav_point_ncx(self, nav_point, chapters, TOC_depth):
    TOC_depth += 1
    ns = {'ncx': 'http://www.daisy.org/z3986/2005/ncx/'}
    chapter_id = nav_point.attrib['id']
    chapter_title = nav_point.find('ncx:navLabel/ncx:text', ns).text
    chapter_title = chapter_title.rjust(TOC_depth * 4 + len(chapter_title), '\u00A0')
    chapter_content_source = nav_point.find('ncx:content', ns).attrib['src']
    chapters.append({'chapter_title': chapter_title, 'TOC_depth': TOC_depth, 'chapter_id': chapter_id, 'chapter_content_source': chapter_content_source})
    if TOC_depth < self.TOC_max_depth:
      for index, nav_point in enumerate(nav_point.findall('ncx:navPoint', ns)):
        self.parse_nav_point_ncx(nav_point, chapters, TOC_depth)

  def parse_toc_xhtml(self, toc_content):
    ns = {'html': 'http://www.w3.org/1999/xhtml', 'epub': 'http://www.idpf.org/2007/ops'}
    chapters = []
    TOC_depth = 0
    root = ET.fromstring(toc_content)
    nav_map = root.find('html:body/html:nav', ns)
    for index, nav_point in enumerate(nav_map.findall('html:ol/html:li', ns)):
      self.parse_nav_point_xhtml(nav_point, chapters, TOC_depth)
    return chapters

  def parse_nav_point_xhtml(self, nav_point, chapters, TOC_depth):
    TOC_depth += 1
    ns = {'html': 'http://www.w3.org/1999/xhtml', 'epub': 'http://www.idpf.org/2007/ops'}
    nav_href = nav_point.find('html:a', ns)
    chapter_id = nav_href.attrib['id']
    chapter_title = nav_href.text
    chapter_title = chapter_title.rjust(TOC_depth * 4 + len(chapter_title), '\u00A0')
    chapter_content_source = nav_href.attrib['href']
    chapters.append({'chapter_title': chapter_title, 'TOC_depth': TOC_depth, 'chapter_id': chapter_id, 'chapter_content_source': chapter_content_source})
    if TOC_depth < self.TOC_max_depth:
      for index, nav_point in enumerate(nav_point.findall('html:ol/html:li', ns)):
        self.parse_nav_point_xhtml(nav_point, chapters, TOC_depth)

  def fetch_chapters_text(self, chapters, file, content_dir):
    converter = html2text.HTML2Text()
    converter.body_width = 0
    converter.ignore_tables = True
    converter.ignore_emphasis = True
    converter.ignore_links = True
    converter.images_to_alt = True
    converter.default_image_alt="Image.\n"

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
      # cut chapter from a big html
      chapter_html = chapter_html[div_pos_start:div_pos_end]
      chapter_html = self.cleanup_html(chapter_html)
      chapter_text =  converter.handle(chapter_html)
      chapter['chapter_text'] = self.cleanup_text(chapter_text)
    return chapters

  def cleanup_html(self, html):
    # remove images alt tag
    html = re.sub(r'alt=".*"', '', html)
    # cleanup some special characters
    cleanup_dictionary = [ ('\u00A0', ' ')]
    for tuple in cleanup_dictionary:
      html = html.replace(tuple[0], tuple[1])
    return html

  def cleanup_text(self, text):
    # remove quote
    text = re.sub(r'>', '', text)
    # remove headers
    text = re.sub(r'#+ ', ' ', text)
    # add dot at the end of each paragraph
    paragraphs = ""
    for paragraph in text.split('\n'):
      paragraph = self.add_period(paragraph)
      paragraph += '\n'
      paragraphs += paragraph
    text = paragraphs
    # cleanup some special characters
    cleanup_dictionary = [('\.', '.')]
    for tuple in cleanup_dictionary:
      text = text.replace(tuple[0], tuple[1])
    return text

  def add_period(self, text):
    if text != None and text.strip() != '':
      if text.strip()[-1] != '.' and text.strip()[-1] != '?' and text.strip()[-1] != '!' and text.strip()[-1] != ':' and text.strip()[-3:] != '...'  and text.strip()[-1] != '"' and text.strip()[-1] != '”':
        text = text.strip() +'. '
    return text

  def save_text_to_file(self, text, filename):
    file = open(filename, "w")
    file.write(text)
    file.close

  def save_cover_image_to_file(self, path):
    cover_file_name = path + self.cover_image_name
    file = open(cover_file_name, "wb")
    file.write(self.cover_image)
    file.close
    return cover_file_name
