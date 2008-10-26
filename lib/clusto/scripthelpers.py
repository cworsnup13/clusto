
import os
import sys
import clusto
import logging
import commands

from ConfigParser import SafeConfigParser
from optparse import OptionParser, make_option


scriptpaths = [os.path.realpath(os.path.join(os.curdir, 'scripts')),
               '/etc/clusto/scripts',
               '/usr/local/bin',
               '/usr/bin',
               ] #+ filter(lambda x: not x.endswith('.egg'), sys.path)

def listClustoScripts(path):
    """
    Return a list of clusto scripts in the given path.
    """

    if not os.path.exists(path):
        return []

    if os.path.isdir(path):
        dirlist = os.listdir(path)
    else:
        dirlist = [path]

    available = filter(lambda x: x.startswith("clusto-")
                       and not x.endswith('~')
                       and os.access(os.path.join(path,x), os.X_OK),
                       dirlist)

    
    return map(lambda x: os.path.join(path, x), available)

def runcmd(args):
    
    args[0] = 'clusto-' + args[0]
    cmdname = args[0]
    paths = os.environ['PATH'].split(':')

    cmd = None
    for path in paths:
	cmdtest = os.path.join(path, cmdname)
	if os.path.exists(cmdtest):
	    cmd = cmdtest
	    break

    if not cmd:
	raise CommandError(cmdname + " is not a clusto-command.")

    
    os.execvpe(cmdname, args, env=os.environ)


def getCommand(cmdname):

    for path in scriptpaths:

        scripts = listClustoScripts(path)

        for s in scripts:
            if s.split('-')[1].split('.')[0] == cmdname:
                return s


    return None

def getCommandHelp(cmdname):

    fullpath = getCommand(cmdname)

    return commands.getoutput(fullpath + " --help-description")
    
def getClustoConfig(filename=None):
    """Find, parse, and return the configuration data needed by clusto."""

    filesearchpath = ['/etc/clusto/clusto.conf']

    
    filename = filename or os.environ.get('CLUSTOCONFIG')

    if not filename:
        filename = filesearchpath[0]

    if filename:
	if not os.path.exists(os.path.realpath(filename)):
	    raise CmdLineError("Config file %s doesn't exist." % filename)
	
    config = SafeConfigParser()    
    config.read([filename])

    if not config.has_section('clusto'):
	config.add_section('clusto')

    if 'CLUSTODSN' in os.environ:
	config.set('clusto', 'dsn', os.environ['CLUSTODSN'])

    if not config.has_option('clusto', 'dsn'):
	raise CmdLineError("No database given for clusto data.")

    return config


def initScript():
    """
    Initialize the clusto environment for clusto scripts.
    """
    config = getClustoConfig()
    clusto.connect(config.get('clusto', 'dsn'))
    clusto.initclusto()
    
    logger = setupLogging(config)

    return (config, logger)


def setupLogging(config=None):

    logging.basicConfig(level=logging.ERROR)

    return logging.getLogger()


def setupClustoEnv(options):
    """
    Take clusto parameters and put it into the shell environment.
    """


    if options.dsn:
        os.environ['CLUSTODSN'] = options.dsn
    if options.configfile:
        os.environ['CLUSTOCONFIG'] = options.configfile

    if os.environ.has_key('CLUSTOCONFIG'):
        config = getClustoConfig(os.environ['CLUSTOCONFIG'])
    else:
        config = getClustoConfig()

    if not os.environ.has_key('CLUSTODSN'):
        os.environ['CLUSTODSN'] = config.get('clusto','dsn')

    return config

class CmdLineError(Exception):
    pass

class CommandError(Exception):
    pass


class ClustoScript(object):

    usage = "%prog [options]"
    option_list = []
    num_args = None
    num_args_min = 0
    short_description = "sample short descripton"
    
    def __init__(self):
        self.parser = OptionParser(usage=self.usage,
                                   option_list=self.option_list)

        self.parser.add_option("--help-description",
                                action="callback",
                               callback=self._help_description,
                               dest="helpdesc",
                               help="print out the short command description")

        
    

    def _help_description(self, option, opt_str, value, parser, *args, **kwargs):

        print self.short_description
        sys.exit(0)
    


def runscript(scriptclass):

    script = scriptclass()

    (options, argv) = script.parser.parse_args(sys.argv)

    config, logger = initScript()

    try:
        if (script.num_args != None and script.num_args != (len(argv)-1)) or script.num_args_min > (len(argv)-1):
            raise CmdLineError("Wrong number of arguments.")
        
        retval = script.main(argv,
                             options,
                             config=config,
                             log=logger)

    except (CmdLineError, LookupError), msg:
        print msg
        script.parser.print_help()
        return 1

    
    return sys.exit(retval)
