from time import time
from datetime import datetime
import logging
from urllib import response

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging_loki
from pytz import timezone, all_timezones
from pytz.exceptions import UnknownTimeZoneError
from starlette_prometheus import PrometheusMiddleware, metrics

# logging configuration
logging_loki.emitter.LokiEmitter.level_tag = 'level'
handler = logging_loki.LokiHandler(
    url='http://loki:3100/loki/api/v1/push',
    version='1'
)

logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s . %(message)s')
logger = logging.getLogger('uservice')
logger.addHandler(handler)

logger.info('Starting FastAPI application')
app = FastAPI()
app.add_middleware(PrometheusMiddleware)
app.add_route('/metrics', metrics)
logger.info('Waiting for connections.')

@app.middleware('http')
async def add_process_time_header(request: Request, call_next):
    start = time()
    response = await call_next(request)
    process_time = time() - start
    response.headers['X-Process-Time'] = str(process_time)
    return response


@app.get('/api/timezone')
def get_list_of_timezones():
    return all_timezones


@app.get("/api/timezone/{area}/{location}")
def get_timezone(request: Request, area, location):
    logger.info(f'Connection from {request.client.host}.')

    try:
        tz = timezone(f'{area}/{location}')
        now = datetime.now(tz)

        return {
            'client_ip': request.client.host,
            'day_of_week': now.weekday(),
            'day': now.day,
            'month': now.month,
            'year': now.year,
            'hour': now.hour,
            'minute': now.minute,
            'second': now.second,
            'datetime': now.isoformat(),
            'unixtime': int(time()),
            'timezone': tz.zone
        }

    except UnknownTimeZoneError as ex:
        logger.error(f'Unknown timezone "{area}/{location}"')
        return JSONResponse(status_code=404, content={
            'message': f'Unknown timezone "{area}/{location}".'
        })


@app.get('/api/exception')
def exception_example():
    try:
        print('>> start')

        file = open('/root/doesnt.exist', 'r')

        10 / 0

        print('>> end')

    except ZeroDivisionError as ex:
        logger.error('>> it is not possible to divide by zero')
        logger.exception(ex)

    except FileNotFoundError as ex:
        logger.error('Error: File was not found')
        logger.exception(ex)

    except PermissionError as ex:
        logger.error('Error: You dont have permissions to access this file')
        logger.exception(ex)

    except Exception as ex:
        # never happens
        pass


@app.get('/api/healthz')
def check_health():
    return {
        'status': 'up'
    }