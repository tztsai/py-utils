from my_utils import debug, partial, override, update_wrapper
import sys, os, re, time, random, requests
from IPython import get_ipython

get_ipython().run_line_magic('load_ext', 'autoreload')
get_ipython().run_line_magic('autoreload', '2')


class UTIL:
    from queue import Queue
    from threading import Thread
    from IPython.core.interactiveshell import InteractiveShell as Shell
    
    loglevel = debug.INFO  #DEBUG-1
    transform_input = False
    _shell = get_ipython()
    _ipy_transform_cell = _shell.transform_cell
    _my_transform_cell = None
    
    @classmethod
    def conf(cls, **kwds):
        for k, v in kwds.items():
            setattr(cls, k, v)
            
        debug.setloglevel(cls.loglevel)
        if cls.loglevel > debug.DEBUG:
            globals()['breakpoint'] = lambda: 0
        elif cls.loglevel < debug.DEBUG:
            debug.loadDebugger()
            
        cls.Shell.transform_cell = cls.transform_cell

    @classmethod
    def transform_cell(cls, cell):
        if cls.transform_input:
            cell = cls._my_transform_cell(cell)
        cell = cls._ipy_transform_cell(cell)
        return cell

    @classmethod
    def coroutine(cls, task):
        if not hasattr(cls, 'tasks'):
            cls.tasks = cls.Queue()
        cls.tasks.put(task)
        if not hasattr(cls, 'task_thread'):
            cls.task_thread = cls.Thread(target=cls.run_tasks)
            cls.task_thread.start()
        return task

    @classmethod
    def run_tasks(cls):
        while not cls.tasks.empty():
            cls.tasks.get()()
        del cls.task_thread, cls.tasks


class NameSpace(dict):
    def __getattr__(self, name):
        return self[name]
    def __setattr__(self, name: str, value) -> None:
        self[name] = value
    def __repr__(self) -> str:
        return '{%s}' % ', '.join(f'{k}={repr(v)}' for k, v in self.items())


def findattrs(obj, substr=''):
    return [a for a in dir(obj) if substr in a]

def copy_text(text):
    try:
        global pd
        s = pd.Series(text)
    except:
        import pandas
        s = pandas.Series(text)
    s.to_clipboard(index=False)

def first(iterable):
    return next(iter(iterable))

def gethtml(url):
    import bs4
    r = requests.get(url)
    return bs4.BeautifulSoup(r.text, 'html.parser')

def download_links(arg=None, confirm=True):
    import bs4
    if type(arg) is str:
        if arg.startswith('<'):
            root_url = ''
            html = bs4.BeautifulSoup(arg, 'html.parser')
        else:
            root_url = arg
            html = gethtml(arg)
    else:
        root_url = ''
        html = arg
    if not root_url:
        root_url = input('Root URL: ')
    links = [root_url + el['href'] for el in html.find_all('a')]
    for url in links:
        if confirm:
            print(url)
            if input('Download? [y/n] ') != 'y':
                continue
        if not url.startswith('http'):
            url = os.path.join(root_url, url)
        os.system(f'curl {url} --output {url.split("/")[-1]}')
        