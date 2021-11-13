
import os
import xml.etree.ElementTree as ET
import re
import base64
import zipfile

class EPUBParser:

  def __init__(self):
    self.TOC_max_depth = 3
    self.book_title = None
    self.book_author = None
    self.book_annotation = None
    self.cover_image = None
    self.book_chapters = []

  def parse(self, filename):
    file = zipfile.ZipFile(filename,"r");  
    root_file = self.parse_container_xml(file.read("META-INF/container.xml"))

    content_dir = os.path.split(root_file)[0]
    if content_dir != "": 
      content_dir = content_dir+"/"   

    self.book_title, self.book_author, toc = self.parse_root_file(file.read(root_file))
    self.book_chapters = self.parse_toc(file.read(content_dir + toc))

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
    root = ET.fromstring(toc_file_xml)
    nav_map = root.find('ncx:navMap', ns)
    for nav_point in enumerate(nav_map.findall('ncx:navPoint', ns)):
      chapter_title = nav_point[1].find('ncx:navLabel/ncx:text', ns).text

    return chapters
