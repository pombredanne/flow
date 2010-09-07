import sys
import os
from optparse import OptionParser

def makeoptions():
   parser = OptionParser()
   parser.add_option("-d", "--debug",
                     action="store_true",
                     dest="debug",
                     default=False,
                     help="Run server in debug mode")
   parser.add_option("-r", "--rpc",
                     action="store_true",
                     dest="rpcserver",
                     default=False,
                     help="Run rpc server only")
   parser.add_option("-w", "--web",
                       action="store_true",
                       dest="webserver",
                       default=False,
                       help="Run web server only")
   parser.add_option("-p", "--port",
                     type = int,
                     action="store",
                     dest="port",
                     default=0,
                     help="Starting port where running servers")
   return parser


if __name__ == '__main__':
    import environment
    options, args = makeoptions().parse_args()
    base = 'allsettings'
    if options.debug:
        setting_module = 'debug'
    else:
        setting_module = 'release'
    s2 = 'jflow.jfsite.allsettings.%s' % setting_module 
    os.environ['JFLOW_SETTINGS_MODULE']   = s2
    os.environ['STDNET_SETTINGS_MODULE']  = s2
    os.environ['UNUK_SETTINGS_MODULE']    = s2
    os.environ['DJANGO_SETTINGS_MODULE']  = s2
    from jflow.conf import settings
   
    from unuk.contrib.txweb import jsonrpc, djangoapp, start
    from unuk.utils import get_logger
    from jflow.rpc import JFlowRPC

    rpcport = options.port or settings.RPC_SERVER_PORT
    webport = rpcport+1
    webserver, rpcserver = None,None
    try:
        if options.rpcserver:
            rpcserver = jsonrpc.ApplicationServer(JFlowRPC, port = rpcport)
            rpcserver.service.logger.info('Listening on port %s'% rpcport)
        if options.webserver:
            webserver = djangoapp.ApplicationServer(local_dir, port = webport)
            webserver.service.logger.info('Listening on port %s'% webport)
        
        if not (webserver or rpcserver):
            rpcserver = jsonrpc.ApplicationServer(SiroRPC, port = rpcport)
            webserver = djangoapp.ApplicationServer(local_dir, port = webport)
    except Exception, e:
        exit()
    
    start()
    