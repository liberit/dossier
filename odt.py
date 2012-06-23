#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, zipfile, xml.dom.minidom

articlechilds=['Point 0', 'Point 0 (number)', 'Standard', 'Manual NumPar 1', 'NumPar 1', 'Manual Heading 4', 'Manual NumPar 2']
paragraphkids=['Point 1', 'Point 1 (letter)', 'Text 1']
listtypes=['Point 0', 'Point 0 (number)', 'Manual NumPar 1', 'NumPar 1', 'Manual Heading 4', 'Manual NumPar 2', 'Point 1', 'Point 1 (letter)']

## u"Default": "p",
## u"Fait à": "",
## u"Institution qui signe": "",
## u"Intérêt EEE": "",
## u"Personne qui signe": "",
## u"Statut": "",

class Node:
    def __init__ (self, title, tpe=None) :
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

    def add(self, node):
        # if last item is a list and this contains the same type as
        # node, then append it there
        if (self.nodes and
            self.nodes[-1].type == 'list' and
            self.nodes[-1].title == node.type):
            self.nodes[-1].nodes.append(node)
            return node
        # check if type is list, if so, create a container and append
        # that to self
        if node.type in listtypes:
            container = Node(node.type, 'list')
            container.nodes.append(node)
            node = container
        self.nodes.append(node)
        return node

    def dump(self,ind=0):
        if self.type!='list':
            if self.type in ['article', 'section']: print '\n'
            if ind>0: print ' ' * (ind * 2),
            print self.title.encode('utf8')
        [x.dump(ind+1) for x in self.nodes]

class ODT:
    def __init__ (self, path) :
        self.footnotes = []
        self.preamble = []
        self.recitals = []
        self.chaps = []
        self.ref = ""
        self.type = ""
        self.title = ""
        self.institutions = ""
        self.adoption = ""
        self.load(path)

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
        stack = {}
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

            elif style == u"Formule d'adoption":
                self.adoption = self.textToString(paragraph)

            elif style == u"Type du document":
                self.type = self.textToString(paragraph)

            elif style == u"Titre objet":
                self.title = self.textToString(paragraph)

            elif style == u"Institution qui agit":
                self.institutions = self.textToString(paragraph)

            elif style == u"Considérant":
                self.recitals.append(self.textToString(paragraph))

            elif not stack and style == u"Standard":
                self.preamble.append(self.textToString(paragraph))

            elif style == u"ChapterTitle":
                if style == prev:
                    last = stack['chapter']
                    last.title="%s %s" % (last.title, self.textToString(paragraph))
                    #print 'append', last.title
                else:
                    node = Node(self.textToString(paragraph),'chapter')
                    self.chaps.append(node)
                    stack = { 'chapter': node }
                    #print 'new',stack['chapter'].title

            elif style == u"SectionTitle":
                if style == prev:
                    last = stack['section']
                    last.title="%s %s" % (last.title, self.textToString(paragraph))
                else:
                    node = Node(self.textToString(paragraph),'section')
                    stack['chapter'].nodes.append(node)
                    stack = { 'chapter': stack['chapter'],
                              'section': node }

            elif style == u"Titre article":
                if style == prev:
                    last = stack['article']
                    last.title="%s %s" % (last.title, self.textToString(paragraph))
                else:
                    target = 'section' if 'section' in stack else 'chapter'
                    node = Node(self.textToString(paragraph),'article')
                    stack[target].add(node)
                    stack = dict([x for x in stack.items() if x[0] in ['chapter', 'section']])
                    stack['article']=node

            elif stack:
                #print style.encode('utf8')
                if style in articlechilds:
                    stack['list'] = stack['article'].add(Node(self.textToString(paragraph), style))
                elif style in paragraphkids:
                    stack['list'].add(Node(self.textToString(paragraph), style))
                else:
                    print >>sys.stderr, '[!] unknown style', style

            else:
                print >>sys.stderr, "<%s>%s</%s>" % (style.encode('utf8'),
                                                     self.textToString(paragraph).encode('utf8'),
                                                     style.encode('utf8'))
            prev = style

    def dump(self):
        print self.ref, self.title
        print
        for p in self.preamble:
            print p
        print
        for i, r in enumerate(self.recitals):
            print (u"  (%s) %s" % (i+1,r)).encode('utf8')
            print
        print
        print self.adoption
        print
        for c in self.chaps:
            print
            print c.title
            for x in c.nodes: x.dump()
        print
        print "Footnotes"
        for i, r in enumerate(self.footnotes):
            print (u"  (%s) %s" % (i+1,r)).encode('utf8')

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
                else: buffer += " "
        return ' '.join(buffer.split())

if __name__ == "__main__" :
    odt = ODT(sys.argv[1])
    #odt.dump()
    odt.html()
