#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Writteby by [Yuri Takhteyev](http://www.freewisdom.org).
License: GPL 2 (http://www.gnu.org/copyleft/gpl.html) or BSD
"""

import sys, zipfile, xml.dom.minidom

            ## u"Default": "p",
            ## u"Fait à": "",
            ## u"Formule d'adoption": "",
            ## u"Institution qui signe": "",
            ## u"Intérêt EEE": "",
            ## u"Manual Heading 4": "",
            ## u"Manual NumPar 1": "",
            ## u"Manual NumPar 2": "",
            ## u"NumPar 1": "",
            ## u"Personne qui signe": "",
            ## u"Point 0": "",
            ## u"Point 0 (number)": "",
            ## u"Point 1": "",
            ## u"Point 1 (letter)": "",
            ## u"Statut": "",
            ## u"Text 1": "",

class Node:
    def __init__ (self, title,tpe=None) :
        self.title=title
        self.nodes=[]
        self.type=tpe

    def __repr__ (self):
        nodes=u', '.join((repr(x) for x in self.nodes))
        if self.type:
            res= u"<%s: %s [%s]>" % (self.type, self.title, nodes)
        elif nodes:
            res= u"<%s [%s]>" % (self.title, nodes)
        else:
            res= u"<%s>" % self.title
        return res

    def dump(self,ind=0):
        print '\t' * ind,
        if self.type:
            print self.type.encode('utf8'),
        print self.title.encode('utf8')
        [x.dump(ind+1) for x in self.nodes]

class OpenDocumentTextFile :
    def __init__ (self, filepath) :
        self.footnotes = []
        self.recitals = []
        self.chaps = []
        self.ref = ""
        self.type = ""
        self.title = ""
        self.institutions = ""
        self.load(filepath)

    def load(self, filepath) :
        zip = zipfile.ZipFile(filepath)
        self.content = xml.dom.minidom.parseString(zip.read("content.xml"))
        zip.close()

        styles = dict([(style.getAttribute('style:name'),
                        style.getAttribute('style:parent-style-name'))
                       for style
                       in self.content.getElementsByTagName("style:style")])
        paragraphs = self.content.getElementsByTagName("text:p")

        prev = None
        for paragraph in paragraphs :
            style=styles.get(paragraph.getAttribute("text:style-name"),'') \
                   .replace('_20_',' ') \
                   .replace('_27_',"'") \
                   .replace("_28_","(") \
                   .replace("_29_",")")

            if style == u"Application directe":
                break

            elif style == u"Référence interinstitutionnelle":
                self.ref = self.textToString(paragraph)

            elif style == u"Type du document":
                self.type = self.textToString(paragraph)

            elif style == u"Titre objet":
                self.title = self.textToString(paragraph)

            elif style == u"Institution qui agit":
                self.institutions = self.textToString(paragraph)

            elif style == u"Considérant":
                self.recitals.append(self.textToString(paragraph))

            elif style == u"ChapterTitle":
                if style == prev:
                    last = self.chaps[-1]
                    last.title="%s %s" % (last.title, self.textToString(paragraph))
                else:
                    self.chaps.append(Node(self.textToString(paragraph),'chapter'))

            elif style == u"SectionTitle":
                if style == prev:
                    last = self.chaps[-1].nodes[-1]
                    last.title="%s %s" % (last.title, self.textToString(paragraph))
                else:
                    self.chaps[-1].nodes.append(Node(self.textToString(paragraph), 'section'))

            elif style == u"Titre article":
                last = self.last()
                if style == prev:
                    last[-1].title="%s %s" % (last[-1].title, self.textToString(paragraph))
                else:
                    last.append(Node(self.textToString(paragraph), 'article'))

            elif self.chaps and self.chaps[-1].nodes:
                node = Node(self.textToString(paragraph), style)
                last = self.last()[-1].nodes
                last.append(node)
            #else:
            #    print >>sys.stderr, "<%s>%s</%s>" % (style.encode('utf8'),
            #                                         self.textToString(paragraph).encode('utf8'),
            #                                         style.encode('utf8'))
            prev = style

    def last(self):
        if not self.chaps[-1].nodes or self.chaps[-1].nodes[-1].type == 'article':
            return self.chaps[-1].nodes
        return self.chaps[-1].nodes[-1].nodes

    def textToString(self, element):
        buffer = u""
        for node in element.childNodes :
            if node.nodeType == xml.dom.Node.TEXT_NODE :
                buffer += node.nodeValue

            elif node.nodeType == xml.dom.Node.ELEMENT_NODE :
                tag = node.tagName

                if tag == "text:span" :

                    text = self.textToString(node)

                    if not text.strip() :
                        return ""  # don't apply styles to white space

                    buffer += text

                elif tag == "text:note" :
                    cite = (node.getElementsByTagName("text:note-citation")[0]
                                .childNodes[0].nodeValue)

                    body = (node.getElementsByTagName("text:note-body")[0]
                                .childNodes[0])

                    self.footnotes.append((cite, self.textToString(body)))

                    buffer += "[^%s]" % cite

                elif tag == "text:s" :
                    try :
                        num = int(node.getAttribute("text:c"))
                        buffer += " "*num
                    except :
                        buffer += " "

                elif tag == "text:tab" :
                    buffer += "    "


                elif tag == "text:a" :

                    text = self.textToString(node)
                    link = node.getAttribute("xlink:href")
                    buffer += "[%s](%s)" % (text, link)

                #else :
                #    buffer += " {" + tag + "} "

        return buffer

    def dump(self):
        for c in self.chaps:
            print c.title
            for x in c.nodes: x.dump()

if __name__ == "__main__" :
    odt = OpenDocumentTextFile(sys.argv[1])
    print odt.ref, odt.title
    odt.dump()
