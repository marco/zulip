#!/usr/bin/env python

"""
Fenced Code Extension for Python Markdown
=========================================

This extension adds Fenced Code Blocks to Python-Markdown.

    >>> import markdown
    >>> text = '''
    ... A paragraph before a fenced code block:
    ...
    ... ~~~
    ... Fenced code block
    ... ~~~
    ... '''
    >>> html = markdown.markdown(text, extensions=['fenced_code'])
    >>> print html
    <p>A paragraph before a fenced code block:</p>
    <pre><code>Fenced code block
    </code></pre>

Works with safe_mode also (we check this because we are using the HtmlStash):

    >>> print markdown.markdown(text, extensions=['fenced_code'], safe_mode='replace')
    <p>A paragraph before a fenced code block:</p>
    <pre><code>Fenced code block
    </code></pre>

Include tilde's in a code block and wrap with blank lines:

    >>> text = '''
    ... ~~~~~~~~
    ...
    ... ~~~~
    ... ~~~~~~~~'''
    >>> print markdown.markdown(text, extensions=['fenced_code'])
    <pre><code>
    ~~~~
    </code></pre>

Language tags:

    >>> text = '''
    ... ~~~~{.python}
    ... # Some python code
    ... ~~~~'''
    >>> print markdown.markdown(text, extensions=['fenced_code'])
    <pre><code class="python"># Some python code
    </code></pre>

Copyright 2007-2008 [Waylan Limberg](http://achinghead.com/).

Project website: <http://packages.python.org/Markdown/extensions/fenced_code_blocks.html>
Contact: markdown@freewisdom.org

License: BSD (see ../docs/LICENSE for details)

Dependencies:
* [Python 2.4+](http://python.org)
* [Markdown 2.0+](http://packages.python.org/Markdown/)
* [Pygments (optional)](http://pygments.org)

"""

import re
import markdown
from zerver.lib.bugdown.codehilite import CodeHilite, CodeHiliteExtension

# Global vars
FENCE_RE = re.compile(r'(?P<fence>^(?:~{3,}))[ ]*(\{?\.?(?P<lang>[a-zA-Z0-9_+-]*)\}?)$', re.MULTILINE|re.DOTALL)
FENCED_BLOCK_RE = re.compile( \
    r'(?P<fence>^(?:~{3,}))[ ]*(\{?\.?(?P<lang>[a-zA-Z0-9_+-]*)\}?)?[ ]*\n(?P<code>.*?)(?<=\n)(?P=fence)[ ]*$',
    re.MULTILINE|re.DOTALL
    )
CODE_WRAP = '<pre><code%s>%s</code></pre>'
LANG_TAG = ' class="%s"'

class FencedCodeExtension(markdown.Extension):

    def extendMarkdown(self, md, md_globals):
        """ Add FencedBlockPreprocessor to the Markdown instance. """
        md.registerExtension(self)

        # Newer versions of Python-Markdown (starting at 2.3?) have
        # a normalize_whitespace preprocessor that needs to go first.
        position = ('>normalize_whitespace'
            if 'normalize_whitespace' in md.preprocessors
            else '_begin')

        md.preprocessors.add('fenced_code_block',
                                 FencedBlockPreprocessor(md),
                                 position)


class FencedBlockPreprocessor(markdown.preprocessors.Preprocessor):

    def __init__(self, md):
        markdown.preprocessors.Preprocessor.__init__(self, md)

        self.checked_for_codehilite = False
        self.codehilite_conf = {}


    def process_fence(self, m, text):
        langclass = ''
        if m.group('lang'):
            langclass = LANG_TAG % m.group('lang')

            if m.group('lang') in ('quote', 'quoted'):
                paragraphs = m.group('code').split("\n\n")
                quoted_paragraphs = []
                for paragraph in paragraphs:
                    lines = paragraph.split("\n")
                    quoted_paragraphs.append("\n".join("> " + line for line in lines if line != ''))
                replacement = "\n\n".join(quoted_paragraphs)
                return '%s\n%s\n%s'% (text[:m.start()], replacement, text[m.end():])

        # If config is not empty, then the codehighlite extension
        # is enabled, so we call it to highlite the code
        if self.codehilite_conf:
            highliter = CodeHilite(m.group('code'),
                    force_linenos=self.codehilite_conf['force_linenos'][0],
                    guess_lang=self.codehilite_conf['guess_lang'][0],
                    css_class=self.codehilite_conf['css_class'][0],
                    style=self.codehilite_conf['pygments_style'][0],
                    lang=(m.group('lang') or None),
                    noclasses=self.codehilite_conf['noclasses'][0])

            code = highliter.hilite()
        else:
            code = CODE_WRAP % (langclass, self._escape(m.group('code')))

        placeholder = self.markdown.htmlStash.store(code, safe=True)
        return '%s\n%s\n%s'% (text[:m.start()], placeholder, text[m.end():])

    def run(self, lines):
        """ Match and store Fenced Code Blocks in the HtmlStash. """

        # Check for code hilite extension
        if not self.checked_for_codehilite:
            for ext in self.markdown.registeredExtensions:
                if isinstance(ext, CodeHiliteExtension):
                    self.codehilite_conf = ext.config
                    break

            self.checked_for_codehilite = True

        text = "\n".join(lines)
        end = 0
        while 1:
            m = FENCED_BLOCK_RE.search(text)
            if m:
                end = m.end()
                text = self.process_fence(m, text)
            else:
                break


        fence = FENCE_RE.search(text, end)
        if fence:
            # If we found a starting fence but no ending fence,
            # then we add a closing fence before the two newlines that
            # markdown automatically inserts
            if text[-2:] == '\n\n':
                text = text[:-2] + '\n' + fence.group('fence') + text[-2:]
            else:
                text += fence.group('fence')
            m = FENCED_BLOCK_RE.search(text)
            if m:
                text = self.process_fence(m, text)

        return text.split("\n")

    def _escape(self, txt):
        """ basic html escaping """
        txt = txt.replace('&', '&amp;')
        txt = txt.replace('<', '&lt;')
        txt = txt.replace('>', '&gt;')
        txt = txt.replace('"', '&quot;')
        return txt


def makeExtension(configs=None):
    return FencedCodeExtension(configs=configs)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
