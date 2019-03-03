# python 3 headers, required if submitting to Ansible
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
      lookup: ssl_key_text
        author: Gaige B. Paulsen <gaige@cluetrust.com>
        version_added: "0.9"
        short_description: read ssl key file contents
        description:
            - returns the contents of the an encrypted ssl key file
        options:
          _terms:
            description: path(s) of files to read
            required: True
          passphrase:
            description: passphrase to decrypt the key file with
        notes:
          - if read in variable context, the file can be interpreted as YAML if the content is valid to the parser.
          - this lookup does not understand globing --- use the fileglob lookup instead.
"""

EXAMPLES = """
- debug: msg="the key in foo.key is {{lookup('ssl_key_text', 'foo.key',passphrase='secret')}}"
"""

from ansible.errors import AnsibleError, AnsibleParserError, AnsibleModuleError
from ansible.plugins.lookup import LookupBase
from ansible.module_utils._text import to_text
from ansible.module_utils import crypto as crypto_utils
from ansible.utils.display import Display

try:
    import OpenSSL
    from OpenSSL import crypto
except ImportError:
    PYOPENSSL_FOUND = False
else:
    PYOPENSSL_FOUND = True

display = Display()


class LookupModule(LookupBase):

    def run(self, terms, variables=None, **kwargs):

        if not PYOPENSSL_FOUND:
            raise AnsibleModuleError('ssl_key_text plugin requires pyOpenSSL')

        # lookups in general are expected to both take a list as input and output a list
        # this is done so they work with the looping construct 'with_'.
        ret = []
        for term in terms:
            display.debug("key lookup term: %s" % term)

            # Find the file in the expected search path, using a class method
            # that implements the 'expected' search path for Ansible plugins.
            lookupfile = self.find_file_in_search_path(variables, 'files', term)

            # Don't use print or your own logging, the display class
            # takes care of it in a unified way.
            display.vvvv(u"key lookup using %s as file" % lookupfile)
            try:
                passphrase = kwargs.get('passphrase', None)
                if passphrase == '':
                    passphrase = None
                if lookupfile:
                    contents = crypto_utils.load_privatekey(lookupfile, passphrase)
                    text_contents = crypto.dump_privatekey(crypto.FILETYPE_PEM, contents)
                    ret.append(to_text(text_contents))
                else:
                    # Always use ansible error classes to throw 'final' exceptions,
                    # so the Ansible engine will know how to deal with them.
                    # The Parser error indicates invalid options passed
                    raise AnsibleParserError()
            except AnsibleParserError:
                raise AnsibleError("could not locate file in lookup: %s" % term)

        return ret
    