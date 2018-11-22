# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from h._version import get_version

# https://blog.csdn.net/kwame211/article/details/79669393
# add by wliang 11-21
import sys
defaultencoding = 'utf-8'
if sys.getdefaultencoding() != defaultencoding:
    reload(sys)
    sys.setdefaultencoding(defaultencoding)

__all__ = ('__version__',)
__version__ = get_version()
