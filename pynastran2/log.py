"""
defines a colorama log
"""
# coding: utf-8
from __future__ import print_function, unicode_literals
import sys
import platform
import os
from six import PY2, string_types

IS_TERMINAL = False
if sys.stdout.isatty():
    IS_TERMINAL = True
# You're running in a real terminal

try:
    from colorama import init as colorinit, Fore #, Style
    colorinit(autoreset=True)
    IS_COLORAMA = True
    IS_TERMINAL = True
except ImportError:
    IS_COLORAMA = False
USE_COLORAMA = IS_COLORAMA and IS_TERMINAL

#else:
    #from colorama import init as colorinit, Fore
    #colorinit(autoreset=True)

    ## You're being piped or redirected
    #IS_TERMINAL = False
#IS_TERMINAL = False


def make_log(display=False):
    """
    Creates 'pyNastran.log' file with information about working environment,
    such as Python version, platform, architecture, etc. Useful for debugging.

    Parameters
    ----------
    display : bool
        do not only create file but also print log information
    """
    smsg = [('sys.version', sys.version), ('sys.version_info', sys.version_info)]
    pmsg = [
        'machine', 'platform', 'processor', 'architecture', 'python_branch',
        'python_revision', 'win32_ver', 'version', 'uname', 'system',
        'python_build', 'python_compiler', 'python_implementation', 'system',
        'mac_ver', 'linux_distribution', 'libc_ver'
    ]

    fmt = '%-{0}s = %s\n'.format(max(map(len, pmsg + [j[0] for j in smsg])))
    msg = ''.join([fmt % (i, str(j).replace('\n', '; ')) for (i, j) in smsg])
    msg += ''.join([fmt % (i, str(getattr(platform, i)())) for i in pmsg])
    if display:
        print(msg)

    with open('pyNastran.log', 'wb') as fil:
        fil.write(msg)


class SimpleLogger(object):
    """
    Simple logger object. In future might be changed to use Python logging module.
    Two levels are supported: 'debug' and 'info'. Info level discards debug
    messages, 'debug' level displays all messages.

    .. note:: Logging module is currently not supported because I don't
      know how to repoint the log file if the program is called a second
      time.  Poor logging can result in:\n
        1) double logging to a single file\n
        2) all logging going to one file\n
      This is really only an issue when calling logging multiple times,
      such as in an optimization loop or testing.
    """

    def __init__(self, level='debug', encoding='utf-8', log_func=None):
        """
        Parameters
        ----------
        level : str
            level of logging: 'info' or 'debug'
        encoding : str; default='utf-8'
            the unicode encoding method
        log_func : log
          funtion that will be used to print log. It should take one argument:
          string that is produces by a logger. Default: print messages to
          stderr using @see stderr_logging function.
        """
        if log_func is None:
            log_func = self.stdout_logging
        assert level in ('info', 'debug', 'warning', 'error'), 'logging level=%r' % level
        #assert encoding in ['utf-8', 'latin-1', 'ascii'], encoding
        self.level = level
        self.log_func = log_func
        self.encoding = encoding
        assert isinstance(encoding, string_types), type(encoding)

    def stdout_logging(self, typ, msg):
        """
        Default logging function. Takes a text and outputs to stdout.

        Parameters
        ----------
        typ : str
            messeage type - ['DEBUG', 'INFO', 'WARNING', 'ERROR']
        msg : str
            message to be displayed

        Message will have format 'typ: msg'
        """
        # max length of 'INFO', 'DEBUG', 'WARNING', etc.
        name = '%-8s' % (typ + ':')
        #if not IS_TERMINAL or not typ:
        if not USE_COLORAMA:
            # if we're writing to a file
            #out = name + msg
            if PY2:
                sys.stdout.write((name + msg).encode(self.encoding)
                                 if typ else msg.encode(self.encoding))
            else:
                sys.stdout.write((name + msg) if typ else msg)
        else:
            _write_screen(typ, name + msg)
        sys.stdout.flush()

    def msg_typ(self, typ, msg):
        """
        Log message of a given type

        Parameters
        ----------
        typ : str
            type of a message (e.g. INFO)
        msg : str
            message to be logged
        """
        n, filename = properties()
        filename_n = '%s:%s' % (filename, n)
        self.log_func(typ, ' %-28s %s\n' % (filename_n, msg))
        #self.log_func(typ, '   fname=%-25s lineNo=%-4s   %s\n' % (fn, n, msg))

    def simple_msg(self, msg, typ=None):
        """
        Log message directly without any altering.

        Parameters
        ----------
        msg : str
            message to be looged without any alteration.
        typ : str
            type of a message (e.g. INFO)
        """
        assert msg is not None, msg
        self.log_func(typ, msg)

    def debug(self, msg):
        """
        Log DEBUG message

        Parameters
        ----------
        msg : str
            message to be logged
        """
        if self.level != 'debug':
            return
        self.msg_typ('DEBUG', msg)

    def info(self, msg):
        """
        Log INFO message

        Parameters
        ----------
        msg : str
            message to be logged
        """
        if self.level not in ('debug', 'info'):
            return
        assert msg is not None, msg
        self.msg_typ('INFO', msg)

    def warning(self, msg):
        """
        Log WARNING message

        Parameters
        ----------
        msg : str
            message to be logged
        """
        assert msg is not None, msg
        self.msg_typ('WARNING', msg)

    def error(self, msg):
        """
        Log ERROR message

        Parameters
        ----------
        msg : str
            message to be logged
        """
        assert msg is not None, msg
        self.msg_typ('ERROR', msg)

    def exception(self, msg):
        """
        Log EXCEPTION message

        Parameters
        ----------
        msg : str
            message to be logged
        """
        assert msg is not None, msg
        self.msg_typ('ERROR', msg)

    def critical(self, msg):
        """
        Log CRITICAL message

        Parameters
        ----------
        msg : str
            message to be logged
        """
        assert msg is not None, msg
        self.msg_typ('CRITICAL', msg)

def properties(nframe=3):
    """
    Gets frame information

    Parameters
    ----------
    nframe : int; default=3
        the number of frames to jump back
        0 = current
        2 = calling from an embedded function (e.g., log_msg)
        3 = calling from an embedded class (e.g., SimpleLogger)

    Returns
    -------
    line number : int
        the line number of the nth frame
    filename : str
        the filen ame of the nth frame
    """
    # jump to get out of the logger code
    frame = sys._getframe(nframe)
    active_file = os.path.basename(frame.f_globals['__file__'])
    if active_file.endswith('.pyc'):
        return frame.f_lineno, active_file[:-1]
    return frame.f_lineno, active_file

def get_logger(log=None, level='debug', encoding='utf-8'):
    """
    This function is useful as it will instantiate a simpleLogger object if log=None.

    Parameters
    ----------

    log: log / None
         a logger object or None
    level : str
        level of logging: 'info' or 'debug'
    """
    return SimpleLogger(level, encoding=encoding) if log is None else log


def get_logger2(log=None, debug=True, encoding='utf-8'):
    """
    This function is useful as it will instantiate a SimpleLogger object
    if log=None.

    Parameters
    ----------
    log : log / None
        a python logging module object;
        if log is set, debug is ignored and uses the
        settings the logging object has
    debug : bool / None
       used to set the logger if no logger is passed in
           True:  logs debug/info/error messages
           False: logs info/error messages
           None:  logs error messages

    Returns
    -------
    log : log / SimpleLogger
        logging
    """
    if log is not None:
        pass
    elif debug is None:
        log = SimpleLogger('warning', encoding=encoding)
    else:
        level = 'debug' if debug else 'info'
        log = SimpleLogger(level, encoding=encoding)
    return log

def log_msg(typ, msg, encoding='utf-8'):
    """
    Functional based logging function equivalent to SimpleLogger.
    Takes a text and outputs to stderr.

    Parameters
    ----------
    typ : str
        messeage type - ['DEBUG', 'INFO', 'WARNING', 'ERROR']
    msg : str
        message to be displayed
    encoding : str; default='utf-8'
        the unicode encoding method

    Message will have format 'typ: msg'
    """
    n, filename = properties(nframe=2)
    filename_n = '%s:%s' % (filename, n)
    _log_msg(typ, '%-8s: %-28s %s\n' % (typ, filename_n, msg), encoding=encoding)

def _log_msg(typ, msg, encoding='utf-8'):
    """
    Helper function for log_msg

    Parameters
    ----------
    typ : str
        messeage type - ['DEBUG', 'INFO', 'WARNING', 'ERROR']
    msg : str
        message to be displayed
    encoding : str; default='utf-8'
        the unicode encoding method
    """
    # max length of 'INFO', 'DEBUG', 'WARNING', etc.

    #name = '%-8s' % (typ + ':')
    #if not IS_TERMINAL or not typ:
    if not IS_TERMINAL:
        # if we're writing to a file
        _write_suppressed(typ, msg, encoding)
    else:
        _write_screen(typ, msg)
    sys.stdout.flush()

def _write_suppressed(typ, msg, encoding):
    """
    Writes to a piped file

    Parameters
    ----------
    typ : str
        messeage type - ['DEBUG', 'INFO', 'WARNING', 'ERROR']
    msg : str
        message to be displayed
    encoding : str; default='utf-8'
        the unicode encoding method
    """
    # if we're writing to a file
    #out = name + msg
    if PY2:
        sys.stdout.write((msg).encode(encoding) if typ else msg.encode(encoding))
    else:
        sys.stdout.write((msg) if typ else msg)
    if IS_COLORAMA and typ == 'ERROR':
        sys.stderr.write(Fore.RED + msg)

def _write_screen(typ, msg):
    """
    Writes to the screen

    Parameters
    ----------
    typ : str
        messeage type - ['DEBUG', 'INFO', 'WARNING', 'ERROR']
    msg : str
        message to be displayed
    """
    # write to the screen
    #
    # Python 3 requires str, not bytes
    # Python 2 seems to be able to use either
    if typ == 'INFO':
        #'\033[ 1 m; 34 m'
        # only works for Python 2
        #out = (Fore.GREEN + msg).encode(encoding)
        # seems to work with both
        sys.stdout.write(Fore.GREEN + msg)
    elif typ == 'DEBUG':
        sys.stdout.write(Fore.CYAN + msg)
    elif typ == 'WARNING':
        # no ORANGE?
        sys.stdout.write(Fore.YELLOW + msg)
    else: # error / other
        sys.stdout.write(Fore.RED + msg)

if __name__ == '__main__':  # pragma: no cover
    # how to use a simple logger
    for nam in ['debug', 'info']:
        #print('--- %s logger ---' % nam)
        test_log = SimpleLogger(nam, encoding='utf-8')
        test_log.debug('debug message')
        test_log.warning('warning')
        test_log.error('errors')
        test_log.exception('exception')
    make_log(display=True)
