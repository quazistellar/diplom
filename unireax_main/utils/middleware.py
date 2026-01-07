import threading

_thread_locals = threading.local()

def get_current_request():
    """функция возвращает текущий запрос, установленный middleware"""
    return getattr(_thread_locals, 'request', None)

class RequestMiddleware:
    """middleware для сохранения объекта запроса в локальном хранилище потока"""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        try:
            response = self.get_response(request)
            return response
        finally:
            if hasattr(_thread_locals, 'request'):
                del _thread_locals.request