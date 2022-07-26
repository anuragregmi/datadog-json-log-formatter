# datadog-json-log-formatter
JSON Log formatter for python / django for [datadog](https://www.datadoghq.com/)

## Dependencies
  - `ddtrace`
  - `python-json-logger`

## Usage
  Use `log_formatter.DataDogJSONLogFormatter` as your formatter in logging settings.
  
  ```py3
  LOGGING = {
       ...,
      'handlers': {
          'console': {
              'class': 'logging.StreamHandler',
              'formatter': 'json'
          },
      },
      'formatters': {
          'json': {
              '()': 'log_formatter.DataDogJSONLogFormatter',
              'format': '%(timestamp)s %(level)s %(name)s %(message)s'
          }
      },
      'root': {
          'handlers': ['console'],
          'level': 'WARNING',
      },
      ...
   }
  ```
  

## Setup datadog and django for log reporting and error tracking

### Prerequisits
 * Basic setup is done for datadog and APM is enabled. Follow this [blog](https://www.datadoghq.com/blog/monitoring-django-performance/) by datadog.
  
### Seting up proper logging and error tracking 

#### This section solves following problems
- Datadog recording multiline logs as separate log records.
- Log levels not reflected *(All logs in datadog displayed as errors)*
- Error Tracking not triggered

#### Steps
**Use JSON formatter**
Dump logs in JSON format for proper parsing of errors and its attributes (eg. traceback).

1. Install `python-json-logger`
```sh
pip install python-json-logger
```

2. Write your custom JSONFormatter to format logs
```py3
import datetime

from pythonjsonlogger import jsonlogger

class DataDogJSONLogFormatter(jsonlogger.JsonFormatter):
  """JSON Log formatter for datadog"""
  def add_fields(self, log_record, record, message_dict):

      super().add_fields(log_record, record, message_dict)

      if not log_record.get('timestamp'):
          # this doesn't use record.created, so it is slightly off
          now = datetime.datetime.now(
              datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')

          log_record['timestamp'] = now
      if log_record.get('level'):
          log_record['level'] = log_record['level'].upper()
      else:
          log_record['level'] = record.levelname

      if log_record['level'] == 'ERROR':
          # add error details in error key so that it is tracked in error tracking
          error_type = record.exc_info[0].__name__ if record.exc_info else 'UnknownException'

          stack_trace = log_record.get("exc_info")

          log_record["error.stack"] = stack_trace
          log_record["error.type"] = error_type
          log_record["error.msg"] = log_record.get(
              "message", "Error Occurred")

          log_record.pop("exc_info", None)
```

3. Use in settings
```py3
LOGGING = {
     ...,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json'
        },
    },
    'formatters': {
        'json': {
            '()': 'log_formatter.DataDogJSONLogFormatter',
            'format': '%(timestamp)s %(level)s %(name)s %(message)s'
        }
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    ...
 }
```

  Now your logs will be parsed properly in datadog.

4. Enable error tracking
Add following code to `DataDogJSONLogFormatter` to enable error tracking
```py3

...
from ddtrace import tracer
...
        
    
class DataDogJSONLogFormatter(jsonlogger.JsonFormatter):
    
    def add_fields(self, log_record, record, message_dict):
        
        ...

        if log_record['level'] == 'ERROR':
            
            ...
        
            if stack_trace and (root_span := tracer.current_root_span()):
                # https://docs.datadoghq.com/tracing/error_tracking/#how-datadog-error-tracking-works
                # From the docs:
                #
                #   Error spans within a trace are processed by Error Tracking
                #   when they are located in the uppermost service span
                #   which is also called the service entry span. The span must
                #   also contain the `error.stack`, `error.msg`, and `error.type`
                #   span tags in order to be tracked.
                #
                # By default error traces from django are not sent to root span
                # as middlewares does not raise them and error traces are limited
                # to lower spans.
                #
                # Here we set error details to root span so that they are
                # processed by error tracking.

                root_span.set_tag("error.stack", stack_trace)
                root_span.set_tag("error.type", error_type)
                root_span.set_tag("error.msg", log_record["error.msg"])

```
