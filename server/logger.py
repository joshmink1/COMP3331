import logging
import threading

lock = threading.Lock()

def setupLogger(name, logFile, level=logging.INFO):
    """To setup as many loggers as you want"""
    lock.acquire()
    formatter = logging.Formatter('%(message)s') # userlog
    # if (logFile == 'messagelog.txt'):
    #     formatter = logging.Formatter('%(message)s') # messagelog
    
    handler = logging.FileHandler(logFile)        
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    lock.release()
    return logger

# def userLogFormat():
#     string = getUserSeqNum() + '; ' + datetime.now() + '; ' + 
#     return string

def getSeqNum(filename):
    lock.acquire()
    counter = 0
    with open(filename, 'r') as f:
        for line in f:
            counter += 1
    lock.release()
    return str(counter + 1)

def groupLoggerCreator(filename):
    groupchatLogger = setupLogger('groupmessagelog', filename)
    return groupchatLogger