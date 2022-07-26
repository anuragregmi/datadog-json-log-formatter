import datetime

from pythonjsonlogger import jsonlogger

from ddtrace import tracer


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

            log_record.pop("exc_info", None)
