from conf import ks, Optional
from util import log

lg = log.get(__name__)

import db.pics as pics
import db.sets as sets
import db.vecs as vecs
import db.psql as psql
import db.sim as sim
from dto import dto, DtoSets, AutoDbField


def init():
    try:
        lg.info(('-'*25) + 'preinit' + ('-'*25))
        sets.init()
        pics.init()
        vecs.init()
        psql.init()
    except Exception as e:
        raise RuntimeError(f'Database initialization failed: {str(e)}')

def close():
    try:
        sets.close()
        vecs.close()
        lg.info('All database closed')
    except Exception as e:
        lg.error(f'Failed to close database connections: {str(e)}')
        return False

    return True

def resetAllData():
    try:
        pics.clearAll()
        vecs.cleanAll()
        lg.info('[clear] All records cleared')
    except Exception as e:
        lg.error(f'[clear] Failed to clear all records: {str(e)}')
        return False

    return True
